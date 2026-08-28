"""
Gamification API routes:
  GET  /api/gamification/status          - full gamification state
  POST /api/gamification/claim           - claim daily reward
  POST /api/gamification/challenge-claim - claim XP for completed daily challenge
"""
import random
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify, g
from models import (
    db, User, DailyClaim, UserAchievement, UserChallengeProgress,
    DailyReward, Achievement, Challenge,
    TranslationHistory, DAILY_REWARDS, ACHIEVEMENTS_DEF_CLEAN, CHALLENGE_POOL,
    xp_for_level, level_from_xp,
)
from auth import token_required

gamification_bp = Blueprint('gamification', __name__)


def _daily_rewards_list():
    try:
        rows = DailyReward.query.order_by(DailyReward.day_index.asc()).all()
        if rows:
            return [int(r.xp_reward) for r in rows]
    except Exception:
        pass
    return DAILY_REWARDS


def _achievement_defs():
    try:
        rows = Achievement.query.filter_by(active=True).all()
        if rows:
            return [{
                'key': a.key,
                'icon': a.icon or '',
                'title': a.title,
                'desc': a.desc,
                'xp_reward': int(a.xp_reward or 0),
            } for a in rows]
    except Exception:
        pass
    return ACHIEVEMENTS_DEF_CLEAN


def _challenge_pool():
    try:
        rows = Challenge.query.filter_by(active=True).all()
        if rows:
            return [{
                'key': c.key,
                'title': c.title,
                'desc': c.desc,
                'target': int(c.target or 1),
                'type': c.type or 'any',
                'xp_reward': int(c.xp_reward or 0),
            } for c in rows]
    except Exception:
        pass
    return CHALLENGE_POOL


def _update_streak(user):
    """Update user streak based on last_active_date."""
    today = date.today()
    if user.last_active_date is None:
        user.streak = 1
    elif user.last_active_date == today:
        pass                        
    elif user.last_active_date == today - timedelta(days=1):
        user.streak += 1
    else:
        user.streak = 1                 
    user.last_active_date = today


def _add_xp(user, amount):
    """Add XP and update level. Returns list of newly unlocked achievements."""
    user.xp += amount
    new_level = level_from_xp(user.xp)
    user.level = new_level
    return _check_achievements(user)


def _check_achievements(user):
    """Check and award any new achievements. Returns list of newly earned ones."""
    earned_keys = {a.achievement_key for a in user.achievements}
    new_achievements = []
    ach_defs = _achievement_defs()

                        
    total_translations = TranslationHistory.query.filter_by(user_id=user.id).count()
    camera_count = TranslationHistory.query.filter_by(user_id=user.id, type='sign-to-text').count()
    text_count = TranslationHistory.query.filter_by(user_id=user.id, type='text-to-sign').count()
    total_claims = DailyClaim.query.filter_by(user_id=user.id).count()
    total_challenges = UserChallengeProgress.query.filter_by(
        user_id=user.id, completed=True).count()

    checks = {
        'first_translation': total_translations >= 1,
        'translations_10': total_translations >= 10,
        'translations_50': total_translations >= 50,
        'translations_100': total_translations >= 100,
        'translations_500': total_translations >= 500,
        'streak_3': user.streak >= 3,
        'streak_7': user.streak >= 7,
        'streak_14': user.streak >= 14,
        'streak_30': user.streak >= 30,
        'level_5': user.level >= 5,
        'level_10': user.level >= 10,
        'daily_claims_7': total_claims >= 7,
        'camera_first': camera_count >= 1,
        'text_sign_first': text_count >= 1,
        'challenge_complete_5': total_challenges >= 5,
        'challenge_complete_20': total_challenges >= 20,
        'xp_1000': user.xp >= 1000,
        'xp_5000': user.xp >= 5000,
    }

    for key, condition in checks.items():
        if condition and key not in earned_keys:
                               
            ach = UserAchievement(user_id=user.id, achievement_key=key)
            db.session.add(ach)
            earned_keys.add(key)

                            
            ach_def = next((a for a in ach_defs if a['key'] == key), None)
            if ach_def:
                user.xp += ach_def['xp_reward']
                user.level = level_from_xp(user.xp)
                new_achievements.append({
                    'key': key,
                    'title': ach_def['title'],
                    'icon': ach_def['icon'],
                    'xp_reward': ach_def['xp_reward'],
                })

    return new_achievements


def _get_daily_challenges(user_id, today):
    """Get or create today's 3 daily challenges for a user."""
    existing = UserChallengeProgress.query.filter_by(
        user_id=user_id, challenge_date=today).all()

    if existing:
        return existing

    pool = _challenge_pool()
    if not pool:
        return []

    yesterday = today - timedelta(days=1)
    yesterday_progress = UserChallengeProgress.query.filter_by(
        user_id=user_id, challenge_date=yesterday).all()
    yesterday_keys = {row.challenge_key for row in yesterday_progress}

                                                                              
    preferred = [c for c in pool if c['key'] not in yesterday_keys]
    selected = []
    if preferred:
        selected.extend(random.sample(preferred, min(3, len(preferred))))

    if len(selected) < 3:
        selected_keys = {c['key'] for c in selected}
        fallback = [c for c in pool if c['key'] not in selected_keys]
        if fallback:
            selected.extend(random.sample(fallback, min(3 - len(selected), len(fallback))))

    for ch in selected:
        prog = UserChallengeProgress(
            user_id=user_id,
            challenge_date=today,
            challenge_key=ch['key'],
            progress=0,
            completed=False,
            xp_claimed=False,
        )
        db.session.add(prog)

    db.session.commit()
    return UserChallengeProgress.query.filter_by(
        user_id=user_id, challenge_date=today).all()


def _challenge_to_dict(prog):
    ch_def = next((c for c in _challenge_pool() if c['key'] == prog.challenge_key), None)
    if not ch_def:
        return None
    return {
        'key': prog.challenge_key,
        'title': ch_def['title'],
        'desc': ch_def['desc'],
        'target': ch_def['target'],
        'progress': prog.progress,
        'completed': prog.completed,
        'xp_claimed': prog.xp_claimed,
        'xp_reward': ch_def['xp_reward'],
    }


@gamification_bp.route('/api/gamification/status', methods=['GET'])
@token_required
def get_status():
    user = g.current_user
    today = date.today()
    daily_rewards = _daily_rewards_list()
    ach_defs = _achievement_defs()

                                
    _update_streak(user)

                                   
    _auto_progress_challenges(user, today, 'login', 1)

    db.session.commit()

                      
    today_claim = DailyClaim.query.filter_by(user_id=user.id, claim_date=today).first()
    total_claims = DailyClaim.query.filter_by(user_id=user.id).count()

                                             
    if today_claim:
        claim_day = today_claim.day_in_cycle
        can_claim = False
        next_reward_xp = daily_rewards[(claim_day + 1) % max(len(daily_rewards), 1)]
    else:
                         
        last_claim = DailyClaim.query.filter_by(user_id=user.id)\
            .order_by(DailyClaim.claim_date.desc()).first()
        if last_claim and last_claim.claim_date == today - timedelta(days=1):
            claim_day = (last_claim.day_in_cycle + 1) % max(len(daily_rewards), 1)
        else:
            claim_day = 0               
        can_claim = True
        next_reward_xp = daily_rewards[claim_day]

                
    challenges = _get_daily_challenges(user.id, today)
    challenges_data = [_challenge_to_dict(c) for c in challenges if _challenge_to_dict(c)]

                  
    earned_keys = {a.achievement_key for a in user.achievements}
    achievements_data = []
    for a_def in ach_defs:
        achievements_data.append({
            'key': a_def['key'],
            'icon': a_def['icon'],
            'title': a_def['title'],
            'desc': a_def['desc'],
            'xp_reward': a_def['xp_reward'],
            'earned': a_def['key'] in earned_keys,
        })

                                   
    current_level_xp = xp_for_level(user.level)
    next_level_xp = xp_for_level(user.level + 1)

    return jsonify({
        'xp': user.xp,
        'level': user.level,
        'streak': user.streak,
        'current_level_xp': current_level_xp,
        'next_level_xp': next_level_xp,
        'daily_claim': {
            'can_claim': can_claim,
            'claim_day': claim_day,
            'next_reward_xp': next_reward_xp,
            'total_claims': total_claims,
            'rewards_calendar': daily_rewards,
        },
        'challenges': challenges_data,
        'achievements': achievements_data,
    })


@gamification_bp.route('/api/gamification/challenges', methods=['GET'])
@token_required
def get_challenges():
    user = g.current_user
    today = date.today()

    _update_streak(user)
    _auto_progress_challenges(user, today, 'login', 1)
    db.session.commit()

    challenges = _get_daily_challenges(user.id, today)
    challenges_data = [_challenge_to_dict(c) for c in challenges if _challenge_to_dict(c)]
    return jsonify({'challenges': challenges_data})


@gamification_bp.route('/api/gamification/achievements', methods=['GET'])
@token_required
def get_achievements():
    user = g.current_user
    today = date.today()

    _update_streak(user)
    _auto_progress_challenges(user, today, 'login', 1)
    db.session.commit()

    earned_keys = {a.achievement_key for a in user.achievements}
    achievements_data = []
    for a_def in _achievement_defs():
        achievements_data.append({
            'key': a_def['key'],
            'icon': a_def['icon'],
            'title': a_def['title'],
            'desc': a_def['desc'],
            'xp_reward': a_def['xp_reward'],
            'earned': a_def['key'] in earned_keys,
        })
    return jsonify({'achievements': achievements_data})


@gamification_bp.route('/api/gamification/claim', methods=['POST'])
@token_required
def claim_daily():
    user = g.current_user
    today = date.today()
    daily_rewards = _daily_rewards_list()

                                    
    existing = DailyClaim.query.filter_by(user_id=user.id, claim_date=today).first()
    if existing:
        return jsonify({'error': 'Recompensa de azi a fost deja colectata'}), 400

                            
    last_claim = DailyClaim.query.filter_by(user_id=user.id)\
        .order_by(DailyClaim.claim_date.desc()).first()
    if last_claim and last_claim.claim_date == today - timedelta(days=1):
        day_in_cycle = (last_claim.day_in_cycle + 1) % max(len(daily_rewards), 1)
    else:
        day_in_cycle = 0

    xp_earned = daily_rewards[day_in_cycle]

    claim = DailyClaim(
        user_id=user.id,
        claim_date=today,
        day_in_cycle=day_in_cycle,
        xp_earned=xp_earned,
    )
    db.session.add(claim)

                   
    _update_streak(user)

            
    new_achievements = _add_xp(user, xp_earned)

                                   
    _auto_progress_challenges(user, today, 'claim', 1)

    db.session.commit()

    return jsonify({
        'success': True,
        'xp_earned': xp_earned,
        'day_in_cycle': day_in_cycle,
        'total_xp': user.xp,
        'level': user.level,
        'streak': user.streak,
        'new_achievements': new_achievements,
    })


def _auto_progress_challenges(user, today, challenge_type, increment):
    """Auto-progress challenges of a given type."""
                                                                     
    _get_daily_challenges(user.id, today)

    challenges = UserChallengeProgress.query.filter_by(
        user_id=user.id, challenge_date=today).all()
    pool = _challenge_pool()
    ch_map = {c['key']: c for c in pool}

    translation_types = {'sign-to-text', 'text-to-sign'}
    is_translation_event = challenge_type in translation_types

    for prog in challenges:
        ch_def = ch_map.get(prog.challenge_key)
        if not ch_def:
            continue
        if ch_def['type'] == challenge_type:
            pass
        elif ch_def['type'] == 'any' and is_translation_event:
            pass
        else:
            continue
        if prog.completed:
            continue

        prog.progress = min(prog.progress + increment, ch_def['target'])
        if prog.progress >= ch_def['target']:
            prog.completed = True


@gamification_bp.route('/api/gamification/challenge-claim', methods=['POST'])
@token_required
def claim_challenge():
    """Claim XP for a completed daily challenge."""
    user = g.current_user
    today = date.today()
    data = request.get_json() or {}
    challenge_key = (data.get('key') or '').strip()

    if not challenge_key:
        return jsonify({'error': 'Cheia challenge-ului lipseste'}), 400

    _update_streak(user)
    _auto_progress_challenges(user, today, 'login', 1)

    progress = UserChallengeProgress.query.filter_by(
        user_id=user.id,
        challenge_date=today,
        challenge_key=challenge_key,
    ).first()

    if not progress:
        return jsonify({'error': 'Challenge-ul nu exista pentru azi'}), 404
    if not progress.completed:
        return jsonify({'error': 'Challenge-ul nu este inca finalizat'}), 400
    if progress.xp_claimed:
        return jsonify({'error': 'XP-ul pentru acest challenge a fost deja colectat'}), 400

    ch_def = next((c for c in _challenge_pool() if c['key'] == challenge_key), None)
    if not ch_def:
        return jsonify({'error': 'Definitia challenge-ului nu a fost gasita'}), 404

    progress.xp_claimed = True
    new_achievements = _add_xp(user, ch_def['xp_reward'])
    db.session.commit()

    return jsonify({
        'success': True,
        'key': challenge_key,
        'xp_earned': ch_def['xp_reward'],
        'total_xp': user.xp,
        'level': user.level,
        'streak': user.streak,
        'new_achievements': new_achievements,
    })


@gamification_bp.route('/api/gamification/progress', methods=['POST'])
@token_required
def report_progress():
    """Called after a translation to update challenge progress and earn XP."""
    user = g.current_user
    today = date.today()
    data = request.get_json() or {}
    action_type = data.get('type', 'any')                                         

    _update_streak(user)

                             
    base_xp = 15 if action_type == 'sign-to-text' else 10
                  
    streak_bonus = min(user.streak * 2, 20)
    total_xp = base_xp + streak_bonus

    new_achievements = _add_xp(user, total_xp)

                         
    _auto_progress_challenges(user, today, action_type, 1)

    db.session.commit()

    return jsonify({
        'success': True,
        'xp_earned': total_xp,
        'base_xp': base_xp,
        'streak_bonus': streak_bonus,
        'total_xp': user.xp,
        'level': user.level,
        'streak': user.streak,
        'new_achievements': new_achievements,
    })

