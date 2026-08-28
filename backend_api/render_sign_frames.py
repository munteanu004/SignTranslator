"""Subprocess renderer: outputs SMPL-X aitviewer frames as JSON lines to stdout.
Usage: python render_sign_frames.py --text "cuvant" [--lookup ENG --lookup_type english]
Each line printed to stdout: {"word":"...", "image":"data:image/jpeg;base64,..."}
Final line: {"done": true}
"""
import sys
import io
import os
import json
import base64
import argparse
import re
import math
import numpy as np
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
for p in [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "sign_avatars" / "visualizer"),
    str(PROJECT_ROOT / "sign_avatars" / "common" / "utils"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def init_aitviewer():
    import cv2                                                             
    from aitviewer.configuration import CONFIG as C
    from aitviewer.headless import HeadlessRenderer
    from aitviewer.models.smpl import SMPLLayer
    from aitviewer.utils.so3 import aa2rot_numpy

    smplx_models = PROJECT_ROOT / "sign_avatars" / "common" / "utils" / "human_model_files"
    C.smplx_models = str(smplx_models.resolve())
    C.device = "cpu"

    renderer = HeadlessRenderer(size=(512, 512))
    renderer.scene.light_mode = "dark"
    renderer.auto_set_camera_target = False
    renderer.scene.camera.position = np.array([0, 0.92, 1.65])
    renderer.scene.camera.target = np.array([0, 0.82, 0])
    renderer.auto_set_floor = False
    renderer.scene.floor.position = np.array([0, -0.30, 0])
    renderer.scene.origin.enabled = False
    renderer.shadows_enabled = False

    smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
    rotation = aa2rot_numpy(np.array([1, 0, 0]) * math.pi)

    return renderer, smpl_layer, rotation


def build_clothing_colors():
    """Reproduce the same clothing vertex colors as api_server._build_smplx_clothing_colors."""
    n_verts = 10475
    colors = np.tile([0.87, 0.73, 0.55, 1.0], (n_verts, 1)).astype(np.float32)
                                       
    colors[:3000] = [0.18, 0.33, 0.62, 1.0]                    
                                       
    colors[3000:7000] = [0.15, 0.15, 0.25, 1.0]                 
                                    
    colors[7000:8500] = [0.1, 0.1, 0.1, 1.0]               
                                               
    return colors


def render_poses(renderer, smpl_layer, rotation, poses, label, jpeg_q=88):
    import cv2
    from aitviewer.renderables.smpl import SMPLSequence

    poses = np.asarray(poses, dtype=np.float32)
    if poses.ndim != 2 or poses.shape[1] < 156:
        return

    T = len(poses)
    seq = SMPLSequence(
        poses_body=poses[:, 3:66],
        poses_root=poses[:, :3],
        poses_left_hand=poses[:, 66:111],
        poses_right_hand=poses[:, 111:156],
        betas=poses[:, 159:169] if poses.shape[1] >= 169 else np.zeros((T, 10), np.float32),
        smpl_layer=smpl_layer,
        color=(0.87, 0.73, 0.55, 1.0),
        rotation=rotation,
    )
    try:
        seq.mesh_seq.vertex_colors = build_clothing_colors()
    except Exception:
        pass

    renderer.scene.add(seq)
    try:
        for fi in range(T):
            seq.current_frame_id = fi
            pil_img = renderer.get_frame()
            bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_q])
            if ok:
                uri = "data:image/jpeg;base64," + base64.b64encode(enc.tobytes()).decode("ascii")
                emit({"word": label, "image": uri, "done": False})
    finally:
        renderer.scene.remove(seq)


def load_pkl_poses(pkl_path):
    import torch
    import pickle

    try:
        data = torch.load(str(pkl_path), map_location="cpu", weights_only=False)
    except Exception:
        with open(pkl_path, "rb") as f:
            class CpuUnpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    if module == "torch.storage" and name == "_load_from_bytes":
                        import io as _io
                        return lambda b: torch.load(_io.BytesIO(b), map_location="cpu", weights_only=False)
                    return super().find_class(module, name)
            data = CpuUnpickler(f).load()

    raw = data.get("smplx") or data.get("body_pose")
    if raw is None:
        return None
    poses = np.asarray(raw, dtype=np.float32)
    return poses if poses.ndim == 2 and poses.shape[1] >= 156 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--lookup", default="")
    parser.add_argument("--lookup_type", default="english")
    parser.add_argument("--max_frames", type=int, default=18)
    parser.add_argument("--jpeg_quality", type=int, default=88)
    args = parser.parse_args()

    text = args.text.strip()
    lookup = args.lookup.strip()
    max_frames = args.max_frames
    jpeg_q = args.jpeg_quality

    try:
        renderer, smpl_layer, rotation = init_aitviewer()
    except Exception as exc:
        emit({"error": f"aitviewer init failed: {exc}", "done": True})
        return

    try:
        from integration.translator_enhanced import EnhancedTranslator
        translator = EnhancedTranslator()
    except Exception as exc:
        emit({"error": f"translator init failed: {exc}", "done": True})
        return

    signs_to_render = []

    if lookup:
                                         
        if args.lookup_type == "romanian":
            sign = translator.find_sign_by_romanian(lookup) or translator.find_sign_by_english(lookup)
        else:
            sign = translator.find_sign_by_english(lookup) or translator.find_sign_by_romanian(lookup)
        if sign and sign.get("pkl_file"):
            signs_to_render.append((text or lookup, sign["pkl_file"]))
    else:
                             
        words = re.findall(r"[\w]+", text, flags=re.UNICODE)
        for word in words:
            en = translator.translate_sentence_ro_to_en(word)
            en_word = re.findall(r"[\w]+", en.lower())[0] if re.findall(r"[\w]+", en.lower()) else word
            sign = translator.find_sign_by_english(en_word)
            if sign and sign.get("pkl_file"):
                signs_to_render.append((word, sign["pkl_file"]))

    if not signs_to_render:
        emit({"error": f"Nu am găsit semne pentru: {text or lookup}", "done": True})
        return

    rendered_any = False
    for label, pkl_path in signs_to_render:
        try:
            poses = load_pkl_poses(pkl_path)
            if poses is None:
                continue
            step = max(1, math.ceil(len(poses) / max_frames))
            sampled = poses[::step][:max_frames]
            render_poses(renderer, smpl_layer, rotation, sampled, label, jpeg_q)
            rendered_any = True
        except Exception as exc:
            emit({"warning": f"Render failed for {label}: {exc}", "done": False})

    if not rendered_any:
        emit({"error": "Nu am putut randa niciun semn.", "done": True})
        return

    emit({"done": True})


if __name__ == "__main__":
    main()
