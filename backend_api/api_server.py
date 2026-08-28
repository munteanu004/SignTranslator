from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
import os
import re
import tempfile
import base64
import json
import math
import cv2
import numpy as np
import unicodedata
import uuid
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import threading
from sqlalchemy import text

app = Flask(__name__)
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
}})

@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

AVATARS_DIR = Path(__file__).parent / 'static' / 'avatars'
AVATARS_DIR.mkdir(parents=True, exist_ok=True)

                          
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///signtranslator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'lsr-sign-translator-secret-2024')

from models import db, seed_gamification_definitions
db.init_app(app)

from auth import auth_bp
from history_routes import history_bp
from settings_routes import settings_bp
from gamification_routes import gamification_bp
from dictionary_routes import dictionary_bp
app.register_blueprint(auth_bp)
app.register_blueprint(history_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(gamification_bp)
app.register_blueprint(dictionary_bp)

with app.app_context():
    db.create_all()

                                                                                         
    try:
        user_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(users)")).fetchall()]
        if "last_active_date" not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN last_active_date DATE"))
        if "phone" not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(30)"))
        if "avatar_url" not in user_cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255)"))
        settings_cols = [r[1] for r in db.session.execute(text("PRAGMA table_info(user_settings)")).fetchall()]
        if "skill_level" not in settings_cols:
            db.session.execute(text("ALTER TABLE user_settings ADD COLUMN skill_level VARCHAR(20) DEFAULT 'incepator'"))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f"WARNING: DB schema check failed: {exc}")

                                                       
    try:
        seed_gamification_definitions()
    except Exception as exc:
        print(f"WARNING: Could not seed gamification definitions: {exc}")
        db.session.rollback()
    print("Database initialized (signtranslator.db)")

                                               
_recognizer = None

def get_recognizer():
    global _recognizer
    if _recognizer is None:
        from sign_recognizer import SignRecognizer
        _recognizer = SignRecognizer()
    return _recognizer

                                           
try:
    with app.app_context():
        get_recognizer()
except Exception as e:
    print(f"WARNING: Could not pre-load AI model: {e}")

                                         
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
    return _whisper_model

                                                                     
ROMANIAN_SIGNS = {
    "buna": {"body": [0.1, -0.2, 0.0], "left_hand": [0.5, 0.4, -0.1], "right_hand": [0.5, 0.4, 0.1]},
    "ziua": {"body": [0.0, 0.1, 0.2], "left_hand": [0.3, 0.6, 0.0], "right_hand": [0.3, 0.6, 0.0]},
    "ma": {"body": [0.0, 0.0, 0.0], "left_hand": [0.2, 0.5, -0.2], "right_hand": [0.0, 0.0, 0.0]},
    "numesc": {"body": [0.1, 0.0, -0.1], "left_hand": [0.4, 0.3, 0.1], "right_hand": [0.4, 0.3, -0.1]},
    "maria": {"body": [0.0, 0.1, 0.0], "left_hand": [0.6, 0.5, 0.0], "right_hand": [0.6, 0.5, 0.0]},
    "am": {"body": [0.1, -0.1, 0.0], "left_hand": [0.3, 0.4, 0.2], "right_hand": [0.0, 0.0, 0.0]},
    "21": {"body": [0.0, 0.0, 0.1], "left_hand": [0.5, 0.7, 0.0], "right_hand": [0.4, 0.6, 0.0]},
    "ani": {"body": [0.0, 0.2, 0.0], "left_hand": [0.2, 0.4, 0.1], "right_hand": [0.2, 0.4, -0.1]},
    "de": {"body": [0.0, 0.0, 0.0], "left_hand": [0.1, 0.2, 0.0], "right_hand": [0.0, 0.0, 0.0]},
    "si": {"body": [0.0, 0.0, 0.0], "left_hand": [0.1, 0.2, 0.0], "right_hand": [0.1, 0.2, 0.0]},
    "invat": {"body": [0.1, 0.1, -0.1], "left_hand": [0.4, 0.6, 0.2], "right_hand": [0.3, 0.5, 0.1]},
    "la": {"body": [0.0, 0.0, 0.1], "left_hand": [0.2, 0.3, 0.0], "right_hand": [0.3, 0.4, 0.0]},
    "universitatea": {"body": [0.0, 0.1, 0.1], "left_hand": [0.6, 0.4, 0.0], "right_hand": [0.6, 0.4, 0.0]},
    "tehnica": {"body": [0.1, 0.0, 0.0], "left_hand": [0.5, 0.5, 0.3], "right_hand": [0.5, 0.5, -0.3]},
    "din": {"body": [0.0, 0.0, 0.0], "left_hand": [0.2, 0.3, 0.1], "right_hand": [0.0, 0.0, 0.0]},
    "moldova": {"body": [0.0, 0.1, 0.2], "left_hand": [0.4, 0.7, 0.1], "right_hand": [0.4, 0.7, -0.1]},
    "specialitatea": {"body": [0.1, 0.0, 0.0], "left_hand": [0.5, 0.4, 0.2], "right_hand": [0.5, 0.4, -0.2]},
    "informatica": {"body": [0.1, -0.1, 0.0], "left_hand": [0.3, 0.6, 0.2], "right_hand": [0.5, 0.4, 0.0]},
    "aplicata": {"body": [0.0, 0.1, -0.1], "left_hand": [0.6, 0.3, 0.0], "right_hand": [0.4, 0.5, 0.1]},
    "sunt": {"body": [0.0, 0.0, 0.0], "left_hand": [0.3, 0.4, 0.1], "right_hand": [0.3, 0.4, -0.1]},
    "in": {"body": [0.0, 0.0, 0.0], "left_hand": [0.1, 0.2, 0.0], "right_hand": [0.0, 0.0, 0.0]},
    "anul": {"body": [0.1, 0.0, 0.1], "left_hand": [0.2, 0.5, 0.0], "right_hand": [0.3, 0.6, 0.0]},
    "3": {"body": [0.0, 0.0, 0.0], "left_hand": [0.5, 0.6, 0.1], "right_hand": [0.0, 0.0, 0.0]},
    "acesta": {"body": [0.0, 0.1, 0.0], "left_hand": [0.4, 0.4, 0.1], "right_hand": [0.4, 0.4, -0.1]},
    "fac": {"body": [0.1, -0.1, 0.0], "left_hand": [0.3, 0.5, 0.2], "right_hand": [0.3, 0.5, -0.2]},
    "teza": {"body": [0.1, 0.1, 0.0], "left_hand": [0.4, 0.4, 0.2], "right_hand": [0.4, 0.4, -0.2]},
    "licenta": {"body": [0.0, 0.2, 0.1], "left_hand": [0.5, 0.5, 0.0], "right_hand": [0.5, 0.5, 0.0]},
}

                         
VIDEOS_DIR = Path(__file__).parent / "generated_videos"
VIDEOS_DIR.mkdir(exist_ok=True)

def clean_romanian_text(text: str) -> str:
    """Normalize Romanian text: lowercase, strip, remove diacritics."""
    normalized = (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return normalized.lower().strip()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if API is running"""
    return jsonify({
        'status': 'ok',
        'message': 'SignTranslator API is running',
        'version': '1.0.0'
    })

@app.route('/api/recognize-frame', methods=['POST'])
def recognize_frame():
    """Accept a base64 JPEG from Expo native camera, run MediaPipe + ASL recognition.

    Expected JSON: { "image": "data:image/jpeg;base64,..." }
    Returns: { success, gloss_en, gloss_ro, confidence, hands_detected }
    """
    data = request.get_json() or {}
    image_data = data.get('image', '')

    try:
                             
        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({'error': 'Invalid image'}), 400

                                
        import mediapipe as mp
        mp_holistic = mp.solutions.holistic
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        with mp_holistic.Holistic(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5,
        ) as holistic:
            results = holistic.process(rgb)

                                                                  
        def lm_to_row(lm):
            return [lm.x, lm.y, lm.z if hasattr(lm, 'z') else 0.0]

        kp = []
        for i in range(33):
            if results.pose_landmarks and i < len(results.pose_landmarks.landmark):
                kp.append(lm_to_row(results.pose_landmarks.landmark[i]))
            else:
                kp.append([0.0, 0.0, 0.0])
        for i in range(21):
            if results.left_hand_landmarks and i < len(results.left_hand_landmarks.landmark):
                kp.append(lm_to_row(results.left_hand_landmarks.landmark[i]))
            else:
                kp.append([0.0, 0.0, 0.0])
        for i in range(21):
            if results.right_hand_landmarks and i < len(results.right_hand_landmarks.landmark):
                kp.append(lm_to_row(results.right_hand_landmarks.landmark[i]))
            else:
                kp.append([0.0, 0.0, 0.0])

        hands_detected = (results.left_hand_landmarks is not None or
                          results.right_hand_landmarks is not None)

                                                                            
        def lm_list(landmarks):
            if landmarks is None:
                return []
            return [[lm.x, lm.y] for lm in landmarks.landmark]

        landmarks_payload = {
            'left_hand':  lm_list(results.left_hand_landmarks),
            'right_hand': lm_list(results.right_hand_landmarks),
            'pose':       [[lm.x, lm.y] for lm in results.pose_landmarks.landmark[:25]]
                          if results.pose_landmarks else [],
        }

                                                                 
        session_id = data.get('session_id', 'default')
        if not hasattr(recognize_frame, '_buffers'):
            recognize_frame._buffers = {}
        buf = recognize_frame._buffers.setdefault(session_id, [])
        buf.append(kp)
        if len(buf) > 150:
            buf = buf[-150:]
            recognize_frame._buffers[session_id] = buf

                                                                                    
                                                                                         
        if len(buf) < 5:
            return jsonify({
                'success': True,
                'gloss_en': '',
                'gloss_ro': '',
                'confidence': 0.0,
                'hands_detected': hands_detected,
                'buffered_frames': len(buf),
                'landmarks': landmarks_payload,
            })

        kp_array = np.array(buf[-40:], dtype=np.float32)                      

        try:
            recognizer = get_asl_recognizer()
            res = recognizer.predict(kp_array, top_k=5)
            gloss_en = res[0]['label']
            conf = res[0]['confidence']
        except Exception:
            recognizer = get_recognizer()
            res = recognizer.predict(kp_array, top_k=5)
            gloss_en = res[0]['label']
            conf = res[0]['confidence']

        try:
            ro = google_translate_candidates(gloss_en, source='en', target='ro')
            gloss_ro = ro[0] if ro else gloss_en
        except Exception:
            gloss_ro = gloss_en

        return jsonify({
            'success': True,
            'gloss_en': gloss_en,
            'gloss_ro': gloss_ro,
            'confidence': conf,
            'hands_detected': hands_detected,
            'buffered_frames': len(buf),
            'top5': res,
            'landmarks': landmarks_payload,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recognize-frame/reset', methods=['POST'])
def reset_frame_buffer():
    """Clear the keypoint buffer for a session."""
    data = request.get_json() or {}
    session_id = data.get('session_id', 'default')
    if hasattr(recognize_frame, '_buffers'):
        recognize_frame._buffers.pop(session_id, None)
    return jsonify({'success': True})


@app.route('/api/recognize-sign', methods=['POST'])
def recognize_sign():
    """Recognize sign language from MediaPipe keypoints using AI model.

    Expected JSON: { "keypoints": [[[x,y,z], ...75], ...T frames] }
    Returns: { prediction, confidence, top5 }
    """
    data = request.get_json() or {}
    keypoints = data.get('keypoints')
    if not keypoints:
        return jsonify({'error': 'No keypoints provided'}), 400

    try:
        import numpy as np
        kp_array = np.array(keypoints, dtype=np.float32)
        if kp_array.ndim != 3 or kp_array.shape[1] != 75 or kp_array.shape[2] != 3:
            return jsonify({
                'error': f'Invalid shape: expected (T, 75, 3), got {list(kp_array.shape)}'
            }), 400

        recognizer = get_recognizer()
        results = recognizer.predict(kp_array, top_k=5)

        label_en = results[0]['label']
        try:
            ro_candidates = google_translate_candidates(label_en, source='en', target='ro')
            label_ro = ro_candidates[0] if ro_candidates else label_en
        except Exception:
            label_ro = label_en

        return jsonify({
            'success': True,
            'prediction': label_en,
            'prediction_ro': label_ro,
            'confidence': results[0]['confidence'],
            'top5': results,
        })
    except Exception as e:
        return jsonify({'error': f'Recognition failed: {e}'}), 500


                                                                               
_asl_recognizer = None

def get_asl_recognizer():
    global _asl_recognizer
    if _asl_recognizer is None:
        from spoter_recognizer import get_asl_recognizer as _load
        _asl_recognizer = _load()
    return _asl_recognizer

try:
    with app.app_context():
        get_asl_recognizer()
except Exception as e:
    print(f"INFO: ASL recognizer not loaded (run setup_spoter.py first): {e}")


@app.route('/api/recognize-asl', methods=['POST'])
def recognize_asl():
    """Recognize ASL sign from MediaPipe keypoints using SPOTER + WLASL100.

    Expected JSON: { "keypoints": [[[x,y,z], ...75], ...T frames] }
    Returns: { success, gloss_en, confidence, top5 }
    """
    data = request.get_json() or {}
    keypoints = data.get('keypoints')
    if not keypoints:
        return jsonify({'error': 'No keypoints provided'}), 400

    try:
        kp_array = np.array(keypoints, dtype=np.float32)
        if kp_array.ndim != 3 or kp_array.shape[1] != 75 or kp_array.shape[2] != 3:
            return jsonify({
                'error': f'Expected shape (T, 75, 3), got {list(kp_array.shape)}'
            }), 400

        recognizer = get_asl_recognizer()
        results = recognizer.predict(kp_array, top_k=5)

        if not results:
            return jsonify({
                'success': False,
                'reason': 'insufficient_hand_data',
                'message': 'Not enough frames with hand landmarks detected.',
            }), 200

        gloss_en = results[0]['label']
        try:
            ro_candidates = google_translate_candidates(gloss_en, source='en', target='ro')
            gloss_ro = ro_candidates[0] if ro_candidates else gloss_en
        except Exception:
            gloss_ro = gloss_en

                                                              
        top5_ro = []
        for item in results:
            try:
                ro = google_translate_candidates(item['label'], source='en', target='ro')
                label_ro = ro[0] if ro else item['label']
            except Exception:
                label_ro = item['label']
            top5_ro.append({
                'label': item['label'],
                'label_ro': label_ro,
                'confidence': item['confidence'],
            })

        return jsonify({
            'success': True,
            'gloss_en': gloss_en,
            'gloss_ro': gloss_ro,
            'confidence': results[0]['confidence'],
            'top5': top5_ro,
        })
    except FileNotFoundError as e:
        return jsonify({'error': str(e), 'setup_required': True}), 503
    except Exception as e:
        return jsonify({'error': f'ASL recognition failed: {e}'}), 500


@app.route('/api/recognize-asl/status', methods=['GET'])
def asl_status():
    """Check if ASL recognizer is ready."""
    from pathlib import Path
    weights = Path(__file__).parent / "models" / "spoter_wlasl100.pth"
    labels = Path(__file__).parent / "models" / "spoter_labels.json"
    ready = weights.exists() and labels.exists()
    return jsonify({
        'ready': ready,
        'message': 'Ready' if ready else 'Run python setup_spoter.py to train the model',
    })


                                                                                 
_ro_recognizer_instance = None

def _get_ro_recognizer():
    global _ro_recognizer_instance
    if _ro_recognizer_instance is None:
        from ro_recognizer import get_ro_recognizer
        _ro_recognizer_instance = get_ro_recognizer()
    return _ro_recognizer_instance

try:
    with app.app_context():
        _get_ro_recognizer()
except Exception as _e:
    print(f"INFO: Romanian recognizer preload skipped: {_e}")


@app.route('/api/recognize-ro', methods=['POST'])
def recognize_ro():
    """Recognize Romanian sign from MediaPipe keypoints.

    Expected JSON: { "keypoints": [[[x,y,z], ...75], ...T frames] }
    Returns: { success, gloss_ro, confidence, top5 }

    Recognizes 10 Romanian signs: mama, tata, salut, da, nu,
    bine, buna, multumesc, apa, ajutor.
    """
    data = request.get_json() or {}
    keypoints = data.get('keypoints')
    if not keypoints:
        return jsonify({'error': 'No keypoints provided'}), 400

    try:
        kp_array = np.array(keypoints, dtype=np.float32)
        if kp_array.ndim != 3 or kp_array.shape[1] != 75 or kp_array.shape[2] != 3:
            return jsonify({
                'error': f'Expected shape (T, 75, 3), got {list(kp_array.shape)}'
            }), 400

        recognizer = _get_ro_recognizer()
        results = recognizer.predict(kp_array, top_k=5)

        if not results:
            return jsonify({
                'succes': False,
                'motiv': 'date_insuficiente',
                'mesaj': 'Nu s-au detectat suficiente cadre cu maini vizibile.',
            }), 200

        return jsonify({
            'succes': True,
            'semn': results[0]['semn'],
            'incredere': results[0]['incredere'],
            'top5': results,
            'tip_model': 'antrenat' if recognizer.finetuned else 'potrivire_template',
        })
    except Exception as e:
        return jsonify({'error': f'Romanian recognition failed: {e}'}), 500


@app.route('/api/recognize-ro/status', methods=['GET'])
def ro_recognizer_status():
    """Check Romanian recognizer status."""
    from pathlib import Path
    pretrained = Path(__file__).parent.parent / "models" / "pretrained_best.pth"
    finetuned = Path(__file__).parent.parent / "models" / "finetuned_best.pth"
    from ro_recognizer import TARGET_SIGNS
    return jsonify({
        'gata': pretrained.exists(),
        'model_antrenat_disponibil': finetuned.exists(),
        'tip_model': 'antrenat' if finetuned.exists() else 'potrivire_template',
        'semne_disponibile': TARGET_SIGNS,
        'mesaj': 'Gata' if pretrained.exists() else 'Lipseste models_backup/pretrained_best.pth',
    })


                                                                                
_FOCUSED_WORDS = ["hello", "love", "stop", "drink", "yes"]
_FOCUSED_RO = {"hello": "salut", "love": "iubire", "stop": "stop", "drink": "a bea", "yes": "da"}
_FOCUSED_THRESHOLD = 0.10                             

_TEMPLATES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'focused_templates.json')
_focused_templates: dict = {}                                              

def _load_templates():
    global _focused_templates
    try:
        if os.path.exists(_TEMPLATES_FILE):
            with open(_TEMPLATES_FILE) as f:
                _focused_templates = json.load(f)
    except Exception:
        _focused_templates = {}

def _save_templates():
    try:
        with open(_TEMPLATES_FILE, 'w') as f:
            json.dump(_focused_templates, f)
    except Exception:
        pass

_load_templates()


def _extract_hand_features(kp_array: np.ndarray) -> np.ndarray:
    """Normalize hand keypoints. Input (T, 75, 3) -> output (T, 84)."""
                                                           
    hands = kp_array[:, 33:, :2].copy()               
    for t in range(len(hands)):
        pts = hands[t]                              
        visible = pts[np.any(pts != 0, axis=1)]
        if len(visible) > 3:
            centroid = visible.mean(axis=0)
            scale = float(np.abs(visible - centroid).max())
            if scale < 1e-5:
                scale = 1.0
            hands[t] = (pts - centroid) / scale
    return hands.reshape(len(hands), -1)            


def _dtw_distance(s1: np.ndarray, s2: np.ndarray) -> float:
    """Normalized DTW distance between two feature sequences using numpy."""
    n, m = len(s1), len(s2)
    if n == 0 or m == 0:
        return float('inf')
                            
    diff = s1[:, np.newaxis, :] - s2[np.newaxis, :, :]              
    C = np.linalg.norm(diff, axis=2)                              
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = C[i-1, j-1] + min(D[i-1, j], D[i, j-1], D[i-1, j-1])
    return float(D[n, m]) / (n + m)


_DTW_ACCEPT_THRESHOLD = 5.0                                                              


@app.route('/api/recognize-focused', methods=['POST'])
def recognize_focused():
    """Recognize one of the 5 focused words.

    Priority 1: DTW template matching (uses user's own recorded templates).
    Priority 2: SPOTER model fallback (filters top-10 to focused words only).
    """
    data = request.get_json() or {}
    keypoints = data.get('keypoints')
    if not keypoints:
        return jsonify({'success': False, 'reason': 'no_keypoints'}), 400

    try:
        kp_array = np.array(keypoints, dtype=np.float32)
        if kp_array.ndim != 3 or kp_array.shape[1] != 75:
            return jsonify({'success': False, 'reason': 'bad_shape'}), 400

        features = _extract_hand_features(kp_array)

                                                                             
        calibrated = {w: v for w, v in _focused_templates.items() if v}
        if calibrated:
            best_word = None
            best_dist = float('inf')
            for word, templates in calibrated.items():
                for tmpl_list in templates:
                    tmpl = np.array(tmpl_list, dtype=np.float32)
                    d = _dtw_distance(features, tmpl)
                    if d < best_dist:
                        best_dist = d
                        best_word = word
            if best_word and best_dist < _DTW_ACCEPT_THRESHOLD:
                conf = max(0.01, 1.0 - best_dist / _DTW_ACCEPT_THRESHOLD)
                return jsonify({
                    'success': True,
                    'word': best_word,
                    'word_ro': _FOCUSED_RO.get(best_word, best_word),
                    'confidence': round(conf, 3),
                    'method': 'dtw',
                    'dtw_dist': round(best_dist, 3),
                })

                                                                              
        recognizer = get_asl_recognizer()
        results = recognizer.predict(kp_array, top_k=10)
        if not results:
            return jsonify({'success': False, 'reason': 'insufficient_hand_data'})

        focused_hits = [r for r in results if r['label'] in _FOCUSED_WORDS]
        if not focused_hits:
            return jsonify({'success': False, 'reason': 'not_in_focused_words'})

        best = focused_hits[0]
        if best['confidence'] < _FOCUSED_THRESHOLD:
            return jsonify({'success': False, 'reason': 'low_confidence',
                            'word': best['label'], 'confidence': best['confidence']})

        return jsonify({
            'success': True,
            'word': best['label'],
            'word_ro': _FOCUSED_RO.get(best['label'], best['label']),
            'confidence': round(best['confidence'], 3),
            'method': 'spoter',
        })

    except FileNotFoundError as e:
        return jsonify({'error': str(e), 'setup_required': True}), 503
    except Exception as e:
        return jsonify({'error': f'Focused recognition failed: {e}'}), 500


@app.route('/api/recognize-focused/record', methods=['POST'])
def record_focused_template():
    """Save a calibration template for a focused word."""
    data = request.get_json() or {}
    word = data.get('word', '').lower()
    keypoints = data.get('keypoints')
    if word not in _FOCUSED_WORDS:
        return jsonify({'error': 'unknown word'}), 400
    if not keypoints:
        return jsonify({'error': 'no keypoints'}), 400
    try:
        kp_array = np.array(keypoints, dtype=np.float32)
        if kp_array.ndim != 3 or kp_array.shape[1] != 75:
            return jsonify({'error': 'bad_shape'}), 400
        features = _extract_hand_features(kp_array)
        if word not in _focused_templates:
            _focused_templates[word] = []
        _focused_templates[word].append(features.tolist())
        _focused_templates[word] = _focused_templates[word][-3:]                           
        _save_templates()
        return jsonify({'success': True, 'word': word, 'template_count': len(_focused_templates[word])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recognize-focused/templates', methods=['GET'])
def get_focused_templates():
    """Return which words have saved templates."""
    calibrated = {w: len(v) for w, v in _focused_templates.items() if v}
    return jsonify({'calibrated': calibrated, 'words': _FOCUSED_WORDS})


@app.route('/api/recognize-focused/words', methods=['GET'])
def focused_words():
    """Return the list of 5 focused target words."""
    _RO = {"hello": "salut", "love": "iubire", "stop": "stop", "drink": "a bea", "yes": "da"}
    _EMOJI = {"hello": "👋", "love": "🤍", "stop": "✋", "drink": "🥤", "yes": "✅"}
    _DESC = {
        "hello": "Mână deschisă lângă frunte",
        "love":  "Brațe încrucișate pe piept",
        "stop":  "Palmă care taie cealaltă palmă",
        "drink": "Pumn în C dus la gură",
        "yes":   "Pumn care se mișcă sus-jos",
    }
    return jsonify({
        'words': [
            {'en': w, 'ro': _RO[w], 'emoji': _EMOJI[w], 'description': _DESC[w]}
            for w in _FOCUSED_WORDS
        ]
    })


                                                                            
@app.route('/api/recognize-rules', methods=['POST'])
def recognize_rules():
    """Geometry-based sign recognition — works without any ML model.
    Recognizes: salut, da, nu, iubire, pace, atentie, ok, putere.
    Input:  { keypoints: [[[x,y,z]×75]×T] }
    Output: { success, sign_ro, sign_en, confidence, method:'rules' }
    """
    from rule_recognizer import recognize_from_keypoints
    data = request.get_json() or {}
    keypoints = data.get('keypoints')
    if not keypoints:
        return jsonify({'success': False, 'reason': 'no_keypoints'}), 400
    try:
        kp_array = np.array(keypoints, dtype=np.float32)
        result = recognize_from_keypoints(kp_array)
        if result is None:
            return jsonify({'success': False, 'reason': 'no_sign_detected'})
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recognize-rules/signs', methods=['GET'])
def recognize_rules_signs():
    """List all signs recognizable by the geometry-based recognizer."""
    signs = [
        {'ro': 'salut',         'en': 'hello',       'emoji': '👋', 'description': 'Mână deschisă — toate 5 degetele sus'},
        {'ro': 'da',            'en': 'yes',         'emoji': '👍', 'description': 'Degetul mare sus (thumbs up)'},
        {'ro': 'nu',            'en': 'no',          'emoji': '👎', 'description': 'Degetul mare jos (thumbs down)'},
        {'ro': 'te iubesc',     'en': 'I love you',  'emoji': '🤟', 'description': 'ILY: index + deget mic sus SAU maini incrucisate pe piept (LSR)'},
        {'ro': 'pace',          'en': 'peace',       'emoji': '✌️',  'description': 'V: index + mijlociu sus'},
        {'ro': 'eu',            'en': 'me',          'emoji': '🫵', 'description': 'Arătător la piept (mâna joasă, fără deget mare)'},
        {'ro': 'copil',         'en': 'child',       'emoji': '🧒', 'description': '4 degete sus, degetul mare îndoit'},
        {'ro': 'a bea',         'en': 'drink',       'emoji': '🥤', 'description': 'Forma Y: deget mare + deget mic sus'},
        {'ro': 'a minca',       'en': 'eat',         'emoji': '🍽️',  'description': 'Toate vârfurile adunate (O plat)'},
        {'ro': 'atentie',       'en': 'attention',   'emoji': '☝️',  'description': 'Arătător ridicat (mâna sus, fără deget mare)'},
        {'ro': 'ok',            'en': 'ok',          'emoji': '👌', 'description': 'Cerc cu degetul mare și index'},
        {'ro': 'putere',        'en': 'power',       'emoji': '✊', 'description': 'Pumn (toate degetele închise)'},
        {'ro': 'mă numesc Maria', 'en': 'my name is Maria', 'emoji': '🙋', 'description': 'Mijlociu + degetul mic sus, celelalte îndoite'},
    ]
    return jsonify({'signs': signs, 'count': len(signs)})


@app.route('/api/text-to-sign', methods=['POST'])
def text_to_sign():
    """Convert text to sign language animation"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        return jsonify({
            'success': True,
            'message': f'Text received: {text}',
            'text': text,
            'frames': []
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcribe', methods=['POST'])
def transcribe_endpoint():
    """Accept audio/video, return Whisper transcription."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    media = request.files['file']
    if media.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        transcription = transcribe_media(media)
        return jsonify({
            "success": True,
            "transcription": transcription,
        })
    except Exception as exc:
        return jsonify({"error": f"Transcription failed: {exc}"}), 500

@app.route('/api/video-frames', methods=['POST'])
def video_frames():
    """Extract frames from video file."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    media = request.files['file']
    if media.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        frames = extract_video_frames(media)
        return jsonify({
            "success": True,
            "frames": frames,
        })
    except Exception as exc:
        return jsonify({"error": f"OpenCV processing failed: {exc}"}), 500

@app.route('/api/render-animation', methods=['POST'])
def render_animation():
    """Build an MP4 animation from base64 frames using OpenCV."""
    payload = request.get_json(silent=True) or {}
    frames = payload.get("frames", [])
    fps = payload.get("fps", 12)

    if not isinstance(frames, list) or not frames:
        return jsonify({"error": "frames must be a non-empty list of base64 images"}), 400

    try:
        video_b64 = render_animation_from_frames(frames, fps=fps)
        return jsonify({
            "success": True,
            "video": video_b64,
            "fps": fps,
        })
    except Exception as exc:
        return jsonify({"error": f"Animation rendering failed: {exc}"}), 500

@app.route('/api/generate-animation', methods=['POST'])
def generate_animation():
    """Generate SMPL animation for Romanian text."""
    data = request.get_json()
    text = data.get('text', '').lower()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
                               
        animation_data = text_to_smpl_animation(text)
        video_frames = generate_smpl_frames(animation_data)
        
        return jsonify({
            'success': True,
            'message': f'Generated animation for: {text}',
            'text': text,
            'frames': video_frames,
            'duration': len(video_frames) / 24,          
            'language': 'romanian'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """Generate SMPL animation video file for Romanian text."""
    data = request.get_json()
    text = data.get('text', '').lower()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
                                  
        video_id = str(uuid.uuid4())
        video_filename = f"animation_{video_id}.mp4"
        video_path = VIDEOS_DIR / video_filename
        
                                                
        animation_data = text_to_smpl_animation(text)
        create_animation_video(animation_data, str(video_path))
        
                                               
        video_url = f"http://localhost:5000/api/video/{video_filename}"
        
        return jsonify({
            'success': True,
            'message': f'Generated video for: {text}',
            'text': text,
            'video_url': video_url,
            'video_id': video_id,
            'duration': len(animation_data) / 24,
            'frames_count': len(animation_data),
            'language': 'romanian'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<filename>')
def serve_video(filename):
    """Serve generated video files."""
    video_path = VIDEOS_DIR / filename
    if not video_path.exists():
        return jsonify({'error': 'Video not found'}), 404
    
    return send_file(
        str(video_path),
        mimetype='video/mp4',
        as_attachment=False,
        download_name=filename
    )

@app.route('/api/generate-romanian-video', methods=['POST'])
def generate_romanian_video():
    """Generate SMPL sign language video for Romanian text."""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No Romanian text provided'}), 400
    
    try:
        video_id = str(uuid.uuid4())
        video_filename = f"romanian_animation_{video_id}.mp4"
        video_path = VIDEOS_DIR / video_filename
        
        clean_text = clean_romanian_text(text)
        animation_data = romanian_text_to_smpl_animation(clean_text)
        create_romanian_sign_video(animation_data, str(video_path), text)
        
        video_url = f"http://localhost:5000/api/video/{video_filename}"
        
        return jsonify({
            'success': True,
            'message': f'Generated Romanian sign language video',
            'original_text': text,
            'clean_text': clean_text,
            'video_url': video_url,
            'video_id': video_id,
            'word_count': len(clean_text.split()),
            'duration': len(animation_data) / 30,
            'language': 'romanian'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def transcribe_media(file_storage):
    """Return Whisper transcription for the uploaded audio/video file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_storage.filename)[1]) as tmp:
        file_storage.save(tmp.name)
        temp_path = tmp.name
    try:
        result = get_whisper_model().transcribe(temp_path, fp16=False)
        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language"),
            "segments": result.get("segments", []),
        }
    finally:
        os.remove(temp_path)

def extract_video_frames(file_storage, every_n=15, max_frames=30):
    """Extract and encode video frames as base64."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_storage.filename)[1]) as tmp:
        file_storage.save(tmp.name)
        temp_path = tmp.name

    frames_encoded = []
    cap = cv2.VideoCapture(temp_path)
    try:
        if not cap.isOpened():
            raise RuntimeError("Unable to open video stream")

        frame_idx = 0
        sampled = 0
        while sampled < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % every_n == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                success, buffer = cv2.imencode('.png', frame_rgb)
                if success:
                    frames_encoded.append(base64.b64encode(buffer).decode('utf-8'))
                    sampled += 1
            frame_idx += 1

        return frames_encoded
    finally:
        cap.release()
        os.remove(temp_path)

def render_animation_from_frames(base64_frames, fps=12):
    """Use OpenCV to stitch decoded base64 frames into a video, return base64 MP4."""
    decoded_frames = []
    for encoded in base64_frames:
        buffer = np.frombuffer(base64.b64decode(encoded), dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Invalid frame data provided")
        decoded_frames.append(frame)

    height, width, _ = decoded_frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
        video_path = tmp_video.name

    writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
    try:
        for frame in decoded_frames:
            resized = cv2.resize(frame, (width, height))
            writer.write(resized)
    finally:
        writer.release()

    with open(video_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode('utf-8')
    os.remove(video_path)
    return video_b64

def text_to_smpl_animation(text):
    """Convert text to SMPL animation keyframes."""
    clean_text = clean_romanian_text(text)
    words = re.findall(r'\b\w+\b', clean_text)
    animation_frames = []

    for i, word in enumerate(words):
        if word in ROMANIAN_SIGNS:
            sign_data = ROMANIAN_SIGNS[word]
        else:
            sign_data = generate_default_romanian_sign(word)

                                                               
        word_frames = []
        for frame in range(24):
            t = frame / 23.0

            frame_data = {
                'timestamp': i + t,
                'body_pose': interpolate_pose(get_neutral_pose(), sign_data['body'], t),
                'left_hand': interpolate_pose([0, 0, 0], sign_data['left_hand'], t),
                'right_hand': interpolate_pose([0, 0, 0], sign_data['right_hand'], t),
                'facial_expression': get_neutral_expression(),
                'word': word,
                'frame': frame
            }
            word_frames.append(frame_data)

        animation_frames.extend(word_frames)

        if i < len(words) - 1:
            for frame in range(12):
                pause_frame = {
                    'timestamp': i + 1 + frame / 24.0,
                    'body_pose': get_neutral_pose(),
                    'left_hand': [0, 0, 0],
                    'right_hand': [0, 0, 0],
                    'facial_expression': get_neutral_expression(),
                    'word': 'pause',
                    'frame': frame
                }
                animation_frames.append(pause_frame)

    return animation_frames

def interpolate_pose(start, end, t):
    """Linear interpolation between two poses."""
    return [
        start[i] + (end[i] - start[i]) * smooth_step(t)
        for i in range(len(start))
    ]

def smooth_step(t):
    """Smooth interpolation curve (ease in/out)."""
    return t * t * (3 - 2 * t)

def get_neutral_pose():
    """Return neutral body pose."""
    return [0.0, 0.0, 0.0]

def get_neutral_expression():
    """Return neutral facial expression."""
    return [0.0] * 10                                   

def generate_smpl_frames(animation_data):
    """Generate visual frames from SMPL animation data."""
    frames = []
    
    for frame_data in animation_data:
                                                   
        frame_image = create_avatar_frame(frame_data)
        frames.append(frame_image)
    
    return frames

def create_avatar_frame(frame_data):
    """Create a single avatar frame as base64 image."""
                                      
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    
                         
    for y in range(512):
        color_val = int(200 + (y / 512) * 55)              
        img[y, :] = [color_val, color_val, 255]                       
    
                                                
    center_x, center_y = 256, 350
    
                                     
    pose = frame_data['body_pose']
    head_x = center_x + int(pose[0] * 100)
    head_y = center_y - 150 + int(pose[1] * 50)
    
               
    cv2.circle(img, (head_x, head_y), 40, (255, 220, 180), -1)              
    cv2.circle(img, (head_x, head_y), 40, (200, 180, 140), 3)                 
    
               
    cv2.circle(img, (head_x - 15, head_y - 10), 5, (50, 50, 50), -1)
    cv2.circle(img, (head_x + 15, head_y - 10), 5, (50, 50, 50), -1)
    
               
    body_bottom_y = center_y + 100
    cv2.line(img, (head_x, head_y + 40), (center_x, body_bottom_y), (100, 100, 200), 8)
    
                                   
    left_hand = frame_data['left_hand']
    right_hand = frame_data['right_hand']
    
              
    left_hand_x = center_x - 80 + int(left_hand[0] * 200)
    left_hand_y = center_y - 20 + int(left_hand[1] * 100) - int(left_hand[2] * 50)
    cv2.line(img, (center_x - 20, center_y - 50), (left_hand_x, left_hand_y), (255, 200, 150), 6)
    cv2.circle(img, (left_hand_x, left_hand_y), 15, (255, 180, 120), -1)        
    
               
    right_hand_x = center_x + 80 + int(right_hand[0] * 200)
    right_hand_y = center_y - 20 + int(right_hand[1] * 100) - int(right_hand[2] * 50)
    cv2.line(img, (center_x + 20, center_y - 50), (right_hand_x, right_hand_y), (255, 200, 150), 6)
    cv2.circle(img, (right_hand_x, right_hand_y), 15, (255, 180, 120), -1)        
    
               
    cv2.line(img, (center_x - 15, body_bottom_y), (center_x - 30, center_y + 200), (100, 100, 200), 6)
    cv2.line(img, (center_x + 15, body_bottom_y), (center_x + 30, center_y + 200), (100, 100, 200), 6)
    
                   
    word = frame_data.get('word', '')
    if word and word != 'pause':
        cv2.putText(img, word.upper(), (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (50, 50, 150), 3)
    
                   
    timestamp = f"{frame_data.get('timestamp', 0):.1f}s"
    cv2.putText(img, timestamp, (400, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
    
                      
    success, buffer = cv2.imencode('.png', img)
    if success:
        return base64.b64encode(buffer).decode('utf-8')
    else:
        raise RuntimeError("Failed to encode frame")

def create_animation_video(animation_data, output_path, fps=24):
    """Create MP4 video file from SMPL animation data."""
    if not animation_data:
        raise ValueError("No animation data provided")
    
                    
    width, height = 1080, 1920                                   
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
                             
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    try:
        print(f"Creating video with {len(animation_data)} frames...")
        
        for i, frame_data in enumerate(animation_data):
                                       
            frame = create_hd_avatar_frame(frame_data, width, height)
            out.write(frame)
            
            if (i + 1) % 24 == 0:                         
                print(f"Processed {i + 1}/{len(animation_data)} frames ({(i+1)/len(animation_data)*100:.1f}%)")
        
        print(f"Video saved: {output_path}")
        
    finally:
        out.release()

def create_hd_avatar_frame(frame_data, width=1080, height=1920):
    """Create high-quality avatar frame for video."""
                     
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
                                
    for y in range(height):
                                 
        r = int(100 + (y / height) * 50)               
        g = int(50 + (y / height) * 100)                
        b = int(200 + (y / height) * 55)               
        img[y, :] = [b, g, r]              
    
                                   
    center_x = width // 2
    center_y = int(height * 0.6)                                       
    
                        
    pose = frame_data['body_pose']
    left_hand = frame_data['left_hand']
    right_hand = frame_data['right_hand']
    word = frame_data.get('word', '')
    timestamp = frame_data.get('timestamp', 0)
    
                          
    scale = 2.5
    
                                       
    head_x = center_x + int(pose[0] * 150 * scale)
    head_y = center_y - int(200 * scale) + int(pose[1] * 80 * scale)
    
                                      
    head_radius = int(60 * scale)
    cv2.circle(img, (head_x, head_y), head_radius, (180, 150, 120), -1)        
    cv2.circle(img, (head_x, head_y), head_radius, (140, 120, 100), 4)            
    
          
    eye_size = int(8 * scale)
    eye_offset = int(20 * scale)
    cv2.circle(img, (head_x - eye_offset, head_y - int(15 * scale)), eye_size, (40, 40, 40), -1)
    cv2.circle(img, (head_x + eye_offset, head_y - int(15 * scale)), eye_size, (40, 40, 40), -1)
    
                          
    mouth_y = head_y + int(20 * scale)
    cv2.ellipse(img, (head_x, mouth_y), (int(15 * scale), int(8 * scale)), 0, 0, 180, (80, 60, 60), 3)
    
          
    body_width = int(12 * scale)
    body_length = int(180 * scale)
    body_top = head_y + head_radius
    body_bottom = body_top + body_length
    
    cv2.line(img, (head_x, body_top), (center_x, body_bottom), (80, 120, 160), body_width)
    
                                      
    shoulder_y = body_top + int(40 * scale)
    arm_width = int(8 * scale)
    
              
    left_shoulder = (center_x - int(40 * scale), shoulder_y)
    left_hand_x = center_x - int(120 * scale) + int(left_hand[0] * 300 * scale)
    left_hand_y = shoulder_y + int(left_hand[1] * 150 * scale) - int(left_hand[2] * 80 * scale)
    
    cv2.line(img, left_shoulder, (left_hand_x, left_hand_y), (120, 100, 80), arm_width)
    cv2.circle(img, (left_hand_x, left_hand_y), int(20 * scale), (150, 120, 90), -1)        
    
               
    right_shoulder = (center_x + int(40 * scale), shoulder_y)
    right_hand_x = center_x + int(120 * scale) + int(right_hand[0] * 300 * scale)
    right_hand_y = shoulder_y + int(right_hand[1] * 150 * scale) - int(right_hand[2] * 80 * scale)
    
    cv2.line(img, right_shoulder, (right_hand_x, right_hand_y), (120, 100, 80), arm_width)
    cv2.circle(img, (right_hand_x, right_hand_y), int(20 * scale), (150, 120, 90), -1)        
    
          
    leg_width = int(10 * scale)
    leg_length = int(250 * scale)
    
    cv2.line(img, (center_x - int(20 * scale), body_bottom), 
             (center_x - int(40 * scale), body_bottom + leg_length), (80, 120, 160), leg_width)
    cv2.line(img, (center_x + int(20 * scale), body_bottom), 
             (center_x + int(40 * scale), body_bottom + leg_length), (80, 120, 160), leg_width)
    
                                       
    if word and word != 'pause':
                                         
        font_scale = 3.0
        thickness = 8
        text_size = cv2.getTextSize(word.upper(), cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (width - text_size[0]) // 2
        text_y = int(height * 0.15)
        
                         
        cv2.rectangle(img, (text_x - 20, text_y - text_size[1] - 20), 
                     (text_x + text_size[0] + 20, text_y + 20), (255, 255, 255), -1)
        cv2.rectangle(img, (text_x - 20, text_y - text_size[1] - 20), 
                     (text_x + text_size[0] + 20, text_y + 20), (200, 200, 200), 3)
        
              
        cv2.putText(img, word.upper(), (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, (50, 50, 150), thickness)
    
                  
    progress = timestamp / 20.0 if timestamp <= 20 else 1.0                         
    bar_width = int(width * 0.8)
    bar_height = 12
    bar_x = (width - bar_width) // 2
    bar_y = height - 100
    
                         
    cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
                   
    fill_width = int(bar_width * progress)
    cv2.rectangle(img, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), (100, 200, 100), -1)
    
               
    time_text = f"{timestamp:.1f}s"
    cv2.putText(img, time_text, (bar_x, bar_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 
               1.2, (255, 255, 255), 4)
    
    return img

def romanian_text_to_smpl_animation(text):
    """Convert Romanian text to SMPL animation keyframes (30fps)."""
    words = re.findall(r'\b\w+\b', text.lower())
    animation_frames = []
    
    for i, word in enumerate(words):
                                         
        if word in ROMANIAN_SIGNS:
            sign_data = ROMANIAN_SIGNS[word]
        else:
            sign_data = generate_default_romanian_sign(word)
        
                                                       
        for frame in range(30):
            t = frame / 29.0          
            
            frame_data = {
                'timestamp': i + t,
                'word': word,
                'frame': frame,
                'body_pose': interpolate_pose([0, 0, 0], sign_data['body'], t),
                'left_hand': interpolate_pose([0, 0, 0], sign_data['left_hand'], t),
                'right_hand': interpolate_pose([0, 0, 0], sign_data['right_hand'], t),
                'facial_expression': [0.0] * 10
            }
            animation_frames.append(frame_data)
        
                                                        
        if i < len(words) - 1:
            for frame in range(15):
                pause_frame = {
                    'timestamp': i + 1 + frame / 30.0,
                    'word': 'pause',
                    'frame': frame,
                    'body_pose': [0, 0, 0],
                    'left_hand': [0, 0, 0],
                    'right_hand': [0, 0, 0],
                    'facial_expression': [0.0] * 10
                }
                animation_frames.append(pause_frame)
    
    return animation_frames

def generate_default_romanian_sign(word):
    """Generate default Romanian sign animation for unknown words."""
                                                               
    hash_val = hash(word) % 1000
    
    return {
        'body': [
            (hash_val % 3 - 1) * 0.1,               
            (hash_val % 5 - 2) * 0.1,               
            (hash_val % 4 - 2) * 0.05               
        ],
        'left_hand': [
            (hash_val % 7) * 0.1,                
            (hash_val % 6) * 0.1,                
            ((hash_val % 5) - 2) * 0.1              
        ],
        'right_hand': [
            (hash_val % 7) * 0.1,                
            (hash_val % 6) * 0.1,                
            -((hash_val % 5) - 2) * 0.1                        
        ]
    }

def create_romanian_sign_video(animation_data, output_path, original_text, fps=30):
    """Create Romanian sign language video."""
    width, height = 1920, 1080
                                                                                
    out = None
    codec_used = None
    for codec in ['avc1', 'H264', 'mp4v']:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if out.isOpened():
            print(f"Using codec {codec} for video writer")
            codec_used = codec
            break
        out.release()
        out = None
    if out is None:
        raise RuntimeError("No suitable codec found for VideoWriter (tried avc1, H264, mp4v)")
    
    try:
        for i, frame_data in enumerate(animation_data):
            frame = create_romanian_sign_frame(frame_data, width, height, original_text)
            out.write(frame)
            
            if (i + 1) % 30 == 0:
                print(f"Processed {i + 1}/{len(animation_data)} frames")
    finally:
        out.release()

                                                                                                    
    if codec_used not in ('avc1', 'H264'):
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            tmp_out = f"{output_path}_h264.mp4"
            cmd = [
                ffmpeg,
                "-y",
                "-i", str(output_path),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(tmp_out),
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                os.replace(tmp_out, output_path)
                print("Transcoded video to H.264 for browser playback.")
            except subprocess.CalledProcessError as exc:
                print(f"ffmpeg transcode failed, keeping original file: {exc}")

def create_romanian_sign_frame(frame_data, width=1920, height=1080, original_text=""):
    """Create frame for Romanian sign language."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
                            
    for y in range(height):
        if y < height // 3:
            img[y, :] = [139, 69, 19]        
        elif y < 2 * height // 3:
            img[y, :] = [0, 215, 255]          
        else:
            img[y, :] = [60, 60, 200]       
    
    center_x = width // 2
    center_y = int(height * 0.65)
    pose = frame_data['body_pose']
    left_hand = frame_data['left_hand']
    right_hand = frame_data['right_hand']
    word = frame_data.get('word', '')
    
    scale = 3.0
    
                 
    head_x = center_x + int(pose[0] * 200 * scale)
    head_y = center_y - int(300 * scale) + int(pose[1] * 100 * scale)
    head_radius = int(80 * scale)
    
    cv2.circle(img, (head_x, head_y), head_radius, (200, 180, 160), -1)
    cv2.circle(img, (head_x, head_y), head_radius, (160, 140, 120), 5)
    
          
    eye_size = int(12 * scale)
    eye_offset = int(25 * scale)
    cv2.circle(img, (head_x - eye_offset, head_y - int(20 * scale)), eye_size, (60, 60, 60), -1)
    cv2.circle(img, (head_x + eye_offset, head_y - int(20 * scale)), eye_size, (60, 60, 60), -1)
    
                   
    body_width = int(15 * scale)
    body_length = int(250 * scale)
    body_top = head_y + head_radius
    body_bottom = body_top + body_length
    
    cv2.line(img, (head_x, body_top), (center_x, body_bottom), (100, 150, 200), body_width)
    
          
    shoulder_y = body_top + int(60 * scale)
    arm_width = int(12 * scale)
    
    left_hand_x = center_x - int(150 * scale) + int(left_hand[0] * 400 * scale)
    left_hand_y = shoulder_y + int(left_hand[1] * 200 * scale) - int(left_hand[2] * 100 * scale)
    cv2.line(img, (center_x - int(60 * scale), shoulder_y), (left_hand_x, left_hand_y), (140, 120, 100), arm_width)
    cv2.circle(img, (left_hand_x, left_hand_y), int(25 * scale), (180, 150, 120), -1)
    
    right_hand_x = center_x + int(150 * scale) + int(right_hand[0] * 400 * scale)
    right_hand_y = shoulder_y + int(right_hand[1] * 200 * scale) - int(right_hand[2] * 100 * scale)
    cv2.line(img, (center_x + int(60 * scale), shoulder_y), (right_hand_x, right_hand_y), (140, 120, 100), arm_width)
    cv2.circle(img, (right_hand_x, right_hand_y), int(25 * scale), (180, 150, 120), -1)
    
                  
    if word and word != 'pause':
        font_scale = 4.0
        thickness = 12
        text_size = cv2.getTextSize(word.upper(), cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (width - text_size[0]) // 2
        text_y = int(height * 0.12)
        
        cv2.rectangle(img, (text_x - 40, text_y - text_size[1] - 40), 
                     (text_x + text_size[0] + 40, text_y + 40), (255, 255, 255), -1)
        cv2.putText(img, word.upper(), (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, (60, 60, 200), thickness)
    
    return img

                                                                        

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPT_AUDIO_TO_SIGN = PROJECT_ROOT / "integration" / "audio_to_sign_video.py"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_smplx_pkl_data(pkl_path: Path):
    """Load project PKL files on CPU without importing the heavy renderer."""
    import pickle
    import io
    import torch

    class CPUUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if module == "torch.storage" and name == "_load_from_bytes":
                return lambda b: torch.load(
                    io.BytesIO(b),
                    map_location="cpu",
                    weights_only=False,
                )
            return super().find_class(module, name)

    try:
        return torch.load(pkl_path, map_location="cpu", weights_only=False)
    except Exception:
        with open(pkl_path, "rb") as f:
            return CPUUnpickler(f).load()


def load_ro_npz_data(npz_path: str):
    """Load Romanian LSR NPZ keypoints file."""
    data = np.load(npz_path)
    return data["joints"], data.get("vis", np.ones(data["joints"].shape[:2], dtype=np.float32))


def iter_romanian_sign_units(translator, text: str, max_words: int = 4):
    """Split Romanian text into (word, ro_sign) units.

    ro_sign is a dict with 'npz_file' when an LSR Romanian sign is found,
    or None when only the WLASL English fallback should be used.
    """
    words = re.findall(r"[\w]+", text.strip(), flags=re.UNICODE)
    return [(word, _lookup_ro_video(word.lower())) for word in words]


def normalize_avatar_phrase(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


_google_translate_cache: dict[tuple[str, str, str], list[str]] = {}

                                                                               
def _load_ro_video_dict() -> dict:
    path = PROJECT_ROOT / "integration" / "ro_video_sign_dictionary.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_RO_VIDEO_DICT: dict = _load_ro_video_dict()


                                                                            
def _load_ro_hamnosys_dict() -> dict:
    path = PROJECT_ROOT / "integration" / "romanian_sign_dictionary.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_RO_HAMNOSYS_DICT: dict = _load_ro_hamnosys_dict()


def _lookup_ro_hamnosys(word: str) -> "dict | None":
    """Look up a Romanian word in the HamNoSys PKL dictionary, with diacritic + fuzzy fallback."""
    if not word:
        return None
    if word in _RO_HAMNOSYS_DICT:
        return _RO_HAMNOSYS_DICT[word]
    norm = normalize_avatar_phrase(word)
    if norm in _RO_HAMNOSYS_DICT:
        return _RO_HAMNOSYS_DICT[norm]
    for key, val in _RO_HAMNOSYS_DICT.items():
        if normalize_avatar_phrase(key) == norm:
            return val
    if len(norm) >= 4:
        best_key, best_dist = None, 3
        for key in _RO_HAMNOSYS_DICT:
            key_norm = normalize_avatar_phrase(key)
            if abs(len(key_norm) - len(norm)) > 2:
                continue
            dist = _levenshtein(norm, key_norm)
            if dist < best_dist:
                best_dist = dist
                best_key = key
        if best_key is not None and best_dist <= 2:
            return _RO_HAMNOSYS_DICT[best_key]
    return None


def _levenshtein(a: str, b: str) -> int:
    """Fast Levenshtein edit distance."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def _lookup_ro_video(word: str) -> "dict | None":
    """Look up a Romanian word in the LSR video dictionary, with diacritic + fuzzy fallback."""
    if not word:
        return None
                      
    if word in _RO_VIDEO_DICT:
        return _RO_VIDEO_DICT[word]
                                             
    norm = normalize_avatar_phrase(word)
    if norm in _RO_VIDEO_DICT:
        return _RO_VIDEO_DICT[norm]
                     
    for key, val in _RO_VIDEO_DICT.items():
        if key.startswith(word) or word.startswith(key):
            return val
                                                                           
                                                                     
    if len(norm) >= 4:
        best_key, best_dist = None, 3
        for key in _RO_VIDEO_DICT:
            key_norm = normalize_avatar_phrase(key)
            if abs(len(key_norm) - len(norm)) > 2:
                continue                                      
            dist = _levenshtein(norm, key_norm)
            if dist < best_dist:
                best_dist = dist
                best_key = key
        if best_key is not None and best_dist <= 2:
            return _RO_VIDEO_DICT[best_key]
    return None


                                                                      
_RO_EN_OFFLINE: dict[str, str] = {
    "mama": "mother", "tata": "father", "frate": "brother", "sora": "sister",
    "familie": "family", "bunica": "grandmother", "bunic": "grandfather",
    "copil": "child", "baiat": "boy", "fata": "girl", "barbat": "man", "femeie": "woman",
    "buna": "hello", "salut": "hello", "pa": "goodbye", "multumesc": "thank",
    "te rog": "please", "scuze": "sorry", "da": "yes", "nu": "no",
    "bine": "good", "rau": "bad", "frumos": "beautiful", "acasa": "home",
    "mancare": "food", "apa": "drink", "lapte": "milk", "paine": "bread",
    "carte": "book", "scoala": "school", "student": "student", "profesor": "teach",
    "calculator": "computer", "telefon": "phone", "masina": "car",
    "caine": "dog", "pisica": "cat", "pasare": "bird",
    "rosu": "red", "albastru": "blue", "verde": "green", "negru": "black",
    "alb": "white", "galben": "yellow", "mers": "walk", "joc": "play",
    "lucru": "work", "ajutor": "help", "iubire": "love", "timp": "time",
    "acum": "now", "ieri": "yesterday", "maine": "tomorrow", "zi": "day",
    "casa": "house", "munca": "work", "scaun": "chair", "masa": "table",
    "intelege": "understand", "stiu": "know", "vad": "see", "vreau": "want",
    "nevoie": "need", "place": "like", "gandesc": "think", "invat": "learn",
    "citesc": "read", "scriu": "write", "cumpar": "buy", "platesc": "pay",
    "opreste": "stop", "asteapta": "wait", "vino": "come", "du-te": "go",
    "vechi": "old", "usor": "easy", "destul": "enough", "mai mult": "more",
    "niciodata": "never", "curand": "soon", "tarziu": "later", "varsta": "age",
    "numele meu": "name", "cine": "who", "ce": "what", "cand": "when",
    "unde": "where", "de ce": "why", "surd": "deaf", "diferit": "different",
                                        
    "ma": "me", "mă": "me", "eu": "me",
    "numesc": "name", "cheama": "name", "cheamă": "name", "numeste": "name", "numește": "name",
    "sunt": "i", "esti": "you", "ești": "you",
    "studenta": "student", "studentă": "student", "elev": "student", "eleva": "student",
    "universitate": "university", "universitatea": "university",
    "tehnica": "technology", "tehnică": "technology", "tehnic": "technology",
    "moldova": "moldova", "chisinau": "chisinau",
    "locuiesc": "live", "traiesc": "live", "trăiesc": "live",
    "ani": "age", "am": "have",
}

                                                                                            
_RO_STOP_WORDS = {
    "la", "in", "în", "de", "din", "pe", "cu", "pentru", "prin", "spre",
    "fara", "fără", "intre", "între", "dupa", "după", "inainte", "înainte",
    "si", "și", "dar", "sau", "ori", "nici", "ca", "că", "daca", "dacă",
    "o", "un", "o", "al", "ai", "ale", "a",
    "mi", "ti", "îi", "ne", "va", "le", "i",
    "cel", "cea", "cei", "cele",
}


def google_translate_candidates(text: str, source: str = "ro", target: str = "en") -> list[str]:
    """Translate with Google Translate's web endpoint and include alternatives."""
    text = (text or "").strip()
    if not text:
        return []

    cache_key = (source, target, text.lower())
    if cache_key in _google_translate_cache:
        return _google_translate_cache[cache_key]

    try:
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        params = urlencode({
            "client": "gtx",
            "sl": source,
            "tl": target,
            "q": text,
            "dt": ["t", "at"],
        }, doseq=True)
        req = Request(
            f"https://translate.googleapis.com/translate_a/single?{params}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(req, timeout=6) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        candidates = []
        translated = "".join(part[0] for part in payload[0] if part and part[0]).strip()
        if translated:
            candidates.append(translated)

                                                                                
        if len(payload) > 5 and isinstance(payload[5], list):
            for alt_block in payload[5]:
                if not isinstance(alt_block, list) or len(alt_block) < 3:
                    continue
                alternatives = alt_block[2]
                if not isinstance(alternatives, list):
                    continue
                for alt in alternatives:
                    if isinstance(alt, list) and alt and isinstance(alt[0], str):
                        candidates.append(alt[0].strip())

        deduped = []
        seen = set()
        for candidate in candidates:
            key = normalize_avatar_phrase(candidate)
            if key and key not in seen:
                seen.add(key)
                deduped.append(candidate)

        if deduped:
            _google_translate_cache[cache_key] = deduped
            return deduped
    except Exception as exc:
        print(f"Google Translate failed for {text!r}: {exc}")
    return []


def google_translate_text(text: str, source: str = "ro", target: str = "en"):
    candidates = google_translate_candidates(text, source=source, target=target)
    return candidates[0] if candidates else None


_VOWELS = frozenset("aeiou")

def _consonant_skeleton(s: str) -> str:
    """Remove vowels and non-alpha chars; lowercase — e.g. 'water'→'wtr', 'wter'→'wtr'."""
    return "".join(c for c in s.lower() if c.isalpha() and c not in _VOWELS)

def _strip_wlasl_key(k: str) -> str:
    """Normalize a raw WLASL key: drop to_ prefix, trailing digits/underscores."""
    k = k.lower().strip()
    if k.startswith("to_"):
        k = k[3:]
    return re.sub(r"[_0-9]+$", "", k)

_wlasl_index_cache: dict = {}                                               

def _get_wlasl_skeleton_index(sign_dictionary: dict) -> dict:
    """Build (once) a consonant-skeleton → WLASL-key lookup."""
    if _wlasl_index_cache:
        return _wlasl_index_cache
    for key in sign_dictionary:
        stripped = _strip_wlasl_key(key)
        for form in (stripped, _consonant_skeleton(stripped)):
            if form and form not in _wlasl_index_cache:
                _wlasl_index_cache[form] = key
    return _wlasl_index_cache


def english_search_candidates(text: str) -> list[str]:
    normalized_space = normalize_avatar_phrase(text)
    normalized_underscore = normalized_space.replace(" ", "_")
    normalized_compact = normalized_space.replace(" ", "")
    tokens = re.findall(r"[a-z0-9_]+", normalized_underscore)

    candidates = []
    for value in [text.lower().strip(), normalized_space, normalized_underscore, normalized_compact]:
        if value and value not in candidates:
            candidates.append(value)
    for token in tokens:
        if token and token not in candidates:
            candidates.append(token)
        to_token = f"to_{token}"
        if token and to_token not in candidates:
            candidates.append(to_token)
    return candidates


def make_avatar_sign(translator, dictionary_key: str, lookup: str, score: float, method_suffix: str):
    data = translator.sign_dictionary[dictionary_key]
    return {
        "word": dictionary_key,
        "english": dictionary_key,
        "lookup": lookup,
        "match_score": round(float(score), 3),
        "pkl_file": data["pkl_file"],
        "method": f"{data.get('source', 'sign_dictionary')}_{method_suffix}",
    }


def find_english_avatar_pkl(
    translator,
    english_text: str,
    min_fuzzy_score: float = 0.72,
    allow_generic_tokens: bool = True,
):
    """Find an SMPL-X PKL in the English dataset.
    Lookup order:
      1. Exact phrase variants
      2. to_<word> variants
      3. Consonant-skeleton index (handles wter=water, fmily=family, school4=school, etc.)
      4. Fuzzy SequenceMatcher (threshold min_fuzzy_score)
    """
    if not english_text:
        return None

    normalized_space = normalize_avatar_phrase(english_text)
    tokens = [t for t in normalized_space.split() if t]
                                                                                 
                                                                                     
    generic_tokens = {
        "a", "an", "the", "of", "and", "or",
        "am", "is", "are", "have", "has",
    }
    if not allow_generic_tokens and len(tokens) == 1 and tokens[0] in generic_tokens:
        return None

                                                                                
    phrase_variants = [
        english_text.lower().strip(),
        normalized_space,
        normalized_space.replace(" ", "_"),
        normalized_space.replace(" ", ""),
    ]
    for candidate in phrase_variants:
        if candidate in translator.sign_dictionary:
            return make_avatar_sign(translator, candidate, english_text, 1.0, "exact")

                                                                               
    safe_tokens = (
        tokens if len(tokens) == 1
        else [t for t in tokens if t not in generic_tokens and len(t) >= 3]
    )
    for token in safe_tokens:
        for candidate in (token, f"to_{token}", f"{token}s"):
            if candidate in translator.sign_dictionary:
                return make_avatar_sign(translator, candidate, english_text, 0.92, "token_exact")

                                                                               
    skel_index = _get_wlasl_skeleton_index(translator.sign_dictionary)
    for token in safe_tokens + [normalized_space.replace(" ", "")]:
        for form in (token, _consonant_skeleton(token)):
            if form and form in skel_index:
                orig_key = skel_index[form]
                return make_avatar_sign(translator, orig_key, english_text, 0.88, "skeleton")

                                                                                
    import difflib
    best_key, best_score = None, 0.0
    for key in translator.sign_dictionary:
        label = normalize_avatar_phrase(key.replace("_", " ").replace("-", " "))
        score = difflib.SequenceMatcher(None, normalized_space, label).ratio()
        if score > best_score:
            best_key, best_score = key, score

    if best_key and best_score >= min_fuzzy_score:
        return make_avatar_sign(translator, best_key, english_text, best_score, "fuzzy")

    return None


def find_avatar_pkl_for_romanian(translator, phrase: str):
    """Romanian input -> Google Translate -> English dataset PKL. UI still shows Romanian phrase."""
    for translated in google_translate_candidates(phrase, source="ro", target="en"):
        sign = find_english_avatar_pkl(translator, translated)
        if sign:
            return sign
    return None


def iter_translated_avatar_sign_units(translator, text: str, max_words: int = 4):
    """Translate the whole Romanian text once, then greedily find English PKL signs."""
    translations = google_translate_candidates(text, source="ro", target="en")
    if not translations:
        return [], None

    best_units = []
    for translated in translations:
        english_tokens = normalize_avatar_phrase(translated).split()
        units = []
        i = 0
        while i < len(english_tokens):
            matched = None
            for length in range(min(max_words, len(english_tokens) - i), 0, -1):
                english_phrase = " ".join(english_tokens[i:i + length])
                sign = find_english_avatar_pkl(
                    translator,
                    english_phrase,
                    allow_generic_tokens=(len(english_tokens) == 1),
                )
                if sign:
                    matched = (english_phrase, sign, length)
                    break
            if matched:
                english_phrase, sign, length = matched
                units.append((text, sign, english_phrase))
                i += length
            else:
                i += 1
        if len(units) > len(best_units):
            best_units = units

    return best_units, translations[0]


def iter_avatar_sign_units(translator, text: str, max_words: int = 4):
    """Greedy Romanian phrase segmentation for PKL avatar playback."""
    words = re.findall(r"[\w]+", text.strip(), flags=re.UNICODE)
    units = []
    i = 0
    while i < len(words):
        matched = None
        for length in range(min(max_words, len(words) - i), 0, -1):
            phrase = " ".join(words[i:i + length])
            sign = find_avatar_pkl_for_romanian(translator, phrase)
            if sign:
                matched = (phrase, sign, length)
                break
        if matched:
            phrase, sign, length = matched
            units.append((phrase, sign))
            i += length
        else:
            units.append((words[i], None))
            i += 1
    return units


def build_live_sign_animation(text: str, max_frames_per_sign: int = 42):
    from integration.translator_enhanced import EnhancedTranslator

    translator = EnhancedTranslator()
    sign_units = iter_romanian_sign_units(translator, text)

    frames = []
    signs = []
    for ro_word, ro_sign in sign_units:
        en_text = translator.translate_sentence_ro_to_en(ro_word)
        en_words = re.findall(r"[\w]+", en_text.lower(), flags=re.UNICODE)
        en_word = en_words[0] if en_words else ro_word

                                                                      
        if ro_sign:
            try:
                joints, vis = load_ro_npz_data(ro_sign["npz_file"])
                                                                     
                step = max(1, int(np.ceil(joints.shape[0] / max_frames_per_sign)))
                signs.append({
                    "word": ro_word,
                    "english": ro_sign.get("english", ro_word),
                    "method": "ro_lsr_video",
                    "source": Path(ro_sign["npz_file"]).name,
                })
                for frame_joints in joints[::step, :67, :]:
                    normalized = [
                        [round(float(x), 4), round(float(y), 4), round(float(c), 3)]
                        for x, y, c in frame_joints
                    ]
                    frames.append({"word": ro_word, "points": normalized})
                continue
            except Exception:
                pass

                                           
        sign = translator.find_sign_by_english(en_word)
        if not sign:
            continue

        pkl_path = Path(sign["pkl_file"])
        data = load_smplx_pkl_data(pkl_path)
        points = np.asarray(data.get("2d"), dtype=np.float32)
        if points.ndim != 3 or points.shape[1] < 25:
            continue

        width = float(data.get("width") or 640)
        height = float(data.get("height") or 360)
        step = max(1, int(np.ceil(points.shape[0] / max_frames_per_sign)))

        signs.append({
            "word": ro_word,
            "english": sign.get("english", en_word),
            "method": sign.get("method", ""),
            "source": pkl_path.name,
        })

        for frame_points in points[::step, :67, :]:
            normalized = []
            for x, y, confidence in frame_points:
                normalized.append([
                    round(float(np.clip(x / width, -0.25, 1.25)), 4),
                    round(float(np.clip(y / height, -0.25, 1.25)), 4),
                    round(float(confidence), 3),
                ])
            frames.append({"word": ro_word, "points": normalized})

    if not frames:
        raise RuntimeError("No sign pose frames found for this text.")

    return {
        "success": True,
        "text": text,
        "fps": 24,
        "frame_count": len(frames),
        "signs": signs,
        "frames": frames,
    }


_smplx_avatar_renderer = None
_aitviewer_live_renderer = None
_aitviewer_live_lock = threading.Lock()
_smplx_npz_cache: dict = {}                                           
_smplx_npz_cache_lock = threading.Lock()

                                                                            
                                                                            
                                                             

_smplx_clothing_colors: "np.ndarray | None" = None


def _build_smplx_clothing_colors() -> np.ndarray:
    """Return (10475, 4) RGBA vertex-color array representing clothed avatar."""
    global _smplx_clothing_colors
    if _smplx_clothing_colors is not None:
        return _smplx_clothing_colors

    npz_path = (
        PROJECT_ROOT
        / "sign_avatars" / "common" / "utils"
        / "human_model_files" / "smplx" / "SMPLX_NEUTRAL.npz"
    )
    data = np.load(str(npz_path), allow_pickle=True)
    weights = data["weights"]                       
    dominant = np.argmax(weights, axis=1)                                         

                                                                            
                           
                                                                   
                                                       
                                                                          
                                                  
                                                                           
    SHIRT_JOINTS  = {3, 6, 9, 13, 14, 16, 17}                               
    PANTS_JOINTS  = {0, 1, 2, 4, 5, 7, 8}                                      
    SHOE_JOINTS   = {10, 11}                                   
                                                                     

                      
    C_SKIN  = np.array([0.87, 0.73, 0.55, 1.0], dtype=np.float32)
    C_SHIRT = np.array([0.20, 0.35, 0.75, 1.0], dtype=np.float32)        
    C_PANTS = np.array([0.18, 0.20, 0.32, 1.0], dtype=np.float32)             
    C_SHOE  = np.array([0.14, 0.11, 0.09, 1.0], dtype=np.float32)              

    colors = np.tile(C_SKIN, (10475, 1))
    for vi, j in enumerate(dominant):
        if j in SHIRT_JOINTS:
            colors[vi] = C_SHIRT
        elif j in PANTS_JOINTS:
            colors[vi] = C_PANTS
        elif j in SHOE_JOINTS:
            colors[vi] = C_SHOE

    _smplx_clothing_colors = colors.astype(np.float32)
    return _smplx_clothing_colors


                                                                             
                                                                                
import queue as _queue

_aitviewer_render_queue: "_queue.Queue | None" = None
_aitviewer_worker_thread: "threading.Thread | None" = None
_aitviewer_worker_ready = threading.Event()

_aitviewer_proc: "subprocess.Popen | None" = None
_aitviewer_proc_lock = threading.Lock()


def _get_or_start_aitviewer_proc() -> "subprocess.Popen":
    """Return the long-lived aitviewer subprocess, starting it if needed."""
    global _aitviewer_proc
    with _aitviewer_proc_lock:
        if _aitviewer_proc is not None and _aitviewer_proc.poll() is None:
            return _aitviewer_proc
        _BATCH = Path(__file__).parent / "_render_aitviewer_batch.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(PROJECT_ROOT),
             str(PROJECT_ROOT / "sign_avatars" / "visualizer"),
             str(PROJECT_ROOT / "sign_avatars" / "common" / "utils"),
             env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        proc = subprocess.Popen(
            [sys.executable, str(_BATCH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
                                                                   
        ready_line = proc.stdout.readline()
        try:
            msg = json.loads(ready_line)
            if not msg.get("ready"):
                raise RuntimeError(f"Unexpected ready msg: {ready_line}")
        except Exception as exc:
            proc.kill()
            raise RuntimeError(f"aitviewer subprocess failed to start: {exc} / {ready_line}")
        _aitviewer_proc = proc
        return proc


def _aitviewer_worker_main():
    """Dedicated thread: owns the OpenGL context and processes render jobs."""
    try:
        visualizer_path = PROJECT_ROOT / "sign_avatars" / "visualizer"
        if str(visualizer_path) not in sys.path:
            sys.path.insert(0, str(visualizer_path))

        from aitviewer.configuration import CONFIG as C
        from aitviewer.headless import HeadlessRenderer
        from aitviewer.models.smpl import SMPLLayer
        from aitviewer.renderables.smpl import SMPLSequence
        from aitviewer.utils.so3 import aa2rot_numpy

        smplx_models_path = PROJECT_ROOT / "sign_avatars" / "common" / "utils" / "human_model_files"
        C.smplx_models = str(smplx_models_path.resolve())
        C.device = "cpu"

        renderer = HeadlessRenderer(size=(640, 640))
        renderer.scene.light_mode = "dark"
        renderer.auto_set_camera_target = False
        renderer.scene.camera.position = np.array([0, 0.92, 1.65])
        renderer.scene.camera.target   = np.array([0, 0.82, 0])
        renderer.auto_set_floor = False
        renderer.scene.floor.position  = np.array([0, -0.30, 0])
        renderer.scene.origin.enabled  = False
        renderer.shadows_enabled = False

        smpl_layer = SMPLLayer(
            model_type="smplx", gender="neutral",
            flat_hand_mean=False, device=C.device,
        )
        seq_rot = aa2rot_numpy(np.array([1, 0, 0]) * np.pi)

    except Exception as exc:
        _aitviewer_worker_ready.set()
        print(f"WARNING: aitviewer worker init failed ({exc}); falling back to CPU renderer")
        return

    _aitviewer_worker_ready.set()

    while True:
        job = _aitviewer_render_queue.get()
        if job is None:
            break
        poses, result_q, jpeg_q = job
        try:
            root_p  = poses[:, :3]
            body_p  = poses[:, 3:66]
            lhand_p = poses[:, 66:111]
            rhand_p = poses[:, 111:156]
            shape   = poses[:, 159:169] if poses.shape[1] >= 169 else np.zeros((len(poses), 10), dtype=np.float32)

            seq = SMPLSequence(
                poses_body=body_p, poses_root=root_p,
                poses_left_hand=lhand_p, poses_right_hand=rhand_p,
                betas=shape, smpl_layer=smpl_layer,
                color=(0.87, 0.73, 0.55, 1), rotation=seq_rot,
            )
            try:
                seq.mesh_seq.vertex_colors = _build_smplx_clothing_colors()
            except Exception:
                pass                                                             
            renderer.scene.add(seq)
            uris = []
            try:
                for fi in range(len(poses)):
                    seq.current_frame_id = fi
                    pil_img = renderer.get_frame()
                    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    ok, enc = cv2.imencode(".jpg", bgr,
                                          [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_q)])
                    if ok:
                        uris.append("data:image/jpeg;base64,"
                                    + base64.b64encode(enc.tobytes()).decode("ascii"))
            finally:
                renderer.scene.remove(seq)
            result_q.put(("ok", uris))
        except Exception as exc:
            result_q.put(("error", str(exc)))


def _ensure_aitviewer_worker():
    global _aitviewer_render_queue, _aitviewer_worker_thread
    if _aitviewer_worker_thread is not None:
        return
    _aitviewer_render_queue = _queue.Queue()
    t = threading.Thread(target=_aitviewer_worker_main, daemon=True, name="aitviewer-render")
    t.start()
    _aitviewer_worker_thread = t
    _aitviewer_worker_ready.wait(timeout=30)


def render_aitviewer_poses_via_worker(poses: np.ndarray, jpeg_quality: int = 92) -> list:
    """Render SMPL-X poses using the persistent aitviewer subprocess."""
    proc = _get_or_start_aitviewer_proc()
    payload = json.dumps({"poses": poses.tolist(), "jpeg_quality": jpeg_quality})
    with _aitviewer_proc_lock:
        proc.stdin.write(payload + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
    if not response_line:
        raise RuntimeError("aitviewer subprocess closed unexpectedly")
    result = json.loads(response_line)
    if "error" in result:
        raise RuntimeError(result["error"])
    return result.get("uris", [])


def get_smplx_avatar_renderer():
    """Load the configured SMPL-X model once and reuse it for CPU frame rendering."""
    global _smplx_avatar_renderer
    if _smplx_avatar_renderer is not None:
        return _smplx_avatar_renderer

    import copy
    import importlib.util
    import torch

    utils_dir = PROJECT_ROOT / "sign_avatars" / "common" / "utils"
    if str(utils_dir) not in sys.path:
        sys.path.insert(0, str(utils_dir))

    module_path = utils_dir / "human_models.py"
    spec = importlib.util.spec_from_file_location("human_models_signtranslator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load SMPL-X human model module: {module_path}")

    human_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(human_models)

    smpl_x = human_models.SMPLX()
    layer = copy.deepcopy(smpl_x.layer["neutral"]).to("cpu")
    layer.eval()

    face_arr = np.asarray(smpl_x.face, dtype=np.int32)
    _smplx_avatar_renderer = {
        "torch": torch,
        "layer": layer,
        "face": face_arr,
        "hand_mask": _precompute_hand_face_mask(face_arr),
    }
    return _smplx_avatar_renderer


def get_aitviewer_live_renderer():
    """Create one persistent aitviewer OpenGL context for live avatar frame rendering."""
    global _aitviewer_live_renderer
    if _aitviewer_live_renderer is not None:
        return _aitviewer_live_renderer

    visualizer_path = PROJECT_ROOT / "sign_avatars" / "visualizer"
    if str(visualizer_path) not in sys.path:
        sys.path.insert(0, str(visualizer_path))

    from aitviewer.configuration import CONFIG as C
    from aitviewer.headless import HeadlessRenderer
    from aitviewer.models.smpl import SMPLLayer

    smplx_models_path = PROJECT_ROOT / "sign_avatars" / "common" / "utils" / "human_model_files"
    C.smplx_models = str(smplx_models_path.resolve())
    C.device = "cpu"

    renderer = HeadlessRenderer(size=(640, 640))
    renderer.scene.light_mode = "dark"
    renderer.auto_set_camera_target = False
                                                                            
                                                          
    renderer.scene.camera.position = np.array([0, 0.92, 1.65])
    renderer.scene.camera.target = np.array([0, 0.82, 0])
    renderer.auto_set_floor = False
    renderer.scene.floor.position = np.array([0, -0.30, 0])
    renderer.scene.origin.enabled = False
    renderer.shadows_enabled = False

    smpl_layer = SMPLLayer(
        model_type="smplx",
        gender="neutral",
        flat_hand_mean=False,
        device=C.device,
    )

    _aitviewer_live_renderer = {
        "renderer": renderer,
        "smpl_layer": smpl_layer,
        "config": C,
    }
    return _aitviewer_live_renderer


def _precompute_hand_face_mask(face: np.ndarray) -> np.ndarray:
    """Return boolean (F,) mask — True if any triangle vertex is a hand vertex."""
    v = face          
    return (
        ((v >= 5361) & (v < 7580)).any(axis=1) |
        ((v >= 8245) & (v < 10464)).any(axis=1)
    )


_LIGHT_DIR = np.array([0.3, 0.6, -0.75], dtype=np.float32)                       
_LIGHT_DIR /= np.linalg.norm(_LIGHT_DIR)
_LIGHT_DIR2 = np.array([-0.5, 0.3, -0.5], dtype=np.float32)                        
_LIGHT_DIR2 /= np.linalg.norm(_LIGHT_DIR2)
_BODY_BASE  = np.array([210, 185, 162], dtype=np.float32)                        
_HAND_BASE  = np.array([240, 212, 180], dtype=np.float32)                         
_N_SHADE    = 12                                


def render_smplx_mesh_frame(mesh: np.ndarray, face: np.ndarray,
                             width: int = 512, height: int = 512,
                             hand_mask: np.ndarray = None) -> str:
    """Render one SMPL-X mesh frame with Lambertian shading using CPU/OpenCV."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (32, 28, 48)                               

                                                  
                                                                                    
                                                                                 
    points = np.stack([mesh[:, 0], -mesh[:, 1]], axis=1).astype(np.float32)

    valid = np.isfinite(points).all(axis=1)
    if not np.any(valid):
        raise RuntimeError("SMPL-X mesh projection failed.")

    finite_points = points[valid]
                                                                                   
    min_xy = np.quantile(finite_points, 0.01, axis=0)
    max_xy = np.quantile(finite_points, 0.99, axis=0)
    span = np.maximum(max_xy - min_xy, 0.1)
                                                                 
    margin = 40
    scale = min((width - margin * 2) / span[0], (height - margin * 2) / span[1])
                                                             
    scale = min(scale, max(width, height) * 2.0)
    center = (min_xy + max_xy) / 2
    pts = ((points - center) * scale + np.array([width / 2, height / 2])).astype(np.int32)

    if hand_mask is None:
        hand_mask = _precompute_hand_face_mask(face)

                                                                 
    v0 = mesh[face[:, 0]]
    v1 = mesh[face[:, 1]]
    v2 = mesh[face[:, 2]]
    cross = np.cross(v1 - v0, v2 - v0).astype(np.float32)
    nlen  = np.linalg.norm(cross, axis=1, keepdims=True)
    normals = cross / np.maximum(nlen, 1e-6)
    diff1   = np.clip(normals @ _LIGHT_DIR, 0.0, 1.0)               
    diff2   = np.clip(normals @ _LIGHT_DIR2, 0.0, 1.0)              
                                                                                  
    shade   = (0.45 + 0.40 * diff1 + 0.15 * diff2)                       

                                      
    tri_depth = mesh[face].mean(axis=1)[:, 2]
    sort_idx  = np.argsort(tri_depth)

    body_idx = sort_idx[~hand_mask[sort_idx]]
    hand_idx  = sort_idx[hand_mask[sort_idx]]

                                                                             
    body_shade  = shade[body_idx]
    body_levels = (body_shade * _N_SHADE).astype(int).clip(0, _N_SHADE - 1)
    for lv in range(_N_SHADE):
        mask = body_levels == lv
        if not mask.any():
            continue
        s     = (lv + 0.5) / _N_SHADE
        intensity = 0.35 + 0.65 * s
        color = (_BODY_BASE * intensity).clip(0, 255).astype(np.uint8)
        polys = [pts[face[body_idx[k]]] for k in np.where(mask)[0]]
        cv2.fillPoly(img, polys, (int(color[2]), int(color[1]), int(color[0])))

                                                           
    hand_shade = shade[hand_idx]
    for k, fi in enumerate(hand_idx):
        s = float(hand_shade[k])
        intensity = 0.35 + 0.65 * s
        color = (_HAND_BASE * intensity).clip(0, 255).astype(np.uint8)
        poly  = pts[face[fi]]
        cv2.fillConvexPoly(img, poly, (int(color[2]), int(color[1]), int(color[0])))

                                               
    if len(hand_idx):
        hand_polys = [pts[face[fi]] for fi in hand_idx]
        cv2.polylines(img, hand_polys, isClosed=True, color=(30, 28, 26), thickness=1)

    ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise RuntimeError("Could not encode SMPL-X avatar frame.")

    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def render_aitviewer_pose_frame_uris(
    poses: np.ndarray,
    jpeg_quality: int = 72,
    video_rotation: bool = True,
) -> list:
    """Render SMPL-X pose rows with the same aitviewer avatar used by the video pipeline."""
    poses = np.asarray(poses, dtype=np.float32)
    if poses.ndim != 2 or poses.shape[1] < 156:
        raise RuntimeError(f"Invalid SMPL-X pose shape for aitviewer: {poses.shape}")

    visualizer_path = PROJECT_ROOT / "sign_avatars" / "visualizer"
    if str(visualizer_path) not in sys.path:
        sys.path.insert(0, str(visualizer_path))

    from aitviewer.renderables.smpl import SMPLSequence
    from aitviewer.utils.so3 import aa2rot_numpy

    root_pose = poses[:, :3]
    body_pose = poses[:, 3:66]
    left_hand = poses[:, 66:111]
    right_hand = poses[:, 111:156]
    shape = poses[:, 159:169] if poses.shape[1] >= 169 else np.zeros((len(poses), 10), dtype=np.float32)

    frame_uris = []
    with _aitviewer_live_lock:
        live = get_aitviewer_live_renderer()
        renderer = live["renderer"]
        smpl_layer = live["smpl_layer"]

        sequence_rotation = (
            aa2rot_numpy(np.array([1, 0, 0]) * np.pi)
            if video_rotation
            else np.eye(3)
        )

        smpl_sequence = SMPLSequence(
            poses_body=body_pose,
            poses_root=root_pose,
            poses_left_hand=left_hand,
            poses_right_hand=right_hand,
            betas=shape,
            smpl_layer=smpl_layer,
            color=(0.8, 0.72, 0.425, 1),
            rotation=sequence_rotation,
        )

        renderer.scene.add(smpl_sequence)
        try:
            for frame_index in range(len(poses)):
                smpl_sequence.current_frame_id = frame_index
                pil_image = renderer.get_frame()
                frame_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                ok, encoded = cv2.imencode(
                    ".jpg",
                    frame_bgr,
                    [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
                )
                if not ok:
                    raise RuntimeError("Could not encode aitviewer SMPL-X frame.")

                frame_uris.append(
                    "data:image/jpeg;base64,"
                    + base64.b64encode(encoded.tobytes()).decode("ascii")
                )
        finally:
            renderer.scene.remove(smpl_sequence)

    return frame_uris


def render_skeleton_frame_from_keypoints(joints: np.ndarray, word: str, width: int = 480, height: int = 270) -> str:
    """Render one frame of MediaPipe keypoints as a JPEG skeleton image."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (28, 24, 36)

                                                                        
    pose = joints[:33]                      
    lhand = joints[33:54]              
    rhand = joints[54:75]               

    def pt(j, scale_x=1.0, scale_y=1.0):
        x = int(np.clip(j[0] * scale_x * width, 0, width - 1))
        y = int(np.clip(j[1] * scale_y * height, 0, height - 1))
        return (x, y)

                                              
    body_edges = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    ]
    for a, b in body_edges:
        if a < len(pose) and b < len(pose):
            cv2.line(img, pt(pose[a]), pt(pose[b]), (80, 200, 180), 2)

                      
    hand_edges = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                  (0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
                  (0,17),(17,18),(18,19),(19,20)]
    for a, b in hand_edges:
        if a < len(lhand) and b < len(lhand):
            cv2.line(img, pt(lhand[a]), pt(lhand[b]), (60, 160, 255), 1)
        if a < len(rhand) and b < len(rhand):
            cv2.line(img, pt(rhand[a]), pt(rhand[b]), (255, 140, 60), 1)

                 
    for j in pose[:25]:
        cv2.circle(img, pt(j), 3, (100, 220, 200), -1)
    for j in lhand:
        cv2.circle(img, pt(j), 2, (100, 180, 255), -1)
    for j in rhand:
        cv2.circle(img, pt(j), 2, (255, 160, 80), -1)

                
    if word:
        cv2.putText(img, word, (8, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (13, 148, 136), 1)

    ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not ok:
        raise RuntimeError("Frame encoding failed.")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def render_dataset_keypoint_avatar_frame(joints: np.ndarray, word: str, width: int = 480, height: int = 270) -> str:
    """Render Romanian dataset landmarks directly for maximum sign readability."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (18, 17, 28)

    pts = np.asarray(joints[:, :2], dtype=np.float32).copy()
    important_idx = [0] + list(range(11, 17)) + [23, 24] + list(range(33, 75))
    important = pts[important_idx]
    valid = np.isfinite(important).all(axis=1)
    important = important[valid]
    if len(important) < 4:
        return render_skeleton_frame_from_keypoints(joints, word, width, height)

    min_xy = important.min(axis=0)
    max_xy = important.max(axis=0)
    span = np.maximum(max_xy - min_xy, 1e-4)
    target_w = width * 0.78
    target_h = height * 0.78
    scale = min(target_w / span[0], target_h / span[1])
    center = (min_xy + max_xy) / 2
    screen_center = np.array([width / 2, height / 2 + 8], dtype=np.float32)
    screen_pts = ((pts - center) * scale + screen_center).astype(np.int32)

    def p(index: int) -> tuple[int, int]:
        x, y = screen_pts[index]
        return int(np.clip(x, 0, width - 1)), int(np.clip(y, 0, height - 1))

    def line(a: int, b: int, color, thickness: int = 5):
        cv2.line(img, p(a), p(b), color, thickness, cv2.LINE_AA)

    def dot(index: int, color, radius: int = 5):
        cv2.circle(img, p(index), radius, color, -1, cv2.LINE_AA)

                                                   
    torso = np.array([p(11), p(12), p(24), p(23)], dtype=np.int32)
    cv2.fillConvexPoly(img, torso, (62, 58, 82))
    cv2.polylines(img, [torso], True, (116, 211, 203), 2, cv2.LINE_AA)
    line(11, 12, (116, 211, 203), 5)
    line(23, 24, (82, 76, 105), 4)

    nose = p(0)
    shoulder_mid = ((np.array(p(11)) + np.array(p(12))) / 2).astype(np.int32)
    head_radius = max(13, int(np.linalg.norm(np.array(p(11)) - np.array(p(12))) * 0.22))
    head_center = (
        int(np.clip((nose[0] + shoulder_mid[0]) / 2, 0, width - 1)),
        int(np.clip(nose[1], 0, height - 1)),
    )
    cv2.circle(img, head_center, head_radius, (231, 196, 145), -1, cv2.LINE_AA)
    cv2.circle(img, head_center, head_radius, (44, 38, 48), 2, cv2.LINE_AA)

                                                           
    left_color = (255, 198, 76)
    right_color = (88, 213, 255)
    line(11, 13, left_color, 8)
    line(13, 15, left_color, 8)
    line(12, 14, right_color, 8)
    line(14, 16, right_color, 8)

    hand_edges = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
    ]

    def hand(start: int, color):
        for a, b in hand_edges:
            line(start + a, start + b, color, 3)
        for i in range(start, start + 21):
            dot(i, color, 4)

    hand(33, left_color)
    hand(54, right_color)

    for index in [11, 12, 13, 14, 15, 16]:
        dot(index, (235, 244, 255), 5)

    cv2.putText(img, "stanga", (18, height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, left_color, 1, cv2.LINE_AA)
    cv2.putText(img, "dreapta", (width - 88, height - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, right_color, 1, cv2.LINE_AA)

    ok, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        raise RuntimeError("Dataset avatar frame encoding failed.")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


                                                                                               
                                                                           
_MP_HAND_TO_SMPLX = [5, 6, 7,                        
                      9, 10, 11,                        
                      17, 18, 19,                      
                      13, 14, 15,                     
                      1, 2, 3]                        
                                                          
_SMPLX_LHAND_IDX = list(range(25, 40))
_SMPLX_RHAND_IDX = list(range(40, 55))
                                                         
_BODY_SMPLX_TO_MP = {1: 23, 2: 24, 16: 11, 17: 12, 18: 13, 19: 14,
                     20: 15, 21: 16, 4: 25, 5: 26, 7: 27, 8: 28}


def render_smplx_from_mediapipe_batch(joints_seq: np.ndarray, npz_path: str) -> list:
    """
    Convert Romanian dataset MediaPipe keypoints (T, 75, 3) to SMPL-X avatar frames.

    The dataset does not contain native SMPL-X poses. A full-body fit bends the
    avatar because MediaPipe z/torso points are noisy and use a different
    coordinate convention. Keep the configured SMPL-X avatar torso/head/legs
    neutral and drive only arms + hands from the dataset motion.
    """
    import torch

    T = joints_seq.shape[0]
    cache_keys = [f"aitviewer-fit-v18-fast:{npz_path}:{fi}" for fi in range(T)]

    with _smplx_npz_cache_lock:
        cached = [_smplx_npz_cache.get(k) for k in cache_keys]
    if all(c is not None for c in cached):
        return cached

    rend = get_smplx_avatar_renderer()
    layer = rend["layer"]

    mp = joints_seq.astype(np.float32).copy()
    mp[:, :, 1] = 1.0 - mp[:, :, 1]
                                                                           
    mp[:, :, 2] *= 0.15

    l_hip = mp[:, 23]
    r_hip = mp[:, 24]
    l_sh = mp[:, 11]
    r_sh = mp[:, 12]
    hip_mid = (l_hip + r_hip) / 2
    sh_mid = (l_sh + r_sh) / 2
    torso_h = np.linalg.norm(sh_mid - hip_mid, axis=1, keepdims=True) * 2.5 + 1e-6
    mp_n = (mp - hip_mid[:, None, :]) / torso_h[:, None, :]

                                                                                        
    target_larm_np = np.stack(
        [mp_n[:, 13, :] - mp_n[:, 11, :], mp_n[:, 33, :] - mp_n[:, 11, :]],
        axis=1,
    )
    target_rarm_np = np.stack(
        [mp_n[:, 14, :] - mp_n[:, 12, :], mp_n[:, 54, :] - mp_n[:, 12, :]],
        axis=1,
    )
                                                                           
                                                                                 
    target_larm_np[:, :, 2] = np.maximum(target_larm_np[:, :, 2], -0.05)
    target_rarm_np[:, :, 2] = np.maximum(target_rarm_np[:, :, 2], -0.05)
    target_larm = torch.tensor(target_larm_np, dtype=torch.float32)
    target_rarm = torch.tensor(target_rarm_np, dtype=torch.float32)

    def hand_targets(mp_hand):
        wrist = mp_hand[:, 0, :]
        idx_mcp = mp_hand[:, 5, :]
        scale = np.linalg.norm(idx_mcp - wrist, axis=1, keepdims=True) + 1e-6
        hand_n = (mp_hand - wrist[:, None, :]) / scale[:, None, :] * 0.103
        return torch.tensor(hand_n[:, _MP_HAND_TO_SMPLX, :], dtype=torch.float32)

    target_lhand = hand_targets(mp_n[:, 33:54, :])
    target_rhand = hand_targets(mp_n[:, 54:75, :])

    global_orient = torch.zeros(T, 3)
    body_pose = torch.zeros(T, 63, requires_grad=True)
    lhand_pose = torch.zeros(T, 45, requires_grad=True)
    rhand_pose = torch.zeros(T, 45, requires_grad=True)
    opt = torch.optim.Adam([body_pose, lhand_pose, rhand_pose], lr=0.04)

                                                          
                                                                                   
    arm_pose_mask = torch.zeros(1, 63)
    for joint_idx in (16, 17, 18, 19, 20, 21):
        start_i = (joint_idx - 1) * 3
        arm_pose_mask[:, start_i:start_i + 3] = 1.0

    zeros = lambda n: torch.zeros(T, n)
    for _ in range(60):
        opt.zero_grad()
        masked_body_pose = body_pose * arm_pose_mask
        out = layer(
            global_orient=global_orient,
            body_pose=masked_body_pose,
            left_hand_pose=lhand_pose,
            right_hand_pose=rhand_pose,
            betas=zeros(10),
            jaw_pose=zeros(3),
            leye_pose=zeros(3),
            reye_pose=zeros(3),
            expression=zeros(10),
        )
        j = out.joints
        larm_pred = j[:, [18, 20], :] - j[:, 16:17, :]
        rarm_pred = j[:, [19, 21], :] - j[:, 17:18, :]
        arm_loss = ((larm_pred - target_larm) ** 2).mean() + ((rarm_pred - target_rarm) ** 2).mean()
        lhand_loss = ((j[:, _SMPLX_LHAND_IDX, :] - j[:, 20:21, :] - target_lhand) ** 2).mean()
        rhand_loss = ((j[:, _SMPLX_RHAND_IDX, :] - j[:, 21:22, :] - target_rhand) ** 2).mean()
        reg = (
            0.06 * masked_body_pose.pow(2).mean()
            + 0.03 * lhand_pose.pow(2).mean()
            + 0.03 * rhand_pose.pow(2).mean()
        )
        (arm_loss + 0.8 * lhand_loss + 0.8 * rhand_loss + reg).backward()
        torch.nn.utils.clip_grad_norm_([body_pose, lhand_pose, rhand_pose], max_norm=1.5)
        opt.step()
        with torch.no_grad():
            body_pose.clamp_(-1.6, 1.6)
            lhand_pose.clamp_(-1.2, 1.2)
            rhand_pose.clamp_(-1.2, 1.2)

    body_np = (body_pose * arm_pose_mask).detach().cpu().numpy()
    lhand_np = lhand_pose.detach().cpu().numpy()
    rhand_np = rhand_pose.detach().cpu().numpy()

                                                                              
                                                                      
    if T > 3:
        def _smooth(arr, w=3):
            kernel = np.array([0.25, 0.5, 0.25])
            out = arr.copy()
            for t in range(1, len(arr) - 1):
                out[t] = arr[t-1]*kernel[0] + arr[t]*kernel[1] + arr[t+1]*kernel[2]
            return out
        body_np  = _smooth(body_np)
        lhand_np = _smooth(lhand_np)
        rhand_np = _smooth(rhand_np)

                                                                             
                                                                        
                                                                     
                                                                                    
                                                                                               
    try:
        global_orient_np = global_orient.detach().cpu().numpy()
        aitviewer_orient = np.full_like(global_orient_np, 0.0)
        aitviewer_orient[:, 0] = -math.pi
        poses_for_aitviewer = np.concatenate(
            [aitviewer_orient, body_np, lhand_np, rhand_np], axis=1
        ).astype(np.float32)
        result_uris = render_aitviewer_poses_via_worker(poses_for_aitviewer)
        if result_uris:
            with _smplx_npz_cache_lock:
                for fi, uri in enumerate(result_uris):
                    _smplx_npz_cache[cache_keys[fi]] = uri
            return result_uris
    except Exception:
        pass                                  

                                                                                    
                                                                                 
                                                                                      
    face_arr = rend["face"]
    hand_mask_arr = rend.get("hand_mask")
    zeros_t = lambda n: torch.zeros(T, n)
    with torch.no_grad():
        out_final = layer(
            global_orient=global_orient,
            body_pose=torch.tensor(body_np, dtype=torch.float32),
            left_hand_pose=torch.tensor(lhand_np, dtype=torch.float32),
            right_hand_pose=torch.tensor(rhand_np, dtype=torch.float32),
            betas=zeros_t(10),
            jaw_pose=zeros_t(3),
            leye_pose=zeros_t(3),
            reye_pose=zeros_t(3),
            expression=zeros_t(10),
        )
        verts_batch = out_final.vertices.cpu().numpy()

    result_uris = [
        render_smplx_mesh_frame(verts, face_arr, hand_mask=hand_mask_arr)
        for verts in verts_batch
    ]
    with _smplx_npz_cache_lock:
        for fi, uri in enumerate(result_uris):
            _smplx_npz_cache[cache_keys[fi]] = uri

    return result_uris

def build_smplx_avatar_frames(text: str, max_frames_per_sign: int = 20):
    """Build live frame images from Romanian LSR first, rendered with the SMPL-X/aitviewer avatar."""
    from integration.translator_enhanced import EnhancedTranslator

    translator = EnhancedTranslator()
    sign_units = iter_romanian_sign_units(translator, text)

    frames = []
    signs = []

    for ro_word, ro_sign in sign_units:
                                                                          
        ro_key = ro_word.strip().lower()
        if ro_key in _RO_STOP_WORDS:
            continue

                                                                     
        offline_en = _RO_EN_OFFLINE.get(ro_key)
        if offline_en:
            en_word = offline_en
        else:
            en_text = translator.translate_sentence_ro_to_en(ro_word)
            en_words = re.findall(r"[\w]+", en_text.lower(), flags=re.UNICODE)
            en_word = en_words[0] if en_words else ro_word

                                                                                       
        ro_hams = _lookup_ro_hamnosys(ro_word.lower().strip())
        if ro_hams and ro_hams.get("pkl_file"):
            try:
                pkl_path = Path(ro_hams["pkl_file"])
                hams_data = load_smplx_pkl_data(pkl_path)
                raw_poses = hams_data.get("smplx")
                if raw_poses is None:
                    raw_poses = hams_data.get("unsmooth_smplx")
                if raw_poses is not None:
                    poses = np.asarray(raw_poses, dtype=np.float32)
                    if poses.ndim == 2 and poses.shape[1] >= 156:
                        step = max(1, int(np.ceil(poses.shape[0] / max_frames_per_sign)))
                        sampled = poses[::step][:max_frames_per_sign]
                        uris = render_aitviewer_poses_via_worker(sampled)
                        for img_uri in uris:
                            frames.append({"word": ro_word, "image": img_uri})
                        signs.append({
                            "word": ro_word,
                            "english": ro_hams.get("english", ro_word),
                            "method": "ro_hamnosys_pkl_aitviewer",
                            "source": pkl_path.name,
                        })
                        continue
            except Exception:
                pass

                                                                                   
        if ro_sign and ro_sign.get("npz_file"):
            try:
                joints, _ = load_ro_npz_data(ro_sign["npz_file"])
                step = max(1, int(np.ceil(joints.shape[0] / max_frames_per_sign)))
                sampled = joints[::step][:max_frames_per_sign]
                for img_uri in render_smplx_from_mediapipe_batch(sampled, ro_sign["npz_file"]):
                    frames.append({"word": ro_word, "image": img_uri})
                signs.append({
                    "word": ro_word,
                    "english": ro_sign.get("english", ro_word),
                    "method": "ro_lsr_video_smplx_fit_aitviewer",
                    "source": Path(ro_sign["npz_file"]).name,
                })
                continue
            except Exception:
                pass

                                                                                        
                                                                                    
                                                  
        spoter_dir = Path(__file__).parent / "spoter_animations"
        spoter_npy = spoter_dir / f"{en_word.lower()}.npy"
        if spoter_npy.exists():
            try:
                kp_seq = np.load(str(spoter_npy))              
                if kp_seq.ndim == 3 and kp_seq.shape[1] == 75:
                    step = max(1, int(np.ceil(kp_seq.shape[0] / max_frames_per_sign)))
                    sampled = kp_seq[::step][:max_frames_per_sign]
                    for img_uri in render_smplx_from_mediapipe_batch(sampled, str(spoter_npy)):
                        frames.append({"word": ro_word, "image": img_uri})
                    signs.append({
                        "word": ro_word,
                        "english": en_word,
                        "method": "spoter_wlasl100_npy",
                        "source": spoter_npy.name,
                    })
                    continue
            except Exception:
                pass

                                                                                   
        sign = translator.find_sign_by_english(en_word)
        if sign:
            try:
                pkl_path = Path(sign["pkl_file"])
                data = load_smplx_pkl_data(pkl_path)
                raw_poses = data.get("smplx")
                if raw_poses is not None:
                    poses = np.asarray(raw_poses, dtype=np.float32)
                    if poses.ndim == 2 and poses.shape[1] >= 156:
                        step = max(1, int(np.ceil(poses.shape[0] / max_frames_per_sign)))
                        sampled = poses[::step][:max_frames_per_sign]
                        uris = render_aitviewer_poses_via_worker(sampled)
                        for img_uri in uris:
                            frames.append({"word": ro_word, "image": img_uri})
                        signs.append({
                            "word": ro_word,
                            "english": sign.get("english", en_word),
                            "method": "smplx_pkl_aitviewer",
                            "source": pkl_path.name,
                        })
                        continue
            except Exception:
                pass

                                                                                               
        try:
            from PIL import Image, ImageDraw
            import io as _io
            W, H = 400, 300
            img = Image.new('RGB', (W, H), color=(18, 8, 35))
            draw = ImageDraw.Draw(img)
                                
            draw.text((W // 2, H // 2 - 20), ro_word, fill=(200, 170, 255), anchor='mm')
            draw.text((W // 2, H // 2 + 16), '(semn indisponibil)', fill=(100, 80, 140), anchor='mm')
            buf = _io.BytesIO()
            img.save(buf, format='JPEG', quality=75)
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            frames.append({"word": ro_word, "image": f"data:image/jpeg;base64,{img_b64}"})
            signs.append({"word": ro_word, "english": en_word, "method": "not_found", "source": ""})
        except Exception:
            pass

    if not frames:
        raise RuntimeError("No avatar frames found for this text.")

    return {
        "success": True,
        "text": text,
        "fps": 12,
        "frame_count": len(frames),
        "signs": signs,
        "frames": frames,
    }

_VIDEO_FRAME_CACHE: dict = {}                                    


def extract_video_frames(video_path: Path, max_frames: int = 30) -> list:
    """Extract up to max_frames evenly-spaced frames from an MP4 as base64 JPEGs."""
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // max_frames)
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0 and len(frames) < max_frames:
            ok, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            if ok:
                frames.append("data:image/jpeg;base64," + base64.b64encode(enc.tobytes()).decode("ascii"))
        idx += 1
    cap.release()
    return frames


def generate_avatar_video(text: str) -> Path:
    """Call the SMPL-X pipeline script to produce an MP4; transcode to H.264 if possible."""
    if not SCRIPT_AUDIO_TO_SIGN.exists():
        raise FileNotFoundError(f"Generator script not found: {SCRIPT_AUDIO_TO_SIGN}")

                                                     
    cache_key = hashlib.md5(text.strip().lower().encode()).hexdigest()
    cached = VIDEOS_DIR / f"cache_{cache_key}.mp4"
    if cached.exists() and cached.stat().st_size > 0:
        return cached

    output_path = VIDEOS_DIR / f"avatar_{uuid.uuid4()}.mp4"
    cmd = [
        sys.executable,
        str(SCRIPT_AUDIO_TO_SIGN),
        "--text",
        text,
        "--output",
        str(output_path),
        "--fps",
        "30",
        "--blend-seconds",
        "1.2",                                     
        "--hold-seconds",
        "1.5",                                                                
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PROJECT_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout or "Generator failed")

    if not output_path.exists() or output_path.stat().st_size == 0:
        details = (proc.stderr.strip() or proc.stdout.strip() or "No generator output").strip()
        raise RuntimeError(f"Generator did not produce a video file. Details: {details[-1200:]}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        tmp_out = output_path.with_suffix(".h264.mp4")
        cmd = [
            ffmpeg,
            "-y",
            "-i", str(output_path),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(tmp_out),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            os.replace(tmp_out, output_path)
            print("Transcoded SMPL-X video to H.264 for browser playback.")
        except subprocess.CalledProcessError:
            if tmp_out.exists():
                tmp_out.unlink(missing_ok=True)
                                

                   
    try:
        import shutil as _shutil
        _shutil.copy2(str(output_path), str(cached))
    except Exception:
        pass

    return output_path


@app.route('/api/sign-animation-frames', methods=['POST'])
def sign_animation_frames():
    """Render the clothed SMPL-X avatar for a sign word/phrase.

    Priority:
      1. SMPL-X PKL file → render_aitviewer_poses_via_worker (clothed 3-D avatar)
      2. Romanian LSR NPZ keypoints → render_smplx_from_mediapipe_batch (tries aitviewer first)
      3. Video pipeline fallback (generate_avatar_video)
    """
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    lookup = (data.get('lookup') or '').strip()
    lookup_label = (data.get('label') or text or lookup).strip()
    if not text and not lookup:
        return jsonify({'error': 'No text provided'}), 400

    render_text = lookup or text

                           
    if render_text in _VIDEO_FRAME_CACHE:
        cached_uris = _VIDEO_FRAME_CACHE[render_text]
        return jsonify({
            'success': True,
            'frames': [{'word': lookup_label, 'image': uri} for uri in cached_uris],
            'fps': 12,
            'frame_count': len(cached_uris),
            'signs': [{'word': lookup_label, 'english': lookup_label, 'method': 'cached', 'source': ''}],
            'text': text,
        })

    try:
                                                                                        
        if len(render_text.split()) > 1:
            return jsonify(build_smplx_avatar_frames(render_text))

        from integration.translator_enhanced import EnhancedTranslator
        translator = EnhancedTranslator()

        frame_uris: list = []
        method_used = ''

                                                                             
                                                                                
        ro_key = normalize_avatar_phrase(render_text)
        lookup_en = _RO_EN_OFFLINE.get(ro_key) or _RO_EN_OFFLINE.get(render_text.lower().strip()) or render_text

                                                                                              
        ro_hams = _lookup_ro_hamnosys(render_text.lower().strip())
        if ro_hams and ro_hams.get('pkl_file'):
            try:
                pkl_path = Path(ro_hams['pkl_file'])
                hams_data = load_smplx_pkl_data(pkl_path)
                raw_poses = hams_data.get('smplx')
                if raw_poses is None:
                    raw_poses = hams_data.get('unsmooth_smplx')
                if raw_poses is not None:
                    poses = np.asarray(raw_poses, dtype=np.float32)
                    if poses.ndim == 2 and poses.shape[1] >= 156:
                        MAX_FRAMES = 30
                        step = max(1, int(np.ceil(len(poses) / MAX_FRAMES)))
                        sampled = poses[::step][:MAX_FRAMES]
                        frame_uris = render_aitviewer_poses_via_worker(sampled)
                        method_used = 'ro_hamnosys_pkl_aitviewer'
            except Exception as _e:
                app.logger.warning(f"HamNoSys render failed for {render_text!r}: {_e}")
                frame_uris = []

                                                                                      
        if not frame_uris:
            ro_sign = _lookup_ro_video(render_text.lower().strip())
            if ro_sign and ro_sign.get('npz_file'):
                try:
                    joints, _ = load_ro_npz_data(ro_sign['npz_file'])
                    MAX_FRAMES = 25
                    step = max(1, int(np.ceil(joints.shape[0] / MAX_FRAMES)))
                    sampled = joints[::step][:MAX_FRAMES]
                    frame_uris = render_smplx_from_mediapipe_batch(sampled, ro_sign['npz_file'])
                    method_used = 'ro_lsr_video'
                except Exception:
                    frame_uris = []

                                                                
        if not frame_uris:
            sign = translator.find_sign_by_english(lookup_en)
            if sign and sign.get('pkl_file'):
                try:
                    pkl_path = Path(sign['pkl_file'])
                    pkl_data = load_smplx_pkl_data(pkl_path)
                    raw_poses = pkl_data.get('smplx')
                    if raw_poses is not None:
                        poses = np.asarray(raw_poses, dtype=np.float32)
                        if poses.ndim == 2 and poses.shape[1] >= 156:
                            MAX_FRAMES = 30
                            step = max(1, int(np.ceil(len(poses) / MAX_FRAMES)))
                            sampled = poses[::step][:MAX_FRAMES]
                            frame_uris = render_aitviewer_poses_via_worker(sampled)
                            method_used = 'smplx_pkl_aitviewer'
                except Exception:
                    frame_uris = []

                                                    
        if not frame_uris:
            fallback_sign = translator.find_sign(lookup_en)
            if fallback_sign and fallback_sign.get('pkl_file'):
                try:
                    pkl_path = Path(fallback_sign['pkl_file'])
                    pkl_data = load_smplx_pkl_data(pkl_path)
                    raw_poses = pkl_data.get('smplx')
                    if raw_poses is not None:
                        poses = np.asarray(raw_poses, dtype=np.float32)
                        if poses.ndim == 2 and poses.shape[1] >= 156:
                            MAX_FRAMES = 30
                            step = max(1, int(np.ceil(len(poses) / MAX_FRAMES)))
                            sampled = poses[::step][:MAX_FRAMES]
                            frame_uris = render_aitviewer_poses_via_worker(sampled)
                            method_used = 'smplx_pkl_fallback'
                except Exception:
                    frame_uris = []

                                                                           
        if not frame_uris:
            video_path = generate_avatar_video(render_text)
            frame_uris = extract_video_frames(video_path, max_frames=30)
            method_used = 'video_pipeline'

        if not frame_uris:
            return jsonify({'error': 'Nu am putut genera animație pentru acest semn.'}), 500

        _VIDEO_FRAME_CACHE[render_text] = frame_uris
        return jsonify({
            'success': True,
            'frames': [{'word': lookup_label, 'image': uri} for uri in frame_uris],
            'fps': 12,
            'frame_count': len(frame_uris),
            'signs': [{'word': lookup_label, 'english': lookup_label, 'method': method_used, 'source': ''}],
            'text': text,
        })
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/generate-3d-video', methods=['POST'])
def generate_3d_video():
    """Generate SMPL-X avatar video using integration/audio_to_sign_video.py."""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        video_path = generate_avatar_video(text)
        video_name = video_path.name
        video_url = f"http://localhost:5000/api/video/{video_name}"
        return jsonify({
            'success': True,
            'message': '3D avatar video generated',
            'video_url': video_url,
            'video_id': video_name,
            'text': text,
            'size_bytes': video_path.stat().st_size,
        })
    except Exception as exc:
        return jsonify({'error': f'3D generation failed: {exc}'}), 500


@app.route('/api/sign-animation', methods=['POST'])
def sign_animation():
    """Return compact live animation frames from SMPL-X PKL data (no MP4 rendering)."""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        return jsonify(build_live_sign_animation(text))
    except Exception as exc:
        return jsonify({'error': f'Live animation failed: {exc}'}), 500


@app.route('/api/sign-avatar-frames', methods=['POST'])
def sign_avatar_frames():
    """Return live JPEG frames rendered from the configured SMPL-X avatar mesh."""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        return jsonify(build_smplx_avatar_frames(text))
    except Exception as exc:
        return jsonify({'error': f'SMPL-X avatar rendering failed: {exc}'}), 500


@app.route('/api/sign-avatar-stream', methods=['GET'])
def sign_avatar_stream():
    """SSE endpoint for Text -> Sign.
    Default mode uses the configured SMPL-X/simplex avatar.
    Optional mode=clear renders direct dataset keypoints for debugging.
    Query param: ?text=<romanian text>&mode=clear|smplx
    Each event: data: {"word":"...","image":"data:image/jpeg;base64,...","done":false}
    Final event: data: {"done":true}
    """
    text = (request.args.get('text') or '').strip()
    mode = (request.args.get('mode') or 'smplx').strip().lower()
    lookup = (request.args.get('lookup') or '').strip()
    lookup_type = (request.args.get('lookup_type') or 'english').strip().lower()
    lookup_label = (request.args.get('label') or '').strip()
    if not text and not lookup:
        return jsonify({'error': 'No text provided'}), 400

    def generate():
        import json as _json
        try:
            from integration.translator_enhanced import EnhancedTranslator

            translator = EnhancedTranslator()

            if mode in {"clear", "keypoints", "dataset"}:
                                                                                           
                sign_units = iter_romanian_sign_units(translator, text)
                max_frames = 30
                for ro_word, ro_sign in sign_units:
                    if not ro_sign or not ro_sign.get("npz_file"):
                        payload = {"warning": f"No Romanian dataset sign for: {ro_word}", "done": False}
                        yield f"data: {_json.dumps(payload)}\n\n"
                        continue
                    try:
                        joints_all, _ = load_ro_npz_data(ro_sign["npz_file"])
                        step = max(1, int(np.ceil(joints_all.shape[0] / max_frames)))
                        sampled = joints_all[::step][:max_frames]
                        for frame_joints in sampled:
                            payload = {
                                "word": ro_word,
                                "image": render_dataset_keypoint_avatar_frame(frame_joints, ro_word),
                                "done": False,
                                "source": "ro_lsr_dataset_keypoints_debug",
                            }
                            yield f"data: {_json.dumps(payload)}\n\n"
                    except Exception as exc:
                        payload = {"warning": f"Romanian dataset debug render failed: {exc}", "done": False}
                        yield f"data: {_json.dumps(payload)}\n\n"
                yield f"data: {_json.dumps({'done': True})}\n\n"
                return

                                                           
                                                                 
                                                                         
                                                                            
            import torch as _torch
            words = re.findall(r"[\w]+", text.strip(), flags=re.UNICODE)
            max_frames = 18
            rendered_any = False

            _ensure_aitviewer_worker()
            rend = get_smplx_avatar_renderer()
            pkl_layer = rend["layer"]
            pkl_face  = rend["face"]
            pkl_hmask = rend.get("hand_mask")

            def _render_pkl_poses(poses_raw, label):
                """Render SMPL-X poses: aitviewer worker first, CPU mesh as fallback."""
                poses = np.asarray(poses_raw, dtype=np.float32)
                if poses.ndim != 2 or poses.shape[1] < 156:
                    return
                step    = max(1, int(np.ceil(poses.shape[0] / max_frames)))
                sampled = poses[::step][:max_frames]

                                                                               
                try:
                    uris = render_aitviewer_poses_via_worker(sampled, jpeg_quality=78)
                    for uri in uris:
                        yield f"data: {_json.dumps({'word': label, 'image': uri, 'done': False})}\n\n"
                    return
                except Exception:
                    pass                        

                                                                               
                with _torch.no_grad():
                    T     = len(sampled)
                    zeros = lambda n: _torch.zeros(T, n)
                    out   = pkl_layer(
                        global_orient=_torch.tensor(sampled[:, :3],      dtype=_torch.float32),
                        body_pose    =_torch.tensor(sampled[:, 3:66],    dtype=_torch.float32),
                        left_hand_pose =_torch.tensor(sampled[:, 66:111], dtype=_torch.float32),
                        right_hand_pose=_torch.tensor(sampled[:, 111:156],dtype=_torch.float32),
                        betas=_torch.tensor(
                            sampled[:, 159:169] if sampled.shape[1] >= 169
                            else np.zeros((T, 10), dtype=np.float32),
                            dtype=_torch.float32,
                        ),
                        jaw_pose=zeros(3), leye_pose=zeros(3),
                        reye_pose=zeros(3), expression=zeros(10),
                    )
                    verts_batch = out.vertices.cpu().numpy()
                for verts in verts_batch:
                    uri = render_smplx_mesh_frame(verts, pkl_face, hand_mask=pkl_hmask)
                    yield f"data: {_json.dumps({'word': label, 'image': uri, 'done': False})}\n\n"

            def _try_en_word(en_word, label):
                """Try WLASL then How2Sign for an English word. Yields SSE events."""
                                                                               
                en_sign = find_english_avatar_pkl(translator, en_word, min_fuzzy_score=0.72)
                if en_sign and en_sign.get("pkl_file"):
                    try:
                        data_pkl = load_smplx_pkl_data(Path(en_sign["pkl_file"]))
                        raw = data_pkl.get("smplx")
                        if raw is not None:
                            yield from _render_pkl_poses(raw, label)
                            return True
                    except Exception:
                        pass

                                                                                
                fb_sign = translator.find_sign(en_word)
                if fb_sign and fb_sign.get("pkl_file"):
                    try:
                        data_pkl = load_smplx_pkl_data(Path(fb_sign["pkl_file"]))
                        raw = data_pkl.get("smplx")
                        if raw is not None:
                            yield from _render_pkl_poses(raw, label)
                            return True
                    except Exception:
                        pass

                return False

            def _normalize_lookup_value(value):
                normalized = unicodedata.normalize("NFD", value.lower())
                normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
                normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
                return re.sub(r"\s+", " ", normalized).strip()

            def _try_exact_lookup(value, label):
                normalized_value = _normalize_lookup_value(value)
                if not normalized_value:
                    return []

                if lookup_type == "romanian":
                    exact_data = translator.romanian_dictionary.get(value) or translator.romanian_dictionary.get(normalized_value)
                    if exact_data and exact_data.get("pkl_file"):
                        try:
                            data_pkl = load_smplx_pkl_data(Path(exact_data["pkl_file"]))
                            raw = data_pkl.get("smplx")
                            if raw is not None:
                                return list(_render_pkl_poses(raw, label))
                        except Exception:
                            return []
                    return []

                return list(_try_en_word(normalized_value, label))

                                                                        
            if lookup:
                exact_events = _try_exact_lookup(lookup, lookup_label or lookup)
                if exact_events:
                    for event in exact_events:
                        rendered_any = True
                        yield event
                    yield f"data: {_json.dumps({'done': True})}\n\n"
                    return
                yield f"data: {_json.dumps({'error': 'Nu am gasit animatia pentru semnul selectat.', 'done': True})}\n\n"
                return

            i = 0
            while i < len(words):
                phrase_found = False

                for length in range(min(3, len(words) - i), 0, -1):
                    phrase = " ".join(words[i:i + length])
                    label = phrase

                    candidates = google_translate_candidates(phrase, source="ro", target="en")

                                                                                              
                    if not candidates:
                        offline = _RO_EN_OFFLINE.get(phrase.lower())
                        if offline:
                            candidates = [offline]
                        else:
                                                                                         
                            candidates = [phrase.lower()]

                    for translated in candidates:
                        events = list(_try_en_word(translated, label))
                        if events:
                            for event in events:
                                rendered_any = True
                                yield event
                            phrase_found = True
                            break
                    if phrase_found:
                        i += length
                        break

                if not phrase_found:
                    i += 1

            if not rendered_any:
                yield f"data: {_json.dumps({'error': 'Nu am gasit semne pentru acest text. Incearca alte cuvinte.', 'done': True})}\n\n"
                return

        except Exception as exc:
            yield f"data: {_json.dumps({'error': str(exc), 'done': True})}\n\n"
            return

        yield f"data: {_json.dumps({'done': True})}\n\n"

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == '__main__':
    print("=" * 60)
    print("SignTranslator API Server Started!")
    print("=" * 60)
    print("Mobile app can connect to: http://localhost:5000")
    print("Health check: http://localhost:5000/api/health")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
