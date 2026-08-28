"""
Recunoastere limbaj semne romanesc.

Metoda principala: ro_sign_10.pth — model GRU antrenat pe 10 semne romanesti (100% val acc).
Fallback: DTW pe keypoints MediaPipe (nu necesita model).
"""

import json
import logging
import math
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

BACKEND_DIR    = Path(__file__).parent
PROJECT_ROOT   = BACKEND_DIR.parent
MODELS_DIR     = PROJECT_ROOT / "models"
MODELS_BACKUP  = PROJECT_ROOT / "models_backup"
RO_DICT_PATH   = PROJECT_ROOT / "integration" / "ro_video_sign_dictionary.json"
RO_SIGN_10_PATH = MODELS_DIR / "ro_sign_10.pth"

TARGET_SIGNS = [
    "stop",
    "ambulanta",
    "casa",
    "a-iubi",
    "telefon",
    "salut",
    "da",
    "nu",
    "multumesc",
    "muzica",
]

T_MODEL = 60                                         


                                                                               
                                                         
                                                                               

def _build_net(n_classes: int = 10):
    import torch.nn as nn
    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(
                nn.Linear(225, 256), nn.ReLU(), nn.Dropout(0.3),
                nn.Linear(256, 128), nn.ReLU(),
            )
            self.gru = nn.GRU(128, 128, 2, batch_first=True,
                              dropout=0.3, bidirectional=True)
            self.cls = nn.Sequential(
                nn.Linear(256, 64), nn.ReLU(), nn.Dropout(0.3),
                nn.Linear(64, n_classes),
            )
        def forward(self, x):
            B, T, J, C = x.shape
            x = self.enc(x.view(B, T, J * C))
            x, _ = self.gru(x)
            return self.cls(x.mean(1))
    return Net()


                                                                               
                            
                                                                               

def _try_load_ro_sign_10():
    """Returneaza (model, sign_to_idx, target_signs, T) sau None."""
    if not RO_SIGN_10_PATH.exists():
        logger.warning(f"ro_sign_10.pth negasit la {RO_SIGN_10_PATH}")
        return None
    try:
        import torch
        ckpt = torch.load(str(RO_SIGN_10_PATH), map_location="cpu", weights_only=False)
        sign_to_idx  = ckpt["sign_to_idx"]
        target_signs = ckpt["target_signs"]
        T            = ckpt.get("T", T_MODEL)

        model = _build_net(n_classes=len(target_signs))
        model.load_state_dict(ckpt["model_state"])
        model.eval()

        logger.info(f"ro_sign_10 incarcat: {len(target_signs)} semne, T={T}")
        return model, sign_to_idx, target_signs, T
    except Exception as e:
        logger.warning(f"Eroare la incarcarea ro_sign_10: {e}")
        return None


def _predict_ro_sign_10(model, sign_to_idx, target_signs, T,
                        keypoints: np.ndarray, top_k: int) -> list:
    import torch
    import torch.nn.functional as F

    kp = keypoints.astype(np.float32)                   
    n = len(kp)
    if n >= T:
        kp = kp[:T]
    else:
        pad = np.zeros((T - n, 75, 3), dtype=np.float32)
        kp = np.concatenate([kp, pad], axis=0)

    x = torch.from_numpy(kp).unsqueeze(0)                 
    with torch.no_grad():
        logits = model(x).squeeze(0)                     
        probs  = F.softmax(logits, dim=0).cpu().numpy()

    results = [
        {"semn": sign, "incredere": float(probs[i])}
        for sign, i in sign_to_idx.items()
    ]
    results.sort(key=lambda r: r["incredere"], reverse=True)
    return results[:top_k]


                                                                               
              
                                                                               

def _normalize_hand_frame(hand: np.ndarray) -> np.ndarray:
    xy = hand[:, :2].copy()
    wrist = xy[0]
    xy -= wrist
    scale = np.linalg.norm(xy[1:], axis=1).max()
    if scale > 1e-6:
        xy /= scale
    return xy.flatten()


def _extract_features(joints: np.ndarray) -> np.ndarray:
    T = joints.shape[0]
    feats = []
    for t in range(T):
        frame = joints[t]
        lh    = frame[33:54, :]
        rh    = frame[54:75, :]
        pose  = frame[:33, :]

        lh_feat = np.zeros(42, dtype=np.float32) if not np.any(lh[:, :2] != 0)\
                  else _normalize_hand_frame(lh).astype(np.float32)
        rh_feat = np.zeros(42, dtype=np.float32) if not np.any(rh[:, :2] != 0)\
                  else _normalize_hand_frame(rh).astype(np.float32)

        ls, rs = pose[11, :2], pose[12, :2]
        lw, rw = pose[15, :2], pose[16, :2]
        center = (ls + rs) / 2.0
        sw = max(np.linalg.norm(rs - ls), 1e-6)
        wrist_feat = np.concatenate([(lw - center) / sw,
                                     (rw - center) / sw]).astype(np.float32)
        feats.append(np.concatenate([lh_feat, rh_feat, wrist_feat]))
    return np.array(feats, dtype=np.float32)


def _subsample(seq: np.ndarray, target: int = 30) -> np.ndarray:
    T = len(seq)
    if T == target:
        return seq
    indices = np.linspace(0, T - 1, target)
    result  = np.zeros((target, seq.shape[1]), dtype=np.float32)
    for i, idx in enumerate(indices):
        lo = int(idx)
        hi = min(lo + 1, T - 1)
        alpha = idx - lo
        result[i] = (1 - alpha) * seq[lo] + alpha * seq[hi]
    return result


def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    T1, T2 = len(a), len(b)
    window = max(abs(T1 - T2), int(0.2 * max(T1, T2)))
    INF = float('inf')
    dp = np.full((T1 + 1, T2 + 1), INF, dtype=np.float64)
    dp[0, 0] = 0.0
    for i in range(1, T1 + 1):
        for j in range(max(1, i - window), min(T2, i + window) + 1):
            cost = float(np.linalg.norm(a[i-1] - b[j-1]))
            dp[i, j] = cost + min(dp[i-1, j], dp[i, j-1], dp[i-1, j-1])
    return float(dp[T1, T2])


                                                                               
                                   
                                                                               

def _disambiguate_salut_multumesc(results: list, kp: np.ndarray) -> list:
    """
    Salut: mana la nivelul fruntii/urechii (Y mic, sus).
    Multumesc: mana la nivelul barbiei (Y mare, jos, sub nas).
    In coordonate MediaPipe normalizate Y creste in jos.
    """
    top_signs = {r["semn"] for r in results[:2]}
    if "salut" not in top_signs and "multumesc" not in top_signs:
        return results

                                                                         
                                    
    rw_y_vals, nose_y_vals = [], []
    for frame in kp:
        nose_y = frame[0, 1]            
        rw_y   = frame[16, 1]                                
        if nose_y > 0 and rw_y > 0:
            nose_y_vals.append(nose_y)
            rw_y_vals.append(rw_y)

    if not rw_y_vals:
        return results

    avg_rw_y   = float(np.mean(rw_y_vals))
    avg_nose_y = float(np.mean(nose_y_vals))

                                                             
    hand_above_nose = avg_rw_y < avg_nose_y

    boosted = []
    for r in results:
        conf = r["incredere"]
        if r["semn"] == "salut":
            conf = conf * 1.5 if hand_above_nose else conf * 0.4
        elif r["semn"] == "multumesc":
            conf = conf * 1.5 if not hand_above_nose else conf * 0.4
        boosted.append({"semn": r["semn"], "incredere": conf})

                    
    total = sum(r["incredere"] for r in boosted) or 1.0
    for r in boosted:
        r["incredere"] /= total

    boosted.sort(key=lambda r: r["incredere"], reverse=True)
    return boosted


                                                                               
                  
                                                                               

class RoRecognizer:
    def __init__(self):
        self._model_data  = None
        self._templates: dict = {}

        result = _try_load_ro_sign_10()
        if result is not None:
            self._model_data = result
            logger.info("Recunoastere RO: model ro_sign_10 activ")
        else:
            self._build_templates()
            logger.info("Recunoastere RO: fallback DTW activ")

    @property
    def finetuned(self) -> bool:
        return self._model_data is not None

    def _load_npz_sequences(self, sign: str) -> list:
        if not RO_DICT_PATH.exists():
            return []
        try:
            with open(RO_DICT_PATH, "r", encoding="utf-8") as f:
                ro_dict = json.load(f)
        except Exception:
            return []
        entry = ro_dict.get(sign)
        if not entry:
            return []
        paths = entry.get("all_instances", [entry.get("npz_file")])
        sequences = []
        for p in paths:
            if not p or not Path(p).exists():
                continue
            try:
                data = np.load(p, allow_pickle=True)
                sequences.append(data["joints"].astype(np.float32))
            except Exception:
                pass
        return sequences

    def _build_templates(self):
        for sign in TARGET_SIGNS:
            sequences = self._load_npz_sequences(sign)
            if not sequences:
                continue
            self._templates[sign] = [
                _subsample(_extract_features(seq), 30) for seq in sequences
            ]

    def predict(self, keypoints: np.ndarray, top_k: int = 5) -> list:
        if keypoints.ndim != 3 or keypoints.shape[1:] != (75, 3):
            raise ValueError(f"Asteptat (T,75,3), primit {keypoints.shape}")

        hand_kp = keypoints[:, 33:, :]
        valid   = np.where(np.any(hand_kp != 0, axis=(1, 2)))[0]
        if len(valid) < 8:
            return []
        kp = keypoints[valid]

        if self._model_data is not None:
            model, sign_to_idx, target_signs, T = self._model_data
            results = _predict_ro_sign_10(model, sign_to_idx, target_signs, T, kp, top_k)
            return _disambiguate_salut_multumesc(results, kp)

        return self._predict_dtw(kp, top_k)

    def _predict_dtw(self, kp: np.ndarray, top_k: int) -> list:
        query = _subsample(_extract_features(kp), 30)
        scores = {sign: min(_dtw_distance(query, tmpl) for tmpl in tmpls)
                  for sign, tmpls in self._templates.items()}
        sorted_signs = sorted(scores.items(), key=lambda x: x[1])
        dist_vals = np.array([s for _, s in sorted_signs], dtype=np.float64)
        inv = 1.0 / (dist_vals + 1e-6)
        exp_inv = np.exp((inv - inv.max()) * 3.0)
        confs = exp_inv / exp_inv.sum()
        return [{"semn": sign, "incredere": float(confs[i])}
                for i, (sign, _) in enumerate(sorted_signs[:top_k])]


_ro_recognizer: Optional[RoRecognizer] = None


def get_ro_recognizer() -> RoRecognizer:
    global _ro_recognizer
    if _ro_recognizer is None:
        _ro_recognizer = RoRecognizer()
    return _ro_recognizer
