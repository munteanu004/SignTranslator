"""
PIPELINE CU VIDEO CONCATENAT: Audio/Video → Text → Video Limbaj Semne

Îmbunătățire față de versiunea improved:
- Toate gesturile într-un singur video MP4
- NU mai sunt ferestre separate
- Output: un singur fișier video cu toată propoziția
"""
import sys
import io
import os
import json
import time
import torch
import pickle
import numpy as np
import cv2
import threading
from pathlib import Path
import re
import math

              
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

                                        
_project_root = Path(__file__).parent.parent
for _p in [
    str(_project_root / "sign_avatars" / "visualizer"),
    str(_project_root / "sign_avatars" / "common" / "utils"),
    str(_project_root),
]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

                   
from aitviewer.renderables.smpl import SMPLSequence
from aitviewer.models.smpl import SMPLLayer
from aitviewer.configuration import CONFIG as C
from aitviewer.headless import HeadlessRenderer
from aitviewer.utils.so3 import aa2rot_numpy


                                                                                            
def aa_to_quat(v):
    """Convert axis-angle 3-vector to quaternion [w,x,y,z]."""
    theta = np.linalg.norm(v)
    if theta < 1e-8:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=float)
    axis = v / theta
    w = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)
    x, y, z = axis * s
    return np.array([w, x, y, z], dtype=float)


def quat_to_aa(q):
    """Convert quaternion [w,x,y,z] to axis-angle 3-vector."""
    w, x, y, z = q
               
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n == 0:
        return np.zeros(3, dtype=float)
    w /= n; x /= n; y /= n; z /= n
    angle = 2.0 * math.acos(max(-1.0, min(1.0, w)))
    s = math.sqrt(1.0 - w * w)
    if s < 1e-8:
                                          
        return np.zeros(3, dtype=float)
    axis = np.array([x, y, z]) / s
    return axis * angle


def quat_slerp(q1, q2, t):
    """Spherical linear interpolation between two quaternions."""
                      
    q1 = q1 / np.linalg.norm(q1)
    q2 = q2 / np.linalg.norm(q2)
    dot = np.dot(q1, q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
    if dot > 0.9995:
                                           
        q = q1 + t * (q2 - q1)
        return q / np.linalg.norm(q)
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    a = math.sin((1 - t) * theta_0) / sin_theta_0
    b = math.sin(t * theta_0) / sin_theta_0
    q = a * q1 + b * q2
    return q / np.linalg.norm(q)


def aa_slerp(a_pose, b_pose, t):
    """Slerp each 3-element axis-angle subvector between a_pose and b_pose.

    a_pose and b_pose are 1D numpy arrays with length multiple of 3.
    Returns a 1D numpy array of same shape with interpolated axis-angle vectors.
    """
    assert a_pose.shape == b_pose.shape
    n = a_pose.shape[0]
    out = np.zeros_like(a_pose)
    for i in range(0, n, 3):
        va = a_pose[i:i+3]
        vb = b_pose[i:i+3]
        qa = aa_to_quat(va)
        qb = aa_to_quat(vb)
        qm = quat_slerp(qa, qb, t)
        out[i:i+3] = quat_to_aa(qm)
    return out

                                                                                                          
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

                                                     
from integration.translator_enhanced import EnhancedTranslator

       
DICTIONARY_PATH = PROJECT_ROOT / "integration/romanian_sign_dictionary.json"

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


class VideoSignLanguageTranslator:
    """Traductor cu output VIDEO (toate gesturile concatenate)"""

    def __init__(self, whisper_model="base"):
        self.whisper_model_name = whisper_model
        self.whisper_model = None
                                                                                         
        self.dictionary = self.load_dictionary()
                                                                   
        self.en_translator = EnhancedTranslator()

                            
        smplx_models_path = os.path.join(
            PROJECT_ROOT,
            'sign_avatars', 'common', 'utils', 'human_model_files'
        )
        C.smplx_models = os.path.abspath(smplx_models_path)

                                       
        if not torch.cuda.is_available():
            C.device = "cpu"

        total_words = len(self.dictionary)
        print(f"✓ Dictionar incarcat: {total_words} cuvinte")
        print(f"✓ Model Whisper selectat: {whisper_model}")

    def load_dictionary(self):
        """Incarca dictionarul romana -> PKL"""
        if not DICTIONARY_PATH.exists():
            print(f"! Dictionar negasit: {DICTIONARY_PATH}")
            return {}

        with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_whisper_model(self):
        """Incarca modelul Whisper (lazy loading)"""
        if self.whisper_model is not None:
            return self.whisper_model

        try:
            import whisper
        except ImportError:
            print("! Whisper nu este instalat!")
            print("! Instalati cu: pip install openai-whisper")
            return None

        print(f"Incarcare model Whisper '{self.whisper_model_name}'...")
        start_time = time.time()
        self.whisper_model = whisper.load_model(self.whisper_model_name)
        load_time = time.time() - start_time

        print(f"✓ Model incarcat in {load_time:.1f} secunde")
        return self.whisper_model

    def transcribe_audio(self, audio_file, language="ro"):
        """Transcrie fisier audio folosind Whisper"""
        print(f"\n{'='*70}")
        print(f"PASUL 1: TRANSCRIERE AUDIO")
        print(f"{'='*70}")
        print(f"Fisier: {audio_file}")

        model = self.load_whisper_model()
        if model is None:
            return None

        print("Transcriere in curs...")
        start_time = time.time()

        result = model.transcribe(str(audio_file), language=language, task='transcribe', verbose=False)

        transcribe_time = time.time() - start_time
        text = result["text"].strip()

        print(f"\n✓ Transcriere finalizata in {transcribe_time:.1f} secunde")
        print(f"✓ Text transcris:")
        print(f'   "{text}"')

        return {'text': text, 'language': language, 'duration': transcribe_time}

    def text_to_signs(self, text):
        """Converteste text in secventa de gesturi PKL"""
        print(f"\n{'='*70}")
        print(f"PASUL 2: TEXT → (RO→EN) → GESTURI")
        print(f"{'='*70}")

        text = text.strip()

                                                                                                
        english_text = self.en_translator.translate_sentence_ro_to_en(text)
        print(f"Text original: {text}")
        print(f"Text tradus RO→EN: {english_text}")

                                                                 
        ro_norm = re.sub(r"[^\w\s]", "", text.lower())
        ro_words = ro_norm.split()

                                
        english_text = re.sub(r"[^\w\s]", "", english_text.lower())
        words = english_text.split()

        print(f"Cuvinte (EN): {words}\n")

        signs = []
        not_found = []

        for i, word in enumerate(words):
                                                                   
            found = self.en_translator.find_sign_by_english(word)
            if found:
                signs.append({
                    'word': found['word'],
                    'pkl_file': found['pkl_file'],
                    'english': found.get('english', word),
                    'method': found.get('method', ''),
                    'input_word': word,
                    'input_ro': ro_words[i] if i < len(ro_words) else word
                })
                print(f"   ✓ EN '{word}' -> PKL {Path(found['pkl_file']).name} via {found.get('method')}")
                continue

                                                                                       
            ro_word = word               
            if ro_word in self.dictionary:
                pkl_file = self.dictionary[ro_word]['pkl_file']
                english = self.dictionary[ro_word].get('english_translation', '')

                signs.append({
                    'word': ro_word,
                    'pkl_file': pkl_file,
                    'english': english,
                    'input_word': ro_word,
                    'input_ro': ro_word
                })
                print(f"   ✓ RO fallback '{ro_word}' -> {english}")
            else:
                not_found.append(word)
                print(f"   ✗ '{word}' -> NU GASIT")

        total_words = len(words)
        found_words = len(signs)
        coverage = (found_words / total_words * 100) if total_words > 0 else 0

        print(f"\n{'='*50}")
        print(f"STATISTICI MAPARE:")
        print(f"  Total cuvinte: {total_words}")
        print(f"  Cuvinte gasite: {found_words}")
        print(f"  Coverage: {coverage:.1f}%")
        print(f"{'='*50}")

        return {'signs': signs, 'stats': {'total_words': total_words, 'found_words': found_words, 'coverage_percent': coverage}}

    def render_video(self, signs, output_file="output_video.mp4", fps=30, quality="medium"):
        """
        Randeaza toate gesturile intr-un singur video MP4

        Args:
            signs: Lista de gesturi PKL
            output_file: Nume fisier output
            fps: Framerate (default 30)
            quality: "low" (480p, rapid), "medium" (720p HD), "high" (1080p Full HD)
        """
        print(f"\n{'='*70}")
        print(f"PASUL 3: GENERARE VIDEO CONCATENAT")
        print(f"{'='*70}")

        if not signs:
            print("! Nu exista gesturi de randat")
            return None

                          
        quality_settings = {
            "low": (640, 480),                                   
            "medium": (1280, 720),                       
            "high": (1920, 1080),                                              
        }

        resolution = quality_settings.get(quality, (1280, 720))

        all_frames = []
        total_signs = len(signs)

        print(f"\nRandare {total_signs} gesturi...")
        print(f"Output: {output_file}")
        print(f"Calitate: {quality} ({resolution[0]}x{resolution[1]})")
        print(f"FPS: {fps}\n")

                                                     
        renderer = HeadlessRenderer(size=resolution)

                                                             
        renderer.scene.light_mode = 'dark'
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled = False
        renderer.shadows_enabled = False                             

        for i, sign in enumerate(signs):
            word = sign['word']
            pkl_file = sign['pkl_file']
            english = sign.get('english', '')
            input_ro = sign.get('input_ro', sign.get('input_word', word))

            print(f"[{i+1}/{total_signs}] Randare: '{word}' ({english})")

            try:
                             
                data = load_pkl_data(pkl_file)
                all_pose = data['smplx']

                                   
                g = all_pose[:, :3]                        
                b = all_pose[:, 3:66]                  
                l = all_pose[:, 66:111]                     
                r = all_pose[:, 111:156]                     
                s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))

                                       
                smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
                smpl_sequence = SMPLSequence(
                    poses_body=b,
                    poses_root=g,
                    poses_left_hand=l,
                    poses_right_hand=r,
                    betas=s,
                    smpl_layer=smpl_layer,
                    color=(0.8, 0.72, 0.425, 1),
                    rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi)
                )

                renderer.scene.add(smpl_sequence)

                num_frames = len(all_pose)
                print(f"  {num_frames} frames")

                                        
                for frame_idx in range(num_frames):
                    smpl_sequence.current_frame_id = frame_idx

                                           
                    pil_image = renderer.get_frame()

                                                 
                    frame_rgb = np.array(pil_image)
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                                             
                    cv2.putText(frame_bgr, f"{input_ro} ({english})",
                                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)

                    all_frames.append(frame_bgr)

                print(f"  ✓ Randat {num_frames} frames")

                                                       
                renderer.scene.remove(smpl_sequence)

            except Exception as e:
                print(f"  ! Eroare la randare: {e}")
                import traceback
                traceback.print_exc()
                continue

        if not all_frames:
            print("\n! Nu s-au putut randa frame-uri")
            return None

        print(f"\n{'='*70}")
        print(f"SALVARE VIDEO")
        print(f"{'='*70}")
        print(f"Total frames: {len(all_frames)}")
        print(f"Durata: {len(all_frames)/fps:.1f} secunde")

                               
        height, width, _ = all_frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

        for frame in all_frames:
            video_writer.write(frame)

        video_writer.release()

        print(f"\n✓ Video salvat: {output_file}")
        print(f"  Rezolutie: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Frames: {len(all_frames)}")

        return output_file

    def render_video_with_callback(self, signs, output_file="output_video.mp4", fps=30, frame_callback=None):
        """
        Randeaza video cu callback pentru fiecare frame (pentru GUI real-time)

        Args:
            signs: Lista de gesturi PKL
            output_file: Nume fisier output
            fps: Framerate
            frame_callback: Functie callback(frame_bgr, frame_idx, total_frames) pentru fiecare frame
        """
        print(f"\n{'='*70}")
        print(f"PASUL 3: GENERARE VIDEO CONCATENAT (cu callback)")
        print(f"{'='*70}")

        if not signs:
            print("! Nu exista gesturi de randat")
            return None

        all_frames = []
        total_signs = len(signs)
        frame_counter = 0

        print(f"\nRandare {total_signs} gesturi...")
        print(f"Output: {output_file}")
        print(f"FPS: {fps}\n")

                                                          
        renderer = HeadlessRenderer(size=(640, 480))

                                                     
        renderer.scene.light_mode = 'dark'
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled = False
        renderer.shadows_enabled = False                             

                                                 
        total_frames_estimated = sum(len(load_pkl_data(sign['pkl_file'])['smplx']) for sign in signs)

        for i, sign in enumerate(signs):
            word = sign['word']
            pkl_file = sign['pkl_file']
            english = sign.get('english', '')
            input_ro = sign.get('input_ro', sign.get('input_word', word))

            print(f"[{i+1}/{total_signs}] Randare: '{word}' ({english})")

            try:
                             
                data = load_pkl_data(pkl_file)
                all_pose = data['smplx']

                                   
                g = all_pose[:, :3]
                b = all_pose[:, 3:66]
                l = all_pose[:, 66:111]
                r = all_pose[:, 111:156]
                s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))

                                       
                smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
                smpl_sequence = SMPLSequence(
                    poses_body=b,
                    poses_root=g,
                    poses_left_hand=l,
                    poses_right_hand=r,
                    betas=s,
                    smpl_layer=smpl_layer,
                    color=(0.8, 0.72, 0.425, 1),
                    rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi)
                )

                renderer.scene.add(smpl_sequence)

                num_frames = len(all_pose)
                print(f"  {num_frames} frames")

                                        
                for frame_idx in range(num_frames):
                    smpl_sequence.current_frame_id = frame_idx

                            
                    pil_image = renderer.get_frame()
                    frame_rgb = np.array(pil_image)
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                                  
                    cv2.putText(frame_bgr, f"{input_ro} ({english})",
                                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)

                    all_frames.append(frame_bgr)

                                                                        
                    if frame_callback:
                        frame_callback(frame_bgr, frame_counter, total_frames_estimated)

                    frame_counter += 1

                print(f"  ✓ Randat {num_frames} frames")
                renderer.scene.remove(smpl_sequence)

            except Exception as e:
                print(f"  ! Eroare: {e}")
                import traceback
                traceback.print_exc()
                continue

        if not all_frames:
            print("\n! Nu s-au putut randa frame-uri")
            return None

                        
        print(f"\n{'='*70}")
        print(f"SALVARE VIDEO")
        print(f"{'='*70}")

        height, width, _ = all_frames[0].shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

        for frame in all_frames:
            video_writer.write(frame)

        video_writer.release()

        print(f"\n✓ Video salvat: {output_file}")
        return output_file

    def display_frames_cv2(self, signs, fps=30, mode='full', hold_seconds=1.0, speed=1.0, blend_seconds=0.2):
        """Display rendered frames in an OpenCV window in realtime.

        Renders each sign into an in-memory list and then builds a playback
        sequence. In `single` mode we take a short centered window from each
        sign and interpolate SMPL poses between signs to produce a smooth
        transition (pose-level interpolation, not pixel cross-fade).
        """
        print("\n✓ Start OpenCV display (apasa 'q' pentru a opri)")

        print("\nPre-rendering (optimized): rendering minimal frames per PKL and caching results...")

                                                          
        n_signs = len(signs)
        sign_frames = [None] * n_signs
        sign_first_pose = [None] * n_signs
        sign_last_pose = [None] * n_signs
        labels = [None] * n_signs

                                                        
        pkl_cache = {}
        cache_lock = threading.Lock()

        renderer = HeadlessRenderer(size=(640, 480))
        renderer.scene.light_mode = 'dark'
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled = False
        renderer.shadows_enabled = False

                                                                                 
        def render_pkl_frames(pkl_file, indices_to_render, renderer_for_render):
            with cache_lock:
                if pkl_file in pkl_cache:
                    return pkl_cache[pkl_file]

            data = load_pkl_data(pkl_file)
            all_pose = data['smplx']

                                    
            first_pose = all_pose[0].copy()
            last_pose = all_pose[-1].copy()

                                                                     
            g = all_pose[:, :3]
            b = all_pose[:, 3:66]
            l = all_pose[:, 66:111]
            r = all_pose[:, 111:156]
            s = all_pose[:, 159:169] if all_pose.shape[1] >= 169 else np.zeros((len(all_pose), 10))

            smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
            smpl_sequence = SMPLSequence(
                poses_body=b,
                poses_root=g,
                poses_left_hand=l,
                poses_right_hand=r,
                betas=s,
                smpl_layer=smpl_layer,
                color=(0.8, 0.72, 0.425, 1),
                rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi)
            )

                                                                                 
            renderer_for_render.scene.add(smpl_sequence)
            frames = []
            try:
                for fi in indices_to_render:
                    fi_clamped = max(0, min(len(all_pose) - 1, fi))
                    smpl_sequence.current_frame_id = fi_clamped
                    pil_image = renderer_for_render.get_frame()
                    frame_rgb = np.array(pil_image)
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                    frames.append(frame_bgr)
            finally:
                renderer_for_render.scene.remove(smpl_sequence)

            info = {
                'frames': frames,
                'first_pose': first_pose,
                'last_pose': last_pose
            }

            with cache_lock:
                pkl_cache[pkl_file] = info

            return info

                                                                                    
        sync_prefill = 2 if n_signs >= 2 else 1

                                                     
        frames_per_clip = max(1, int(round(hold_seconds * fps)))

                                          
        def render_sign(i):
            sign = signs[i]
            pkl_file = sign['pkl_file']
            input_ro = sign.get('input_ro', sign.get('input_word', sign.get('word', '')))
            label = f"{input_ro} ({sign.get('english','')})"
            labels[i] = label

                                     
            data = load_pkl_data(pkl_file)
            all_pose = data['smplx']
            count = len(all_pose)

            if mode == 'single':
                mid = count // 2
                half = frames_per_clip // 2
                start = max(0, mid - half)
                end = min(count, start + frames_per_clip)
                indices = list(range(start, end))
            else:
                indices = list(range(count))

                                      
            info = render_pkl_frames(pkl_file, indices, label)
            sign_frames[i] = info['frames']
            sign_first_pose[i] = info['first_pose']
            sign_last_pose[i] = info['last_pose']

            print(f"  Prepared sign {i+1}/{n_signs}: {label} ({len(sign_frames[i])} frames)")

                                              
        try:
            for i in range(min(sync_prefill, n_signs)):
                render_sign(i)
        except KeyboardInterrupt:
            print("\nPre-rendering interrupted by user")

                                                                               
        def background_renderer(start_idx=0):
                                                                                        
            try:
                bg_renderer = HeadlessRenderer(size=(640, 480))
            except Exception:
                                                             
                try:
                    bg_renderer = HeadlessRenderer(size=(320, 240))
                except Exception as e:
                    print(f"  ! Background renderer init failed: {e}")
                    return

            bg_renderer.scene.light_mode = 'dark'
            bg_renderer.auto_set_camera_target = False
            bg_renderer.scene.camera.position = np.array([0, 0.90, 2.0])
            bg_renderer.scene.camera.target = np.array([0, 0.80, 0])
            bg_renderer.auto_set_floor = False
            bg_renderer.scene.floor.position = np.array([0, -0.30, 0])
            bg_renderer.scene.origin.enabled = False
            bg_renderer.shadows_enabled = False

            for j in range(start_idx, n_signs):
                try:
                    sign = signs[j]
                    pkl_file = sign['pkl_file']

                                                                                 
                    data_tmp = load_pkl_data(pkl_file)
                    count_tmp = len(data_tmp['smplx'])
                    if mode == 'single':
                        mid = count_tmp // 2
                        half = frames_per_clip // 2
                        start = max(0, mid - half)
                        end = min(count_tmp, start + frames_per_clip)
                        indices = list(range(start, end))
                    else:
                        indices = list(range(count_tmp))

                    info = render_pkl_frames(pkl_file, indices, bg_renderer)
                    with cache_lock:
                                                                       
                        for idx_j, f in enumerate(info['frames']):
                            if sign_frames[j] is None:
                                sign_frames[j] = info['frames']
                                sign_first_pose[j] = info['first_pose']
                                sign_last_pose[j] = info['last_pose']
                                labels[j] = f"{sign.get('input_ro', sign.get('input_word', sign.get('word','')))} ({sign.get('english','')})"
                                break
                    print(f"  Prepared sign {j+1}/{n_signs} (bg): {labels[j]} ({len(info['frames'])} frames)")
                except Exception as e:
                    print(f"  ! Background render error for sign {j}: {e}")
                    import traceback
                    traceback.print_exc()

        bg_thread = None
        if sync_prefill < n_signs:
            bg_thread = threading.Thread(target=background_renderer, args=(sync_prefill,))
            bg_thread.daemon = True
            bg_thread.start()

                                                                                                      
        cv2.namedWindow('SignAnimation', cv2.WINDOW_NORMAL)

        current_sign = 0
        playing = True
        frame_delay = max(1, int(round(1000.0 / (fps * max(0.001, speed)))))

        print(f"\nAfisare animatie (streaming) cu OpenCV. Controale: SPACE play/pause, q/ESC iesire, ,/. prev/next")

        while current_sign < n_signs:
                                                              
            wait_count = 0
            while sign_frames[current_sign] is None:
                time.sleep(0.05)
                wait_count += 1
                if wait_count > 200:
                                        
                    print(f"\n! Timeout waiting for sign {current_sign+1} to render")
                    return

            clip = sign_frames[current_sign]
            label = labels[current_sign]

                                         
            for f_idx, frame in enumerate(clip):
                display = frame.copy()
                cv2.putText(display, f"{label}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
                cv2.putText(display, f"Sign: {current_sign+1}/{n_signs} Frame: {f_idx+1}/{len(clip)}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('SignAnimation', display)

                key = cv2.waitKey(frame_delay if playing else 0) & 0xFF
                if key == ord('q') or key == 27:
                    cv2.destroyAllWindows()
                    return
                elif key == ord(' '):
                    playing = not playing
                elif key == ord(','):
                                         
                    current_sign = max(0, current_sign - 1)
                    break
                elif key == ord('.'):
                                       
                    break

                                                            
            if current_sign + 1 < n_signs:
                                                    
                wait_count = 0
                while sign_first_pose[current_sign+1] is None:
                    time.sleep(0.02)
                    wait_count += 1
                    if wait_count > 200:
                        break

                a_pose = sign_last_pose[current_sign]
                b_pose = sign_first_pose[current_sign+1]
                if a_pose is not None and b_pose is not None:
                    blend_frames = max(1, int(round(blend_seconds * fps)))
                                                                                                        
                                                                                                
                    for t in range(1, blend_frames + 1):
                        alpha = t / (blend_frames + 1)

                        try:
                            interp_pose = aa_slerp(a_pose, b_pose, alpha)
                        except Exception:
                                                                             
                            interp_pose = (1.0 - alpha) * a_pose + alpha * b_pose

                                                    
                        g = interp_pose[:3]
                        bod = interp_pose[3:66]
                        lef = interp_pose[66:111]
                        rig = interp_pose[111:156]
                        bet = interp_pose[159:169] if interp_pose.shape[0] >= 169 else np.zeros((10,))

                        smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
                        smpl_sequence = SMPLSequence(
                            poses_body=bod.reshape(1, -1),
                            poses_root=g.reshape(1, -1),
                            poses_left_hand=lef.reshape(1, -1),
                            poses_right_hand=rig.reshape(1, -1),
                            betas=bet.reshape(1, -1),
                            smpl_layer=smpl_layer,
                            color=(0.8, 0.72, 0.425, 1),
                            rotation=aa2rot_numpy(np.array([1, 0, 0]) * np.pi)
                        )

                        renderer.scene.add(smpl_sequence)
                        smpl_sequence.current_frame_id = 0
                        pil_image = renderer.get_frame()
                        frame_rgb = np.array(pil_image)
                        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

                                                                                                               
                        if len(clip) > 0:
                            prev_frame = clip[-1]
                            fade_alpha = 0.5 * (1.0 - (t / (blend_frames + 1)))
                            display = cv2.addWeighted(prev_frame, fade_alpha, frame_bgr, 1.0 - fade_alpha, 0)
                        else:
                            display = frame_bgr.copy()

                        cv2.putText(display, f"(transition)", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
                        cv2.imshow('SignAnimation', display)
                        key = cv2.waitKey(frame_delay if playing else 0) & 0xFF
                        if key == ord('q') or key == 27:
                            cv2.destroyAllWindows()
                            return
                        renderer.scene.remove(smpl_sequence)

            current_sign += 1

        cv2.destroyAllWindows()

        cv2.destroyAllWindows()


def main():
    """Functia principala"""
    print("\n" + "="*70)
    print("SIGN LANGUAGE TRANSLATOR - VIDEO CONCATENAT")
    print("="*70)

    import argparse
    parser = argparse.ArgumentParser(
        description="Traductor cu video concatenat (toate gesturile intr-un singur fisier)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:

  # Text direct
  python audio_to_sign_video.py --text "copil iubi animal" --output "test.mp4"

  # Audio cu model base
  python audio_to_sign_video.py --audio "input.mp3" --model base --output "traducere.mp4"

  # Audio cu model medium
  python audio_to_sign_video.py --audio "input.mp3" --model medium --output "traducere.mp4"
        """
    )
    parser.add_argument('--audio', type=str, help='Fisier audio/video de transcris')
    parser.add_argument('--text', type=str, help='Text direct (skip transcriere)')
    parser.add_argument('--model', type=str, default='base',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Model Whisper (default: base)')
    parser.add_argument('--output', '-o', type=str, default='output_signs.mp4',
                        help='Fisier output video (default: output_signs.mp4)')
    parser.add_argument('--fps', type=int, default=30,
                        help='Framerate video (default: 30)')
    parser.add_argument('--realtime', action='store_true', help='Enable realtime frame callback (no final file saving until done)')
    parser.add_argument('--mode', type=str, choices=['full', 'single'], default='full',
                        help='Playback mode for realtime: "full" = all frames, "single" = one representative frame per sign')
    parser.add_argument('--hold-seconds', type=float, default=1.0,
                        help='When --mode single: approximate duration in seconds for the short motion clip shown per sign (preserves motion)')
    parser.add_argument('--speed', type=float, default=1.0,
                        help='Playback speed multiplier for realtime display (e.g., 2.0 = 2x faster, 0.5 = half speed)')
    parser.add_argument('--blend-seconds', type=float, default=0.2,
                        help='Cross-dissolve duration in seconds between clips to smooth transitions')

    args = parser.parse_args()

                                
    translator = VideoSignLanguageTranslator(whisper_model=args.model)

                      
    if args.text:
        text = args.text
        print(f"\nMod: TEXT DIRECT")
        print(f"Text: \"{text}\"")
    elif args.audio:
        audio_file = Path(args.audio)
        if not audio_file.exists():
            print(f"! Fisier negasit: {audio_file}")
            return

        transcription_result = translator.transcribe_audio(audio_file)

        if not transcription_result:
            return

        text = transcription_result['text']
    else:
        print(f"\nMod: DEMO")
        text = "copil iubi animal"
        print(f"Text demo: \"{text}\"")

                            
    result = translator.text_to_signs(text)
    signs = result['signs']

    if not signs:
        print("\n! Nu s-au gasit gesturi pentru acest text")
        return

                    
                                                 
    if args.realtime:
                                                        
        def frame_cb(frame_bgr, frame_idx, total_frames):
            pct = (frame_idx / total_frames * 100) if total_frames > 0 else 0
            if frame_idx % max(1, total_frames//10) == 0:
                print(f"[Realtime] frame {frame_idx}/{total_frames} ({pct:.0f}% )")
                                                                              
        try:
            translator.display_frames_cv2(signs, fps=args.fps, mode=args.mode, hold_seconds=args.hold_seconds, speed=args.speed, blend_seconds=args.blend_seconds)
            output_file = None
        except Exception:
                                                           
            output_file = translator.render_video_with_callback(signs, output_file=args.output, fps=args.fps, frame_callback=frame_cb)
    else:
        output_file = translator.render_video(signs, output_file=args.output, fps=args.fps)

    if output_file:
        print(f"\n{'='*70}")
        print(f"✓ FINALIZAT")
        print(f"{'='*70}")
        print(f"\nVideo generat: {output_file}")
        print(f"Poti vedea videoul cu:")
        print(f"  - Windows Media Player")
        print(f"  - VLC Player")
        print(f"  - Orice player video")
        print()

if __name__ == "__main__":
    main()
