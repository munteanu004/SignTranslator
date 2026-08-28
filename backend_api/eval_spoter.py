"""
Evalueaza modelul SPOTER antrenat pe setul de validare WLASL100.
Ruleaza din backend_api/:  python eval_spoter.py
"""
import ast, json, sys
import numpy as np
import torch
import pandas as pd
from pathlib import Path
from spoter_model import SPOTER
from torch.utils.data import Dataset, DataLoader

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR   = Path(__file__).parent / "spoter_data"
WEIGHTS    = MODELS_DIR / "spoter_wlasl100.pth"
LABELS     = MODELS_DIR / "spoter_labels.json"
VAL_CSV    = DATA_DIR / "WLASL100_val_25fps.csv"
TRAIN_CSV  = DATA_DIR / "WLASL100_train_25fps.csv"

BODY_IDENTIFIERS = [
    "nose","neck","rightEye","leftEye","rightEar","leftEar",
    "rightShoulder","leftShoulder","rightElbow","leftElbow",
    "rightWrist","leftWrist",
]
HAND_IDENTIFIERS_BASE = [
    "wrist","indexTip","indexDIP","indexPIP","indexMCP",
    "middleTip","middleDIP","middlePIP","middleMCP",
    "ringTip","ringDIP","ringPIP","ringMCP",
    "littleTip","littleDIP","littlePIP","littleMCP",
    "thumbTip","thumbIP","thumbMP","thumbCMC",
]
ALL_IDENTIFIERS = BODY_IDENTIFIERS + [h+"_0" for h in HAND_IDENTIFIERS_BASE] + [h+"_1" for h in HAND_IDENTIFIERS_BASE]


def normalize_body(row):
    seq_len = len(row["leftEar"])
    last_sp = last_ep = None
    for i in range(seq_len):
        ls,rs = row["leftShoulder"][i], row["rightShoulder"][i]
        nk,ns = row["neck"][i], row["nose"][i]
        if (ls[0]==0 or rs[0]==0) and (nk[0]==0 or ns[0]==0):
            if last_sp is None: continue
            sp,ep = last_sp,last_ep
        else:
            if ls[0]!=0 and rs[0]!=0:
                hm = ((ls[0]-rs[0])**2+(ls[1]-rs[1])**2)**0.5
            else:
                hm = ((nk[0]-ns[0])**2+(nk[1]-ns[1])**2)**0.5
            cx = row["neck"][i][0]
            sp = [cx-3*hm, row["leftEye"][i][1]+hm]
            ep = [cx+3*hm, sp[1]-6*hm]
            sp[0]=max(sp[0],0); sp[1]=max(sp[1],0)
            ep[0]=max(ep[0],0); ep[1]=max(ep[1],0)
            last_sp,last_ep = sp,ep
        dx = ep[0]-sp[0]; dy = sp[1]-ep[1]
        if dx==0 or dy==0: continue
        for ident in BODY_IDENTIFIERS:
            pt=list(row[ident][i])
            if pt[0]==0: continue
            pt[0]=(pt[0]-sp[0])/dx; pt[1]=(pt[1]-ep[1])/dy
            row[ident][i]=pt
    return row


def normalize_hand(row, side):
    for i in range(len(row["wrist_"+side])):
        if row["wrist_"+side][i][0]==0: continue
        pts=[row[h+"_"+side][i] for h in HAND_IDENTIFIERS_BASE]
        xs=[p[0] for p in pts if p[0]!=0]; ys=[p[1] for p in pts if p[1]!=0]
        if not xs or not ys: continue
        mnx,mxx=min(xs),max(xs); mny,mxy=min(ys),max(ys)
        dx=mxx-mnx or 1; dy=mxy-mny or 1
        for h in HAND_IDENTIFIERS_BASE:
            pt=list(row[h+"_"+side][i])
            if pt[0]==0: continue
            pt[0]=(pt[0]-mnx)/dx; pt[1]=(pt[1]-mny)/dy
            row[h+"_"+side][i]=pt
    return row


class WLASLDataset(Dataset):
    def __init__(self, csv_path):
        df = pd.read_csv(csv_path, encoding="utf-8")
        df.columns = [c.replace("_left_","_0_").replace("_right_","_1_") for c in df.columns]
        if "neck_X" not in df.columns:
            n = len(ast.literal_eval(df["leftEar_X"].iloc[0]))
            df["neck_X"] = [str([0.0]*n)]*len(df)
            df["neck_Y"] = [str([0.0]*n)]*len(df)
        self.data=[]; self.labels=[]
        for _,row in df.iterrows():
            try:
                seq_len = len(ast.literal_eval(row["leftEar_X"]))
                sample = np.zeros((seq_len, len(ALL_IDENTIFIERS), 2), dtype=np.float32)
                for j,ident in enumerate(ALL_IDENTIFIERS):
                    sample[:,j,0]=ast.literal_eval(row[ident+"_X"])
                    sample[:,j,1]=ast.literal_eval(row[ident+"_Y"])
                self.data.append(sample); self.labels.append(int(row["labels"]))
            except: continue

    def __len__(self): return len(self.data)

    def __getitem__(self, idx):
        arr = self.data[idx].copy()
        d = {ident: [list(arr[t,j]) for t in range(arr.shape[0])] for j,ident in enumerate(ALL_IDENTIFIERS)}
        d = normalize_body(d); d = normalize_hand(d,"0"); d = normalize_hand(d,"1")
        out = np.zeros_like(arr)
        for j,ident in enumerate(ALL_IDENTIFIERS):
            for t in range(arr.shape[0]): out[t,j]=d[ident][t]
        tensor = torch.from_numpy(out) - 0.5
        return tensor, torch.tensor(self.labels[idx], dtype=torch.long)


def main():
    if not WEIGHTS.exists():
        print("Model negasit:", WEIGHTS); sys.exit(1)

    with open(LABELS) as f:
        label_map = {int(k):v for k,v in json.load(f).items()}
    num_classes = len(label_map)

    model = SPOTER(num_classes=num_classes, hidden_dim=108)
    model.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
    model.eval()
    print(f"Model incarcat: {num_classes} clase")

    for split_name, csv_path in [("TRAIN", TRAIN_CSV), ("VAL", VAL_CSV)]:
        if not csv_path.exists():
            print(f"{split_name}: fisier lipsa ({csv_path})"); continue
        ds = WLASLDataset(str(csv_path))
        print(f"\n{split_name}: {len(ds)} exemple")

        top1=top5=total=0
        with torch.no_grad():
            for i,(x,y) in enumerate(ds):
                out = model(x).squeeze()
                if out.dim()==0: out=out.unsqueeze(0)
                _,top5_idx = out.topk(min(5,num_classes))
                top1 += (out.argmax().item()==y.item())
                top5 += (y.item() in top5_idx.tolist())
                total += 1
                if (i+1)%100==0:
                    print(f"  {i+1}/{len(ds)}  top1={100*top1/total:.1f}%  top5={100*top5/total:.1f}%", end="\r")

        print(f"\n  {split_name} Top-1: {100*top1/total:.2f}%   Top-5: {100*top5/total:.2f}%   ({total} exemple)")

    print("\nGata.")


if __name__=="__main__":
    main()
