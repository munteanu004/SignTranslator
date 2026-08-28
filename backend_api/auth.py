import io
import json
import urllib.request
import urllib.error
import jwt
import datetime
import base64
import uuid
from functools import wraps
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from models import db, User, UserSettings

auth_bp = Blueprint('auth', __name__)


def token_required(f):
    """Decorator: reads JWT from Authorization header, sets g.current_user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({'error': 'Token lipseste'}), 401

        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET'],
                                 algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if not user:
                return jsonify({'error': 'Utilizator inexistent'}), 401
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirat'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token invalid'}), 401

        return f(*args, **kwargs)
    return decorated


def _create_token(user):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'name': user.name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')


def _user_dict(user):
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'phone': user.phone or '',
        'avatar_url': user.avatar_url or '',
        'xp': user.xp,
        'streak': user.streak,
        'level': user.level,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


@auth_bp.route('/api/auth/google', methods=['POST'])
def google_login():
    data = request.get_json() or {}
    credential = (data.get('credential') or '').strip()
    if not credential:
        return jsonify({'error': 'Token Google lipseste'}), 400

    try:
        url = f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            info = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return jsonify({'error': 'Token Google invalid'}), 401
    except Exception:
        return jsonify({'error': 'Eroare la verificarea tokenului Google'}), 401

    if info.get('error'):
        return jsonify({'error': 'Token Google invalid'}), 401

    email = (info.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Email Google lipsa'}), 400

    name = info.get('name') or email.split('@')[0]
    picture = info.get('picture') or ''

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(uuid.uuid4().hex),
            avatar_url=picture or None,
        )
        db.session.add(user)
        db.session.flush()
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

    token = _create_token(user)
    return jsonify({'token': token, 'user': _user_dict(user)})


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or len(password) < 4:
        return jsonify({'error': 'Completeaza toate campurile (parola min 4 caractere)'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email deja inregistrat'}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.flush()               

                             
    settings = UserSettings(user_id=user.id)
    db.session.add(settings)
    db.session.commit()

    token = _create_token(user)
    return jsonify({'token': token, 'user': _user_dict(user)}), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Email sau parola gresita'}), 401

    token = _create_token(user)
    return jsonify({'token': token, 'user': _user_dict(user)})


@auth_bp.route('/api/auth/me', methods=['GET'])
@token_required
def get_me():
    return jsonify({'user': _user_dict(g.current_user)})


@auth_bp.route('/api/auth/profile', methods=['OPTIONS'])
def update_profile_options():
                                                        
                                                                            
    return ('', 204)


@auth_bp.route('/api/auth/profile', methods=['PUT'])
@token_required
def update_profile():
    data = request.get_json() or {}
    user = g.current_user

    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    skill_level = (data.get('skill_level') or '').strip()
    new_password = data.get('new_password') or ''
    current_password = data.get('current_password') or ''

    if name:
        user.name = name

    if email and email != user.email:
        if User.query.filter(User.email == email, User.id != user.id).first():
            return jsonify({'error': 'Email deja folosit de alt cont'}), 409
        user.email = email

    if phone is not None:
        user.phone = phone or None

    if skill_level in ('incepator', 'intermediar', 'avansat'):
        settings = user.settings
        if settings:
            settings.skill_level = skill_level

    if new_password:
        if len(new_password) < 4:
            return jsonify({'error': 'Parola noua trebuie sa aiba minim 4 caractere'}), 400
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({'error': 'Parola curenta este incorecta'}), 400
        user.password_hash = generate_password_hash(new_password)

    db.session.commit()
    return jsonify({'user': _user_dict(user)})


@auth_bp.route('/api/auth/avatar', methods=['POST'])
@token_required
def upload_avatar():
    data = request.get_json() or {}
    data_url = data.get('data_url') or ''

    if not data_url.startswith('data:image/'):
        return jsonify({'error': 'Format imagine invalid'}), 400

    try:
        header, encoded = data_url.split(',', 1)
        raw_bytes = base64.b64decode(encoded)
    except Exception:
        return jsonify({'error': 'Format imagine invalid'}), 400

    try:
        img = Image.open(io.BytesIO(raw_bytes))

        if img.mode != 'RGB':
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background

        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

        img = img.resize((400, 400), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95, optimize=True)
        img_bytes = buf.getvalue()
        ext = 'jpg'
    except Exception:
                                                     
        ext = 'jpg' if 'jpeg' in header.lower() else 'png'
        img_bytes = raw_bytes

    avatars_dir = Path(current_app.root_path) / 'static' / 'avatars'
    avatars_dir.mkdir(parents=True, exist_ok=True)

                                         
    user = g.current_user
    if user.avatar_url:
        old_name = user.avatar_url.split('/')[-1]
        old_path = avatars_dir / old_name
        if old_path.exists():
            old_path.unlink()

    filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    (avatars_dir / filename).write_bytes(img_bytes)

    user.avatar_url = f"/api/auth/avatar/{filename}"
    db.session.commit()

    return jsonify({'avatar_url': user.avatar_url})


@auth_bp.route('/api/auth/avatar/<filename>', methods=['GET'])
def serve_avatar(filename):
    avatars_dir = Path(current_app.root_path) / 'static' / 'avatars'
    response = send_from_directory(str(avatars_dir), filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response
