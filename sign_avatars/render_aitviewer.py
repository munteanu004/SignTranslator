"""
Script de randare folosind aitviewer - Viewer 3D Interactiv
Adaptat pentru fișierele PKL din SignTranslator
"""

import os
import sys
import numpy as np
import torch
import pickle

# Verificare aitviewer
try:
    from aitviewer.configuration import CONFIG as C
    from aitviewer.headless import HeadlessRenderer
    from aitviewer.models.smpl import SMPLLayer
    from aitviewer.renderables.smpl import SMPLSequence
    from aitviewer.utils.so3 import aa2rot_numpy
    from aitviewer.viewer import Viewer
    print("✓ aitviewer găsit!")
except ImportError as e:
    print(f"❌ EROARE: aitviewer nu este instalat!")
    print(f"   Rulează: cd visualizer && pip install -e .")
    print(f"   Eroare: {e}")
    sys.exit(1)

from argparse import ArgumentParser


def load_pkl_data(pkl_path):
    """Încarcă date PKL cu suport CUDA -> CPU"""
    print(f"Încărcare: {pkl_path}")

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


def render_avatar(pkl_path, headless=False, output_video=None):
    """
    Randează avatar folosind aitviewer

    Args:
        pkl_path: Calea către fișierul PKL
        headless: True = export video automat, False = viewer interactiv
        output_video: Calea pentru video output (doar dacă headless=True)
    """

    print(f"\n{'='*60}")
    print(f"RANDARE AVATAR CU AITVIEWER")
    print(f"{'='*60}\n")

    # Încarcă date
    data = load_pkl_data(pkl_path)

    if 'smplx' not in data:
        print(f"❌ EROARE: Fișierul nu conține date 'smplx'!")
        return

    all_pose = data['smplx']
    print(f"✓ Date încărcate: {len(all_pose)} frame-uri")

    # Separă componentele SMPL-X
    g = all_pose[:, :3]          # global_orient (3)
    b = all_pose[:, 3:66]        # body_pose (63)
    l = all_pose[:, 66:111]      # left_hand_pose (45)
    r = all_pose[:, 111:156]     # right_hand_pose (45)
    j = all_pose[:, 156:159]     # jaw_pose (3)

    # Shape și expression
    if all_pose.shape[1] >= 169:
        s = all_pose[:, 159:169]  # betas (10)
    else:
        s = np.zeros((len(all_pose), 10))

    if all_pose.shape[1] >= 179:
        exp = all_pose[:, 169:179]  # expression (10)
    else:
        exp = np.zeros((len(all_pose), 10))

    print(f"  - Global orient: {g.shape}")
    print(f"  - Body pose: {b.shape}")
    print(f"  - Hands: L={l.shape}, R={r.shape}")
    print(f"  - Face: jaw={j.shape}, expr={exp.shape}")

    # Creează viewer
    print(f"\nCreare viewer 3D...")
    if headless:
        print(f"  Mod: HEADLESS (export video automat)")
        viewer = HeadlessRenderer(size=(1920, 1080))
    else:
        print(f"  Mod: INTERACTIV (folosește mouse și taste)")
        viewer = Viewer(size=(1920, 1080))

    # Creează SMPL-X layer
    smpl_layer = SMPLLayer(
        model_type="smplx",
        gender="neutral",
        flat_hand_mean=False,
        device=C.device
    )

    # Creează secvența SMPL-X
    print(f"Generare mesh-uri SMPL-X...")
    smpl_sequence = SMPLSequence(
        poses_body=b,
        poses_root=g,
        poses_left_hand=l,
        poses_right_hand=r,
        betas=s,
        smpl_layer=smpl_layer,
        color=(0.95, 0.75, 0.65, 1.0),  # Culoare piele naturală
        rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi),  # Rotire 180° pe X
        name=os.path.basename(pkl_path)
    )

    viewer.scene.add(smpl_sequence)

    # Configurare scenă pentru vizibilitate MAXIMĂ a mâinilor
    print(f"Configurare scenă pentru mâini clare...")

    # Iluminare
    viewer.scene.light_mode = 'dark'  # Fundal întunecat pentru contrast
    viewer.shadows_enabled = True     # Activează umbre pentru relief

    # Cameră optimizată pentru limbaj semnale
    viewer.auto_set_camera_target = False
    viewer.scene.camera.position = np.array([0.0, 0.9, 2.0])  # Poziție frontală
    viewer.scene.camera.target = np.array([0.0, 0.8, 0.0])    # Focus pe partea superioară

    # Setări animație
    viewer.playback_fps = 30
    viewer.scene.fps = 30

    # Podea
    viewer.auto_set_floor = False
    viewer.scene.floor.position = np.array([0, -0.3, 0])
    viewer.scene.origin.enabled = False

    print(f"✓ Scenă configurată!")

    # Afișare controale
    if not headless:
        print(f"\n{'='*60}")
        print(f"CONTROALE VIEWER:")
        print(f"{'='*60}")
        print(f"  SPACE    - Play/Pause animație")
        print(f"  . / ,    - Frame următor/anterior")
        print(f"  S        - Toggle umbre (shadow)")
        print(f"  D        - Toggle dark mode")
        print(f"  O        - Toggle cameră ortografică")
        print(f"  X        - Centrează camera pe obiect")
        print(f"  P        - Salvează screenshot")
        print(f"  Mouse    - Rotește camera (click + drag)")
        print(f"  Scroll   - Zoom in/out")
        print(f"  ESC      - Ieșire")
        print(f"{'='*60}\n")

        print(f"🎬 Pentru export video:")
        print(f"   Menu: File -> Export Video")
        print(f"   Sau rulează cu --headless pentru export automat")
        print(f"\n{'='*60}\n")

    # Rulare viewer
    if headless:
        if output_video is None:
            output_video = pkl_path.replace('.pkl', '_aitviewer.mp4')

        print(f"Export video: {output_video}")
        viewer.save_video(video_dir=output_video, output_fps=30)
        print(f"✓ Video salvat: {output_video}")
    else:
        print(f"Lansare viewer interactiv...")
        viewer.run()


if __name__ == "__main__":
    parser = ArgumentParser(description='Randare avatar 3D cu aitviewer')

    parser.add_argument(
        'pkl_file',
        type=str,
        help='Calea către fișierul .pkl cu date SMPL-X'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Mod headless: export video automat fără interfață'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Calea pentru video output (doar cu --headless)'
    )

    args = parser.parse_args()

    if not os.path.exists(args.pkl_file):
        print(f"❌ EROARE: Fișierul nu există: {args.pkl_file}")
        sys.exit(1)

    render_avatar(args.pkl_file, args.headless, args.output)
