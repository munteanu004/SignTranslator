"""
One-time setup: downloads WLASL100 skeletal data and trains SPOTER.
Run once from backend_api/ directory:
    python setup_spoter.py

Output: models/spoter_wlasl100.pth  +  models/spoter_labels.json
Training time: ~30-60 minutes on CPU.
"""

import os
import sys
import ast
import json
import random
import logging
import urllib.request

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

from spoter_model import SPOTER

                                                                               
MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "spoter_data"
MODELS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

TRAIN_CSV = DATA_DIR / "WLASL100_train_25fps.csv"
VAL_CSV = DATA_DIR / "WLASL100_val_25fps.csv"
WEIGHTS_OUT = MODELS_DIR / "spoter_wlasl100.pth"
LABELS_OUT = MODELS_DIR / "spoter_labels.json"

TRAIN_URL = "https://github.com/maty-bohacek/spoter/releases/download/supplementary-data/WLASL100_train_25fps.csv"
VAL_URL = "https://github.com/maty-bohacek/spoter/releases/download/supplementary-data/WLASL100_val_25fps.csv"

                                         
                                                                              
                                                              
                                                                                 
WLASL_KNOWN_GLOSSES = {
    0: "book", 1: "drink", 2: "computer", 3: "before", 4: "chair",
    5: "go", 6: "clothes", 7: "who", 8: "candy", 9: "cousin",
    10: "deaf", 11: "different", 12: "fine", 13: "finish", 14: "help",
    15: "house", 16: "like", 17: "man", 18: "many", 19: "mother",
    20: "name", 21: "need", 22: "no", 23: "pay", 24: "pizza",
    25: "play", 26: "school", 27: "sorry", 28: "student", 29: "teach",
    30: "thank", 31: "walk", 32: "what", 33: "when", 34: "where",
    35: "who", 36: "why", 37: "woman", 38: "yes", 39: "you",
    40: "yourself", 41: "about", 42: "again", 43: "age", 44: "all",
    45: "any", 46: "cool", 47: "dark", 48: "dog", 49: "eat",
    50: "father", 51: "food", 52: "girl", 53: "good", 54: "hello",
    55: "here", 56: "home", 57: "hot", 58: "know", 59: "later",
    60: "learn", 61: "live", 62: "love", 63: "more", 64: "never",
    65: "now", 66: "old", 67: "please", 68: "read", 69: "right",
    70: "see", 71: "sister", 72: "soon", 73: "stop", 74: "study",
    75: "tell", 76: "think", 77: "time", 78: "understand", 79: "wait",
    80: "want", 81: "watch", 82: "with", 83: "work", 84: "write",
    85: "yesterday", 86: "another", 87: "bird", 88: "black", 89: "blue",
    90: "brother", 91: "buy", 92: "clean", 93: "come", 94: "day",
    95: "decide", 96: "do", 97: "easy", 98: "enough", 99: "family",
}

                                                                               
BODY_IDENTIFIERS = [
    "nose", "neck", "rightEye", "leftEye", "rightEar", "leftEar",
    "rightShoulder", "leftShoulder", "rightElbow", "leftElbow",
    "rightWrist", "leftWrist",
]
HAND_IDENTIFIERS_BASE = [
    "wrist", "indexTip", "indexDIP", "indexPIP", "indexMCP",
    "middleTip", "middleDIP", "middlePIP", "middleMCP",
    "ringTip", "ringDIP", "ringPIP", "ringMCP",
    "littleTip", "littleDIP", "littlePIP", "littleMCP",
    "thumbTip", "thumbIP", "thumbMP", "thumbCMC",
]
HAND_IDENTIFIERS = (
    [h + "_0" for h in HAND_IDENTIFIERS_BASE] +
    [h + "_1" for h in HAND_IDENTIFIERS_BASE]
)
ALL_IDENTIFIERS = BODY_IDENTIFIERS + HAND_IDENTIFIERS            


                                                                               

def _normalize_body(row: dict) -> dict:
    seq_len = len(row["leftEar"])
    last_sp, last_ep = None, None
    for i in range(seq_len):
        ls, rs = row["leftShoulder"][i], row["rightShoulder"][i]
        nk, ns = row["neck"][i], row["nose"][i]
        if (ls[0] == 0 or rs[0] == 0) and (nk[0] == 0 or ns[0] == 0):
            if last_sp is None:
                continue
            sp, ep = last_sp, last_ep
        else:
            if ls[0] != 0 and rs[0] != 0:
                head_metric = ((ls[0]-rs[0])**2 + (ls[1]-rs[1])**2) ** 0.5
            else:
                head_metric = ((nk[0]-ns[0])**2 + (nk[1]-ns[1])**2) ** 0.5
            cx = row["neck"][i][0]
            sp = [cx - 3*head_metric, row["leftEye"][i][1] + head_metric]
            ep = [cx + 3*head_metric, sp[1] - 6*head_metric]
            sp[0] = max(sp[0], 0); sp[1] = max(sp[1], 0)
            ep[0] = max(ep[0], 0); ep[1] = max(ep[1], 0)
            last_sp, last_ep = sp, ep

        dx = ep[0] - sp[0]
        dy = sp[1] - ep[1]
        if dx == 0 or dy == 0:
            continue
        for ident in BODY_IDENTIFIERS:
            pt = list(row[ident][i])
            if pt[0] == 0:
                continue
            pt[0] = (pt[0] - sp[0]) / dx
            pt[1] = (pt[1] - ep[1]) / dy
            row[ident][i] = pt
    return row


def _normalize_hand(row: dict, side: str) -> dict:
    wrist_key = "wrist_" + side
    seq_len = len(row[wrist_key])
    for i in range(seq_len):
        wrist = row[wrist_key][i]
        if wrist[0] == 0:
            continue
        pts = [row[h + "_" + side][i] for h in HAND_IDENTIFIERS_BASE]
        xs = [p[0] for p in pts if p[0] != 0]
        ys = [p[1] for p in pts if p[1] != 0]
        if not xs or not ys:
            continue
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        dx = max_x - min_x or 1
        dy = max_y - min_y or 1
        for h in HAND_IDENTIFIERS_BASE:
            pt = list(row[h + "_" + side][i])
            if pt[0] == 0:
                continue
            pt[0] = (pt[0] - min_x) / dx
            pt[1] = (pt[1] - min_y) / dy
            row[h + "_" + side][i] = pt
    return row


                                                                               

class WLASL100Dataset(Dataset):
    def __init__(self, csv_path: str, normalize: bool = True):
        df = pd.read_csv(csv_path, encoding="utf-8")
        df.columns = [c.replace("_left_", "_0_").replace("_right_", "_1_") for c in df.columns]
        if "neck_X" not in df.columns:
            df["neck_X"] = [str([0.0]*len(ast.literal_eval(df["leftEar_X"].iloc[0])))] * len(df)
            df["neck_Y"] = [str([0.0]*len(ast.literal_eval(df["leftEar_X"].iloc[0])))] * len(df)

        self.data = []
        self.labels = []
        for _, row in df.iterrows():
            try:
                seq_len = len(ast.literal_eval(row["leftEar_X"]))
                sample = np.zeros((seq_len, len(ALL_IDENTIFIERS), 2), dtype=np.float32)
                for j, ident in enumerate(ALL_IDENTIFIERS):
                    xs = ast.literal_eval(row[ident + "_X"])
                    ys = ast.literal_eval(row[ident + "_Y"])
                    sample[:, j, 0] = xs
                    sample[:, j, 1] = ys
                self.data.append(sample)
                self.labels.append(int(row["labels"]))                            
            except Exception:
                continue

        self.normalize = normalize

    def _to_dict(self, arr: np.ndarray) -> dict:
        d = {}
        for j, ident in enumerate(ALL_IDENTIFIERS):
            d[ident] = [list(arr[t, j]) for t in range(arr.shape[0])]
        return d

    def _from_dict(self, d: dict, T: int) -> np.ndarray:
        out = np.zeros((T, len(ALL_IDENTIFIERS), 2), dtype=np.float32)
        for j, ident in enumerate(ALL_IDENTIFIERS):
            for t in range(T):
                out[t, j] = d[ident][t]
        return out

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        arr = self.data[idx].copy()
        if self.normalize:
            d = self._to_dict(arr)
            d = _normalize_body(d)
            d = _normalize_hand(d, "0")
            d = _normalize_hand(d, "1")
            arr = self._from_dict(d, arr.shape[0])
        tensor = torch.from_numpy(arr) - 0.5
        label = torch.tensor(self.labels[idx], dtype=torch.long)
        return tensor, label


                                                                                

def _download(url: str, dest: Path):
    if dest.exists():
        print(f"  Already exists: {dest.name}")
        return
    print(f"  Downloading {dest.name} (~{['60MB','14MB'][dest.name.startswith('WLASL100_val')]})")
    urllib.request.urlretrieve(url, dest)
    print(f"  Saved {dest.name}")


                                                                                

def train():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    print("=" * 60)
    print("SPOTER WLASL100 Setup")
    print("=" * 60)

                      
    print("\n[1/3] Downloading WLASL100 skeletal data...")
    _download(TRAIN_URL, TRAIN_CSV)
    _download(VAL_URL, VAL_CSV)

                                     
    print("\n[2/3] Building label mapping...")
    df_train = pd.read_csv(TRAIN_CSV, encoding="utf-8")
    unique_labels = sorted(df_train["labels"].unique().tolist())
    num_classes = len(unique_labels)
    print(f"  Found {num_classes} classes: labels {unique_labels[0]}..{unique_labels[-1]}")

                                        
    label_map = {}
    for csv_label in unique_labels:
        label_map[int(csv_label)] = WLASL_KNOWN_GLOSSES.get(int(csv_label), f"sign_{csv_label}")

    with open(LABELS_OUT, "w") as f:
        json.dump(label_map, f, indent=2)
    print(f"  Label map saved -> {LABELS_OUT}")

                     
    print(f"\n[3/3] Training SPOTER ({num_classes} classes, hidden_dim=108, 100 epochs)...")
    print("  This takes ~30-60 min on CPU. Press Ctrl+C to stop early.\n")

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    train_set = WLASL100Dataset(str(TRAIN_CSV))
    val_set = WLASL100Dataset(str(VAL_CSV), normalize=True)
    train_loader = DataLoader(train_set, shuffle=True)
    val_loader = DataLoader(val_set, shuffle=False)

    model = SPOTER(num_classes=num_classes, hidden_dim=108).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.1, patience=5)

    best_val_acc = 0.0

    for epoch in range(1, 101):
        model.train()
        correct = total = 0
        for x, y in train_loader:
            x, y = x.squeeze(0).to(device), y.to(device)
            out = model(x)
                                                                  
            out = out.squeeze()
            if out.dim() == 1:
                out = out.unsqueeze(0)
            loss = criterion(out, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            pred = out.argmax(dim=-1)
            correct += (pred == y).sum().item()
            total += y.size(0)

        train_acc = correct / total if total > 0 else 0

                    
        model.eval()
        v_correct = v_total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.squeeze(0).to(device), y.to(device)
                out = model(x).squeeze()
                if out.dim() == 1:
                    out = out.unsqueeze(0)
                pred = out.argmax(dim=-1)
                v_correct += (pred == y).sum().item()
                v_total += y.size(0)
        val_acc = v_correct / v_total if v_total > 0 else 0
        scheduler.step(1 - val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), WEIGHTS_OUT)

        if epoch % 10 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/100  train={train_acc:.3f}  val={val_acc:.3f}  best={best_val_acc:.3f}")

    print(f"\nDone. Best val accuracy: {best_val_acc:.3f}")
    print(f"Weights saved -> {WEIGHTS_OUT}")
    print(f"Labels  saved -> {LABELS_OUT}")
    print("\nYou can now start the API server.")


if __name__ == "__main__":
    train()
