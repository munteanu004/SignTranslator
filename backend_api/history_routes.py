import json
from flask import Blueprint, request, jsonify, g
from models import db, TranslationHistory
from auth import token_required

history_bp = Blueprint('history', __name__)


@history_bp.route('/api/history', methods=['GET'])
@token_required
def get_history():
    """Return user's translation history, newest first."""
    type_filter = request.args.get('type')
    query = TranslationHistory.query.filter_by(user_id=g.current_user.id)

    if type_filter:
        query = query.filter_by(type=type_filter)

    entries = query.order_by(TranslationHistory.created_at.desc()).limit(100).all()

    return jsonify({
        'history': [_entry_dict(e) for e in entries],
    })


@history_bp.route('/api/history', methods=['POST'])
@token_required
def create_history():
    """Save a new translation history entry."""
    data = request.get_json() or {}

    entry = TranslationHistory(
        user_id=g.current_user.id,
        type=data.get('type', 'sign-to-text'),
        input_text=data.get('input_text', ''),
        output_text=data.get('output_text', ''),
        words=json.dumps(data.get('words', []), ensure_ascii=False),
        confidence=data.get('confidence'),
    )
    db.session.add(entry)

              
    g.current_user.xp = (g.current_user.xp or 0) + 10
    db.session.commit()

    return jsonify({'entry': _entry_dict(entry)}), 201


@history_bp.route('/api/history/<int:entry_id>', methods=['DELETE'])
@token_required
def delete_history(entry_id):
    """Delete a specific history entry (owned by current user)."""
    entry = TranslationHistory.query.filter_by(
        id=entry_id, user_id=g.current_user.id
    ).first()

    if not entry:
        return jsonify({'error': 'Inregistrare negasita'}), 404

    db.session.delete(entry)
    db.session.commit()
    return jsonify({'success': True})


@history_bp.route('/api/history', methods=['DELETE'])
@token_required
def clear_history():
    """Delete all history for current user."""
    TranslationHistory.query.filter_by(user_id=g.current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True})


def _entry_dict(entry):
    words = []
    if entry.words:
        try:
            words = json.loads(entry.words)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        'id': entry.id,
        'type': entry.type,
        'input_text': entry.input_text,
        'output_text': entry.output_text,
        'words': words,
        'confidence': entry.confidence,
        'timestamp': entry.created_at.isoformat() if entry.created_at else None,
    }
