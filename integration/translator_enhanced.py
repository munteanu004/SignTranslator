"""
Enhanced Translator cu Google Translate pentru mai multe match-uri
"""
import sys
import io
import json
from pathlib import Path

              
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
                                                         
DICTIONARY_PATH = PROJECT_ROOT / "integration" / "sign_dictionary.json"

class EnhancedTranslator:
    """Translator imbunatatit cu multiple strategii"""

    def __init__(self):
        self.dictionary = self.load_dictionary()
        print(f"✓ Dictionar incarcat (engleza): {len(self.dictionary)} cuvinte")

                                  
        try:
            from googletrans import Translator
            self.translator = Translator()
            self.has_translator = True
            print("✓ Google Translate: DISPONIBIL")
        except Exception:
            self.translator = None
            self.has_translator = False
            print("! Google Translate: INDISPONIBIL")

                                                
        self.synonyms = {
            'salut': ['hello', 'hi', 'greet'],
            'bună': ['hello', 'hi', 'good'],
            'buna': ['hello', 'hi', 'good'],
            'mulțumesc': ['thank', 'thanks', 'grateful'],
            'multumesc': ['thank', 'thanks', 'grateful'],
            'te rog': ['please'],
            'scuze': ['sorry', 'excuse', 'pardon'],
            'ajutor': ['help', 'assist'],
            'mașină': ['car', 'auto', 'vehicle'],
            'masina': ['car', 'auto', 'vehicle'],
            'carte': ['book'],
            'telefon': ['phone', 'telephone', 'cell'],
            'computer': ['computer', 'pc'],
        }

    def load_dictionary(self):
        """Incarca dictionarul existent"""
        if not DICTIONARY_PATH.exists():
            return {}

        with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    def translate_with_google(self, word):
        """Traduce cuvantul cu Google Translate"""
        if not self.has_translator:
            return []

        try:
            result = self.translator.translate(word, src='ro', dest='en')
            if result and result.text:
                return [result.text.lower()]
        except Exception as e:
            print(f"  ! Eroare Google Translate: {e}")

        return []

    def translate_sentence_ro_to_en(self, sentence):
        """
        Translate a Romanian sentence to English (best-effort).

        Returns the translated English text (lowercased) or None.
        """
        sentence = (sentence or '').strip()
        if not sentence:
            return ''

                                              
        if self.has_translator:
            try:
                result = self.translator.translate(sentence, src='ro', dest='en')
                if result and result.text:
                    return result.text.lower()
            except Exception as e:
                print(f"  ! Eroare Google Translate (sentence): {e}")

                                                                
        words = sentence.split()
        translated_words = []
        for w in words:
            w_clean = w.lower().strip()
                                 
            if w_clean in self.synonyms and self.synonyms[w_clean]:
                translated_words.append(self.synonyms[w_clean][0])
            else:
                                                                                   
                translated_words.append(w_clean)

        return ' '.join(translated_words)

    def find_sign_by_english(self, english_word):
        """
        Find PKL mapping using an English word lookup in the English-first dictionary.

        Returns dict or None
        """
        if not english_word:
            return None

        word = english_word.lower().strip()

                                                                                    
        if word in self.dictionary:
            data = self.dictionary[word]
            return {
                'word': word,
                'pkl_file': data['pkl_file'],
                'english': word,
                'source': data.get('source', ''),
                'method': 'direct-en'
            }

                                                                        
        for key in self.dictionary.keys():
            if word in key or key in word:
                data = self.dictionary[key]
                return {
                    'word': key,
                    'pkl_file': data['pkl_file'],
                    'english': key,
                    'source': data.get('source', ''),
                    'method': f'fuzzy-en ({key})'
                }

        return None

    def get_synonyms(self, word):
        """Obtine sinonime pentru cuvant"""
        synonyms = []

                             
        if word in self.synonyms:
            synonyms.extend(self.synonyms[word])

                             
        if self.has_translator:
            google_trans = self.translate_with_google(word)
            synonyms.extend(google_trans)

                            
                                               
        common_variants = {
            'mânca': ['eat', 'food'],
            'manca': ['eat', 'food'],
            'bea': ['drink', 'water'],
            'dormi': ['sleep', 'bed'],
            'lucra': ['work', 'job'],
            'învăța': ['learn', 'study', 'school'],
            'invata': ['learn', 'study', 'school'],
        }

        if word in common_variants:
            synonyms.extend(common_variants[word])

        return list(set(synonyms))                     

    def find_sign(self, word):
        """
        Gaseste PKL pentru un cuvant folosind multiple strategii

        Returns:
            dict sau None
        """
        word = word.lower().strip()

                                    
        if word in self.dictionary:
            return {
                'word': word,
                'pkl_file': self.dictionary[word]['pkl_file'],
                'english': self.dictionary[word].get('english_translation', ''),
                'source': self.dictionary[word].get('source', ''),
                'method': 'direct'
            }

                               
        synonyms = self.get_synonyms(word)

        for synonym in synonyms:
                                                         
                                                  
            for ro_word, data in self.dictionary.items():
                en_word = data.get('english_translation', '').lower()
                if en_word == synonym.lower():
                    return {
                        'word': word,
                        'pkl_file': data['pkl_file'],
                        'english': synonym,
                        'source': data.get('source', ''),
                        'method': f'synonym ({synonym})',
                        'original_ro': ro_word
                    }

                                                                 
                                  
        for dict_word in self.dictionary.keys():
            if self._are_similar(word, dict_word):
                return {
                    'word': word,
                    'pkl_file': self.dictionary[dict_word]['pkl_file'],
                    'english': self.dictionary[dict_word].get('english_translation', ''),
                    'source': self.dictionary[dict_word].get('source', ''),
                    'method': f'fuzzy match ({dict_word})'
                }

                            
        return None

    def _are_similar(self, word1, word2):
        """Verifica daca doua cuvinte sunt similare"""
                                                
        if word1 in word2 or word2 in word1:
            return True

                                         
        word1_clean = self._remove_diacritics(word1)
        word2_clean = self._remove_diacritics(word2)

        return word1_clean == word2_clean

    def _remove_diacritics(self, text):
        """Elimina diacritice"""
        diacritics = {
            'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
            'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T'
        }

        for old, new in diacritics.items():
            text = text.replace(old, new)

        return text


def test_enhanced_translator():
    """Test pentru translator imbunatatit"""
    print("\n" + "="*70)
    print("TEST ENHANCED TRANSLATOR")
    print("="*70 + "\n")

    translator = EnhancedTranslator()

    test_words = [
                                    
        'da', 'nu', 'bine',

                                                
        'salut', 'bună', 'mulțumesc',

                                        
        'cainele', 'animalul',

                             
        'calculator', 'masina'
    ]

    print("Testare cuvinte:\n")

    for word in test_words:
        print(f"Cuvant: '{word}'")
        result = translator.find_sign(word)

        if result:
            method = result.get('method', 'unknown')
            english = result.get('english', '?')
            pkl = Path(result['pkl_file']).name

            print(f"  ✓ GASIT via {method}")
            print(f"    EN: {english}")
            print(f"    PKL: {pkl}")

            if 'original_ro' in result:
                print(f"    Original: {result['original_ro']}")
        else:
            print(f"  ✗ NU GASIT")

        print()

    print("="*70)


if __name__ == "__main__":
    test_enhanced_translator()
