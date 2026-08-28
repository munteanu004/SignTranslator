#!/usr/bin/env python3
"""
Baseline training script for 2D->3D lifting using synthetic pairs produced by generate_synthetic_pairs.py.

- Input: JSONL with per-frame records containing keys: joints2d (Jx2 with nulls), joints3d (Jx3), vis (J), etc.
- Model: simple MLP mapping flattened 2D (2J) to flattened 3D (3J).
- Loss: masked MSE using 'vis' to include only visible joints in the loss.

Example:
  python sign_avatars/tools/train_lifting_baseline.py \
    --train_jsonl data/demo/out.jsonl \
    --epochs 10 --batch_size 128 --lr 1e-3 --hidden 1024 --out_path models/lifting_mlp_demo.pth
"""
import argparse
import json
import math
import os
from typing import List, Tuple

import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, random_split
from tqdm import tqdm


def ensure_parent_dir(path: str):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


class Pairs2D3DDataset(Dataset):
    def __init__(self, jsonl_path: str):
        super().__init__()
        self.records = []
        self._J = None
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                j2 = obj['joints2d']  # list of [x, y] or [None, None]
                j3 = obj['joints3d']  # list of [x, y, z]
                vis = obj.get('vis', None)  # list of 0/1
                j2 = np.array(j2, dtype=float)  # will convert None->nan
                j3 = np.array(j3, dtype=float)
                if j2.ndim != 2 or j2.shape[1] != 2:
                    raise ValueError('joints2d must be Jx2')
                if j3.ndim != 2 or j3.shape[1] != 3:
                    raise ValueError('joints3d must be Jx3')
                if self._J is None:
                    self._J = j3.shape[0]
                else:
                    if j3.shape[0] != self._J:
                        # Skip inconsistent J
                        continue
                if vis is None:
                    # If no visibility, infer as joints2d fully present
                    vis = (~np.isnan(j2).any(axis=1)).astype(np.uint8).tolist()
                vis = np.array(vis, dtype=np.float32)
                # Input: replace NaNs with zeros
                j2 = np.nan_to_num(j2, nan=0.0).astype(np.float32)
                j3 = j3.astype(np.float32)
                self.records.append((j2, j3, vis))
        if not self.records:
            raise RuntimeError(f'No valid records found in {jsonl_path}')
        self.J = self._J
        self.in_dim = self.J * 2
        self.out_dim = self.J * 3

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        j2, j3, vis = self.records[idx]
        x = torch.from_numpy(j2.reshape(-1))  # 2J
        y = torch.from_numpy(j3.reshape(-1))  # 3J
        m = torch.from_numpy(vis)             # J
        return x, y, m


class MLP(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, hidden: int = 1024, depth: int = 3, dropout: float = 0.0):
        super().__init__()
        layers = []
        d = in_dim
        for i in range(depth - 1):
            layers.append(nn.Linear(d, hidden))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            d = hidden
        layers.append(nn.Linear(d, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def masked_mse(pred: torch.Tensor, target: torch.Tensor, vis: torch.Tensor) -> torch.Tensor:
    """
    pred, target: (B, 3J); vis: (B, J) with 0/1.
    Mask is expanded to (B, 3J) by repeating each vis thrice.
    """
    B = pred.shape[0]
    J3 = pred.shape[1]
    J = J3 // 3
    mask = vis.unsqueeze(-1).repeat(1, 3).reshape(B, J3)
    diff = (pred - target) * mask
    denom = mask.sum().clamp(min=1.0)
    return (diff.pow(2).sum() / denom)


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    total_loss = 0.0
    count = 0
    with torch.no_grad():
        for x, y, m in loader:
            x = x.to(device)
            y = y.to(device)
            m = m.to(device)
            pred = model(x)
            loss = masked_mse(pred, y, m)
            total_loss += loss.item()
            count += 1
    return total_loss / max(count, 1)


def train(args):
    dataset = Pairs2D3DDataset(args.train_jsonl)
    N = len(dataset)
    val_n = max(1, int(math.ceil(N * args.val_ratio)))
    train_n = N - val_n
    train_set, val_set = random_split(dataset, [train_n, val_n])

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=False)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False, num_workers=0, drop_last=False)

    device = torch.device('cuda' if torch.cuda.is_available() and not args.cpu else 'cpu')
    model = MLP(dataset.in_dim, dataset.out_dim, hidden=args.hidden, depth=args.depth, dropout=args.dropout).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode='min', factor=0.5, patience=3, min_lr=1e-6)

    best_val = float('inf')
    ensure_parent_dir(args.out_path)

    for epoch in range(1, args.epochs + 1):
        model.train()
        pbar = tqdm(train_loader, desc=f'Epoch {epoch}/{args.epochs}')
        for x, y, m in pbar:
            x = x.to(device)
            y = y.to(device)
            m = m.to(device)
            opt.zero_grad(set_to_none=True)
            pred = model(x)
            loss = masked_mse(pred, y, m)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            opt.step()
            pbar.set_postfix(loss=f'{loss.item():.4f}')

        val_loss = evaluate(model, val_loader, device)
        sched.step(val_loss)
        tqdm.write(f'Val loss: {val_loss:.6f}')
        if val_loss < best_val:
            best_val = val_loss
            torch.save({
                'model': model.state_dict(),
                'in_dim': dataset.in_dim,
                'out_dim': dataset.out_dim,
                'hidden': args.hidden,
                'depth': args.depth,
                'dropout': args.dropout,
                'val_loss': best_val,
            }, args.out_path)
            tqdm.write(f'Saved best to {args.out_path}')

    print('Training finished. Best val loss:', best_val)


def parse_args():
    p = argparse.ArgumentParser(description='Train a baseline MLP for 2D->3D lifting on synthetic pairs JSONL')
    p.add_argument('--train_jsonl', type=str, required=True, help='Path to JSONL produced by generate_synthetic_pairs.py')
    p.add_argument('--out_path', type=str, default='models/lifting_mlp.pth', help='Path to save the best model checkpoint')
    p.add_argument('--epochs', type=int, default=20)
    p.add_argument('--batch_size', type=int, default=256)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--weight_decay', type=float, default=0.0)
    p.add_argument('--hidden', type=int, default=1024)
    p.add_argument('--depth', type=int, default=3)
    p.add_argument('--dropout', type=float, default=0.0)
    p.add_argument('--val_ratio', type=float, default=0.1, help='Fraction for validation split')
    p.add_argument('--grad_clip', type=float, default=1.0)
    p.add_argument('--cpu', action='store_true', help='Force CPU even if CUDA is available')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    train(args)
