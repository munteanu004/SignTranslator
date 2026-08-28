from flask import Blueprint, request, jsonify, g
from models import db, UserSettings
from auth import token_required

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings', methods=['GET'])
@token_required
def get_settings():
    settings = UserSettings.query.filter_by(user_id=g.current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=g.current_user.id)
        db.session.add(settings)
        db.session.commit()

    return jsonify({'settings': _settings_dict(settings)})


@settings_bp.route('/api/settings', methods=['PUT'])
@token_required
def update_settings():
    data = request.get_json() or {}
    settings = UserSettings.query.filter_by(user_id=g.current_user.id).first()

    if not settings:
        settings = UserSettings(user_id=g.current_user.id)
        db.session.add(settings)

    allowed = ['language', 'avatar_speed', 'notifications', 'sounds', 'haptic']
    for key in allowed:
        if key in data:
            setattr(settings, key, data[key])

    db.session.commit()
    return jsonify({'settings': _settings_dict(settings)})


def _settings_dict(s):
    return {
        'language': s.language,
        'avatar_speed': s.avatar_speed,
        'notifications': s.notifications,
        'sounds': s.sounds,
        'haptic': s.haptic,
    }
