"""
Construieste un dictionar care mapeaza cuvinte in limba romana la fisierele PKL corespunzatoare
Foloseste traducere Romana -> Engleza -> PKL gesture
"""
import json
import os
import sys
import io
from pathlib import Path

                         
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

          
PROJECT_ROOT = Path(__file__).parent.parent
WLASL_JSON = PROJECT_ROOT / "sign_avatars/datasets/word2motion/WLASL_v0.3.json"
HAMNOSYS_JSON = PROJECT_ROOT / "sign_avatars/datasets/hamnosys2motion/data.json"
HAMNOSYS_PKL_DIR = PROJECT_ROOT / "hamnosys_pkls_default_shape/hamnosys_pkls_default_shape"
WLASL_PKL_DIR = PROJECT_ROOT / "wlasl_pkls_cropFalse_defult_shape/wlasl_pkls_cropFalse_defult_shape"
OUTPUT_JSON = PROJECT_ROOT / "integration/romanian_sign_dictionary.json"

                                                                
ROMANIAN_TO_ENGLISH = {
              
    'salut': 'hello',
    'bună': 'hello',
    'buna': 'hello',
    'hai': 'hi',
    'pa': 'goodbye',
    'la revedere': 'goodbye',
    'ciao': 'goodbye',

               
    'mulțumesc': 'thank',
    'multumesc': 'thank',
    'mersi': 'thank',
    'te rog': 'please',
    'vă rog': 'please',
    'scuze': 'sorry',
    'îmi pare rău': 'sorry',
    'pardon': 'sorry',

           
    'da': 'yes',
    'nu': 'no',

                     
    'ajutor': 'help',
    'mâncare': 'food',
    'mancare': 'food',
    'apă': 'water',
    'apa': 'water',
    'mânca': 'eat',
    'manca': 'eat',
    'bea': 'drink',
    'dormi': 'sleep',
    'somn': 'sleep',
    'lucru': 'work',
    'muncă': 'work',
    'munca': 'work',

            
    'casă': 'home',
    'casa': 'home',
    'acasă': 'home',
    'acasa': 'home',
    'școală': 'school',
    'scoala': 'school',

              
    'prieten': 'friend',
    'prietenă': 'friend',
    'prietena': 'friend',
    'familie': 'family',
    'mamă': 'mother',
    'mama': 'mother',
    'tată': 'father',
    'tata': 'father',
    'frate': 'brother',
    'soră': 'sister',
    'sora': 'sister',

            
    'zero': 'zero',
    'unu': 'one',
    'doi': 'two',
    'două': 'two',
    'doua': 'two',
    'trei': 'three',
    'patru': 'four',
    'cinci': 'five',
    'șase': 'six',
    'sase': 'six',
    'șapte': 'seven',
    'sapte': 'seven',
    'opt': 'eight',
    'nouă': 'nine',
    'noua': 'nine',
    'zece': 'ten',

            
    'roșu': 'red',
    'rosu': 'red',
    'albastru': 'blue',
    'verde': 'green',
    'galben': 'yellow',
    'negru': 'black',
    'alb': 'white',

          
    'azi': 'today',
    'astăzi': 'today',
    'astazi': 'today',
    'mâine': 'tomorrow',
    'maine': 'tomorrow',
    'ieri': 'yesterday',
    'acum': 'now',
    'după': 'after',
    'dupa': 'after',
    'înainte': 'before',
    'inainte': 'before',

                  
    'merge': 'go',
    'veni': 'come',
    'face': 'do',
    'avea': 'have',
    'fi': 'be',
    'vedea': 'see',
    'spune': 'say',
    'știe': 'know',
    'stie': 'know',
    'vrea': 'want',
    'putea': 'can',

                        
    'carte': 'book',
    'școală': 'school',
    'scoala': 'school',
    'timp': 'time',
    'zi': 'day',
    'noapte': 'night',
    'om': 'person',
    'bărbat': 'man',
    'barbat': 'man',
    'femeie': 'woman',
    'copil': 'child',
    'lume': 'world',
    'viață': 'life',
    'viata': 'life',
    'mână': 'hand',
    'mana': 'hand',
    'ochi': 'eye',
    'cap': 'head',

             
    'bine': 'good',
    'rău': 'bad',
    'rau': 'bad',
    'mult': 'much',
    'puțin': 'little',
    'putin': 'little',
    'mare': 'big',
    'mic': 'small',

             
    'câine': 'dog',
    'caine': 'dog',
    'pisică': 'cat',
    'pisica': 'cat',
    'animal': 'animal',
    'pasăre': 'bird',
    'pasare': 'bird',
    'pește': 'fish',
    'peste': 'fish',
    'cal': 'horse',
    'vacă': 'cow',
    'vaca': 'cow',

                     
    'iubi': 'love',
    'place': 'like',
    'urî': 'hate',
    'uri': 'hate',
    'gândi': 'think',
    'gandi': 'think',
    'simți': 'feel',
    'simti': 'feel',
    'auzi': 'hear',
    'asculta': 'listen',
    'vorbí': 'speak',
    'vorbi': 'speak',
    'citi': 'read',
    'scrie': 'write',
    'învăța': 'learn',
    'invata': 'learn',
    'înțelege': 'understand',
    'intelege': 'understand',
    'găsi': 'find',
    'gasi': 'find',
    'cauta': 'search',
    'căuta': 'search',
    'lua': 'take',
    'da': 'give',
    'pune': 'put',
    'deschide': 'open',
    'închide': 'close',
    'inchide': 'close',
    'începe': 'start',
    'incepe': 'start',
    'termina': 'finish',
    'opri': 'stop',
    'continua': 'continue',
    'aștepta': 'wait',
    'astepta': 'wait',
    'alerga': 'run',
    'sări': 'jump',
    'sari': 'jump',
    'sta': 'sit',
    'ridica': 'stand',
    'pleca': 'leave',
    'rămâne': 'stay',
    'ramane': 'stay',

                              
    'nume': 'name',
    'vârstă': 'age',
    'varsta': 'age',
    'număr': 'number',
    'numar': 'number',
    'oraș': 'city',
    'oras': 'city',
    'țară': 'country',
    'tara': 'country',
    'stradă': 'street',
    'strada': 'street',
    'mașină': 'car',
    'masina': 'car',
    'autobuz': 'bus',
    'tren': 'train',
    'avion': 'airplane',
    'bicicletă': 'bicycle',
    'bicicleta': 'bicycle',
    'telefon': 'phone',
    'computer': 'computer',
    'televizor': 'television',
    'cameră': 'room',
    'camera': 'room',
    'bucătărie': 'kitchen',
    'bucatarie': 'kitchen',
    'baie': 'bathroom',
    'dormitor': 'bedroom',
    'ușă': 'door',
    'usa': 'door',
    'fereastră': 'window',
    'fereastra': 'window',
    'masă': 'table',
    'masa': 'table',
    'scaun': 'chair',
    'pat': 'bed',

                        
    'pâine': 'bread',
    'paine': 'bread',
    'lapte': 'milk',
    'cafea': 'coffee',
    'ceai': 'tea',
    'suc': 'juice',
    'bere': 'beer',
    'vin': 'wine',
    'carne': 'meat',
    'pui': 'chicken',
    'ou': 'egg',
    'brânză': 'cheese',
    'branza': 'cheese',
    'fructe': 'fruit',
    'măr': 'apple',
    'mar': 'apple',
    'banană': 'banana',
    'banana': 'banana',
    'portocală': 'orange',
    'portocala': 'orange',
    'legume': 'vegetables',
    'salată': 'salad',
    'salata': 'salad',
    'supă': 'soup',
    'supa': 'soup',
    'pizza': 'pizza',
    'hamburger': 'hamburger',

                  
    'haină': 'coat',
    'haina': 'coat',
    'pantaloni': 'pants',
    'cămaşă': 'shirt',
    'camasa': 'shirt',
    'rochie': 'dress',
    'fustă': 'skirt',
    'fusta': 'skirt',
    'pantofi': 'shoes',
    'cizme': 'boots',
    'pălărie': 'hat',
    'palarie': 'hat',
    'geacă': 'jacket',
    'geaca': 'jacket',

                         
    'fericit': 'happy',
    'trist': 'sad',
    'supărat': 'angry',
    'suparat': 'angry',
    'speriat': 'scared',
    'obosit': 'tired',
    'bolnav': 'sick',
    'sănătos': 'healthy',
    'sanatos': 'healthy',
    'foame': 'hungry',
    'sete': 'thirsty',
    'cald': 'hot',
    'frig': 'cold',
    'frumos': 'beautiful',
    'urât': 'ugly',
    'urat': 'ugly',

                           
    'aici': 'here',
    'acolo': 'there',
    'sus': 'up',
    'jos': 'down',
    'stânga': 'left',
    'stanga': 'left',
    'dreapta': 'right',
    'aproape': 'near',
    'departe': 'far',
    'în': 'in',
    'pe': 'on',
    'sub': 'under',
    'peste': 'over',
    'între': 'between',
    'intre': 'between',
    'cu': 'with',
    'fără': 'without',
    'fara': 'without',
    'pentru': 'for',
    'despre': 'about',

               
    'ce': 'what',
    'cine': 'who',
    'când': 'when',
    'cand': 'when',
    'unde': 'where',
    'de ce': 'why',
    'cum': 'how',
    'cât': 'how much',
    'cat': 'how much',
    'care': 'which',
}

def load_english_dictionary():
    """Incarca dictionarul engleza -> PKL"""
    english_dict = {}

                      
    if WLASL_JSON.exists():
        with open(WLASL_JSON, 'r', encoding='utf-8') as f:
            wlasl_data = json.load(f)

        for entry in wlasl_data:
            gloss = entry.get('gloss', '').lower().strip()
            if gloss and 'instances' in entry and len(entry['instances']) > 0:
                video_id = entry['instances'][0].get('video_id', '')
                if video_id:
                    pkl_file = f"{video_id.zfill(5)}.pkl"
                    pkl_path = WLASL_PKL_DIR / pkl_file

                    if pkl_path.exists():
                        english_dict[gloss] = {
                            'pkl_file': str(pkl_path),
                            'source': 'WLASL',
                            'video_id': video_id
                        }

                                  
    if HAMNOSYS_JSON.exists():
        with open(HAMNOSYS_JSON, 'r', encoding='utf-8') as f:
            hamnosys_data = json.load(f)

        for sign_id, data in hamnosys_data.items():
            type_name = data.get('type_name', '').lower().strip()
            if type_name:
                clean_name = type_name.replace('^', '').replace('-', '_').replace('1', '').replace('2', '').replace('a', '').replace('b', '')

                pkl_file = f"{sign_id}.pkl"
                pkl_path = HAMNOSYS_PKL_DIR / pkl_file

                if pkl_path.exists() and clean_name not in english_dict:
                    english_dict[clean_name] = {
                        'pkl_file': str(pkl_path),
                        'source': 'HamNoSys',
                        'sign_id': sign_id
                    }

    return english_dict

def build_romanian_dictionary():
    """Construieste dictionarul roman -> PKL"""
    print("Construire dictionar limba romana -> limbaj semne...")
    print("="*70)

                                           
    print("\n1. Incarcare dictionar engleza -> PKL...")
    english_dict = load_english_dictionary()
    print(f"   ✓ Incarcate {len(english_dict)} cuvinte engleza")

                                                             
    print("\n2. Mapare romana -> engleza -> PKL...")
    romanian_dict = {}

    mapped_count = 0
    unmapped = []

    for ro_word, en_word in ROMANIAN_TO_ENGLISH.items():
        if en_word in english_dict:
            romanian_dict[ro_word] = english_dict[en_word].copy()
            romanian_dict[ro_word]['english_translation'] = en_word
            mapped_count += 1
        else:
            unmapped.append(f"{ro_word} -> {en_word}")

    print(f"   ✓ Mapate {mapped_count} cuvinte romanesti")

    if unmapped:
        print(f"   ! {len(unmapped)} cuvinte nemapate:")
        for item in unmapped[:10]:
            print(f"      - {item}")
        if len(unmapped) > 10:
            print(f"      ... si inca {len(unmapped) - 10}")

                             
    print(f"\n3. Salvare dictionar...")
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(romanian_dict, f, indent=2, ensure_ascii=False)

    print(f"   ✓ Dictionar salvat: {OUTPUT_JSON}")
    print(f"\n{'='*70}")
    print(f"✓ TOTAL: {len(romanian_dict)} cuvinte romanesti in dictionar")
    print(f"{'='*70}\n")

    return romanian_dict

if __name__ == "__main__":
    dictionary = build_romanian_dictionary()

                      
    print("\nExemple din dictionar:")
    print("-"*70)
    for i, (ro_word, data) in enumerate(list(dictionary.items())[:20]):
        en_word = data.get('english_translation', '?')
        pkl_name = Path(data['pkl_file']).name
        print(f"{i+1}. '{ro_word}' -> '{en_word}' -> {pkl_name}")
    print("-"*70)
