"""
Evaluare rapida: Model pre-antrenat vs Random init (pe CPU).
Foloseste subset mic (300 train + 200 test) pentru viteza.
"""
import sys, os, json, time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'training'))
from model import SignTranslatorNet

# === Config ===
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "ro_cache")
DATASET_JSON = os.path.join(BASE, "ro-sign-language-recognition/datasets/processed_dataset/dataset.json")
PRETRAINED = os.path.join(BASE, "models_backup/pretrained_best.pth")
MAX_SEQ = 150
HIDDEN = 256
BATCH = 32  # batch mai mare = mai putine iteratii
MAX_TRAIN = 300
MAX_TEST = 200


class CachedDataset(Dataset):
    def __init__(self, samples, cache_dir):
        self.samples = samples
        self.cache_dir = cache_dir

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        d = np.load(os.path.join(self.cache_dir, f"{s['video_id']}.npz"))
        joints, vis = d['joints'].copy(), d['vis'].copy()
        T = joints.shape[0]

        # Pad/crop la MAX_SEQ
        if T > MAX_SEQ:
            sel = np.linspace(0, T-1, MAX_SEQ, dtype=int)
            joints, vis = joints[sel], vis[sel]
        elif T < MAX_SEQ:
            joints = np.concatenate([joints, np.zeros((MAX_SEQ-T, 75, 3), dtype=np.float32)])
            vis = np.concatenate([vis, np.zeros((MAX_SEQ-T, 75), dtype=np.float32)])

        # Normalizare simpla
        valid = vis > 0.5
        if valid.any():
            for t in range(min(T, MAX_SEQ)):
                if valid[t].any():
                    joints[t] -= joints[t, valid[t]].mean(axis=0)
            vj = joints[valid.any(axis=1)]
            if len(vj) > 0:
                md = np.abs(vj[:, :, :2]).max()
                if md > 1e-6:
                    joints[:, :, :2] /= md

        mask = torch.zeros(MAX_SEQ, dtype=torch.bool)
        if T < MAX_SEQ:
            mask[T:] = True

        return {
            'joints': torch.from_numpy(joints).float(),
            'mask': mask,
            'label': torch.tensor(s['label'], dtype=torch.long)
        }


def extract_features(model, loader, device, name=""):
    """Extrage features din backbone (fara classifier)."""
    model.eval()
    orig = model.classifier
    model.classifier = nn.Identity()
    all_f, all_l = [], []
    total_batches = len(loader)

    with torch.no_grad():
        for i, batch in enumerate(loader):
            feat = model(batch['joints'].to(device), batch['mask'].to(device))
            all_f.append(feat.cpu())
            all_l.append(batch['label'])
            print(f"\r    [{name}] Batch {i+1}/{total_batches}", end="", flush=True)

    model.classifier = orig
    print()
    return torch.cat(all_f), torch.cat(all_l)


def main():
    device = torch.device('cpu')
    t0 = time.time()

    print("=" * 55)
    print("  EVALUARE: Pre-trained vs Random (CPU, subset mic)")
    print("=" * 55)

    # Incarca date
    with open(DATASET_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    glosses = sorted(set(e['gloss'] for e in data))
    g2i = {g: i for i, g in enumerate(glosses)}
    num_classes = len(glosses)

    train_s, test_s = [], []
    for entry in data:
        lab = g2i[entry['gloss']]
        for inst in entry['instances']:
            if os.path.exists(os.path.join(CACHE_DIR, f"{inst['video_id']}.npz")):
                s = {'video_id': inst['video_id'], 'label': lab}
                (train_s if inst['split'] == 'train' else test_s).append(s)

    # Subset mic
    import random
    random.seed(42)
    random.shuffle(train_s)
    random.shuffle(test_s)
    train_s = train_s[:MAX_TRAIN]
    test_s = test_s[:MAX_TEST]
    print(f"Train: {len(train_s)}, Test: {len(test_s)}, Clase: {num_classes}")

    tr_loader = DataLoader(CachedDataset(train_s, CACHE_DIR), batch_size=BATCH, num_workers=0)
    te_loader = DataLoader(CachedDataset(test_s, CACHE_DIR), batch_size=BATCH, num_workers=0)

    # Model 1: Pre-trained
    print("\n>>> Model PRE-TRAINED...")
    m_pt = SignTranslatorNet(num_classes=num_classes, hidden_dim=HIDDEN).to(device)
    ckpt = torch.load(PRETRAINED, map_location='cpu')
    bb = ckpt['backbone']
    sd = m_pt.state_dict()
    loaded = {k: v for k, v in bb.items() if k in sd and sd[k].shape == v.shape}
    sd.update(loaded)
    m_pt.load_state_dict(sd, strict=False)
    print(f"    {len(loaded)}/{len(sd)} params loaded (epoch {ckpt.get('epoch')})")

    # Model 2: Random
    print(">>> Model RANDOM...")
    m_rand = SignTranslatorNet(num_classes=num_classes, hidden_dim=HIDDEN).to(device)

    # Extractie features
    print("\n>>> Extrag features...")
    pt_tr_f, pt_tr_l = extract_features(m_pt, tr_loader, device, "PT-train")
    pt_te_f, pt_te_l = extract_features(m_pt, te_loader, device, "PT-test")
    print(f"    Pre-trained done: {time.time()-t0:.0f}s")

    r_tr_f, r_tr_l = extract_features(m_rand, tr_loader, device, "Rand-train")
    r_te_f, r_te_l = extract_features(m_rand, te_loader, device, "Rand-test")
    print(f"    Random done: {time.time()-t0:.0f}s")

    del m_pt, m_rand  # elibereaza memorie

    # KNN (k=5)
    print("\n>>> KNN accuracy (k=5)...")
    def knn(tr_f, tr_l, te_f, te_l, k=5):
        tr_f = tr_f / tr_f.norm(dim=1, keepdim=True).clamp(min=1e-8)
        te_f = te_f / te_f.norm(dim=1, keepdim=True).clamp(min=1e-8)
        sim = te_f @ tr_f.T
        _, top_idx = sim.topk(k, dim=1)
        c1 = sum(tr_l[top_idx[i, 0]] == te_l[i] for i in range(len(te_l)))
        c5 = sum(te_l[i] in tr_l[top_idx[i]] for i in range(len(te_l)))
        return 100.0*c1/len(te_l), 100.0*c5/len(te_l)

    pt_k1, pt_k5 = knn(pt_tr_f, pt_tr_l, pt_te_f, pt_te_l)
    r_k1, r_k5 = knn(r_tr_f, r_tr_l, r_te_f, r_te_l)

    # Linear Probe (30 epoci — suficient)
    print(">>> Linear Probe (30 epoci)...")
    def lprobe(tr_f, tr_l, te_f, te_l, nc, ep=30):
        mean, std = tr_f.mean(0), tr_f.std(0).clamp(min=1e-6)
        tr_n, te_n = (tr_f-mean)/std, (te_f-mean)/std
        probe = nn.Linear(tr_f.shape[1], nc)
        opt = torch.optim.Adam(probe.parameters(), lr=0.01, weight_decay=1e-4)
        crit = nn.CrossEntropyLoss()
        for e in range(ep):
            probe.train()
            perm = torch.randperm(len(tr_n))
            for i in range(0, len(tr_n), 128):
                idx = perm[i:i+128]
                loss = crit(probe(tr_n[idx]), tr_l[idx])
                opt.zero_grad(); loss.backward(); opt.step()
        probe.eval()
        with torch.no_grad():
            logits = probe(te_n)
            t1 = logits.argmax(1).eq(te_l).float().mean().item() * 100
            _, t5p = logits.topk(min(5, nc), dim=1)
            t5 = 100.0 * sum(te_l[i] in t5p[i] for i in range(len(te_l))) / len(te_l)
        return t1, t5

    pt_l1, pt_l5 = lprobe(pt_tr_f, pt_tr_l, pt_te_f, pt_te_l, num_classes)
    r_l1, r_l5 = lprobe(r_tr_f, r_tr_l, r_te_f, r_te_l, num_classes)

    # REZULTATE
    print("\n" + "=" * 62)
    print("  REZULTATE")
    print("=" * 62)
    print(f"{'Metrica':<28} {'Pre-trained':>12} {'Random':>12} {'Diff':>8}")
    print("-" * 62)
    print(f"{'KNN Top-1':<28} {pt_k1:>11.2f}% {r_k1:>11.2f}% {pt_k1-r_k1:>+7.2f}%")
    print(f"{'KNN Top-5':<28} {pt_k5:>11.2f}% {r_k5:>11.2f}% {pt_k5-r_k5:>+7.2f}%")
    print(f"{'Linear Probe Top-1':<28} {pt_l1:>11.2f}% {r_l1:>11.2f}% {pt_l1-r_l1:>+7.2f}%")
    print(f"{'Linear Probe Top-5':<28} {pt_l5:>11.2f}% {r_l5:>11.2f}% {pt_l5-r_l5:>+7.2f}%")
    print("=" * 62)

    if pt_k1 > r_k1 and pt_l1 > r_l1:
        print("\n>>> CONCLUZIE: Pre-training-ul AJUTA!")
    elif pt_k1 > r_k1 or pt_l1 > r_l1:
        print("\n>>> CONCLUZIE: Pre-training-ul ajuta PARTIAL.")
    else:
        print("\n>>> CONCLUZIE: Pre-training-ul NU ajuta semnificativ.")

    print(f"\nTimp total: {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
