"""
Geometry-based sign recognizer — no ML model required.

Uses MediaPipe Holistic keypoints (T, 75, 3):
  indices  0-32: body pose
  indices 33-53: left hand  (21 pts)
  indices 54-74: right hand (21 pts)

Recognized signs (Romanian / English):
  salut         / hello       — all 5 fingers extended
  copil         / child       — 4 fingers (index–pinky), thumb tucked
  da            / yes         — thumbs up
  nu            / no          — thumbs down
  iubire        / love        — ILY (index + pinky up)
  pace          / peace       — V sign (index + middle up)
  eu            / me          — pointing (index only, no thumb), wrist at mid/low height
  atentie       / attention   — pointing (index only, no thumb), wrist raised high
  a bea         / drink       — Y shape (thumb + pinky extended)
  a minca       / eat         — all fingertips bunched together (flat-O)
  ok            / ok          — OK circle (thumb tip near index tip)
  putere        / power       — fist (no fingers extended)
  mă numesc Maria / my name is Maria — mijlociu + degetul mic (celelalte îndoite)
"""
import numpy as np
from typing import Optional, Tuple, Dict

                                                                             
_W = 0                                         
_TH_CMC, _TH_MCP, _TH_IP, _TH_TIP = 1, 2, 3, 4
_IX_MCP, _IX_PIP, _IX_DIP, _IX_TIP = 5, 6, 7, 8
_MD_MCP, _MD_PIP, _MD_DIP, _MD_TIP = 9, 10, 11, 12
_RG_MCP, _RG_PIP, _RG_DIP, _RG_TIP = 13, 14, 15, 16
_PK_MCP, _PK_PIP, _PK_DIP, _PK_TIP = 17, 18, 19, 20

_TIPS = [_IX_TIP, _MD_TIP, _RG_TIP, _PK_TIP]
_MCPS = [_IX_MCP, _MD_MCP, _RG_MCP, _PK_MCP]
_ALL_TIPS = [_TH_TIP, _IX_TIP, _MD_TIP, _RG_TIP, _PK_TIP]


def _palm_size(hand: np.ndarray) -> float:
    return float(np.linalg.norm(hand[_MD_MCP] - hand[_W])) + 1e-7


def _is_valid(pt: np.ndarray) -> bool:
    """A landmark is valid only if it's not at the origin (0,0)."""
    return float(pt[0]) != 0.0 or float(pt[1]) != 0.0


def _finger_extended(hand: np.ndarray, finger: int) -> bool:
    """
    Returns True if the given finger is extended.
    finger: 0=thumb, 1=index, 2=middle, 3=ring, 4=pinky
    Uses tip-to-wrist / MCP-to-wrist distance ratio (rotation-invariant).
    Returns False if critical landmarks are missing (at origin).
    """
    if finger == 0:
        if not (_is_valid(hand[_TH_TIP]) and _is_valid(hand[_TH_CMC])):
            return False
        tip_d = np.linalg.norm(hand[_TH_TIP] - hand[_W])
        cmc_d = np.linalg.norm(hand[_TH_CMC] - hand[_W])
        if cmc_d < 1e-5:
            return False
        return tip_d > cmc_d * 1.6
    fi = finger - 1
    if not (_is_valid(hand[_TIPS[fi]]) and _is_valid(hand[_MCPS[fi]])):
        return False
    tip_d = np.linalg.norm(hand[_TIPS[fi]] - hand[_W])
    mcp_d = np.linalg.norm(hand[_MCPS[fi]] - hand[_W])
    if mcp_d < 1e-5:
        return False
    return tip_d > mcp_d * 1.35


def _thumb_direction(hand: np.ndarray) -> str:
    """Returns 'up', 'down', or 'side' based on thumb tip vs wrist y-position."""
    ps = _palm_size(hand)
    dy = float(hand[_TH_TIP][1]) - float(hand[_W][1])
    if dy < -ps * 0.5:
        return 'up'
    if dy > ps * 0.5:
        return 'down'
    return 'side'


def _tips_spread(hand: np.ndarray) -> float:
    """Mean distance of each fingertip from the centroid of all 5 fingertips.
    Small value = tips bunched together (flat-O / eating gesture)."""
    tips = np.array([hand[i] for i in _ALL_TIPS])
    if not all(_is_valid(hand[i]) for i in _ALL_TIPS):
        return float('inf')
    centroid = tips.mean(axis=0)
    return float(np.mean(np.linalg.norm(tips - centroid, axis=1)))


def _classify_hand(hand: np.ndarray, nose_y: float = 0.0) -> Optional[Tuple[str, str, float]]:
    """
    Classify a single hand (21, 2 or 21, 3 — only x,y used).
    nose_y: normalized Y of nose landmark (0 = not available).
    Returns (sign_ro, sign_en, confidence) or None.
    """
    hand = hand[:, :2].copy()

                                             
    if np.count_nonzero(hand) < 10:
        return None
    ps = _palm_size(hand)
    if ps < 1e-4:
        return None

    th = _finger_extended(hand, 0)
    ix = _finger_extended(hand, 1)
    md = _finger_extended(hand, 2)
    rg = _finger_extended(hand, 3)
    pk = _finger_extended(hand, 4)

                                                                               
    if th and ix and md and rg and pk:
        wrist_y = float(hand[_W][1])
                                                                   
                                                           
                                                          
        if nose_y > 0:
            if wrist_y > nose_y + 0.10:                                    
                return ('multumesc', 'thank you', 0.89)
        else:
            if wrist_y > 0.60:                                                      
                return ('multumesc', 'thank you', 0.87)
        return ('salut', 'hello', 0.92)

                                                                             
    if ix and md and rg and pk and not th:
        return ('copil', 'child', 0.87)

                                                                             
    if ix and pk and not md and not rg:
        return ('te iubesc', 'I love you', 0.92)

                                                                             
    if ix and md and not rg and not pk:
        return ('pace', 'peace', 0.90)

                                                                              
    if th and ix and not md and not rg and not pk:
        return ('telefon', 'phone', 0.87)

    wrist_y = float(hand[_W][1])

                                                                             
    if th and pk and not ix and not md and not rg:
        return ('a bea', 'drink', 0.87)


                                                                              
    if ix and not th and not md and not rg and not pk:
        if wrist_y > 0.45:
            return ('eu', 'me', 0.83)
        return ('atentie', 'attention', 0.85)

                                                                              
    if md and pk and not th and not ix and not rg:
        return ('mă numesc Maria', 'my name is Maria', 0.88)

                                                                             
    if not ix and not md and not rg and not pk:
                        
        direction = _thumb_direction(hand)
        if direction == 'up':
            return ('da', 'yes', 0.88)
        if direction == 'down':
            return ('nu', 'no', 0.88)
        return ('putere', 'power', 0.78)

                                                                             
                                                                         
    if _is_valid(hand[_TH_TIP]) and _is_valid(hand[_IX_TIP]):
        d_ti = np.linalg.norm(hand[_TH_TIP] - hand[_IX_TIP])
        if d_ti / ps < 0.50 and not md and not rg and not pk:
            return ('mic', 'small', 0.86)

                                                                              
    if _is_valid(hand[_TH_TIP]) and _is_valid(hand[_IX_TIP]):
        d_ti = np.linalg.norm(hand[_TH_TIP] - hand[_IX_TIP])
        if d_ti / ps < 0.40 and md and rg:
            return ('ok', 'ok', 0.85)

    return None


def _check_a_minca_lsr(frame: np.ndarray) -> bool:
    """
    Detecteaza gestul LSR 'a minca': ambele maini ridicate la nivelul gurii.
    Conditii stricte ca sa nu se confunde cu multumesc (o singura mana la fata).
    """
    nose = frame[0, :2]
    ls   = frame[11, :2]              
    rs   = frame[12, :2]              
    lw   = frame[15, :2]                      
    rw   = frame[16, :2]                       

                                    
    if float(nose[0]) == 0 and float(nose[1]) == 0:
        return False

    lw_valid = float(lw[0]) != 0 or float(lw[1]) != 0
    rw_valid = float(rw[0]) != 0 or float(rw[1]) != 0
    if not (lw_valid and rw_valid):
        return False

                                                                   
                                                                          
                                                                
    left_hand  = frame[33:54, :2]
    right_hand = frame[54:75, :2]
    if np.count_nonzero(left_hand) < 8 or np.count_nonzero(right_hand) < 8:
        return False

    nose_y      = float(nose[1])
    shoulder_w  = float(np.linalg.norm(rs - ls)) + 1e-6

                                                                             
                                                                        
                                                          
    lw_dy = float(lw[1]) - nose_y
    rw_dy = float(rw[1]) - nose_y
    lw_near = -0.03 <= lw_dy <= 0.22
    rw_near = -0.03 <= rw_dy <= 0.22
    if not (lw_near and rw_near):
        return False

                                                                               
    wrist_dist = float(np.linalg.norm(lw - rw)) / shoulder_w
    if wrist_dist > 1.1:
        return False

                                                
    face_x   = float(nose[0])
    lw_x_ok  = abs(float(lw[0]) - face_x) < 0.35
    rw_x_ok  = abs(float(rw[0]) - face_x) < 0.35
    return lw_x_ok and rw_x_ok


def _check_te_iubesc_lsr(frame: np.ndarray) -> bool:
    """
    Detecteaza gestul LSR 'te iubesc': ambele maini incrucisate pe piept.
    Foloseste landmark-urile de pose pentru pozitia incheieturilor.
    Pose: 11=umar stang, 12=umar drept, 15=incheietura stanga, 16=incheietura dreapta
    """
    ls  = frame[11, :2]               
    rs  = frame[12, :2]               
    lw  = frame[15, :2]                       
    rw  = frame[16, :2]                        

                                       
    if not all(float(p[0]) != 0 or float(p[1]) != 0 for p in [ls, rs, lw, rw]):
        return False

    shoulder_w = float(np.linalg.norm(rs - ls))
    if shoulder_w < 1e-4:
        return False

    chest_center = (ls + rs) / 2.0
    chest_y      = float(chest_center[1])

                                                            
                                               
    lw_y_rel = (float(lw[1]) - chest_y) / shoulder_w
    rw_y_rel = (float(rw[1]) - chest_y) / shoulder_w
    if not (0.0 <= lw_y_rel <= 1.2 and 0.0 <= rw_y_rel <= 1.2):
        return False

                                                         
    lw_x_dist = abs(float(lw[0]) - float(chest_center[0])) / shoulder_w
    rw_x_dist = abs(float(rw[0]) - float(chest_center[0])) / shoulder_w
    if lw_x_dist > 0.7 or rw_x_dist > 0.7:
        return False

                                                                              
    wrist_dist = float(np.linalg.norm(lw - rw)) / shoulder_w
    return wrist_dist < 0.6


def _check_familie_frame(frame: np.ndarray) -> bool:
    """Verifica daca frame-ul are ambele maini deschise la nivelul pieptului."""
    if np.count_nonzero(frame[33:54, :2]) < 8 or np.count_nonzero(frame[54:75, :2]) < 8:
        return False
    nose_y = float(frame[0, 1])
    lw_y   = float(frame[15, 1])
    rw_y   = float(frame[16, 1])
    if lw_y <= 0 or rw_y <= 0:
        return False
    if nose_y > 0:
        return (0.15 <= lw_y - nose_y <= 0.65) and (0.15 <= rw_y - nose_y <= 0.65)
    return (0.40 <= lw_y <= 0.82) and (0.40 <= rw_y <= 0.82)


def _wrists_motion_score(window: np.ndarray):
    """
    Returneaza amplitudinea miscarii (range) pentru incheieturile pose[15] si pose[16].
    Valori mici = maini statice; valori mari = maini in miscare.
    """
    lw = window[:, 15, :2].astype(float)
    rw = window[:, 16, :2].astype(float)
    lv = np.any(lw != 0, axis=1)
    rv = np.any(rw != 0, axis=1)
    if lv.sum() < 3 or rv.sum() < 3:
        return 0.0, 0.0
    lm = float(np.linalg.norm(lw[lv].max(0) - lw[lv].min(0)))
    rm = float(np.linalg.norm(rw[rv].max(0) - rw[rv].min(0)))
    return lm, rm


def recognize_from_keypoints(kp_array: np.ndarray) -> Optional[Dict]:
    """
    kp_array: (T, 75, 3) MediaPipe Holistic keypoints, float32.
    Uses the last 12 frames for temporal voting.
    Returns a result dict or None if no sign is confidently recognized.
    """
    if kp_array.ndim != 3 or kp_array.shape[1] != 75:
        return None

    T = len(kp_array)
    window = kp_array[max(0, T - 12):]

    votes: Dict[str, list] = {}

    for frame in window:
        right  = frame[54:75]
        left   = frame[33:54]
        nose_y = float(frame[0, 1]) if (float(frame[0, 0]) != 0 or float(frame[0, 1]) != 0) else 0.0

                                                                               
        if _check_a_minca_lsr(frame):
            result = ('a minca', 'eat', 0.91)
        elif _check_te_iubesc_lsr(frame):
            result = ('te iubesc', 'I love you', 0.93)
        else:
            result = _classify_hand(right, nose_y) or _classify_hand(left, nose_y)
                                                                               
                                                                            
                                                                        
            if result and result[0] == 'multumesc':
                lw_y = float(frame[15, 1])
                if lw_y > 0:
                    if nose_y > 0:
                                                                             
                        if (lw_y - nose_y) < 0.25:
                            result = None
                    else:
                                                                                 
                        if lw_y < 0.58:
                            result = None
        if result:
            sign_ro, sign_en, conf = result
            votes.setdefault(sign_ro, []).append((sign_en, conf))

                                                                              
    familie_frames = sum(1 for f in window if _check_familie_frame(f))
    if familie_frames >= len(window) * 0.30:
        lm, rm = _wrists_motion_score(window)
        if lm > 0.020 and rm > 0.020:
                                                                               
            wdists = []
            for f in window:
                lw = f[15, :2].astype(float)
                rw = f[16, :2].astype(float)
                if np.any(lw != 0) and np.any(rw != 0):
                    wdists.append(float(np.linalg.norm(lw - rw)))
            if len(wdists) >= 4:
                d_range = max(wdists) - min(wdists)
                sw = float(np.linalg.norm(
                    window[-1][12, :2].astype(float) - window[-1][11, :2].astype(float))) + 1e-6
                if d_range / sw > 0.25:
                    for _ in range(familie_frames):
                        votes.setdefault('familie', []).append(('family', 0.88))

    if not votes:
        return None

                                                                              
    if 'a minca' in votes:
        lm, rm = _wrists_motion_score(window)
        both_moving = lm > 0.018 and rm > 0.018
        if not both_moving:
            del votes['a minca']
        if not votes:
            return None

                                                                     
    best_ro = max(votes, key=lambda s: (len(votes[s]), sum(c for _, c in votes[s])))
    entries = votes[best_ro]
    vote_ratio = len(entries) / len(window)

                                                    
    if vote_ratio < 0.50:
        return None

    avg_conf = float(np.mean([c for _, c in entries])) * min(vote_ratio * 1.2, 1.0)
    sign_en = entries[0][0]

    return {
        'success': True,
        'sign_ro': best_ro,
        'sign_en': sign_en,
        'confidence': round(avg_conf, 3),
        'votes': len(entries),
        'total_frames': len(window),
        'method': 'rules',
    }
