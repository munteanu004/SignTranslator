"""
Randare avatar 3D cu aitviewer si afisare cu OpenCV
Foloseste aitviewer pentru rendering headless, apoi afiseaza cu OpenCV
"""
import sys
import os
import io
import torch
import pickle
import numpy as np
import cv2
import argparse
from pathlib import Path

# Fix encoding on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from aitviewer.renderables.smpl import SMPLSequence
from aitviewer.models.smpl import SMPLLayer
from aitviewer.configuration import CONFIG as C
from aitviewer.headless import HeadlessRenderer
from aitviewer.utils.so3 import aa2rot_numpy


def load_pkl_data(pkl_path):
    """Load PKL file with CUDA fallback"""
    try:
        data = torch.load(pkl_path, map_location=torch.device('cpu'), weights_only=False)
    except:
        with open(pkl_path, 'rb') as f:
            class CPU_Unpickler(pickle.Unpickler):
                def find_class(self, module, name):
                    if module == 'torch.storage' and name == '_load_from_bytes':
                        return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
                    return super().find_class(module, name)
            data = CPU_Unpickler(f).load()
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--pkl_file', type=str, required=True, help='Calea catre fisierul .pkl')
    parser.add_argument('--fps', type=int, default=30, help='FPS pentru redare')
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"RANDARE AVATAR 3D CU AITVIEWER + OpenCV")
    print(f"{'='*70}\n")

    # Incarca date
    print(f"Incarcare: {args.pkl_file}")
    data = load_pkl_data(args.pkl_file)

    all_pose = data['smplx']
    print(f"Date incarcate: {len(all_pose)} frame-uri, {all_pose.shape[1]} parametri/frame")

    # Separa componente
    g = all_pose[:, :3]         # global_orient
    b = all_pose[:, 3:66]       # body_pose
    l = all_pose[:, 66:111]     # left_hand_pose
    r = all_pose[:, 111:156]    # right_hand_pose
    j = all_pose[:, 156:159]    # jaw_pose
    s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))
    exp = all_pose[:, 169:179] if all_pose.shape[1] >= 179 else np.zeros((len(all_pose), 10))

    # Set correct SMPL-X models path
    smplx_models_path = os.path.join(
        os.path.dirname(__file__),
        'common', 'utils', 'human_model_files'
    )
    C.smplx_models = os.path.abspath(smplx_models_path)

    # Use CPU if CUDA not available
    if not torch.cuda.is_available():
        C.device = "cpu"

    # Creeaza renderer headless
    print(f"\nCreare renderer headless...")
    renderer = HeadlessRenderer(size=(1280, 720))

    # SMPL-X Layer
    smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)

    # Secventa SMPL-X
    print(f"Generare mesh-uri...")
    smpl_sequence = SMPLSequence(
        poses_body=b,
        poses_root=g,
        poses_left_hand=l,
        poses_right_hand=r,
        betas=s,
        smpl_layer=smpl_layer,
        color=(0.8, 0.72, 0.425, 1),
        rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi),
        name=os.path.basename(args.pkl_file).replace('.pkl', '')
    )
    renderer.scene.add(smpl_sequence)

    # Configurare scena
    print(f"Configurare scena...")
    renderer.scene.light_mode = 'dark'
    renderer.auto_set_camera_target = False
    renderer.scene.camera.position = np.array([0, 0.90, 2.0])
    renderer.scene.camera.target = np.array([0, 0.80, 0])
    renderer.auto_set_floor = False
    renderer.playback_fps = args.fps
    renderer.scene.fps = args.fps
    renderer.scene.floor.position = np.array([0, -0.30, 0])
    renderer.scene.origin.enabled = False
    renderer.shadows_enabled = True

    print(f"\nGata! Rendering frames...")

    # Render toate frame-urile
    frames = []
    num_frames = len(all_pose)

    for i in range(num_frames):
        # Set frame curent
        smpl_sequence.current_frame_id = i

        # Render frame - returns PIL Image
        pil_image = renderer.get_frame()

        # Convert PIL Image -> numpy array -> BGR pentru OpenCV
        frame_rgb = np.array(pil_image)
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        frames.append(frame_bgr)

        print(f"  Frame {i+1}/{num_frames} rendered", end='\r')

    print(f"\n\nAfisare animatie cu OpenCV...")
    print(f"{'='*70}")
    print(f"CONTROALE:")
    print(f"{'='*70}")
    print(f"  SPACE      Play/Pause")
    print(f"  q / ESC    Iesire")
    print(f"  , / .      Frame anterior/urmator")
    print(f"{'='*70}\n")

    # Afisare cu OpenCV
    cv2.namedWindow('Avatar 3D - POISSON', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Avatar 3D - POISSON', 1280, 720)

    current_frame = 0
    playing = True
    frame_delay = int(1000 / args.fps)

    while True:
        # Afiseaza frame-ul curent
        frame = frames[current_frame].copy()

        # Adauga text cu frame number
        cv2.putText(frame, f"Frame: {current_frame+1}/{num_frames}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Avatar 3D - POISSON', frame)

        # Wait for key
        key = cv2.waitKey(frame_delay if playing else 0) & 0xFF

        if key == ord('q') or key == 27:  # q sau ESC
            break
        elif key == ord(' '):  # SPACE
            playing = not playing
        elif key == ord(','):  # Frame anterior
            current_frame = max(0, current_frame - 1)
            playing = False
        elif key == ord('.'):  # Frame urmator
            current_frame = min(num_frames - 1, current_frame + 1)
            playing = False

        # Avansare automata daca playing
        if playing:
            current_frame = (current_frame + 1) % num_frames

    cv2.destroyAllWindows()
    print("\nInchis!")
