import csv, os, json

csv_files = [
    r'c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\sign_avatars\datasets\language2motion\text\how2sign_realigned_train.csv',
    r'c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\sign_avatars\datasets\language2motion\text\how2sign_realigned_val.csv',
    r'c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\sign_avatars\datasets\language2motion\text\how2sign_realigned_test.csv',
]
pkl_dir = r'c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\how2sign_pkls_cropTrue_shapeTrue\how2sign_pkls_cropTrue_shapeTrue'
existing_pkls = set(f.replace('.pkl', '') for f in os.listdir(pkl_dir))

                                                 
best = {}

for csv_f in csv_files:
    with open(csv_f) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            sname = row['SENTENCE_NAME']
            if sname not in existing_pkls:
                continue
            sentence = row['SENTENCE'].strip()
            words_raw = sentence.lower().split()
            sent_len = len(words_raw)
            for w_raw in set(words_raw):
                w = ''.join(c for c in w_raw if c.isalpha())
                if len(w) < 2:
                    continue
                if w not in best or sent_len < best[w][0]:
                    best[w] = (sent_len, sname, sentence)

out = {}
for w, (slen, sname, sent) in best.items():
    pkl_path = os.path.join(pkl_dir, sname + '.pkl')
    out[w] = {
        'pkl_file': pkl_path,
        'sentence': sent,
        'source': 'How2Sign',
    }

out_path = r'c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\integration\how2sign_word_dictionary.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)

print(f'Saved {len(out)} words to how2sign_word_dictionary.json')
for w in ['thank', 'hello', 'water', 'mother', 'family', 'beautiful', 'love', 'help', 'sorry', 'please', 'good', 'yes', 'no']:
    if w in out:
        print(f'  {w}: "{out[w]["sentence"][:70]}"')
