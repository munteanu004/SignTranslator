"""
Dataset loaders pentru SignTranslator.

1. How2SignDataset — incarca pkl-uri How2Sign pentru pre-antrenare
2. RomanianSignDataset — incarca videouri romanesti cu MediaPipe pentru fine-tuning
3. Augmentari de date pentru robustete
"""
import json
import os
import io
import pickle
import random
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader


# =============================================================================
# AUGMENTARI
# =============================================================================

class SignAugmentation:
    """Augmentari specifice pentru limbajul semnelor."""

    def __init__(self, training: bool = True):
        self.training = training

    def __call__(self, joints: np.ndarray, vis: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        joints: (T, J, C)
        vis: (T, J)
        """
        if not self.training:
            return joints, vis

        # Flip orizontal (cu 50% sansa)
        if random.random() < 0.5:
            joints = self._horizontal_flip(joints)

        # Scalare aleatoare
        if random.random() < 0.7:
            scale = random.uniform(0.8, 1.2)
            joints[:, :, :2] *= scale

        # Rotatie mica (-15, +15 grade)
        if random.random() < 0.5:
            angle = random.uniform(-15, 15)
            joints = self._rotate(joints, angle)

        # Translatie aleatoare
        if random.random() < 0.5:
            tx = random.uniform(-0.1, 0.1)
            ty = random.uniform(-0.1, 0.1)
            joints[:, :, 0] += tx
            joints[:, :, 1] += ty

        # Zgomot gaussian
        if random.random() < 0.5:
            noise = np.random.randn(*joints.shape).astype(np.float32) * 0.01
            joints = joints + noise

        # Drop temporal (sterge frame-uri aleatorii)
        if random.random() < 0.3:
            joints, vis = self._temporal_drop(joints, vis, drop_ratio=0.1)

        # Joint dropout (ascunde articulatii aleatorii)
        if random.random() < 0.3:
            joints, vis = self._joint_dropout(joints, vis, drop_prob=0.05)

        return joints, vis

    def _horizontal_flip(self, joints: np.ndarray) -> np.ndarray:
        """Oglindire orizontala cu swap stanga-dreapta."""
        joints = joints.copy()
        # Inverseaza X
        joints[:, :, 0] = -joints[:, :, 0]

        # Swap perechi stanga-dreapta (MediaPipe Pose)
        swap_pairs_pose = [
            (1, 4), (2, 5), (3, 6), (7, 8), (9, 10),
            (11, 12), (13, 14), (15, 16), (17, 18), (19, 20),
            (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)
        ]
        for (a, b) in swap_pairs_pose:
            joints[:, [a, b]] = joints[:, [b, a]]

        # Swap left hand (33-53) cu right hand (54-74)
        left_hand = joints[:, 33:54].copy()
        joints[:, 33:54] = joints[:, 54:75]
        joints[:, 54:75] = left_hand

        return joints

    def _rotate(self, joints: np.ndarray, angle_deg: float) -> np.ndarray:
        """Rotatie 2D in jurul centrului."""
        joints = joints.copy()
        rad = np.deg2rad(angle_deg)
        cos_a, sin_a = np.cos(rad), np.sin(rad)

        # Centrul scheletului (media articulatiilor vizibile)
        cx = np.nanmean(joints[:, :, 0])
        cy = np.nanmean(joints[:, :, 1])

        x = joints[:, :, 0] - cx
        y = joints[:, :, 1] - cy
        joints[:, :, 0] = x * cos_a - y * sin_a + cx
        joints[:, :, 1] = x * sin_a + y * cos_a + cy

        return joints

    def _temporal_drop(self, joints: np.ndarray, vis: np.ndarray,
                       drop_ratio: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """Sterge frame-uri aleatoare."""
        T = joints.shape[0]
        num_drop = max(1, int(T * drop_ratio))
        keep_idx = sorted(random.sample(range(T), T - num_drop))
        if len(keep_idx) < 2:
            return joints, vis
        return joints[keep_idx], vis[keep_idx]

    def _joint_dropout(self, joints: np.ndarray, vis: np.ndarray,
                       drop_prob: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
        """Ascunde articulatii aleatorii (pune la 0)."""
        joints = joints.copy()
        vis = vis.copy()
        mask = np.random.rand(*vis.shape) < drop_prob
        joints[mask] = 0.0
        vis[mask] = 0
        return joints, vis


# =============================================================================
# HOW2SIGN DATASET — pentru pre-antrenare
# =============================================================================

class CpuUnpickler(pickle.Unpickler):
    """Unpickler care mapeaza tensorii CUDA pe CPU."""
    def find_class(self, module, name):
        if module == 'torch.storage' and name == '_load_from_bytes':
            return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
        return super().find_class(module, name)


class How2SignDataset(Dataset):
    """
    Dataset How2Sign — incarca pkl-uri cu keypoints 3D.
    Folosit pentru pre-antrenare cu self-supervised learning.
    """

    def __init__(self, pkl_dir: str, max_seq_len: int = 150,
                 num_joints: int = 75, max_pkls: Optional[int] = None,
                 augment: bool = True):
        super().__init__()
        self.pkl_dir = pkl_dir
        self.max_seq_len = max_seq_len
        self.num_joints = num_joints
        self.augmentation = SignAugmentation(training=augment)

        # Gaseste toate pkl-urile
        pkl_files = sorted([f for f in os.listdir(pkl_dir) if f.endswith('.pkl')])
        if max_pkls is not None:
            pkl_files = pkl_files[:max_pkls]
        self.pkl_files = pkl_files

        print(f"How2SignDataset: {len(self.pkl_files)} secvente din {pkl_dir}")

    def __len__(self) -> int:
        return len(self.pkl_files)

    def _load_pkl(self, path: str) -> dict:
        """Incarca pkl in mod sigur (gestioneaza tensori CUDA)."""
        try:
            data = torch.load(path, map_location='cpu', weights_only=False)
        except Exception:
            with open(path, 'rb') as f:
                data = CpuUnpickler(f).load()
        return data

    def _extract_joints(self, data) -> Optional[np.ndarray]:
        """Extrage joints3d din structura pkl. Returneaza (T, J, 3) sau None."""
        if isinstance(data, dict):
            for key in ['joints3d', 'joints', 'body_joints', 'keypoints3d',
                        'pred_joints', 'smpl_joints', 'body_pose_results']:
                if key in data:
                    val = data[key]
                    if isinstance(val, torch.Tensor):
                        val = val.cpu().numpy()
                    if isinstance(val, np.ndarray):
                        if val.ndim == 3 and val.shape[-1] == 3:
                            return val.astype(np.float32)
                        if val.ndim == 2 and val.shape[-1] == 3:
                            return val[np.newaxis].astype(np.float32)
            # Cauta recursiv
            for key, val in data.items():
                if isinstance(val, dict):
                    result = self._extract_joints(val)
                    if result is not None:
                        return result
                elif isinstance(val, (torch.Tensor, np.ndarray)):
                    if isinstance(val, torch.Tensor):
                        val = val.cpu().numpy()
                    if val.ndim == 3 and val.shape[-1] == 3 and val.shape[1] > 10:
                        return val.astype(np.float32)
        elif isinstance(data, (torch.Tensor, np.ndarray)):
            if isinstance(data, torch.Tensor):
                data = data.cpu().numpy()
            if data.ndim == 3 and data.shape[-1] == 3:
                return data.astype(np.float32)
        return None

    def _pad_or_crop_joints(self, joints: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Ajusteaza numarul de joints si lungimea secventei.
        joints: (T, J_orig, 3)
        return: (max_seq_len, num_joints, 3), vis (max_seq_len, num_joints)
        """
        T, J_orig, C = joints.shape

        # Ajusteaza numarul de joints
        if J_orig >= self.num_joints:
            joints = joints[:, :self.num_joints, :]
        else:
            # Pad cu zerouri
            pad = np.zeros((T, self.num_joints - J_orig, C), dtype=np.float32)
            joints = np.concatenate([joints, pad], axis=1)

        # Vizibilitate: 1 pentru articulatiile reale, 0 pentru padding
        vis = np.ones((T, self.num_joints), dtype=np.float32)
        if J_orig < self.num_joints:
            vis[:, J_orig:] = 0.0

        # Ajusteaza lungimea temporala
        if T > self.max_seq_len:
            # Subsamplare uniforma
            indices = np.linspace(0, T - 1, self.max_seq_len, dtype=int)
            joints = joints[indices]
            vis = vis[indices]
        elif T < self.max_seq_len:
            # Pad temporal cu zerouri
            pad_t = np.zeros((self.max_seq_len - T, self.num_joints, C), dtype=np.float32)
            joints = np.concatenate([joints, pad_t], axis=0)
            pad_vis = np.zeros((self.max_seq_len - T, self.num_joints), dtype=np.float32)
            vis = np.concatenate([vis, pad_vis], axis=0)

        return joints, vis

    def _normalize(self, joints: np.ndarray, vis: np.ndarray) -> np.ndarray:
        """Normalizare: centreaza si scaleaza scheletul."""
        # Centreaza pe articulatia 0 (nas/cap) sau media
        valid_mask = vis > 0.5  # (T, J)
        if valid_mask.any():
            # Media articulatiilor vizibile per frame
            for t in range(joints.shape[0]):
                if valid_mask[t].any():
                    center = joints[t, valid_mask[t]].mean(axis=0)
                    joints[t] -= center

            # Scaleaza la [-1, 1] bazat pe distanta maxima
            valid_joints = joints[valid_mask.any(axis=1)]
            if len(valid_joints) > 0:
                max_dist = np.abs(valid_joints[:, :, :2]).max()
                if max_dist > 1e-6:
                    joints[:, :, :2] /= max_dist

        return joints

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        pkl_path = os.path.join(self.pkl_dir, self.pkl_files[idx])

        try:
            data = self._load_pkl(pkl_path)
            joints = self._extract_joints(data)
        except Exception:
            joints = None

        if joints is None:
            # Returneaza zerouri ca fallback
            joints = np.zeros((self.max_seq_len, self.num_joints, 3), dtype=np.float32)
            vis = np.zeros((self.max_seq_len, self.num_joints), dtype=np.float32)
            mask = torch.ones(self.max_seq_len, dtype=torch.bool)
            return {
                'joints': torch.from_numpy(joints),
                'vis': torch.from_numpy(vis),
                'mask': mask,
                'label': torch.tensor(-1, dtype=torch.long)
            }

        T_orig = joints.shape[0]

        # Augmentare INAINTE de padding (temporal drop schimba lungimea)
        joints_vis = np.ones((joints.shape[0], joints.shape[1]), dtype=np.float32)
        if joints.shape[1] < self.num_joints:
            joints_vis[:, joints.shape[1]:] = 0.0
        joints, joints_vis = self.augmentation(joints, joints_vis)
        T_orig = min(T_orig, joints.shape[0])

        joints, vis = self._pad_or_crop_joints(joints)

        # Normalizare
        joints = self._normalize(joints, vis)

        # Mask: True = padding
        mask = torch.zeros(self.max_seq_len, dtype=torch.bool)
        if T_orig < self.max_seq_len:
            mask[T_orig:] = True

        return {
            'joints': torch.from_numpy(joints).float(),
            'vis': torch.from_numpy(vis).float(),
            'mask': mask,
            'label': torch.tensor(-1, dtype=torch.long)  # No label for pretrain
        }


# =============================================================================
# ROMANIAN SIGN DATASET — pentru fine-tuning
# =============================================================================

class RomanianSignDataset(Dataset):
    """
    Dataset romanesc — extrage keypoints din videouri cu MediaPipe.
    Folosit pentru fine-tuning cu clasificare de glosuri.
    """

    def __init__(self, dataset_json: str, videos_dir: str,
                 max_seq_len: int = 150, num_joints: int = 75,
                 split: str = 'train', augment: bool = True,
                 cache_dir: Optional[str] = None):
        super().__init__()
        self.videos_dir = videos_dir
        self.max_seq_len = max_seq_len
        self.num_joints = num_joints
        self.augmentation = SignAugmentation(training=augment and split == 'train')
        self.cache_dir = cache_dir

        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

        # Incarca dataset.json
        with open(dataset_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Construieste mapare gloss -> index
        self.glosses = sorted(set(entry['gloss'] for entry in data))
        self.gloss_to_idx = {g: i for i, g in enumerate(self.glosses)}
        self.num_classes = len(self.glosses)

        # Colecteaza instante pentru split-ul dorit
        self.samples = []
        for entry in data:
            gloss = entry['gloss']
            label = self.gloss_to_idx[gloss]
            for inst in entry['instances']:
                if inst['split'] == split:
                    video_id = inst['video_id']
                    video_path = os.path.join(videos_dir, f"{video_id}.mp4")
                    if os.path.exists(video_path):
                        self.samples.append({
                            'video_path': video_path,
                            'video_id': video_id,
                            'gloss': gloss,
                            'label': label
                        })

        print(f"RomanianSignDataset [{split}]: {len(self.samples)} instante, "
              f"{self.num_classes} clase")

    def __len__(self) -> int:
        return len(self.samples)

    def _extract_keypoints_mediapipe(self, video_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extrage keypoints din video cu MediaPipe Holistic.
        Returneaza (T, 75, 3) si (T, 75).
        """
        import mediapipe as mp
        mp_holistic = mp.solutions.holistic

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return np.zeros((1, self.num_joints, 3), dtype=np.float32), \
                   np.zeros((1, self.num_joints), dtype=np.float32)

        all_joints = []
        all_vis = []

        with mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as holistic:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = holistic.process(rgb)

                joints = np.zeros((self.num_joints, 3), dtype=np.float32)
                vis = np.zeros(self.num_joints, dtype=np.float32)

                # Pose (0-32)
                if results.pose_landmarks:
                    for j, lm in enumerate(results.pose_landmarks.landmark):
                        if j < 33:
                            joints[j] = [lm.x, lm.y, lm.z]
                            vis[j] = 1.0 if lm.visibility > 0.5 else 0.0

                # Left hand (33-53)
                if results.left_hand_landmarks:
                    for j, lm in enumerate(results.left_hand_landmarks.landmark):
                        if j < 21:
                            joints[33 + j] = [lm.x, lm.y, lm.z]
                            vis[33 + j] = 1.0

                # Right hand (54-74)
                if results.right_hand_landmarks:
                    for j, lm in enumerate(results.right_hand_landmarks.landmark):
                        if j < 21:
                            joints[54 + j] = [lm.x, lm.y, lm.z]
                            vis[54 + j] = 1.0

                all_joints.append(joints)
                all_vis.append(vis)

        cap.release()

        if not all_joints:
            return np.zeros((1, self.num_joints, 3), dtype=np.float32), \
                   np.zeros((1, self.num_joints), dtype=np.float32)

        return np.array(all_joints, dtype=np.float32), np.array(all_vis, dtype=np.float32)

    def _get_cached_or_extract(self, video_path: str, video_id: str) -> Tuple[np.ndarray, np.ndarray]:
        """Foloseste cache daca exista, altfel extrage cu MediaPipe."""
        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, f"{video_id}.npz")
            if os.path.exists(cache_path):
                data = np.load(cache_path)
                return data['joints'], data['vis']

        joints, vis = self._extract_keypoints_mediapipe(video_path)

        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, f"{video_id}.npz")
            np.savez_compressed(cache_path, joints=joints, vis=vis)

        return joints, vis

    def _pad_or_crop(self, joints: np.ndarray, vis: np.ndarray) -> Tuple[np.ndarray, np.ndarray, int]:
        """Ajusteaza la max_seq_len. Returneaza si lungimea originala."""
        T = joints.shape[0]
        T_orig = T

        if T > self.max_seq_len:
            indices = np.linspace(0, T - 1, self.max_seq_len, dtype=int)
            joints = joints[indices]
            vis = vis[indices]
        elif T < self.max_seq_len:
            pad_j = np.zeros((self.max_seq_len - T, self.num_joints, 3), dtype=np.float32)
            joints = np.concatenate([joints, pad_j], axis=0)
            pad_v = np.zeros((self.max_seq_len - T, self.num_joints), dtype=np.float32)
            vis = np.concatenate([vis, pad_v], axis=0)

        return joints, vis, T_orig

    def _normalize(self, joints: np.ndarray, vis: np.ndarray) -> np.ndarray:
        """Normalizare identica cu How2Sign."""
        valid_mask = vis > 0.5
        if valid_mask.any():
            for t in range(joints.shape[0]):
                if valid_mask[t].any():
                    center = joints[t, valid_mask[t]].mean(axis=0)
                    joints[t] -= center
            valid_joints = joints[valid_mask.any(axis=1)]
            if len(valid_joints) > 0:
                max_dist = np.abs(valid_joints[:, :, :2]).max()
                if max_dist > 1e-6:
                    joints[:, :, :2] /= max_dist
        return joints

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]

        joints, vis = self._get_cached_or_extract(
            sample['video_path'], sample['video_id']
        )

        joints, vis, T_orig = self._pad_or_crop(joints, vis)
        joints, vis = self.augmentation(joints, vis)
        joints = self._normalize(joints, vis)

        mask = torch.zeros(self.max_seq_len, dtype=torch.bool)
        if T_orig < self.max_seq_len:
            mask[T_orig:] = True

        return {
            'joints': torch.from_numpy(joints).float(),
            'vis': torch.from_numpy(vis).float(),
            'mask': mask,
            'label': torch.tensor(sample['label'], dtype=torch.long)
        }


# =============================================================================
# CACHE ALL — pre-proceseaza toate videourile o singura data
# =============================================================================

def cache_all_videos(dataset_json: str, videos_dir: str, cache_dir: str,
                     num_joints: int = 75):
    """
    Pre-proceseaza TOATE videourile si salveaza keypoints in cache.
    Ruleaza asta o singura data inainte de antrenare!
    """
    from tqdm import tqdm

    os.makedirs(cache_dir, exist_ok=True)

    with open(dataset_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Colecteaza toate video_id-urile
    all_videos = set()
    for entry in data:
        for inst in entry['instances']:
            video_path = os.path.join(videos_dir, f"{inst['video_id']}.mp4")
            if os.path.exists(video_path):
                all_videos.add((inst['video_id'], video_path))

    print(f"Total videouri de procesat: {len(all_videos)}")

    # Dummy dataset pentru extragere
    import mediapipe as mp
    mp_holistic = mp.solutions.holistic

    processed = 0
    skipped = 0

    for video_id, video_path in tqdm(all_videos, desc="Cache keypoints"):
        cache_path = os.path.join(cache_dir, f"{video_id}.npz")
        if os.path.exists(cache_path):
            skipped += 1
            continue

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                skipped += 1
                continue

            all_joints = []
            all_vis = []

            with mp_holistic.Holistic(
                static_image_mode=False,
                model_complexity=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            ) as holistic:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = holistic.process(rgb)

                    joints = np.zeros((num_joints, 3), dtype=np.float32)
                    vis = np.zeros(num_joints, dtype=np.float32)

                    if results.pose_landmarks:
                        for j, lm in enumerate(results.pose_landmarks.landmark):
                            if j < 33:
                                joints[j] = [lm.x, lm.y, lm.z]
                                vis[j] = 1.0 if lm.visibility > 0.5 else 0.0
                    if results.left_hand_landmarks:
                        for j, lm in enumerate(results.left_hand_landmarks.landmark):
                            if j < 21:
                                joints[33 + j] = [lm.x, lm.y, lm.z]
                                vis[33 + j] = 1.0
                    if results.right_hand_landmarks:
                        for j, lm in enumerate(results.right_hand_landmarks.landmark):
                            if j < 21:
                                joints[54 + j] = [lm.x, lm.y, lm.z]
                                vis[54 + j] = 1.0

                    all_joints.append(joints)
                    all_vis.append(vis)

            cap.release()

            if all_joints:
                np.savez_compressed(
                    cache_path,
                    joints=np.array(all_joints, dtype=np.float32),
                    vis=np.array(all_vis, dtype=np.float32)
                )
                processed += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"Eroare la {video_id}: {e}")
            skipped += 1

    print(f"Gata! Procesate: {processed}, Sarite: {skipped}, Deja in cache: {len(all_videos) - processed - skipped}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pre-proceseaza videourile romanesti')
    parser.add_argument('--dataset_json', type=str, required=True)
    parser.add_argument('--videos_dir', type=str, required=True)
    parser.add_argument('--cache_dir', type=str, default='data/ro_cache')
    args = parser.parse_args()

    cache_all_videos(args.dataset_json, args.videos_dir, args.cache_dir)
