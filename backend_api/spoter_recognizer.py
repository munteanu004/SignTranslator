"""
SPOTER-based ASL sign recognizer.
Converts MediaPipe (T, 75, 3) keypoints → SPOTER (T, 54, 2) → English gloss.

MediaPipe layout (75 landmarks):
  [0-32]  pose (33 landmarks)
  [33-53] left hand (21 landmarks)
  [54-74] right hand (21 landmarks)

SPOTER layout (54 landmarks):
  [0-11]  body (12: nose, neck, rightEye, leftEye, rightEar, leftEar,
                    rightShoulder, leftShoulder, rightElbow, leftElbow,
                    rightWrist, leftWrist)
  [12-32] left hand (21 landmarks, reordered)
  [33-53] right hand (21 landmarks, reordered)
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch

from spoter_model import SPOTER

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
WEIGHTS_PATH = MODELS_DIR / "spoter_wlasl100.pth"
LABELS_PATH = MODELS_DIR / "spoter_labels.json"

                                                                            
                                                              
                                                           
                                                      
                                                           
                                                    
                                                                                  
                                                                          
                                                                                 
                                                                          
                                                                             
_HAND_REORDER = [0, 8, 7, 6, 5, 12, 11, 10, 9, 16, 15, 14, 13, 20, 19, 18, 17, 4, 3, 2, 1]

                                                                
_BODY_FROM_POSE = {
    "nose": 0,
    "rightEye": 5,
    "leftEye": 2,
    "rightEar": 8,
    "leftEar": 7,
    "rightShoulder": 12,
    "leftShoulder": 11,
    "rightElbow": 14,
    "leftElbow": 13,
    "rightWrist": 16,
    "leftWrist": 15,
}
                                                                                 
_BODY_ORDER = [
    "nose", "neck", "rightEye", "leftEye", "rightEar", "leftEar",
    "rightShoulder", "leftShoulder", "rightElbow", "leftElbow",
    "rightWrist", "leftWrist",
]


def _mediapipe_to_spoter(keypoints: np.ndarray) -> np.ndarray:
    """
    Convert MediaPipe keypoints (T, 75, 3) → SPOTER format (T, 54, 2).
    Only X and Y are kept (Z is discarded).
    """
    T = keypoints.shape[0]
    out = np.zeros((T, 54, 2), dtype=np.float32)

    pose = keypoints[:, :33, :2]                     
    left_hand = keypoints[:, 33:54, :2]              
    right_hand = keypoints[:, 54:75, :2]             

                                                                               
    for col, name in enumerate(_BODY_ORDER):
        if name == "neck":
                                  
            out[:, col, :] = (pose[:, 11, :] + pose[:, 12, :]) / 2.0
        else:
            out[:, col, :] = pose[:, _BODY_FROM_POSE[name], :]

                                                                               
    out[:, 12:33, :] = left_hand[:, _HAND_REORDER, :]

                                                                               
    out[:, 33:54, :] = right_hand[:, _HAND_REORDER, :]

    return out


def _normalize_body_single(arr: np.ndarray) -> np.ndarray:
    """Bohacek body normalization on (T, 54, 2)."""
    arr = arr.copy()
    T = arr.shape[0]
    BODY_IDX = {name: i for i, name in enumerate(_BODY_ORDER)}
    last_sp = last_ep = None

    for t in range(T):
        ls = arr[t, BODY_IDX["leftShoulder"]]
        rs = arr[t, BODY_IDX["rightShoulder"]]
        nk = arr[t, BODY_IDX["neck"]]
        ns = arr[t, BODY_IDX["nose"]]

        if (ls[0] == 0 or rs[0] == 0) and (nk[0] == 0 or ns[0] == 0):
            if last_sp is None:
                continue
            sp, ep = last_sp, last_ep
        else:
            if ls[0] != 0 and rs[0] != 0:
                head_metric = float(((ls[0]-rs[0])**2 + (ls[1]-rs[1])**2) ** 0.5)
            else:
                head_metric = float(((nk[0]-ns[0])**2 + (nk[1]-ns[1])**2) ** 0.5)
            cx = float(nk[0])
            eye_y = float(arr[t, BODY_IDX["leftEye"]][1])
            sp = [cx - 3*head_metric, eye_y + head_metric]
            ep = [cx + 3*head_metric, sp[1] - 6*head_metric]
            sp[0] = max(sp[0], 0); sp[1] = max(sp[1], 0)
            ep[0] = max(ep[0], 0); ep[1] = max(ep[1], 0)
            last_sp, last_ep = sp, ep

        dx = ep[0] - sp[0]
        dy = sp[1] - ep[1]
        if dx == 0 or dy == 0:
            continue

        for i in range(12):                       
            if arr[t, i, 0] == 0:
                continue
            arr[t, i, 0] = (arr[t, i, 0] - sp[0]) / dx
            arr[t, i, 1] = (arr[t, i, 1] - ep[1]) / dy

    return arr


def _normalize_hand_single(arr: np.ndarray, start_col: int) -> np.ndarray:
    """Normalize hand landmarks in columns [start_col, start_col+21)."""
    arr = arr.copy()
    T = arr.shape[0]
    end_col = start_col + 21

    for t in range(T):
        hand = arr[t, start_col:end_col, :]
        xs = hand[:, 0]
        ys = hand[:, 1]
        nz = xs != 0
        if not nz.any():
            continue
        min_x, max_x = xs[nz].min(), xs[nz].max()
        min_y, max_y = ys[nz].min(), ys[nz].max()
        dx = max_x - min_x or 1.0
        dy = max_y - min_y or 1.0
        for j in range(21):
            if arr[t, start_col + j, 0] == 0:
                continue
            arr[t, start_col + j, 0] = (arr[t, start_col + j, 0] - min_x) / dx
            arr[t, start_col + j, 1] = (arr[t, start_col + j, 1] - min_y) / dy

    return arr


class ASLRecognizer:
    """Loads trained SPOTER model and runs inference on MediaPipe keypoints."""

    def __init__(self):
        if not WEIGHTS_PATH.exists():
            raise FileNotFoundError(
                f"SPOTER weights not found at {WEIGHTS_PATH}.\n"
                "Run  python setup_spoter.py  first (takes ~30-60 min on CPU)."
            )
        if not LABELS_PATH.exists():
            raise FileNotFoundError(
                f"Label mapping not found at {LABELS_PATH}.\n"
                "Run  python setup_spoter.py  first."
            )

        with open(LABELS_PATH) as f:
            raw = json.load(f)
                                             
        self.labels = {int(k): v for k, v in raw.items()}
        num_classes = len(self.labels)

        self.model = SPOTER(num_classes=num_classes, hidden_dim=108)
        self.model.load_state_dict(torch.load(WEIGHTS_PATH, map_location="cpu"))
        self.model.eval()
        logger.info(f"ASL recognizer loaded — {num_classes} classes")

    def predict(self, keypoints: np.ndarray, top_k: int = 5) -> list[dict]:
        """
        keypoints: np.ndarray of shape (T, 75, 3) — MediaPipe output
        Returns list of dicts: [{"label": str, "confidence": float}, ...]
        Returns empty list if insufficient hand data is present.
        """
        if keypoints.shape[1] != 75 or keypoints.shape[2] != 3:
            raise ValueError(f"Expected (T, 75, 3), got {keypoints.shape}")

                                                                        
                                                                           
        hand_kp = keypoints[:, 33:, :]              
        frame_has_hand = np.any(hand_kp != 0, axis=(1, 2))        
        valid_frames = np.where(frame_has_hand)[0]

                                                                              
                                                                               
                                                                              
        MIN_HAND_FRAMES = 15
        if len(valid_frames) < MIN_HAND_FRAMES:
            logger.debug(
                f"Skipping inference: only {len(valid_frames)}/{len(keypoints)} "
                f"frames have hand data (need {MIN_HAND_FRAMES})"
            )
            return []

                                                                
        filtered_kp = keypoints[valid_frames]               

        spoter_kp = _mediapipe_to_spoter(filtered_kp)                      
        spoter_kp = _normalize_body_single(spoter_kp)
        spoter_kp = _normalize_hand_single(spoter_kp, 12)              
        spoter_kp = _normalize_hand_single(spoter_kp, 33)               
        spoter_kp -= 0.5                                                             

        tensor = torch.from_numpy(spoter_kp)               
        with torch.no_grad():
            out = self.model(tensor)                               
            logits = out.squeeze()                            
            probs = torch.softmax(logits, dim=-1).cpu().numpy()

        top_indices = np.argsort(probs)[::-1][:top_k]
        results = []
        for idx in top_indices:
            results.append({
                "label": self.labels.get(int(idx), f"sign_{idx}"),
                "confidence": float(probs[idx]),
            })
        return results


                
_recognizer = None                                 


def get_asl_recognizer() -> ASLRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = ASLRecognizer()
    return _recognizer
