"""
Creeaza un video continuu din multiple gesturi PKL
În loc să deschidă fiecare gest separat, le concatenează într-un singur video
"""
import sys
import io
import json
import subprocess
from pathlib import Path
import cv2
import numpy as np

              
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
AVATAR_SCRIPT = PROJECT_ROOT / "sign_avatars/vis_opencv.py"

def render_gesture_to_frames(pkl_file):
    """
    Randeaza un gest PKL si returneaza frame-urile ca numpy arrays

    Args:
        pkl_file: Calea catre fisierul PKL

    Returns:
        list: Lista de frame-uri (numpy arrays)
    """
    print(f"  Randare: {Path(pkl_file).name}")

                                                    
                                                                          
                                                     

                                  
    sys.path.insert(0, str(PROJECT_ROOT / "sign_avatars"))

    try:
        from vis_opencv import load_pkl_data
        import torch
        from aitviewer.renderables.smpl import SMPLSequence
        from aitviewer.models.smpl import SMPLLayer
        from aitviewer.configuration import CONFIG as C
        from aitviewer.headless import HeadlessRenderer
        from aitviewer.utils.so3 import aa2rot_numpy

                      
        data = load_pkl_data(pkl_file)
        all_pose = data['smplx']

                           
        g = all_pose[:, :3]
        b = all_pose[:, 3:66]
        l = all_pose[:, 66:111]
        r = all_pose[:, 111:156]
        s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))

                                
        smplx_models_path = PROJECT_ROOT / "sign_avatars/common/utils/human_model_files"
        C.smplx_models = str(smplx_models_path.absolute())

        if not torch.cuda.is_available():
            C.device = "cpu"

                          
        renderer = HeadlessRenderer(size=(1280, 720))

                      
        smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)

                         
        smpl_sequence = SMPLSequence(
            poses_body=b,
            poses_root=g,
            poses_left_hand=l,
            poses_right_hand=r,
            betas=s,
            smpl_layer=smpl_layer,
            color=(0.8, 0.72, 0.425, 1),
            rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi),
            name=Path(pkl_file).stem
        )
        renderer.scene.add(smpl_sequence)

                           
        renderer.scene.light_mode = 'dark'
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.shadows_enabled = True

                                  
        frames = []
        num_frames = len(all_pose)

        for i in range(num_frames):
            smpl_sequence.current_frame_id = i
            pil_image = renderer.get_frame()
            frame_rgb = np.array(pil_image)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            frames.append(frame_bgr)

        print(f"    ✓ {len(frames)} frames randate")
        return frames

    except Exception as e:
        print(f"    ! Eroare: {e}")
        return []

def create_continuous_video(signs, output_video, fps=30, transition_frames=10):
    """
    Creeaza un video continuu din multiple gesturi

    Args:
        signs: Lista de gesturi (dictionaries cu 'word' si 'pkl_file')
        output_video: Calea output video
        fps: FPS pentru video
        transition_frames: Numarul de frame-uri de tranzitie intre gesturi
    """
    print(f"\n{'='*70}")
    print(f"CREARE VIDEO CONTINUU")
    print(f"{'='*70}")
    print(f"Gesturi: {len(signs)}")
    print(f"Output: {output_video}")
    print(f"FPS: {fps}")

    all_frames = []

                         
    for i, sign in enumerate(signs):
        word = sign['word']
        pkl_file = sign['pkl_file']

        print(f"\n[{i+1}/{len(signs)}] {word}")
        frames = render_gesture_to_frames(pkl_file)

        if frames:
            all_frames.extend(frames)

                                                                     
            if i < len(signs) - 1:                        
                print(f"    Adaugare tranzitie...")
                                       
                for j in range(transition_frames // 2):
                    alpha = 1 - (j / (transition_frames // 2))
                    faded = (frames[-1] * alpha).astype(np.uint8)
                    all_frames.append(faded)
                                 
                black_frame = np.zeros_like(frames[-1])
                all_frames.extend([black_frame] * 3)
                                                                                                 

    if not all_frames:
        print("\n! Nu s-au putut genera frame-uri")
        return

                 
    print(f"\nScriere video: {len(all_frames)} frame-uri...")
    height, width = all_frames[0].shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

    for frame in all_frames:
        out.write(frame)

    out.release()

    print(f"✓ Video creat: {output_video}")
    print(f"  Durata: {len(all_frames) / fps:.2f}s")

    return output_video

def main():
    """Functia principala"""
    import argparse

    parser = argparse.ArgumentParser(description="Creeaza video continuu din gesturi")
    parser.add_argument('--text', type=str, required=True, help='Textul de tradus')
    parser.add_argument('--output', type=str, default='output_signs.mp4', help='Fisier output')
    parser.add_argument('--fps', type=int, default=30, help='FPS video')
    args = parser.parse_args()

                         
    from audio_to_sign_language import SignLanguageTranslator

    translator = SignLanguageTranslator()

                                 
    signs = translator.text_to_signs(args.text)

    if not signs:
        print("\n! Nu s-au gasit gesturi")
        return

                   
    output_path = Path(args.output)
    create_continuous_video(signs, output_path, fps=args.fps)

    print(f"\n{'='*70}")
    print(f"✓ FINALIZAT")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
