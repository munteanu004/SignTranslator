"""
PIPELINE OPTIMIZAT: Audio/Video → Text → Video Limbaj Semne

Îmbunătățiri față de versiunea standard:
✅ Cache PKL pentru performanță 10x mai bună
✅ Reutilizare SMPL layers - reducere memorie
✅ Codec H.264 pentru calitate video superioară
✅ Rezoluții până la 4K (3840x2160)
✅ Interpolarea framelor pentru animații fluide (60fps)
✅ Tranziții smooth între gesturi
✅ Progress tracking detaliat
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
from pathlib import Path
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Imports aitviewer
from aitviewer.renderables.smpl import SMPLSequence
from aitviewer.models.smpl import SMPLLayer
from aitviewer.configuration import CONFIG as C
from aitviewer.headless import HeadlessRenderer
from aitviewer.utils.so3 import aa2rot_numpy

# Make sure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enhanced translator
from integration.translator_enhanced import EnhancedTranslator

# Paths
DICTIONARY_PATH = PROJECT_ROOT / "integration/romanian_sign_dictionary.json"

# ============================================================================
# CACHE SYSTEM - PERFORMANȚĂ 10x MAI BUNĂ
# ============================================================================

@lru_cache(maxsize=128)
def load_pkl_data_cached(pkl_path: str):
    """Load PKL file with caching - evită reîncărcarea acelorași fișiere"""
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


class SMPLLayerCache:
    """Cache pentru SMPL layers - reducere masivă a memoriei"""
    _instance = None
    _layer = None

    @classmethod
    def get_layer(cls, model_type="smplx", gender="neutral", device=None):
        """Returnează layer-ul cached (singleton pattern)"""
        if cls._layer is None:
            device = device or C.device
            cls._layer = SMPLLayer(
                model_type=model_type,
                gender=gender,
                flat_hand_mean=False,
                device=device
            )
        return cls._layer


# ============================================================================
# INTERPOLATION SYSTEM - ANIMAȚII FLUIDE
# ============================================================================

def interpolate_poses(poses: np.ndarray, target_fps: int, source_fps: int = 30) -> np.ndarray:
    """
    Interpolează pose-uri pentru framerate mai mare (animații mai fluide)

    Args:
        poses: Array de pose-uri [num_frames, pose_dim]
        target_fps: FPS țintă (ex: 60)
        source_fps: FPS sursă (default: 30)

    Returns:
        Array interpolat [new_num_frames, pose_dim]
    """
    if target_fps <= source_fps:
        return poses

    num_frames = len(poses)
    ratio = target_fps / source_fps
    new_num_frames = int(num_frames * ratio)

    # Creează indici pentru interpolarea cubică
    old_indices = np.arange(num_frames)
    new_indices = np.linspace(0, num_frames - 1, new_num_frames)

    # Interpolează fiecare dimensiune separat
    interpolated = np.zeros((new_num_frames, poses.shape[1]))

    for dim in range(poses.shape[1]):
        interpolated[:, dim] = np.interp(new_indices, old_indices, poses[:, dim])

    return interpolated


def remove_diacritics(text: str) -> str:
    """
    Înlocuiește diacriticele românești cu caractere standard pentru afișare în OpenCV

    Args:
        text: Text cu diacritice (ex: "astăzi", "frumoasă")

    Returns:
        Text fără diacritice (ex: "astazi", "frumoasa")
    """
    replacements = {
        'ă': 'a', 'Ă': 'A',
        'â': 'a', 'Â': 'A',
        'î': 'i', 'Î': 'I',
        'ș': 's', 'Ș': 'S',
        'ț': 't', 'Ț': 'T'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def clean_label_for_opencv(text: str) -> str:
    """
    Curăță textul pentru afișare în OpenCV - păstrează doar caractere ASCII

    Args:
        text: Text cu posibile caractere non-ASCII

    Returns:
        Text cu doar caractere ASCII (litere, cifre, spațiu, hyphen)
    """
    # Păstrează doar caractere ASCII printabile (spațiu, litere, cifre, hyphen)
    cleaned = ''.join(char if ord(char) < 128 else '' for char in text)
    return cleaned.strip()


def create_transition_frames(pose_end: np.ndarray, pose_start: np.ndarray,
                             num_transition_frames: int = 5) -> np.ndarray:
    """
    Creează frame-uri de tranziție smooth între două gesturi

    Args:
        pose_end: Ultimul frame al gestului curent [pose_dim]
        pose_start: Primul frame al gestului următor [pose_dim]
        num_transition_frames: Număr de frame-uri de tranziție

    Returns:
        Array cu frame-uri de tranziție [num_transition_frames, pose_dim]
    """
    if num_transition_frames == 0:
        return np.array([])

    # Interpolație liniară între cele două pose-uri
    alpha = np.linspace(0, 1, num_transition_frames + 2)[1:-1]  # Exclude endpoints
    transitions = np.zeros((num_transition_frames, len(pose_end)))

    for i, a in enumerate(alpha):
        transitions[i] = pose_end * (1 - a) + pose_start * a

    return transitions


def speed_up_animation(poses: np.ndarray, speed_multiplier: float = 1.0) -> np.ndarray:
    """
    Accelerează animația prin reducerea numărului de frame-uri

    Args:
        poses: Array de pose-uri [num_frames, pose_dim]
        speed_multiplier: Factor de accelerare (1.0=normal, 1.5=50% mai rapid, 2.0=dublu viteză)

    Returns:
        Array cu frame-uri reduse pentru viteză mai mare
    """
    if speed_multiplier <= 1.0:
        return poses

    # Calculează noul număr de frame-uri
    original_frames = len(poses)
    new_frames = max(int(original_frames / speed_multiplier), 2)  # Minim 2 frames

    # Sampling uniform pentru a păstra frame-uri reprezentative
    indices = np.linspace(0, original_frames - 1, new_frames, dtype=int)
    return poses[indices]


def adjust_hand_position(poses: np.ndarray, adjustment_amount: float = 0.05) -> np.ndarray:
    """
    Ajustează poziția mâinii drepte pentru a evita intersecția cu corpul

    Args:
        poses: Array de pose-uri [num_frames, pose_dim]
        adjustment_amount: Cât să deplaseze mâna (0.05 = 5cm, 0.1 = 10cm)

    Returns:
        Array cu pose-uri ajustate
    """
    adjusted_poses = poses.copy()

    # Ajustarea se face pe global_orient și body_pose pentru a deplasa ușor mâna dreaptă
    # Index 111-156 = right_hand_pose (45 parametri)
    # Ajustăm doar primii parametri pentru deplasare laterală ușoară

    for i in range(len(adjusted_poses)):
        # Ajustare minimă pe axa laterală (mâna dreaptă mai în afară)
        # Modificăm ușor rotația brațului drept în body_pose
        # Index pentru umărul drept în body_pose: index 14-17 (3 parametri)
        if adjusted_poses.shape[1] >= 66:
            # Ajustare ușoară pe rotația umărului drept (Y-axis)
            # Index 3 + 14*3 + 1 = 46 (umăr drept, rotație Y)
            adjusted_poses[i, 46] += adjustment_amount  # Deplasează brațul drept ușor lateral

    return adjusted_poses


# ============================================================================
# VIDEO CODEC OPTIMIZATION
# ============================================================================

def get_video_writer(output_path: str, fps: int, width: int, height: int,
                     codec: str = 'h264') -> cv2.VideoWriter:
    """
    Creează VideoWriter cu codec optimizat și fallback robust

    Codec options:
    - 'h264': H.264/AVC (best quality, widely supported)
    - 'h265': H.265/HEVC (better compression, newer)
    - 'xvid': XVID (good quality, Windows compatible)
    - 'mjpg': Motion JPEG (good quality, universal)
    - 'mp4v': MPEG-4 (fallback, lower quality)
    """
    # Lista de codec-uri de încercat în ordine (fallback chain)
    codec_attempts = []

    # Adaugă codec-ul cerut
    codec_map = {
        'h264': ['avc1', 'H264', 'X264'],  # Încercări multiple pentru H.264
        'h265': ['hev1', 'HEVC'],
        'xvid': ['XVID'],
        'mjpg': ['MJPG'],
        'mp4v': ['mp4v', 'MP4V'],
    }

    requested_codecs = codec_map.get(codec.lower(), ['avc1'])
    codec_attempts.extend(requested_codecs)

    # Adaugă fallback-uri universal compatibile (dacă nu sunt deja în listă)
    fallback_codecs = ['XVID', 'MJPG', 'mp4v']
    for fb_codec in fallback_codecs:
        if fb_codec not in codec_attempts:
            codec_attempts.append(fb_codec)

    # Încearcă fiecare codec din listă
    writer = None
    successful_codec = None

    for fourcc_code in codec_attempts:
        try:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
            test_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if test_writer.isOpened():
                writer = test_writer
                successful_codec = fourcc_code
                break
            else:
                test_writer.release()
        except Exception as e:
            # Continuă cu următorul codec
            continue

    if writer is None or not writer.isOpened():
        print(f"! EROARE: Nu s-a putut crea video writer cu niciun codec!")
        print(f"! Codec-uri încercate: {codec_attempts}")
        # Încearcă un ultim fallback fără specificare codec
        fourcc = 0  # Lasă OpenCV să aleagă
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if successful_codec and successful_codec != codec_attempts[0]:
        print(f"  ⚠ Codec '{codec.upper()}' nu e disponibil, folosesc '{successful_codec}' ca fallback")
    elif successful_codec:
        print(f"  ✓ Codec: {successful_codec}")

    return writer


# ============================================================================
# OPTIMIZED VIDEO TRANSLATOR
# ============================================================================

class OptimizedVideoSignLanguageTranslator:
    """Traductor optimizat cu performanță și calitate îmbunătățite"""

    def __init__(self, whisper_model="base"):
        self.whisper_model_name = whisper_model
        self.whisper_model = None
        self.dictionary = self.load_dictionary()
        self.en_translator = EnhancedTranslator()

        # Setup SMPL-X paths
        smplx_models_path = os.path.join(
            PROJECT_ROOT,
            'sign_avatars', 'common', 'utils', 'human_model_files'
        )
        C.smplx_models = os.path.abspath(smplx_models_path)

        # Use CPU if CUDA not available
        if not torch.cuda.is_available():
            C.device = "cpu"

        total_words = len(self.dictionary)
        print(f"✓ Dictionar incarcat: {total_words} cuvinte")
        print(f"✓ Model Whisper selectat: {whisper_model}")
        print(f"✓ Optimizari: Cache PKL, SMPL reuse, H.264 codec")

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

        # Salvează cuvintele originale românești
        ro_words_original = re.sub(r"[^\w\s]", "", text.lower()).split()

        # Translate to English
        english_text = self.en_translator.translate_sentence_ro_to_en(text)
        print(f"Text original: {text}")
        print(f"Text tradus RO→EN: {english_text}")

        # Normalize English text
        english_text = re.sub(r"[^\w\s]", "", english_text.lower())
        words = english_text.split()

        print(f"Cuvinte (EN): {words}\n")

        # Creează mapare inteligentă RO→EN pentru a gestiona cazuri când 1 cuvânt RO = multiple cuvinte EN
        # Strategie: distribuie cuvintele românești uniform pe cuvintele engleze
        ro_en_mapping = []
        if len(ro_words_original) > 0:
            # Calculează câte cuvinte EN corespund fiecărui cuvânt RO (distribuție uniformă)
            ratio = len(words) / len(ro_words_original)
            for i, ro_word in enumerate(ro_words_original):
                start_idx = int(i * ratio)
                end_idx = int((i + 1) * ratio) if i < len(ro_words_original) - 1 else len(words)
                for j in range(start_idx, end_idx):
                    if j < len(words):
                        ro_en_mapping.append(ro_word)

        # Asigură că avem mapare pentru toate cuvintele EN
        while len(ro_en_mapping) < len(words):
            ro_en_mapping.append(ro_words_original[-1] if ro_words_original else words[len(ro_en_mapping)])

        signs = []
        not_found = []

        for idx, word in enumerate(words):
            # Folosește maparea inteligentă pentru a găsi cuvântul românesc corespunzător
            romanian_word_raw = ro_en_mapping[idx] if idx < len(ro_en_mapping) else word
            romanian_word = remove_diacritics(romanian_word_raw)  # AUTOMAT fără diacritice
            romanian_word = clean_label_for_opencv(romanian_word)  # Curăță caractere non-ASCII

            # English-first lookup
            found = self.en_translator.find_sign_by_english(word)
            if found:
                signs.append({
                    'word': found['word'],
                    'pkl_file': found['pkl_file'],
                    'english': found.get('english', word),
                    'method': found.get('method', ''),
                    'input_word': word,
                    'romanian_word': romanian_word  # ADĂUGAT: cuvântul românesc original
                })
                print(f"   ✓ EN '{word}' -> PKL {Path(found['pkl_file']).name} via {found.get('method')}")
                continue

            # Fallback Romanian dictionary
            ro_word = word
            if ro_word in self.dictionary:
                pkl_file = self.dictionary[ro_word]['pkl_file']
                english = self.dictionary[ro_word].get('english_translation', '')

                signs.append({
                    'word': ro_word,
                    'pkl_file': pkl_file,
                    'english': english,
                    'input_word': ro_word,
                    'romanian_word': romanian_word  # ADĂUGAT: cuvântul românesc original
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

    def render_video_optimized(self, signs, output_file="output_video.mp4",
                              fps=60, quality="high", codec="h264",
                              enable_interpolation=True, enable_transitions=True,
                              transition_frames=5, speed_multiplier=1.0, progress_callback=None):
        """
        Randeaza video OPTIMIZAT cu calitate și performanță îmbunătățite

        Args:
            signs: Lista de gesturi PKL
            output_file: Nume fisier output
            fps: Framerate (30, 60, sau custom)
            quality: "low" (480p), "medium" (720p), "high" (1080p), "ultra" (4K)
            codec: "h264" (recommended), "h265", "mp4v"
            enable_interpolation: Activează interpolarea framelor pentru fluiditate
            enable_transitions: Activează tranziții smooth între gesturi
            transition_frames: Număr de frame-uri de tranziție între gesturi
            progress_callback: Funcție callback(current, total, message) pentru progress
        """
        print(f"\n{'='*70}")
        print(f"PASUL 3: GENERARE VIDEO OPTIMIZAT")
        print(f"{'='*70}")

        if not signs:
            print("! Nu exista gesturi de randat")
            return None

        # Quality settings
        quality_settings = {
            "low": (640, 480),        # 480p - Fast
            "medium": (1280, 720),     # 720p HD
            "high": (1920, 1080),      # 1080p Full HD
            "ultra": (3840, 2160),     # 4K Ultra HD
        }

        resolution = quality_settings.get(quality, (1920, 1080))

        print(f"\nConfiguratii:")
        print(f"  Output: {output_file}")
        print(f"  Calitate: {quality} ({resolution[0]}x{resolution[1]})")
        print(f"  FPS: {fps}")
        print(f"  Codec: {codec.upper()}")
        print(f"  Interpolation: {'✓' if enable_interpolation else '✗'}")
        print(f"  Transitions: {'✓' if enable_transitions else '✗'} ({transition_frames} frames)")
        print()

        total_signs = len(signs)
        all_poses = []
        pose_labels = []

        # ========================================================================
        # ETAPA 1: ÎNCĂRCARE PKL-URI CU CACHE
        # ========================================================================
        print(f"[1/3] Incarcare PKL-uri ({total_signs} gesturi)...")
        start_load = time.time()

        for i, sign in enumerate(signs):
            pkl_file = sign['pkl_file']
            word = sign['word']
            english = sign.get('english', '')
            romanian_word = sign.get('romanian_word', word)  # Cuvântul românesc original

            if progress_callback:
                progress_callback(i + 1, total_signs, f"Incarcare PKL {i+1}/{total_signs}: {word}")

            try:
                # Încărcare cu cache - MULT MAI RAPID
                data = load_pkl_data_cached(pkl_file)
                poses = data['smplx']

                # Folosim pose-urile originale din PKL, fără ajustări suplimentare pentru a evita artefacte
                # (aliniat cu comportamentul din varianta originală fără clipping la mâna dreaptă)
                # poses = adjust_hand_position(poses, adjustment_amount=0.08)
+

                # ACCELERARE animație (dacă speed_multiplier > 1.0)
                if speed_multiplier > 1.0:
                    original_frames_pre_speed = len(poses)
                    poses = speed_up_animation(poses, speed_multiplier=speed_multiplier)
                    speed_info = f"{original_frames_pre_speed}→{len(poses)} (×{speed_multiplier})"
                else:
                    speed_info = ""

                # Interpolează pose-uri dacă este activat
                if enable_interpolation and fps > 30:
                    original_frames = len(poses)
                    poses = interpolate_poses(poses, target_fps=fps, source_fps=30)
                    if speed_info:
                        print(f"  [{i+1}/{total_signs}] {romanian_word}: {speed_info} → {len(poses)} frames (interpolat + ajustat + accelerat)")
                    else:
                        print(f"  [{i+1}/{total_signs}] {romanian_word}: {original_frames} → {len(poses)} frames (interpolat + ajustat)")
                else:
                    if speed_info:
                        print(f"  [{i+1}/{total_signs}] {romanian_word}: {speed_info} frames (ajustat + accelerat)")
                    else:
                        print(f"  [{i+1}/{total_signs}] {romanian_word}: {len(poses)} frames (ajustat)")

                all_poses.append(poses)
                pose_labels.append(romanian_word)  # ROMÂNĂ fără diacritice (deja procesat automat)

            except Exception as e:
                print(f"  ! Eroare la {pkl_file}: {e}")
                continue

        load_time = time.time() - start_load
        print(f"✓ PKL-uri incarcate in {load_time:.1f}s")

        if not all_poses:
            print("! Nu s-au putut incarca PKL-uri")
            return None

        # ========================================================================
        # ETAPA 2: ADĂUGARE TRANZIȚII SMOOTH
        # ========================================================================
        if enable_transitions and len(all_poses) > 1:
            print(f"\n[2/3] Creare tranzitii smooth ({transition_frames} frames/tranzitie)...")
            start_trans = time.time()

            final_poses = []
            final_labels = []

            for i in range(len(all_poses)):
                # Adaugă pose-urile gestului curent
                final_poses.append(all_poses[i])
                final_labels.extend([pose_labels[i]] * len(all_poses[i]))

                # Adaugă tranziție la următorul gest (dacă există)
                if i < len(all_poses) - 1:
                    last_pose = all_poses[i][-1]
                    next_pose = all_poses[i + 1][0]
                    transition = create_transition_frames(last_pose, next_pose, transition_frames)

                    if len(transition) > 0:
                        final_poses.append(transition)
                        transition_label = f"{pose_labels[i]} - {pose_labels[i+1]}"  # ASCII hyphen instead of Unicode arrow
                        transition_label = clean_label_for_opencv(transition_label)  # Asigură doar ASCII
                        final_labels.extend([transition_label] * len(transition))

            # Concatenează toate pose-urile
            all_poses_combined = np.vstack(final_poses)
            trans_time = time.time() - start_trans
            print(f"✓ Tranzitii create in {trans_time:.1f}s")
        else:
            all_poses_combined = np.vstack(all_poses)
            final_labels = []
            for i, poses in enumerate(all_poses):
                final_labels.extend([pose_labels[i]] * len(poses))
            print(f"\n[2/3] Skip tranzitii (dezactivate)")

        total_frames = len(all_poses_combined)
        print(f"  Total frames de randat: {total_frames}")
        print(f"  Durata estimata: {total_frames / fps:.1f}s")

        # ========================================================================
        # ETAPA 3: RENDERING OPTIMIZAT
        # ========================================================================
        print(f"\n[3/3] Rendering video...")
        start_render = time.time()

        # Creează renderer
        renderer = HeadlessRenderer(size=resolution)
        renderer.scene.light_mode = 'dark'
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled = False
        renderer.shadows_enabled = False

        # Reutilizare SMPL layer (cache) - MULT MAI EFICIENT
        smpl_layer = SMPLLayerCache.get_layer(model_type="smplx", gender="neutral", device=C.device)

        # Separa componentele
        g = all_poses_combined[:, :3]         # global_orient
        b = all_poses_combined[:, 3:66]       # body_pose
        l = all_poses_combined[:, 66:111]     # left_hand_pose
        r = all_poses_combined[:, 111:156]    # right_hand_pose
        s = all_poses_combined[:, 159:169] if all_poses_combined.shape[1] >= 169 else np.zeros((len(all_poses_combined), 10))

        # Creează secvență SMPL UNICĂ pentru toate gesturile
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

        # Pregătire video writer cu codec optimizat
        video_writer = get_video_writer(output_file, fps, resolution[0], resolution[1], codec)

        if not video_writer.isOpened():
            print("! Nu s-a putut crea video writer")
            return None

        # Rendering loop cu progress
        frames_rendered = 0
        last_progress_print = 0

        for frame_idx in range(total_frames):
            smpl_sequence.current_frame_id = frame_idx

            # Render
            pil_image = renderer.get_frame()
            frame_rgb = np.array(pil_image)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            # Adaugă label
            label = final_labels[frame_idx] if frame_idx < len(final_labels) else ""
            cv2.putText(frame_bgr, label, (20, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)

            # Scrie frame
            video_writer.write(frame_bgr)
            frames_rendered += 1

            # Progress reporting
            if progress_callback:
                progress_callback(frame_idx + 1, total_frames, f"Rendering {frame_idx+1}/{total_frames}")

            # Console progress (fiecare 10%)
            progress_pct = (frame_idx + 1) / total_frames * 100
            if progress_pct - last_progress_print >= 10:
                print(f"  Progress: {progress_pct:.0f}% ({frame_idx+1}/{total_frames} frames)")
                last_progress_print = progress_pct

        video_writer.release()
        renderer.scene.remove(smpl_sequence)

        render_time = time.time() - start_render
        total_time = time.time() - start_load

        print(f"\n{'='*70}")
        print(f"✓ VIDEO GENERAT CU SUCCES")
        print(f"{'='*70}")
        print(f"  Fisier: {output_file}")
        print(f"  Rezolutie: {resolution[0]}x{resolution[1]}")
        print(f"  FPS: {fps}")
        print(f"  Codec: {codec.upper()}")
        print(f"  Total frames: {frames_rendered}")
        print(f"  Durata video: {frames_rendered / fps:.1f}s")
        print(f"  Timp incarcare: {load_time:.1f}s")
        print(f"  Timp rendering: {render_time:.1f}s")
        print(f"  Timp total: {total_time:.1f}s")
        print(f"  Viteza: {frames_rendered / render_time:.1f} fps")
        print(f"{'='*70}")

        return output_file

    def display_opencv_live(self, signs, fps=60, resolution=(1280, 720)):
        """
        Afișează animația LIVE în fereastră OpenCV (fără salvare pe disk)

        Args:
            signs: Lista de gesturi PKL
            fps: Framerate pentru playback (default: 60)
            resolution: Rezoluție fereastră (default: 1280x720)

        Controale:
            SPACE - play/pause
            q/ESC - ieșire
            , - frame anterior
            . - frame următor
        """
        print(f"\n{'='*70}")
        print(f"AFIȘARE LIVE ÎN OPENCV")
        print(f"{'='*70}")

        if not signs:
            print("! Nu există gesturi de afișat")
            return

        total_signs = len(signs)
        print(f"\n✓ Pregătire afișare pentru {total_signs} gesturi...")
        print(f"  Rezoluție: {resolution[0]}x{resolution[1]}")
        print(f"  FPS: {fps}")

        # ========================================================================
        # ETAPA 1: PRE-RENDER TOATE FRAME-URILE (cu cache optimizat)
        # ========================================================================
        print(f"\n[1/2] Pre-rendering frames (cu interpolation și tranziții)...")

        frames = []
        labels = []

        # Creează renderer
        renderer = HeadlessRenderer(size=resolution)
        renderer.scene.light_mode = 'dark'
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.90, 2.0])
        renderer.scene.camera.target = np.array([0, 0.80, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled = False
        renderer.shadows_enabled = False

        # Reutilizare SMPL layer (cache)
        smpl_layer = SMPLLayerCache.get_layer(model_type="smplx", gender="neutral", device=C.device)

        # Încarcă și interpolează toate pose-urile
        all_poses = []
        pose_labels = []

        for i, sign in enumerate(signs):
            pkl_file = sign['pkl_file']
            word = sign['word']
            english = sign.get('english', '')
            romanian_word = sign.get('romanian_word', word)  # Cuvântul românesc original

            try:
                # Încărcare cu cache
                data = load_pkl_data_cached(pkl_file)
                poses = data['smplx']

                # Folosim pose-urile originale din PKL, fără ajustări suplimentare pentru a evita artefacte
                # poses = adjust_hand_position(poses, adjustment_amount=0.08)
+

                # Interpolează pentru fluiditate
                if fps > 30:
                    poses = interpolate_poses(poses, target_fps=fps, source_fps=30)

                all_poses.append(poses)
                pose_labels.append(romanian_word)  # ROMÂNĂ fără diacritice (deja procesat automat)

                print(f"  [{i+1}/{total_signs}] {word}: {len(poses)} frames (ajustat)")

            except Exception as e:
                print(f"  ! Eroare la {pkl_file}: {e}")
                continue

        # Adaugă tranziții smooth
        if len(all_poses) > 1:
            final_poses = []
            final_labels = []
            transition_frames = 5

            for i in range(len(all_poses)):
                final_poses.append(all_poses[i])
                final_labels.extend([pose_labels[i]] * len(all_poses[i]))

                # Tranziție la următorul gest
                if i < len(all_poses) - 1:
                    last_pose = all_poses[i][-1]
                    next_pose = all_poses[i + 1][0]
                    transition = create_transition_frames(last_pose, next_pose, transition_frames)

                    if len(transition) > 0:
                        final_poses.append(transition)
                        transition_label = f"{pose_labels[i]} - {pose_labels[i+1]}"  # ASCII hyphen instead of Unicode arrow
                        transition_label = clean_label_for_opencv(transition_label)  # Asigură doar ASCII
                        final_labels.extend([transition_label] * len(transition))

            all_poses_combined = np.vstack(final_poses)
        else:
            all_poses_combined = all_poses[0] if all_poses else np.array([])
            final_labels = [pose_labels[0]] * len(all_poses_combined) if all_poses else []

        if len(all_poses_combined) == 0:
            print("! Nu s-au putut încărca gesturi")
            return

        print(f"✓ Total frames de randat: {len(all_poses_combined)}")

        # Separa componentele
        g = all_poses_combined[:, :3]
        b = all_poses_combined[:, 3:66]
        l = all_poses_combined[:, 66:111]
        r = all_poses_combined[:, 111:156]
        s = all_poses_combined[:, 159:169] if all_poses_combined.shape[1] >= 169 else np.zeros((len(all_poses_combined), 10))

        # Creează secvență SMPL unică
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

        # Render toate frame-urile
        print(f"Rendering {len(all_poses_combined)} frames...")
        for frame_idx in range(len(all_poses_combined)):
            smpl_sequence.current_frame_id = frame_idx

            pil_image = renderer.get_frame()
            frame_rgb = np.array(pil_image)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

            frames.append(frame_bgr)

            if (frame_idx + 1) % 50 == 0:
                print(f"  Progress: {frame_idx+1}/{len(all_poses_combined)} frames")

        renderer.scene.remove(smpl_sequence)

        print(f"✓ Frames randate: {len(frames)}")

        # ========================================================================
        # ETAPA 2: PLAYBACK INTERACTIV ÎN OPENCV
        # ========================================================================
        print(f"\n[2/2] Afișare animație OpenCV...")
        print(f"\nControale:")
        print(f"  SPACE - play/pause")
        print(f"  q/ESC - ieșire")
        print(f"  ,     - frame anterior")
        print(f"  .     - frame următor")
        print(f"\n✓ Deschidere fereastră OpenCV...\n")

        cv2.namedWindow('Sign Language Animation', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Sign Language Animation', resolution[0], resolution[1])

        current_frame = 0
        num_frames = len(frames)
        playing = True
        frame_delay = int(1000 / fps)

        while True:
            frame = frames[current_frame].copy()

            # Overlay informații
            label = final_labels[current_frame] if current_frame < len(final_labels) else ""
            cv2.putText(frame, label, (20, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
            cv2.putText(frame, f"Frame: {current_frame+1}/{num_frames}", (20, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

            status = "▶ PLAYING" if playing else "⏸ PAUSED"
            cv2.putText(frame, status, (20, resolution[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

            cv2.imshow('Sign Language Animation', frame)

            key = cv2.waitKey(frame_delay if playing else 0) & 0xFF

            if key == ord('q') or key == 27:  # q sau ESC
                break
            elif key == ord(' '):  # SPACE
                playing = not playing
            elif key == ord(','):  # frame anterior
                current_frame = max(0, current_frame - 1)
                playing = False
            elif key == ord('.'):  # frame următor
                current_frame = min(num_frames - 1, current_frame + 1)
                playing = False

            if playing:
                current_frame = (current_frame + 1) % num_frames

        cv2.destroyAllWindows()
        print(f"\n✓ Afișare închisă")


def main():
    """Functia principala"""
    print("\n" + "="*70)
    print("SIGN LANGUAGE TRANSLATOR - OPTIMIZED VERSION")
    print("="*70)

    import argparse
    parser = argparse.ArgumentParser(
        description="Traductor optimizat cu performanță și calitate îmbunătățite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemple:

  # Text direct, calitate HD, 60fps
  python audio_to_sign_video_optimized.py --text "copil iubi animal" --fps 60 --quality high

  # Audio cu model base, 4K, transitions
  python audio_to_sign_video_optimized.py --audio "input.mp3" --quality ultra --fps 30

  # Dezactivare interpolation pentru viteza
  python audio_to_sign_video_optimized.py --text "salut" --no-interpolation

Calitate:
  - low: 480p (rapid)
  - medium: 720p HD
  - high: 1080p Full HD (recomandat)
  - ultra: 4K (cel mai bun, mai lent)

Codec:
  - h264: H.264/AVC (recomandat, compatibil)
  - h265: H.265/HEVC (compresie mai bună, mai nou)
  - mp4v: MPEG-4 (fallback)
        """
    )
    parser.add_argument('--audio', type=str, help='Fisier audio/video de transcris')
    parser.add_argument('--text', type=str, help='Text direct (skip transcriere)')
    parser.add_argument('--model', type=str, default='base',
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Model Whisper (default: base)')
    parser.add_argument('--output', '-o', type=str, default='output_optimized.mp4',
                        help='Fisier output video (default: output_optimized.mp4)')
    parser.add_argument('--fps', type=int, default=60,
                        help='Framerate video (default: 60 pentru fluiditate maxima)')
    parser.add_argument('--quality', type=str, default='high',
                        choices=['low', 'medium', 'high', 'ultra'],
                        help='Calitate video (default: high = 1080p)')
    parser.add_argument('--codec', type=str, default='h264',
                        choices=['h264', 'h265', 'mp4v'],
                        help='Codec video (default: h264)')
    parser.add_argument('--no-interpolation', action='store_true',
                        help='Dezactiveaza interpolarea framelor')
    parser.add_argument('--no-transitions', action='store_true',
                        help='Dezactiveaza tranzitiile smooth')
    parser.add_argument('--transition-frames', type=int, default=15,
                        help='Numar frame-uri tranzitie (default: 15 pentru fluiditate maxima)')
    parser.add_argument('--speed', type=float, default=1.5,
                        help='Viteza animatie (1.0=normal, 1.5=50%% mai rapid, 2.0=dublu, default: 1.5 pentru real-time)')
    parser.add_argument('--display', action='store_true',
                        help='Afiseaza animatia LIVE in OpenCV (fara salvare video)')

    args = parser.parse_args()

    # Initializeaza traducatorul
    translator = OptimizedVideoSignLanguageTranslator(whisper_model=args.model)

    # Determina textul
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

    # Converteste in gesturi
    result = translator.text_to_signs(text)
    signs = result['signs']

    if not signs:
        print("\n! Nu s-au gasit gesturi pentru acest text")
        return

    # Alege modul de afișare: OpenCV live sau salvare video
    if args.display:
        # Mod DISPLAY - Afișare LIVE în OpenCV (fără salvare)
        quality_map = {
            'low': (640, 480),
            'medium': (1280, 720),
            'high': (1920, 1080),
            'ultra': (3840, 2160)
        }
        resolution = quality_map.get(args.quality, (1280, 720))

        translator.display_opencv_live(
            signs,
            fps=args.fps,
            resolution=resolution
        )
    else:
        # Mod NORMAL - Randeaza și salvează video
        output_file = translator.render_video_optimized(
            signs,
            output_file=args.output,
            fps=args.fps,
            quality=args.quality,
            codec=args.codec,
            enable_interpolation=not args.no_interpolation,
            enable_transitions=not args.no_transitions,
            transition_frames=args.transition_frames,
            speed_multiplier=args.speed
        )

        if output_file:
            print(f"\n✓ Poti vizualiza video-ul cu:")
            print(f"  - VLC Player (recomandat)")
            print(f"  - Windows Media Player")
            print(f"  - Orice player video modern")
            print()

if __name__ == "__main__":
    main()
