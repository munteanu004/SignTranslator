"""
SignRecognizer — loads the trained ST-GCN+Transformer model and runs inference
on MediaPipe keypoint sequences for Romanian Sign Language recognition.
"""
import sys
import os
import json
import torch
import numpy as np

                                                          
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'training'))

from model import SignTranslatorNet

MAX_SEQ_LEN = 150
NUM_JOINTS = 75
JOINT_DIM = 3


class SignRecognizer:
    def __init__(self):
                                                                                 
        dataset_path = os.path.join(
            BASE_DIR, 'ro-sign-language-recognition',
            'datasets', 'processed_dataset', 'dataset.json'
        )
        if os.path.exists(dataset_path):
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.glosses = sorted(set(e['gloss'] for e in data))
        else:
                                                    
            print(f"WARNING: dataset.json not found at {dataset_path}")
            self.glosses = [f'sign_{i}' for i in range(1926)]

        self.num_classes = len(self.glosses)
        print(f"SignRecognizer: {self.num_classes} classes loaded")

                     
        self.device = torch.device('cpu')
        self.model = SignTranslatorNet(
            in_channels=JOINT_DIM,
            num_joints=NUM_JOINTS,
            hidden_dim=256,
            num_classes=self.num_classes,
            gcn_layers=4,
            gcn_dropout=0.1,
            transformer_heads=8,
            transformer_layers=4,
            transformer_dim=256,
            transformer_dropout=0.1,
            transformer_ff_dim=1024,
            num_scales=4,
            max_seq_len=MAX_SEQ_LEN,
        ).to(self.device)

                                                         
        ckpt_path = os.path.join(BASE_DIR, 'models', 'pretrained_best.pth')
        if os.path.exists(ckpt_path):
            ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
            bb = ckpt.get('backbone', ckpt)                                   
            sd = self.model.state_dict()
            loaded = {k: v for k, v in bb.items() if k in sd and sd[k].shape == v.shape}
            sd.update(loaded)
            self.model.load_state_dict(sd, strict=False)
            print(f"SignRecognizer: loaded {len(loaded)}/{len(sd)} weight tensors from {ckpt_path}")
        else:
            print(f"WARNING: No checkpoint at {ckpt_path}, using random weights")

        self.model.eval()

    def preprocess(self, keypoints: np.ndarray) -> tuple:
        """
        Preprocess raw keypoints for model input.

        Args:
            keypoints: (T, 75, 3) array from MediaPipe

        Returns:
            x: (1, 150, 75, 3) tensor
            mask: (1, 150) bool tensor (True = padding)
        """
        T = keypoints.shape[0]
        result = np.zeros((MAX_SEQ_LEN, NUM_JOINTS, JOINT_DIM), dtype=np.float32)

        if T > MAX_SEQ_LEN:
                                 
            indices = np.linspace(0, T - 1, MAX_SEQ_LEN, dtype=int)
            result = keypoints[indices].copy()
            actual_len = MAX_SEQ_LEN
        elif T > 0:
            result[:T] = keypoints[:T]
            actual_len = T
        else:
            actual_len = 0

                                                          
        for t in range(min(actual_len, MAX_SEQ_LEN)):
            frame = result[t]
            valid = np.any(frame != 0, axis=1)                         
            if valid.any():
                center = frame[valid].mean(axis=0)
                result[t] -= center

                                  
        if actual_len > 0:
            valid_data = result[:actual_len]
            max_dist = np.abs(valid_data[:, :, :2]).max()
            if max_dist > 1e-6:
                result[:, :, :2] /= max_dist

                   
        x = torch.from_numpy(result).float().unsqueeze(0)                   

                      
        mask = torch.zeros(1, MAX_SEQ_LEN, dtype=torch.bool)
        if actual_len < MAX_SEQ_LEN:
            mask[0, actual_len:] = True

        return x, mask

    def predict(self, keypoints: np.ndarray, top_k: int = 5) -> list:
        """
        Run inference on keypoint sequence.

        Args:
            keypoints: (T, 75, 3) numpy array
            top_k: number of top predictions to return

        Returns:
            list of {'label': str, 'confidence': float}
        """
        x, mask = self.preprocess(keypoints)
        x = x.to(self.device)
        mask = mask.to(self.device)

        with torch.no_grad():
            try:
                logits = self.model(x, mask)
            except TypeError:
                                                       
                logits = self.model(x)

            probs = torch.softmax(logits, dim=-1)[0]
            topk_probs, topk_indices = probs.topk(min(top_k, self.num_classes))

        results = []
        for prob, idx in zip(topk_probs.tolist(), topk_indices.tolist()):
            results.append({
                'label': self.glosses[idx],
                'confidence': round(prob, 4),
            })

        return results
