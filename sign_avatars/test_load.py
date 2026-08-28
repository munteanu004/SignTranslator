"""Test loading PKL file"""
import sys
import torch
import pickle
import io

pkl_path = r"c:\Users\user\Desktop\OneDrive\Documents\SignTranslator\hamnosys_pkls_default_shape\hamnosys_pkls_default_shape\POISSON.pkl"

print(f"Loading: {pkl_path}")

try:
    data = torch.load(pkl_path, map_location=torch.device('cpu'), weights_only=False)
except:
    with open(pkl_path, 'rb') as f:
        class CPU_Unpickler(pickle.Unpickler):
            def find_class(self, module, name):
                if module == 'torch.storage' and name == '_load_from_bytes':
                    return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
                return super().find_class(module, name)
        data = CPU_Unpickler(f).load()

print(f"Data keys: {data.keys()}")
all_pose = data['smplx']
print(f"Shape: {all_pose.shape}")
print(f"Frames: {len(all_pose)}")
print(f"Params per frame: {all_pose.shape[1]}")
print("SUCCESS!")
