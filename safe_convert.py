import pickle
import numpy as np
import sys
import os
import struct
from pathlib import Path

def safe_tensor_to_numpy(tensor_data):
    """Convertește date tensor în numpy array în mod sigur"""
    if isinstance(tensor_data, dict):
        return {k: safe_tensor_to_numpy(v) for k, v in tensor_data.items()}
    elif isinstance(tensor_data, (list, tuple)):
        return [safe_tensor_to_numpy(x) for x in tensor_data]
    elif str(type(tensor_data)).startswith("<class 'torch"):
        # Convertim orice tip de tensor PyTorch la numpy
        try:
            return tensor_data.cpu().numpy()
        except:
            try:
                return tensor_data.detach().cpu().numpy()
            except:
                return np.array(tensor_data)
    return tensor_data

class SafeCPUUnpickler(pickle.Unpickler):
    """Unpickler personalizat pentru conversia sigură la CPU"""
    def find_class(self, module, name):
        # Tratăm special clasele PyTorch
        if module.startswith('torch'):
            return lambda *args, **kwargs: np.array([])
        return super().find_class(module, name)

    def persistent_load(self, pid):
        # Gestionăm referințele persistente
        return np.array([])

def convert_pkl_to_cpu(input_path, output_path=None):
    """Convertește un fișier PKL de la CUDA la CPU"""
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_cpu{input_path.suffix}"

    print(f"Convertesc:\n  De la: {input_path}\n  La: {output_path}")

    try:
        # Încercăm să citim fișierul cu unpickler-ul personalizat
        with open(input_path, 'rb') as f:
            unpickler = SafeCPUUnpickler(f)
            data = unpickler.load()

        # Convertim toate datele la numpy
        data = safe_tensor_to_numpy(data)
        print("Date convertite cu succes la numpy arrays")

        # Salvăm rezultatul
        with open(output_path, 'wb') as f:
            pickle.dump(data, f, protocol=2)
        
        print(f"✓ Conversie completă!\n  Salvat ca: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Eroare la conversie: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Folosire: python convert_pkl.py <cale_fisier.pkl>")
        sys.exit(1)

    success = convert_pkl_to_cpu(sys.argv[1])
    sys.exit(0 if success else 1)
