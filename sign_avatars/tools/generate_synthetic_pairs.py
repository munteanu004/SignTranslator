#!/usr/bin/env python3
"""
SignAvatars 3D → 2D synthetic projection dataset generator.

- Input: directory of sequences with 3D joints or SMPL-X parameters (per sequence files, e.g., .npz/.pkl).
- Output: JSONL with paired 2D-3D per frame (or per sequence), ready to train a 2D→3D lifting model.

Notes:
- This script assumes either:
  (A) files contain 'joints3d' key with shape (T, J, 3), or
  (B) files contain SMPL-X params (poses, betas, transl, etc.) and you have 'smplx' installed and a model folder.
- If you only have SMPL-X parameters, set --smplx-model-dir to the folder with SMPL-X meshes (download from SMPL-X release).

Install:
  pip install numpy scipy tqdm transforms3d
  # Optional for SMPL-X reconstruction:
  pip install smplx torch

Example:
  python tools/signavatars_preprocess.py \
    --input_dir "/data/signavatars" \
    --output_path "/data/sa_pairs.jsonl" \
    --format auto \
    --sample_cameras 3 \
    --noise_px 1.2 \
    --occlusion_prob 0.03 \
    --drop_joint_prob 0.005
"""
import argparse
import glob
import json
import os
import sys
from typing import Dict, Tuple, Optional, List
import numpy as np
from tqdm import tqdm
try:
    import transforms3d.euler as t3d_euler
except ImportError:
    raise SystemExit("Please install transforms3d: pip install transforms3d")

# Optional SMPL-X
_SMPLX_AVAILABLE = False
try:
    import torch  # noqa
    import smplx  # noqa
    _SMPLX_AVAILABLE = True
except Exception:
    _SMPLX_AVAILABLE = False

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate 2D↔3D pairs from SignAvatars 3D data.")
    p.add_argument("--input_dir", required=True, type=str, help="Directory with SignAvatars sequences (.npz/.pkl/.npy).")
    p.add_argument("--output_path", required=True, type=str, help="Output JSONL path (per-frame records).")
    p.add_argument("--format", choices=["auto", "joints3d", "smplx"], default="auto",
                   help="Input format: 'joints3d' if files contain T×J×3, 'smplx' if files store SMPL-X params.")
    p.add_argument("--max_sequences", type=int, default=None, help="Limit number of sequences for a quick run.")
    p.add_argument("--sample_cameras", type=int, default=1, help="How many random cameras per sequence.")
    p.add_argument("--image_size", type=int, nargs=2, default=[1280, 720], help="Synthetic image size W H (for intrinsics).")
    p.add_argument("--focal_range", type=float, nargs=2, default=[700.0, 1200.0], help="Range for focal length fx=fy sampled uniform.")
    p.add_argument("--yaw_pitch_roll_deg", type=float, nargs=6, default=[-35, 35, -20, 20, -5, 5],
                   help="Camera yaw_min yaw_max pitch_min pitch_max roll_min roll_max (degrees).")
    p.add_argument("--radius_range", type=float, nargs=2, default=[2.5, 4.5], help="Camera radius distance from subject (meters).")
    p.add_argument("--noise_px", type=float, default=1.0, help="Gaussian noise sigma (pixels) added to 2D.")
    p.add_argument("--occlusion_prob", type=float, default=0.02, help="Probability per joint to be marked invisible per frame.")
    p.add_argument("--drop_joint_prob", type=float, default=0.002, help="Probability per joint to be dropped (NaN) per frame.")
    p.add_argument("--smplx-model-dir", type=str, default=None, help="Path to SMPL-X model directory (if using SMPL-X params).")
    p.add_argument("--seq_glob", type=str, default="**/*.npz", help="Glob to find sequence files under input_dir.")
    return p.parse_args()

def ensure_parent_dir(path: str):
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def load_sequence(path: str) -> Dict:
    """
    Try to load a sequence file (.npz or .npy/.pkl with numpy). Return a dict with keys:
    - 'joints3d': np.ndarray (T, J, 3) if available
    - 'smplx': dict of SMPL-X params if available
    - 'fps': float (optional)
    - 'sequence_id': str
    """
    base = os.path.basename(path)
    sequence_id = os.path.splitext(base)[0]
    data = {}

    try:
        if path.endswith(".npz"):
            npz = np.load(path, allow_pickle=True)
            keys = list(npz.keys())
            # Heuristics
            if "joints3d" in npz:
                j3 = np.array(npz["joints3d"])
                if j3.ndim == 3 and j3.shape[-1] == 3:
                    data["joints3d"] = j3
            # Common SMPL-X keys
            smplx_keys = ["poses", "betas", "transl", "expression", "jaw_pose", "leye_pose", "reye_pose", "left_hand_pose", "right_hand_pose", "body_pose", "global_orient"]
            if any(k in keys for k in smplx_keys):
                smplx_params = {k: npz[k] for k in keys if k in smplx_keys}
                if smplx_params:
                    data["smplx"] = smplx_params
            if "fps" in npz:
                data["fps"] = float(npz["fps"])
        elif path.endswith(".npy") or path.endswith(".pkl"):
            arr = np.load(path, allow_pickle=True)
            if isinstance(arr, dict):
                if "joints3d" in arr:
                    j3 = np.array(arr["joints3d"])
                    if j3.ndim == 3 and j3.shape[-1] == 3:
                        data["joints3d"] = j3
                if "smplx" in arr:
                    data["smplx"] = arr["smplx"]
                if "fps" in arr:
                    data["fps"] = float(arr["fps"])
            elif isinstance(arr, np.ndarray) and arr.ndim == 3 and arr.shape[-1] == 3:
                data["joints3d"] = arr
    except Exception as e:
        print(f"Warning: failed to load {path}: {e}", file=sys.stderr)

    data["sequence_id"] = sequence_id
    return data

def reconstruct_joints_from_smplx(smplx_params: Dict, model_dir: str, device: str = "cpu") -> Optional[np.ndarray]:
    """
    Reconstruct joints3d (T, J, 3) from SMPL-X parameters.
    Requires smplx installed and model_dir set to SMPL-X model folder.
    """
    if not _SMPLX_AVAILABLE:
        print("Error: SMPL-X not available. Install 'smplx' and 'torch'.", file=sys.stderr)
        return None
    if not model_dir or not os.path.exists(model_dir):
        print("Error: missing --smplx-model-dir for SMPL-X reconstruction.", file=sys.stderr)
        return None

    # Lazy import inside to avoid hard dep for non-smplx users
    import torch
    import smplx

    # Build SMPL-X model (use neutral or per-gender if available)
    model = smplx.create(model_dir, model_type='smplx', gender='neutral', use_pca=False, num_betas=10, num_expression_coeffs=10)
    model = model.to(device)

    # Expected shapes: batched over T
    # Try to infer T
    T = None
    for k, v in smplx_params.items():
        if isinstance(v, np.ndarray) and v.ndim >= 2:
            T = v.shape[0]
            break
    if T is None:
        print("Error: cannot infer T from SMPL-X params.", file=sys.stderr)
        return None

    # Prepare tensors
    def to_torch(name, default_shape):
        x = smplx_params.get(name, None)
        if x is None:
            return None
        return torch.tensor(x, dtype=torch.float32, device=device)

    global_orient = to_torch("global_orient", (T, 3))
    body_pose = to_torch("body_pose", (T, 63))
    betas = to_torch("betas", (T, 10)) if smplx_params.get("betas", None) is not None else torch.zeros((T, 10), device=device)
    transl = to_torch("transl", (T, 3)) if smplx_params.get("transl", None) is not None else torch.zeros((T, 3), device=device)
    left_hand_pose = to_torch("left_hand_pose", (T, 45)) if smplx_params.get("left_hand_pose", None) is not None else None
    right_hand_pose = to_torch("right_hand_pose", (T, 45)) if smplx_params.get("right_hand_pose", None) is not None else None
    jaw_pose = to_torch("jaw_pose", (T, 3)) if smplx_params.get("jaw_pose", None) is not None else None
    leye_pose = to_torch("leye_pose", (T, 3)) if smplx_params.get("leye_pose", None) is not None else None
    reye_pose = to_torch("reye_pose", (T, 3)) if smplx_params.get("reye_pose", None) is not None else None
    expression = to_torch("expression", (T, 10)) if smplx_params.get("expression", None) is not None else torch.zeros((T, 10), device=device)

    # Forward in small batches if needed (memory)
    joints_all = []
    bs = 128
    for start in range(0, T, bs):
        end = min(T, start + bs)
        out = model(
            global_orient=global_orient[start:end] if global_orient is not None else None,
            body_pose=body_pose[start:end] if body_pose is not None else None,
            left_hand_pose=left_hand_pose[start:end] if left_hand_pose is not None else None,
            right_hand_pose=right_hand_pose[start:end] if right_hand_pose is not None else None,
            jaw_pose=jaw_pose[start:end] if jaw_pose is not None else None,
            leye_pose=leye_pose[start:end] if leye_pose is not None else None,
            reye_pose=reye_pose[start:end] if reye_pose is not None else None,
            betas=betas[start:end] if betas is not None else None,
            expression=expression[start:end] if expression is not None else None,
            transl=transl[start:end] if transl is not None else None,
            return_verts=False
        )
        # out.joints: (B, J, 3) in meters
        joints_all.append(out.joints.detach().cpu().numpy())

    joints3d = np.concatenate(joints_all, axis=0)  # (T, J, 3)
    return joints3d

def sample_camera(yaw_pitch_roll_deg: List[float], radius_range: Tuple[float, float], focal_range: Tuple[float, float],
                  image_size: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample a simple pinhole camera looking at origin:
    - R: world->camera rotation (3x3)
    - t: world->camera translation (3,)
    - K: intrinsics (3x3)
    """
    yaw = np.deg2rad(np.random.uniform(yaw_pitch_roll_deg[0], yaw_pitch_roll_deg[1]))
    pitch = np.deg2rad(np.random.uniform(yaw_pitch_roll_deg[2], yaw_pitch_roll_deg[3]))
    roll = np.deg2rad(np.random.uniform(yaw_pitch_roll_deg[4], yaw_pitch_roll_deg[5]))
    Rz = rotation_matrix_z(roll)
    Ry = rotation_matrix_y(yaw)
    Rx = rotation_matrix_x(pitch)
    R = Rz @ Ry @ Rx  # Z-Y-X
    radius = np.random.uniform(radius_range[0], radius_range[1])
    # Place camera on -Z axis rotated by R, looking at origin
    cam_pos = np.array([0.0, 0.0, radius])
    t = -(R @ cam_pos)
    W, H = image_size
    f = np.random.uniform(focal_range[0], focal_range[1])
    cx = W / 2.0 + np.random.uniform(-0.05 * W, 0.05 * W)
    cy = H / 2.0 + np.random.uniform(-0.05 * H, 0.05 * H)
    K = np.array([[f, 0, cx],
                  [0, f, cy],
                  [0, 0, 1]], dtype=np.float32)
    return R.astype(np.float32), t.astype(np.float32), K

def rotation_matrix_x(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0],
                     [0, ca, -sa],
                     [0, sa, ca]], dtype=np.float32)

def rotation_matrix_y(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[ca, 0, sa],
                     [0, 1, 0],
                     [-sa, 0, ca]], dtype=np.float32)

def rotation_matrix_z(a):
    ca, sa = np.cos(a), np.sin(a)
    return np.array([[ca, -sa, 0],
                     [sa, ca, 0],
                     [0, 0, 1]], dtype=np.float32)

def project_points(Pw: np.ndarray, R: np.ndarray, t: np.ndarray, K: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project 3D world points (J, 3) to image 2D (J, 2) with visibility mask (J,).
    Returns (uv, visible)
    """
    Pc = (R @ Pw.T).T + t[None, :]  # (J,3)
    z = Pc[:, 2].copy()
    visible = (z > 0.2)  # simple near-plane
    uv = (Pc[:, :2] / z[:, None]) @ K[:2, :2].T + K[:2, 2]  # x/z * fx + cx
    return uv.astype(np.float32), visible.astype(np.uint8)

def add_noise_and_occlusion(uv: np.ndarray, visible: np.ndarray, noise_px: float, occl_prob: float, drop_prob: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Add Gaussian noise, random occlusions (visibility=0), and hard drops (NaN).
    """
    uv_noisy = uv.copy()
    if noise_px > 0:
        uv_noisy += np.random.randn(*uv.shape).astype(np.float32) * float(noise_px)
    vis = visible.copy()
    # Random occlusions
    occl = (np.random.rand(uv.shape[0]) < occl_prob).astype(np.uint8)
    vis = (vis & (1 - occl)).astype(np.uint8)
    # Drops
    drop = (np.random.rand(uv.shape[0]) < drop_prob)
    uv_noisy[drop] = np.nan
    vis[drop] = 0
    return uv_noisy, vis

def main():
    args = parse_args()
    ensure_parent_dir(args.output_path)

    files = sorted(glob.glob(os.path.join(args.input_dir, args.seq_glob), recursive=True))
    if args.max_sequences is not None:
        files = files[: args.max_sequences]
    if not files:
        print("No sequence files found. Check --input_dir and --seq_glob.", file=sys.stderr)
        sys.exit(2)

    if args.format == "smplx" and not _SMPLX_AVAILABLE:
        print("Warning: 'smplx' not available; cannot reconstruct from SMPL-X. Falling back to joints3d only.", file=sys.stderr)

    with open(args.output_path, "w", encoding="utf-8") as out:
        pbar = tqdm(files, desc="Sequences")
        for seq_path in pbar:
            rec = load_sequence(seq_path)
            seq_id = rec.get("sequence_id", os.path.basename(seq_path))
            joints3d = rec.get("joints3d", None)

            # Reconstruct from SMPL-X if needed
            if joints3d is None and (args.format in ["auto", "smplx"]) and ("smplx" in rec):
                joints3d = reconstruct_joints_from_smplx(rec["smplx"], args.smplx_model_dir)
                if joints3d is None:
                    print(f"Skipping {seq_path}: cannot reconstruct joints from SMPL-X.", file=sys.stderr)
                    continue

            if joints3d is None:
                if args.format == "smplx":
                    print(f"Skipping {seq_path}: no SMPL-X params found.", file=sys.stderr)
                else:
                    print(f"Skipping {seq_path}: no joints3d found.", file=sys.stderr)
                continue

            T, J, C = joints3d.shape
            fps = rec.get("fps", 30.0)

            for cam_idx in range(args.sample_cameras):
                R, t, K = sample_camera(args.yaw_pitch_roll_deg, tuple(args.radius_range), tuple(args.focal_range), tuple(args.image_size))
                for f_idx in range(T):
                    Pw = joints3d[f_idx]  # (J,3), assumed meters
                    uv, vis0 = project_points(Pw, R, t, K)
                    uv, vis = add_noise_and_occlusion(uv, vis0, args.noise_px, args.occlusion_prob, args.drop_joint_prob)
                    ts = f_idx / fps
                    line = {
                        "sequence_id": seq_id,
                        "cam_index": cam_idx,
                        "frame_index": int(f_idx),
                        "timestamp_sec": float(np.round(ts, 6)),
                        "joints2d": np.where(np.isnan(uv), None, uv).tolist(),
                        "joints3d": Pw.tolist(),
                        "R": R.tolist(),
                        "t": t.tolist(),
                        "K": K.tolist(),
                        "vis": vis.tolist()
                    }
                    out.write(json.dumps(line) + '\n')
    
    if args.smplx_model_dir:
        print(f"Finished generating {os.path.basename(args.output_path)}. Remember to delete SMPL-X model files when done due to licensing.")
    else:
        print(f"Finished generating {os.path.basename(args.output_path)}.")


if __name__ == "__main__":
    main()