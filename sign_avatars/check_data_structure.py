"""
Script pentru a verifica structura datelor din fișierul PKL
Rulează înainte de enhancement pentru a vedea ce date ai disponibile
"""

import pickle
import torch
import sys

def inspect_pkl_file(pkl_path):
    """
    Inspectează structura unui fișier PKL pentru avatare
    """
    print(f"\n{'='*60}")
    print(f"Inspectare fișier: {pkl_path}")
    print(f"{'='*60}\n")
    
    # Încearcă să încarce cu torch
    data = None
    try:
        print("Încerc încărcare cu torch.load()...")
        data = torch.load(pkl_path, map_location='cpu')
        print("✓ Încărcat cu torch.load()\n")
    except Exception as e:
        print(f"✗ Eroare torch.load(): {e}")
        
        # Încearcă cu pickle
        try:
            print("Încerc încărcare cu pickle.load()...")
            with open(pkl_path, 'rb') as f:
                data = pickle.load(f)
            print("✓ Încărcat cu pickle.load()\n")
        except Exception as e2:
            print(f"✗ Eroare pickle.load(): {e2}")
            return
    
    if data is None:
        print("Nu s-au putut încărca datele!")
        return
    
    # Analizează structura
    print("STRUCTURA DATELOR:")
    print("-" * 60)
    
    if isinstance(data, dict):
        print(f"Tip: Dictionary cu {len(data)} chei\n")
        print("Chei disponibile:")
        for key in data.keys():
            value = data[key]
            print(f"  • '{key}':")
            print(f"      Tip: {type(value).__name__}")
            
            if isinstance(value, (list, tuple)):
                print(f"      Lungime: {len(value)}")
                if len(value) > 0:
                    print(f"      Primul element tip: {type(value[0]).__name__}")
                    if hasattr(value[0], 'shape'):
                        print(f"      Primul element shape: {value[0].shape}")
            elif hasattr(value, 'shape'):
                print(f"      Shape: {value.shape}")
            elif isinstance(value, (int, float, str)):
                print(f"      Valoare: {value}")
            print()
    
    elif isinstance(data, (list, tuple)):
        print(f"Tip: {type(data).__name__} cu {len(data)} elemente\n")
        if len(data) > 0:
            print(f"Primul element tip: {type(data[0]).__name__}")
            if isinstance(data[0], dict):
                print(f"Primul element chei: {list(data[0].keys())}")
    
    else:
        print(f"Tip: {type(data).__name__}")
        if hasattr(data, 'shape'):
            print(f"Shape: {data.shape}")
    
    print("\n" + "="*60)
    
    # Caută informații despre mesh
    print("\nCAUTĂ INFORMAȚII DESPRE MESH:")
    print("-" * 60)
    
    def search_mesh_data(obj, path="root"):
        """Caută recursiv date de tip vertices/faces"""
        findings = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}"
                
                # Caută chei relevante
                if any(keyword in key.lower() for keyword in ['vert', 'face', 'mesh', 'pose', 'joint']):
                    findings.append((current_path, key, type(value).__name__, 
                                   value.shape if hasattr(value, 'shape') else len(value) if isinstance(value, (list, tuple)) else None))
                
                # Caută recursiv
                findings.extend(search_mesh_data(value, current_path))
        
        elif isinstance(obj, (list, tuple)) and len(obj) > 0:
            findings.extend(search_mesh_data(obj[0], f"{path}[0]"))
        
        return findings
    
    mesh_findings = search_mesh_data(data)
    
    if mesh_findings:
        print("\nGăsit date potențiale pentru mesh:")
        for path, key, dtype, size in mesh_findings:
            print(f"  • {path}")
            print(f"      Cheie: '{key}'")
            print(f"      Tip: {dtype}")
            if size is not None:
                print(f"      Dimensiune: {size}")
            print()
    else:
        print("Nu s-au găsit chei evidente pentru vertices/faces")
    
    print("="*60)
    
    # Sugestii
    print("\nSUGESTII PENTRU ENHANCEMENT:")
    print("-" * 60)
    print("Bazat pe analiza de mai sus, trebuie să modifici funcția")
    print("'enhance_existing_video()' din enhance_avatar.py pentru a")
    print("extrage corect vertices și faces din structura ta de date.")
    print("\nExemplu de cod de adaptat:")
    print("""
    # În loc de:
    vertices = data['frames'][frame_idx]['vertices']
    
    # Folosește calea corectă din analiza de mai sus:
    vertices = data['<cheia_ta_aici>'][frame_idx]
    """)
    print("="*60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python check_data_structure.py <cale_fisier.pkl>")
        print("\nExemplu:")
        print('  python check_data_structure.py "calea/catre/fisier.pkl"')
        sys.exit(1)
    
    pkl_file = sys.argv[1]
    inspect_pkl_file(pkl_file)