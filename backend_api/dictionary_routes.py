import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify, request


dictionary_bp = Blueprint('dictionary', __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGN_DICTIONARY_PATH = PROJECT_ROOT / 'integration' / 'sign_dictionary.json'
HOW2SIGN_DICTIONARY_PATH = PROJECT_ROOT / 'integration' / 'how2sign_word_dictionary.json'
ROMANIAN_DICTIONARY_PATH = PROJECT_ROOT / 'integration' / 'romanian_sign_dictionary.json'
TRANSLATION_CACHE_PATH = PROJECT_ROOT / 'integration' / 'dictionary_google_ro_cache.json'
CATALOG_TARGET_SIZE = 1240

CATEGORY_RULES = {
    'Salutari': {'hello', 'hi', 'goodbye', 'welcome', 'please', 'sorry', 'thanks', 'thank', 'yes', 'no'},
    'Familie': {'family', 'mother', 'father', 'mom', 'dad', 'brother', 'sister', 'baby', 'child', 'children', 'son', 'daughter', 'parent'},
    'Emotii': {'love', 'happy', 'sad', 'angry', 'fear', 'afraid', 'excited', 'calm', 'smile', 'cry', 'laugh', 'hope'},
    'Numere': {'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'first', 'second', 'third'},
    'Culori': {'red', 'blue', 'green', 'yellow', 'black', 'white', 'brown', 'purple', 'pink', 'orange', 'gray', 'grey'},
    'Verbe': {'go', 'come', 'eat', 'drink', 'sleep', 'work', 'read', 'write', 'open', 'close', 'learn', 'teach', 'help', 'start', 'stop', 'walk', 'run', 'play'},
    'Casa': {'house', 'home', 'room', 'door', 'window', 'kitchen', 'bathroom', 'bedroom', 'chair', 'table', 'bed', 'floor', 'wall'},
    'Mancare': {'food', 'water', 'milk', 'bread', 'apple', 'banana', 'meat', 'fish', 'fruit', 'vegetable', 'coffee', 'tea', 'rice', 'soup', 'sugar', 'sauce', 'steak', 'cheese', 'bacon', 'beans', 'beef', 'basil', 'appetite'},
    'Timp': {'today', 'tomorrow', 'yesterday', 'morning', 'evening', 'night', 'time', 'day', 'week', 'month', 'year', 'now', 'spring', 'summer', 'winter', 'afternoon', 'noon', 'anniversary', 'appointment'},
    'Locuri': {'school', 'city', 'country', 'street', 'hospital', 'store', 'market', 'office', 'park', 'church', 'factory', 'restaurant', 'apartment', 'address', 'beach', 'arena', 'aisle', 'alley'},
    'Animale': {'dog', 'cat', 'bird', 'horse', 'cow', 'fish', 'animal', 'bear', 'lion', 'tiger', 'snake', 'wolf', 'alligator', 'aphid', 'avian', 'beast'},
    'Corp': {'hand', 'head', 'eye', 'ear', 'nose', 'mouth', 'arm', 'leg', 'body', 'face', 'finger', 'heart', 'hair', 'foot', 'abdomen', 'ankle', 'hip'},
    'Transport': {'car', 'bus', 'train', 'airplane', 'plane', 'bicycle', 'bike', 'road', 'drive', 'truck', 'ship', 'boat'},
    'Natura': {'tree', 'flower', 'grass', 'river', 'mountain', 'sea', 'ocean', 'sun', 'moon', 'wind', 'rain', 'snow', 'earth', 'stone'},
    'Sanatate': {'doctor', 'nurse', 'medicine', 'medication', 'pain', 'sick', 'ill', 'hospital', 'health', 'tooth', 'blood', 'virus'},
    'Educatie': {'school', 'student', 'teacher', 'book', 'paper', 'pen', 'pencil', 'question', 'answer', 'study', 'class', 'lesson'},
    'Tehnologie': {'phone', 'computer', 'internet', 'video', 'camera', 'screen', 'keyboard', 'mouse', 'email', 'radio', 'television', 'tv'},
    'Profesii': {
        'doctor', 'teacher', 'worker', 'farmer', 'driver', 'chef', 'reporter', 'artist', 'lawyer',
        'engineer', 'assistant', 'agent', 'porter', 'baker', 'audiologist', 'dentist', 'florist',
        'stylist', 'dietitian', 'physician', 'scientist', 'therapist', 'technician', 'pediatrician',
        'psychiatrist', 'psychologist', 'veterinarian', 'archaeologist', 'reflexologist', 'musician',
        'nurse', 'professor', 'profesor', 'pilot', 'mechanic', 'electrician', 'plumber', 'carpenter',
        'journalist', 'translator', 'interpreter', 'programmer', 'developer', 'designer', 'firefighter',
        'policeman', 'policewoman', 'surgeon', 'pharmacist'
    },
    'Haine': {'shirt', 'pants', 'shoe', 'shoes', 'dress', 'coat', 'jacket', 'hat', 'sock', 'skirt', 'clothes', 'robe', 'apron', 'badge'},
    'Intrebari': {'who', 'what', 'when', 'where', 'why', 'how', 'which'},
    'Obiecte': {'glass', 'knife', 'fork', 'spoon', 'box', 'bag', 'key', 'ball', 'lamp', 'clock', 'bottle', 'paper', 'alarm', 'agenda', 'tube', 'file', 'page', 'quart', 'arrow', 'armor', 'award', 'bands', 'beads'},
    'Persoane': {'person', 'people', 'man', 'woman', 'boy', 'girl', 'friend', 'aunt', 'uncle', 'actor', 'author', 'audience', 'adult', 'baby', 'president'},
    'Actiuni': {'ask', 'agree', 'allow', 'adapt', 'adopt', 'adjust', 'affect', 'aid', 'aim', 'announce', 'analyze', 'appear', 'approach', 'arrive', 'assist', 'assume', 'appreciate', 'argue', 'answer', 'keep', 'know', 'like', 'make', 'put', 'take', 'talk', 'think', 'touch', 'wear', 'find', 'give', 'push', 'pull', 'follow', 'turn', 'meet', 'respond', 'accomplish', 'approve', 'annoy', 'pause', 'sell', 'walk', 'admit', 'adore', 'align', 'alter', 'apply', 'avoid', 'begin', 'began', 'begun', 'buy', 'cut', 'end', 'fit', 'get', 'hit', 'hug', 'want'},
    'Calitati': {'able', 'active', 'available', 'appropriate', 'advanced', 'good', 'bad', 'small', 'large', 'little', 'old', 'young', 'true', 'poor', 'rare', 'strong', 'weak', 'cold', 'hot', 'simple', 'double', 'expensive', 'agile', 'alive', 'awake', 'awful', 'basic'},
    'Directii': {'above', 'across', 'around', 'apart', 'ahead', 'under', 'over', 'inside', 'outside', 'right', 'left', 'east', 'west', 'north', 'south', 'straight', 'behind', 'front', 'route'},
    'Comunicare': {'asl', 'alphabet', 'adjective', 'adverb', 'article', 'language', 'speak', 'talk', 'question', 'answer', 'read', 'write', 'sign', 'signal', 'meaning', 'accent'},
    'Lume': {'africa', 'america', 'arizona', 'australia', 'france', 'island', 'earth', 'world', 'country', 'state', 'city', 'region'},
    'Societate': {'army', 'authority', 'arrest', 'law', 'legal', 'police', 'government', 'court', 'alcohol', 'violence', 'president', 'attorney'},
    'Abstracte': {'about', 'all', 'any', 'another', 'also', 'almost', 'again', 'always', 'already', 'against', 'anyway', 'alone', 'entire', 'truth', 'theme', 'force', 'piece', 'place', 'attitude', 'advantage', 'relation', 'patience', 'attention'},
    'Vreme': {'air', 'fire', 'fog', 'wind', 'rain', 'snow', 'storm', 'sun', 'cloud', 'weather', 'thirst'},
    'Sezoane': {'spring', 'summer', 'autumn', 'winter', 'april'},
    'Sport': {'sport', 'archery', 'walking', 'run', 'ball', 'game'},
    'Stiinta': {'algebra', 'anatomy', 'biology', 'science', 'math', 'chemistry', 'audiology'},
    'Siguranta': {'accident', 'alarm', 'poison', 'danger', 'emergency'},
    'Relatii': {'parents', 'relation', 'friendship', 'marriage'},
}

CATEGORY_ORDER = [
    'Salutari',
    'Familie',
    'Emotii',
    'Numere',
    'Culori',
    'Verbe',
    'Casa',
    'Mancare',
    'Timp',
    'Locuri',
    'Animale',
    'Corp',
    'Transport',
    'Natura',
    'Sanatate',
    'Educatie',
    'Tehnologie',
    'Profesii',
    'Haine',
    'Intrebari',
    'Obiecte',
    'Persoane',
    'Actiuni',
    'Calitati',
    'Directii',
    'Comunicare',
    'Lume',
    'Societate',
    'Abstracte',
    'Vreme',
    'Sezoane',
    'Sport',
    'Stiinta',
    'Siguranta',
    'Relatii',
    'Diverse',
]

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'do', 'for', 'from', 'he', 'her', 'hers', 'him', 'his',
    'i', 'if', 'in', 'into', 'is', 'it', 'its', 'me', 'my', 'of', 'on', 'or', 'our', 'ours', 'she', 'that',
    'the', 'their', 'them', 'there', 'these', 'they', 'this', 'those', 'to', 'too', 'up', 'us', 'we', 'with', 'you', 'your'
}

WORD_PRIORITY = {
    'thanks': 50,
    'thank': 50,
    'please': 50,
    'hello': 50,
    'goodbye': 50,
    'help': 45,
    'water': 45,
    'food': 45,
    'mother': 45,
    'father': 45,
    'friend': 45,
    'love': 45,
    'school': 40,
    'book': 40,
    'home': 40,
    'work': 40,
}

LOW_VALUE_WORDS = {
    'about', 'after', 'ago', 'all', 'any', 'also', 'another', 'but', 'can', 'has', 'have',
    'days', 'seen', 'sees', 'sold', 'tout', 'vert', 'fin', 'lit', 'sang',
}

PREFERRED_ROMANIAN_OVERRIDES = {
    'agent': 'Agent',
    'archaeologist': 'Arheolog',
    'artist': 'Artist',
    'assistant': 'Asistent',
    'audiologist': 'Audiolog',
    'baker': 'Brutar',
    'chef': 'Bucătar',
    'dentist': 'Stomatolog',
    'dietitian': 'Dietetician',
    'doctor': 'Doctor',
    'driver': 'Șofer',
    'engineer': 'Inginer',
    'farmer': 'Fermier',
    'florist': 'Florist',
    'journalist': 'Jurnalist',
    'lawyer': 'Avocat',
    'mechanic': 'Mecanic',
    'musician': 'Muzician',
    'nurse': 'Asistent medical',
    'pediatrician': 'Pediatru',
    'pharmacist': 'Farmacist',
    'physician': 'Medic',
    'pilot': 'Pilot',
    'plumber': 'Instalator',
    'police': 'Polițist',
    'policeman': 'Polițist',
    'policewoman': 'Polițistă',
    'porter': 'Hamal',
    'professor': 'Profesor',
    'programmer': 'Programator',
    'psychiatrist': 'Psihiatru',
    'psychologist': 'Psiholog',
    'reflexologist': 'Reflexolog',
    'reporter': 'Reporter',
    'scientist': 'Om de știință',
    'stylist': 'Stilist',
    'surgeon': 'Chirurg',
    'teacher': 'Profesor',
    'technician': 'Tehnician',
    'therapist': 'Terapeut',
    'translator': 'Traducător',
    'veterinarian': 'Medic veterinar',
    'worker': 'Muncitor',
}

USEFUL_SHORT_WORDS = {
    'age', 'air', 'art', 'ask', 'buy', 'bye', 'cut', 'dry', 'egg', 'end', 'far', 'fit', 'fly',
    'fog', 'fun', 'get', 'god', 'gun', 'guy', 'gym', 'hip', 'hit', 'hug', 'ice', 'ink', 'man',
    'ok', 'old', 'put', 'run', 'sale', 'talk', 'tube', 'want', 'wear',
}


@dictionary_bp.route('/api/dictionary', methods=['GET'])
def get_dictionary_entries():
    query = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or 'Toate').strip()
    limit = _safe_int(request.args.get('limit'), default=120, minimum=1, maximum=CATALOG_TARGET_SIZE)
    offset = _safe_int(request.args.get('offset'), default=0, minimum=0, maximum=CATALOG_TARGET_SIZE)

    catalog = _load_catalog()
    filtered = _filter_entries(catalog['entries'], query=query, category=category)
    page = filtered[offset:offset + limit]
    response_entries = [
        {k: v for k, v in entry.items() if k not in {'search_terms', 'needs_translation'}}
        for entry in page
    ]

    return jsonify({
        'entries': response_entries,
        'total': len(filtered),
        'catalog_total': len(catalog['entries']),
        'categories': catalog['categories'],
    })


def _safe_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


@lru_cache(maxsize=1)
def _load_catalog():
    sign_dictionary = _load_json(SIGN_DICTIONARY_PATH)
    how2sign_dictionary = _load_json(HOW2SIGN_DICTIONARY_PATH)
    romanian_dictionary = _load_json(ROMANIAN_DICTIONARY_PATH)
    english_to_romanian = _build_english_to_romanian_index(romanian_dictionary)

    entries = []
    seen_ids = set()

    for english_word, data in sign_dictionary.items():
        if str(data.get('source')) != 'WLASL':
            continue
        entry = _build_entry(english_word, data, english_to_romanian, source_override='WLASL')
        if not entry or entry['id'] in seen_ids:
            continue
        seen_ids.add(entry['id'])
        entries.append(entry)

    for english_word, data in how2sign_dictionary.items():
        entry = _build_entry(english_word, data, english_to_romanian, source_override='How2Sign')
        if not entry or entry['id'] in seen_ids:
            continue
        seen_ids.add(entry['id'])
        entries.append(entry)

    entries.sort(key=_entry_sort_key)
    trimmed_entries = entries[:CATALOG_TARGET_SIZE]
    _apply_romanian_translations(trimmed_entries)

    category_counts = [{'name': 'Toate', 'count': len(trimmed_entries)}]
    for category_name in CATEGORY_ORDER:
        count = sum(1 for entry in trimmed_entries if entry['category'] == category_name)
        if count > 0:
            category_counts.append({'name': category_name, 'count': count})

    return {
        'entries': trimmed_entries,
        'categories': category_counts,
    }


def _build_english_to_romanian_index(romanian_dictionary):
    english_to_romanian = {}
    for ro_word, data in romanian_dictionary.items():
        ro_clean = _clean_display_word(ro_word)
        if not _is_clean_phrase(ro_clean):
            continue
        english_value = data.get('english_translation') or data.get('english') or ''
        english_key = _normalize_key(str(english_value))
        if not english_key:
            continue
        english_to_romanian.setdefault(english_key, [])
        if ro_clean not in english_to_romanian[english_key]:
            english_to_romanian[english_key].append(ro_clean)
    return english_to_romanian


def _build_entry(english_word, data, english_to_romanian, source_override=None):
    english_clean = _clean_display_word(english_word)
    if not _is_candidate_dictionary_word(english_clean):
        return None

    lookup_key = _normalize_key(english_word)
    romanian_aliases = english_to_romanian.get(lookup_key, [])
    override_word = PREFERRED_ROMANIAN_OVERRIDES.get(lookup_key)
    if override_word:
        display_word = override_word
    elif romanian_aliases:
        display_word = romanian_aliases[0]
    else:
        display_word = english_clean.title()
    category = _classify_category(english_clean)
    level = _classify_level(english_clean)
    xp = {'Usor': 10, 'Mediu': 15, 'Dificil': 20}[level]
    source = source_override or str(data.get('source') or 'Unknown')

    return {
        'id': f"en:{lookup_key}",
        'word': display_word,
        'english': english_clean.title(),
        'category': category,
        'level': level,
        'xp': xp,
        'source': source,
        'has_animation': True,
        'lookup': lookup_key,
        'lookup_type': 'english',
        'needs_translation': not bool(romanian_aliases) and not bool(override_word),
        'search_terms': _build_search_terms(display_word, english_clean, romanian_aliases),
    }


def _entry_sort_key(item):
    normalized_english = _normalize_key(item['english'])
    normalized_word = _normalize_key(item['word'])
    has_romanian_alias = normalized_word != normalized_english
    category_rank = CATEGORY_ORDER.index(item['category']) if item['category'] in CATEGORY_ORDER else len(CATEGORY_ORDER)
    source_rank = 0 if item['source'] == 'WLASL' else 1
    token_count = len(normalized_english.split())
    length_rank = len(normalized_english.replace(' ', ''))
    priority = WORD_PRIORITY.get(normalized_english, 0)
    is_diverse = 1 if item['category'] == 'Diverse' else 0
    quality_penalty = _entry_quality_penalty(item)
    return (
        source_rank,
        is_diverse,
        quality_penalty,
        -priority,
        0 if has_romanian_alias else 1,
        category_rank,
        token_count,
        length_rank,
        item['english'].lower(),
    )


def _apply_romanian_translations(entries):
    cache = _load_translation_cache()
    missing = []

    for entry in entries:
        english_key = _normalize_key(entry['english'])
        if not entry.get('needs_translation'):
            continue
        translated = cache.get(english_key)
        if translated:
            entry['word'] = translated
        else:
            missing.append(entry)

    if not missing:
        return

    english_words = [entry['english'] for entry in missing]
    translated_map = _translate_words_to_romanian(english_words)
    if not translated_map:
        return

    updated = False
    for entry in missing:
        english_key = _normalize_key(entry['english'])
        translated = translated_map.get(english_key)
        if translated:
            entry['word'] = translated
            cache[english_key] = translated
            updated = True

    if updated:
        _save_translation_cache(cache)


def _filter_entries(entries, query, category):
    normalized_query = _normalize_key(query)
    normalized_category = category.strip().lower()

    filtered = []
    for entry in entries:
        if normalized_category and normalized_category != 'toate' and entry['category'].lower() != normalized_category:
            continue
        if normalized_query:
            haystack = entry.get('search_terms', '')
            if normalized_query not in haystack:
                continue
        filtered.append(entry)
    return filtered


def _load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def _load_translation_cache():
    data = _load_json(TRANSLATION_CACHE_PATH)
    return data if isinstance(data, dict) else {}


def _save_translation_cache(cache):
    try:
        with open(TRANSLATION_CACHE_PATH, 'w', encoding='utf-8') as handle:
            json.dump(cache, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _translate_words_to_romanian(words):
    words = [word.strip() for word in words if word and word.strip()]
    if not words:
        return {}

    translated = {}
    batch_size = 40
    for start in range(0, len(words), batch_size):
        batch = words[start:start + batch_size]
        translated.update(_translate_batch_to_romanian(batch))
    return translated


def _translate_batch_to_romanian(words):
    try:
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        query = "\n".join(words)
        params = urlencode({
            'client': 'gtx',
            'sl': 'en',
            'tl': 'ro',
            'q': query,
            'dt': 't',
        })
        req = Request(
            f'https://translate.googleapis.com/translate_a/single?{params}',
            headers={'User-Agent': 'Mozilla/5.0'},
        )
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode('utf-8'))

        translated_text = ''.join(part[0] for part in payload[0] if part and part[0]).strip()
        translated_lines = [line.strip() for line in translated_text.split('\n')]

        out = {}
        for source_word, translated_word in zip(words, translated_lines):
            cleaned = _clean_romanian_label(translated_word)
            if cleaned:
                out[_normalize_key(source_word)] = cleaned
        return out
    except Exception:
        return {}


def _clean_romanian_label(value):
    cleaned = str(value).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if not cleaned:
        return ''
    cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _build_search_terms(display_word, english_word, romanian_aliases):
    parts = [display_word, english_word, *romanian_aliases]
    return ' '.join(_normalize_key(part) for part in parts if part)


def _clean_display_word(word):
    cleaned = str(word).replace('_', ' ').replace('-', ' ').replace('+', ' ').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned


def _normalize_key(value):
    text = unicodedata.normalize('NFD', str(value).lower())
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9 ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _is_candidate_dictionary_word(word):
    normalized = _normalize_key(word)
    if not normalized:
        return False
    if not _is_clean_phrase(normalized):
        return False

    tokens = normalized.split()
    if normalized in STOPWORDS:
        return False
    if any(token in STOPWORDS for token in tokens):
        return False
    if any(len(token) == 1 for token in tokens):
        return False
    if any(token.isdigit() for token in tokens):
        return False
    if any(len(token) <= 2 and token not in {'ok'} for token in tokens):
        return False
    if not all(re.search(r'[aeiouy]', token) for token in tokens if len(token) <= 4):
        return False
    return True


def _entry_quality_penalty(item):
    normalized_english = _normalize_key(item['english'])
    tokens = normalized_english.split()
    source = item['source']
    penalty = 0

    if normalized_english in LOW_VALUE_WORDS:
        penalty += 3

    if source == 'How2Sign' and item['category'] == 'Diverse':
        penalty += 4

    if source == 'How2Sign' and len(tokens) == 1:
        token = tokens[0]
        if len(token) == 3 and token not in USEFUL_SHORT_WORDS:
            penalty += 6
        elif len(token) == 4 and token not in USEFUL_SHORT_WORDS:
            penalty += 2

    if source == 'How2Sign' and len(tokens) == 1 and tokens[0].endswith('ed'):
        penalty += 2

    return penalty


def _is_clean_phrase(word):
    normalized = _normalize_key(word)
    if not normalized:
        return False
    if len(normalized) < 2 or len(normalized) > 28:
        return False
    if normalized[0].isdigit():
        return False
    words = normalized.split()
    if len(words) > 3:
        return False
    return all(len(part) > 0 for part in words)


def _classify_category(english_word):
    normalized = _normalize_key(english_word)
    tokens = normalized.split()
    for category, keywords in CATEGORY_RULES.items():
        if normalized in keywords or any(token in keywords for token in tokens):
            return category

    if any(token.endswith('ing') for token in tokens):
        return 'Actiuni'
    if any(token.endswith(('tion', 'sion', 'ment', 'ness', 'ity')) for token in tokens):
        return 'Abstracte'
    if any(token.endswith(('ology', 'graphy', 'metry')) for token in tokens):
        return 'Stiinta'
    if any(token.endswith('day') for token in tokens):
        return 'Timp'
    if any(token.endswith(('ful', 'less', 'ive', 'ous', 'ish')) for token in tokens):
        return 'Calitati'
    return 'Diverse'


def _classify_level(english_word):
    normalized = _normalize_key(english_word)
    token_count = len(normalized.split())
    length = len(normalized.replace(' ', ''))
    if token_count == 1 and length <= 5:
        return 'Usor'
    if token_count <= 2 and length <= 9:
        return 'Mediu'
    return 'Dificil'
