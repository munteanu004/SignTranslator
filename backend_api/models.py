from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(30), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    last_active_date = db.Column(db.Date, nullable=True)

    history = db.relationship('TranslationHistory', backref='user', lazy=True,
                              cascade='all, delete-orphan')
    settings = db.relationship('UserSettings', backref='user', uselist=False,
                               lazy=True, cascade='all, delete-orphan')
    achievements = db.relationship('UserAchievement', backref='user', lazy=True,
                                   cascade='all, delete-orphan')
    daily_claims = db.relationship('DailyClaim', backref='user', lazy=True,
                                   cascade='all, delete-orphan')
    challenge_progress = db.relationship('UserChallengeProgress', backref='user',
                                         lazy=True, cascade='all, delete-orphan')


class TranslationHistory(db.Model):
    __tablename__ = 'translation_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    input_text = db.Column(db.Text)
    output_text = db.Column(db.Text)
    words = db.Column(db.Text)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    language = db.Column(db.String(5), default='ro')
    avatar_speed = db.Column(db.String(10), default='normal')
    skill_level = db.Column(db.String(20), default='incepator')
    notifications = db.Column(db.Boolean, default=True)
    sounds = db.Column(db.Boolean, default=True)
    haptic = db.Column(db.Boolean, default=True)


                        

                                                                
LEVEL_XP = [0, 0, 100, 250, 500, 800, 1200, 1700, 2300, 3000, 4000,
            5200, 6600, 8200, 10000, 12500, 15500, 19000, 23000, 28000, 34000]

                                                                   
DAILY_REWARDS = [10, 15, 20, 30, 40, 50, 75]

                           
ACHIEVEMENTS_DEF = [
    {'key': 'first_translation', 'icon': '🏆', 'title': 'Prima traducere',
     'desc': 'Fa prima ta traducere', 'xp_reward': 20},
    {'key': 'translations_10', 'icon': '📝', 'title': '10 traduceri',
     'desc': 'Completeaza 10 traduceri', 'xp_reward': 50},
    {'key': 'translations_50', 'icon': '📚', 'title': '50 traduceri',
     'desc': 'Completeaza 50 traduceri', 'xp_reward': 100},
    {'key': 'translations_100', 'icon': '🎓', 'title': '100 traduceri',
     'desc': 'Completeaza 100 traduceri', 'xp_reward': 200},
    {'key': 'translations_500', 'icon': '💎', 'title': '500 traduceri',
     'desc': 'Completeaza 500 traduceri', 'xp_reward': 500},
    {'key': 'streak_3', 'icon': '🔥', 'title': 'Streak 3 zile',
     'desc': 'Foloseste aplicatia 3 zile consecutiv', 'xp_reward': 30},
    {'key': 'streak_7', 'icon': '🔥', 'title': 'Streak 7 zile',
     'desc': 'Foloseste aplicatia 7 zile consecutiv', 'xp_reward': 75},
    {'key': 'streak_14', 'icon': '🔥', 'title': 'Streak 14 zile',
     'desc': 'Foloseste aplicatia 14 zile consecutiv', 'xp_reward': 150},
    {'key': 'streak_30', 'icon': '💪', 'title': 'Streak 30 zile',
     'desc': 'Foloseste aplicatia 30 zile consecutiv', 'xp_reward': 300},
    {'key': 'level_5', 'icon': '⭐', 'title': 'Nivel 5',
     'desc': 'Ajunge la nivelul 5', 'xp_reward': 50},
    {'key': 'level_10', 'icon': '🌟', 'title': 'Nivel 10',
     'desc': 'Ajunge la nivelul 10', 'xp_reward': 150},
    {'key': 'daily_claims_7', 'icon': '📅', 'title': '7 recompense zilnice',
     'desc': 'Colecteaza 7 recompense zilnice', 'xp_reward': 50},
    {'key': 'camera_first', 'icon': '📷', 'title': 'Prima recunoastere',
     'desc': 'Recunoaste primul semn cu camera', 'xp_reward': 25},
    {'key': 'text_sign_first', 'icon': '✍️', 'title': 'Primul avatar',
     'desc': 'Genereaza primul video cu avatar', 'xp_reward': 25},
    {'key': 'challenge_complete_5', 'icon': '🎯', 'title': '5 provocari',
     'desc': 'Completeaza 5 provocari zilnice', 'xp_reward': 40},
    {'key': 'challenge_complete_20', 'icon': '🏅', 'title': '20 provocari',
     'desc': 'Completeaza 20 provocari zilnice', 'xp_reward': 100},
    {'key': 'xp_1000', 'icon': '💰', 'title': '1000 XP',
     'desc': 'Acumuleaza 1000 XP in total', 'xp_reward': 50},
    {'key': 'xp_5000', 'icon': '👑', 'title': '5000 XP',
     'desc': 'Acumuleaza 5000 XP in total', 'xp_reward': 200},
]

                                                                            
ACHIEVEMENTS_DEF_CLEAN = [
    {'key': 'first_translation', 'icon': '🏆', 'title': 'Prima traducere',
     'desc': 'Fa prima ta traducere', 'xp_reward': 20},
    {'key': 'translations_10', 'icon': '📝', 'title': '10 traduceri',
     'desc': 'Completeaza 10 traduceri', 'xp_reward': 50},
    {'key': 'translations_50', 'icon': '📚', 'title': '50 traduceri',
     'desc': 'Completeaza 50 traduceri', 'xp_reward': 100},
    {'key': 'translations_100', 'icon': '🎓', 'title': '100 traduceri',
     'desc': 'Completeaza 100 traduceri', 'xp_reward': 200},
    {'key': 'translations_500', 'icon': '💎', 'title': '500 traduceri',
     'desc': 'Completeaza 500 traduceri', 'xp_reward': 500},
    {'key': 'streak_3', 'icon': '🔥', 'title': 'Streak 3 zile',
     'desc': 'Foloseste aplicatia 3 zile consecutiv', 'xp_reward': 30},
    {'key': 'streak_7', 'icon': '🔥', 'title': 'Streak 7 zile',
     'desc': 'Foloseste aplicatia 7 zile consecutiv', 'xp_reward': 75},
    {'key': 'streak_14', 'icon': '🔥', 'title': 'Streak 14 zile',
     'desc': 'Foloseste aplicatia 14 zile consecutiv', 'xp_reward': 150},
    {'key': 'streak_30', 'icon': '💪', 'title': 'Streak 30 zile',
     'desc': 'Foloseste aplicatia 30 zile consecutiv', 'xp_reward': 300},
    {'key': 'level_5', 'icon': '⭐', 'title': 'Nivel 5',
     'desc': 'Ajunge la nivelul 5', 'xp_reward': 50},
    {'key': 'level_10', 'icon': '🌟', 'title': 'Nivel 10',
     'desc': 'Ajunge la nivelul 10', 'xp_reward': 150},
    {'key': 'daily_claims_7', 'icon': '📅', 'title': '7 recompense zilnice',
     'desc': 'Colecteaza 7 recompense zilnice', 'xp_reward': 50},
    {'key': 'camera_first', 'icon': '📷', 'title': 'Prima recunoastere',
     'desc': 'Recunoaste primul semn cu camera', 'xp_reward': 25},
    {'key': 'text_sign_first', 'icon': '✌️', 'title': 'Primul avatar',
     'desc': 'Genereaza primul video cu avatar', 'xp_reward': 25},
    {'key': 'challenge_complete_5', 'icon': '🎯', 'title': '5 provocari',
     'desc': 'Completeaza 5 provocari zilnice', 'xp_reward': 40},
    {'key': 'challenge_complete_20', 'icon': '🏅', 'title': '20 provocari',
     'desc': 'Completeaza 20 provocari zilnice', 'xp_reward': 100},
    {'key': 'xp_1000', 'icon': '💰', 'title': '1000 XP',
     'desc': 'Acumuleaza 1000 XP in total', 'xp_reward': 50},
    {'key': 'xp_5000', 'icon': '💠', 'title': '5000 XP',
     'desc': 'Acumuleaza 5000 XP in total', 'xp_reward': 200},
]

                      
CHALLENGE_POOL = [
    {'key': 'live_3', 'title': 'Traducere live x3', 'desc': 'Fa 3 traduceri cu camera',
     'target': 3, 'type': 'sign-to-text', 'xp_reward': 25},
    {'key': 'live_5', 'title': 'Traducere live x5', 'desc': 'Fa 5 traduceri cu camera',
     'target': 5, 'type': 'sign-to-text', 'xp_reward': 40},
    {'key': 'text_3', 'title': 'Text in semne x3', 'desc': 'Traduce 3 propozitii in semne',
     'target': 3, 'type': 'text-to-sign', 'xp_reward': 25},
    {'key': 'text_5', 'title': 'Text in semne x5', 'desc': 'Traduce 5 propozitii in semne',
     'target': 5, 'type': 'text-to-sign', 'xp_reward': 40},
    {'key': 'any_5', 'title': '5 traduceri azi', 'desc': 'Fa 5 traduceri de orice tip',
     'target': 5, 'type': 'any', 'xp_reward': 30},
    {'key': 'any_10', 'title': '10 traduceri azi', 'desc': 'Fa 10 traduceri de orice tip',
     'target': 10, 'type': 'any', 'xp_reward': 60},
    {'key': 'daily_login', 'title': 'Login zilnic', 'desc': 'Conecteaza-te la aplicatie',
     'target': 1, 'type': 'login', 'xp_reward': 10},
    {'key': 'claim_reward', 'title': 'Recompensa zilnica', 'desc': 'Colecteaza recompensa zilnica',
     'target': 1, 'type': 'claim', 'xp_reward': 15},
]


class DailyClaim(db.Model):
    """Tracks daily reward claims. One per user per day."""
    __tablename__ = 'daily_claims'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    claim_date = db.Column(db.Date, nullable=False)
    day_in_cycle = db.Column(db.Integer, nullable=False)                                      
    xp_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserAchievement(db.Model):
    """Tracks earned achievements."""
    __tablename__ = 'user_achievements'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_key = db.Column(db.String(50), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserChallengeProgress(db.Model):
    """Tracks daily challenge progress. Reset each day."""
    __tablename__ = 'user_challenge_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_date = db.Column(db.Date, nullable=False)
    challenge_key = db.Column(db.String(50), nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    xp_claimed = db.Column(db.Boolean, default=False)


                                                

class DailyReward(db.Model):
    __tablename__ = 'daily_rewards'
    id = db.Column(db.Integer, primary_key=True)
    day_index = db.Column(db.Integer, unique=True, nullable=False)          
    xp_reward = db.Column(db.Integer, nullable=False)


class Achievement(db.Model):
    __tablename__ = 'achievements'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    icon = db.Column(db.String(16), default='')
    title = db.Column(db.String(120), nullable=False)
    desc = db.Column(db.String(255), nullable=False)
    xp_reward = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)


class Challenge(db.Model):
    __tablename__ = 'challenges'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    desc = db.Column(db.String(255), nullable=False)
    target = db.Column(db.Integer, default=1)
    type = db.Column(db.String(30), default='any')                                                     
    xp_reward = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)


def seed_gamification_definitions():
    """Idempotently seed gamification definition tables from the in-code defaults."""
    if DailyReward.query.count() == 0:
        for i, xp in enumerate(DAILY_REWARDS):
            db.session.add(DailyReward(day_index=i, xp_reward=int(xp)))

    if Achievement.query.count() == 0:
        for a in ACHIEVEMENTS_DEF_CLEAN:
            db.session.add(Achievement(
                key=a['key'],
                icon=a.get('icon', ''),
                title=a.get('title', ''),
                desc=a.get('desc', ''),
                xp_reward=int(a.get('xp_reward', 0)),
                active=True,
            ))

    if Challenge.query.count() == 0:
        for c in CHALLENGE_POOL:
            db.session.add(Challenge(
                key=c['key'],
                title=c.get('title', ''),
                desc=c.get('desc', ''),
                target=int(c.get('target', 1)),
                type=c.get('type', 'any'),
                xp_reward=int(c.get('xp_reward', 0)),
                active=True,
            ))

    db.session.commit()


def xp_for_level(level):
    """Return total XP needed to reach a given level."""
    if level < len(LEVEL_XP):
        return LEVEL_XP[level]
                                             
    return int(level * level * 50)


def level_from_xp(xp):
    """Return the level for a given XP amount."""
    for lvl in range(len(LEVEL_XP) - 1, 0, -1):
        if xp >= LEVEL_XP[lvl]:
            return lvl
                                 
    lvl = len(LEVEL_XP) - 1
    while xp >= xp_for_level(lvl + 1):
        lvl += 1
    return max(1, lvl)
