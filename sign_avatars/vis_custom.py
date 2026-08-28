"""
Script adaptat din vis_language2motion.py pentru fișierele PKL din SignTranslator
Folosește aitviewer pentru randare 3D interactivă
"""

import os
import sys
import numpy as np
import torch
import pickle
from argparse import ArgumentParser

# Verificare aitviewer
try:
    from aitviewer.configuration import CONFIG as C
    from aitviewer.headless import HeadlessRenderer
    from aitviewer.models.smpl import SMPLLayer
    from aitviewer.renderables.smpl import SMPLSequence
    from aitviewer.utils.so3 import aa2rot_numpy
    from aitviewer.viewer import Viewer
    AITVIEWER_AVAILABLE = True
except ImportError:
    AITVIEWER_AVAILABLE = False
    print("⚠️  aitviewer nu este instalat. Instalează cu:")
    print("   cd visualizer && pip install -e .")


def batch_rodrigues(param):
    """Convertește axis-angle la matrici de rotație"""
    def quat2mat(quat):
        norm_quat = quat / np.linalg.norm(quat, axis=1, keepdims=True)
        w, x, y, z = norm_quat[:, 0], norm_quat[:, 1], norm_quat[:, 2], norm_quat[:, 3]
        w2, x2, y2, z2 = w**2, x**2, y**2, z**2
        wx, wy, wz = w*x, w*y, w*z
        xy, xz, yz = x*y, x*z, y*z
        rot_mat = np.stack([w2 + x2 - y2 - z2, 2*xy - 2*wz, 2*wx + 2*yz,
                            2*xy + 2*wz, w2 - x2 + y2 - z2, 2*yz - 2*wx,
                            2*wz - 2*xy, 2*wx - 2*yz, w2 - x2 - y2 + z2], axis=1).reshape(-1, 3, 3)
        return rot_mat

    l1norm = np.linalg.norm(param + 1e-8, axis=1)
    angle = np.expand_dims(l1norm, -1)
    normalized = np.divide(param, angle)
    angle = angle * 0.5
    v_cos = np.cos(angle)
    v_sin = np.sin(angle)
    quat = np.concatenate([v_cos, v_sin * normalized], axis=1)
    return quat2mat(quat)


def load_pkl_data(pkl_path):
    """Încarcă PKL cu suport CUDA->CPU"""
    try:
        data = torch.load(pkl_path, map_location=torch.device('cpu'), weights_only=False)
    except:
        import io
        with open(pkl_path, 'rb') as f:
            class CPU_Unpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    if module == 'torch.storage' and name == '_load_from_bytes':
                        return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
                    return super().find_class(module, name)
            data = CPU_Unpickler(f).load()
    return data


if __name__ == "__main__":
    if not AITVIEWER_AVAILABLE:
        print("\n❌ Nu pot continua fără aitviewer!")
        print("   Instalează cu: cd visualizer && pip install -e .")
        sys.exit(1)

    parser = ArgumentParser()
    parser.add_argument('--pkl_file', type=str, required=True, help='Calea către fișierul PKL')
    parser.add_argument('--headless', action='store_true', help='Export video fără GUI')
    parser.add_argument('--output', type=str, default=None, help='Calea video output')
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"RANDARE AVATAR 3D CU AITVIEWER")
    print(f"{'='*70}\n")

    # Încarcă date
    print(f"Incarcare: {args.pkl_file}")
    data = load_pkl_data(args.pkl_file)

    all_pose = data['smplx']
    print(f"Date incarcate: {len(all_pose)} frame-uri, {all_pose.shape[1]} parametri/frame")

    # Separă componente
    g = all_pose[:, :3]         # global_orient
    b = all_pose[:, 3:66]       # body_pose
    l = all_pose[:, 66:111]     # left_hand
    r = all_pose[:, 111:156]    # right_hand
    j = all_pose[:, 156:159]    # jaw

    # Shape și expression cu fallback
    s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))
    exp = all_pose[:, 169:179] if all_pose.shape[1] >= 179 else np.zeros((len(all_pose), 10))

    # Set correct SMPL-X models path
    smplx_models_path = os.path.join(
        os.path.dirname(__file__),
        'common', 'utils', 'human_model_files'
    )
    C.smplx_models = os.path.abspath(smplx_models_path)
    print(f"Models path: {C.smplx_models}")

    # Use CPU if CUDA not available
    if not torch.cuda.is_available():
        C.device = "cpu"

    # Creează viewer
    print(f"\nCreare viewer...")
    if args.headless:
        print(f"   Mod: HEADLESS (export automat)")
        viewer = HeadlessRenderer(size=(1920, 1080))
    else:
        print(f"   Mod: INTERACTIV")
        viewer = Viewer(size=(1920, 1080))

    # SMPL-X Layer
    smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)

    # Secvență SMPL-X
    print(f"Generare mesh-uri...")
    smpl_sequence = SMPLSequence(
        poses_body=b,
        poses_root=g,
        poses_left_hand=l,
        poses_right_hand=r,
        betas=s,
        smpl_layer=smpl_layer,
        color=(0.95, 0.70, 0.60, 1.0),  # Culoare caldă pentru vizibilitate
        rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi),
        name=os.path.basename(args.pkl_file).replace('.pkl', '')
    )
    viewer.scene.add(smpl_sequence)

    # Configurare scenă
    print(f"Configurare scena...")
    viewer.scene.light_mode = 'dark'
    viewer.auto_set_camera_target = False
    viewer.scene.camera.position = np.array([0, 0.90, 2.0])
    viewer.scene.camera.target = np.array([0, 0.80, 0])
    viewer.auto_set_floor = False
    viewer.playback_fps = 30
    viewer.scene.fps = 30
    viewer.scene.floor.position = np.array([0, -0.30, 0])
    viewer.scene.origin.enabled = False
    viewer.shadows_enabled = True

    print(f"Gata!\n")

    if not args.headless:
        print(f"{'='*70}")
        print(f"CONTROALE:")
        print(f"{'='*70}")
        print(f"  SPACE      Play/Pause")
        print(f"  . / ,      Frame urmator/anterior")
        print(f"  S          Toggle shadows")
        print(f"  D          Toggle dark mode")
        print(f"  Mouse      Roteste (drag) / Zoom (scroll)")
        print(f"  ESC        Iesire")
        print(f"\n  Export: Menu -> File -> Export Video")
        print(f"{'='*70}\n")
        print(f"Lansare viewer...")
        viewer.run()
    else:
        output_video = args.output or args.pkl_file.replace('.pkl', '_aitviewer.mp4')
        print(f"Export video: {output_video}")
        viewer.save_video(video_dir=output_video, output_fps=30)
        print(f"Video salvat!")
