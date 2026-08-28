"""
Script pentru generarea avatarului REALIST de limbaj semnale.
Caracteristici:
- Avatar SMPL-X cu detalii anatomice complete: față, corp, mâini
- Iluminare profesională tip studio pentru vizibilitate maximă a gesturilor
- Mâini ultra-vizibile cu lumini dedicate pentru degete, palmă și încheieturi
- Față realistă cu expresii clare și texturi naturale
- Corp complet vizibil cu relief muscular și anatomie corectă
- Cameră optimizată pentru limbaj semnale: captează toate gesturile mâinilor
- Post-procesare avansată pentru claritate și realism maxim
- Rezoluție Full HD (1920x1080) pentru detalii supreme
"""

# -*- coding: utf-8 -*-
import sys
import io

# Setare encoding UTF-8 pentru output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np

# Patch pentru compatibilitate NumPy 2.0 cu pyrender (care folosește np.infty depreciat)
if not hasattr(np, 'infty'):
    np.infty = np.inf

import pyrender
import trimesh
import pickle
import cv2
import os
from pathlib import Path
import copy
import importlib.util

# Importuri pentru SMPL-X și logica locală
try:
    import smplx
    import torch
    
    # Calea către modulul care trebuie importat
    module_path = os.path.join(os.path.dirname(__file__), 'common', 'utils', 'human_models.py')
    
    # Verifică dacă fișierul există
    if not os.path.exists(module_path):
        raise ImportError(f"Modulul 'human_models.py' nu a fost găsit la: {module_path}")

    # Încărcare directă a modulului 'human_models'
    print(f"Încărcare modul 'human_models' de la: {module_path}")
    spec = importlib.util.spec_from_file_location("human_models_temp", module_path)
    human_models_temp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(human_models_temp)
    
    # Extrage clasa SMPLX
    CustomSMPLX = human_models_temp.SMPLX

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
except ImportError as e:
    print(f"EROARE: Nu s-au putut importa dependențele necesare: {e}")
    print("Asigură-te că ai instalat 'smplx' și că 'human_models.py' există în 'sign_avatars/common/utils/'.")
    exit(1)


class EnhancedAvatarRenderer:
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        
        # Inițializează și încarcă modelul SMPL-X folosind clasa CustomSMPLX
        print("Inițializare model SMPL-X via CustomSMPLX (logica locală)...")
        smplx_wrapper = CustomSMPLX()
        
        # Extrage stratul 'neutral' și îl mută pe device
        self.smplx_model = copy.deepcopy(smplx_wrapper.layer['neutral']).to(device) 
        
        print("✓ Model SMPL-X încărcat și gata de utilizare.")
        
        # Scene și renderer
        self.scene = None
        self.renderer = pyrender.OffscreenRenderer(
            self.width, 
            self.height,
            point_size=1.0
        )
        
    def create_scene(self):
        """Scenă cu fundal ÎNTUNECAT pentru contrast maxim cu mâinile LUMINATE"""
        self.scene = pyrender.Scene(
            ambient_light=[0.40, 0.40, 0.42],  # Lumină ambientală moderată - mâinile vor fi iluminate separat
            bg_color=[0.10, 0.12, 0.15, 1.0]  # Fundal ÎNTUNECAT pentru contrast cu mâinile
        )
        
    def create_skin_material(self):
        """Material pentru corp - culoare normală"""
        material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[0.85, 0.65, 0.55, 1.0],  # Culoare naturală corp
            metallicFactor=0.0,
            roughnessFactor=0.50,  # Semi-mat
            doubleSided=True,
            alphaMode='OPAQUE'
        )
        return material

    def create_detailed_hand_material(self):
        """Material SPECIAL pentru mâini - ULTRA-LUMINOS pentru a ieși în evidență!!!"""
        material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[1.0, 0.95, 0.85, 1.0],  # Culoare FOARTE DESCHISĂ - aproape galben-deschis
            metallicFactor=0.0,
            roughnessFactor=0.10,  # FOARTE lucios pentru a reflecta toată lumina
            doubleSided=True,
            alphaMode='OPAQUE'
        )
        return material
    
    def setup_professional_lighting(self):
        """Sistem de iluminare FOCALIZAT pe MÂINI pentru limbaj semnale"""

        # Lumini generale moderate pentru corp și față
        key_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=4.0)
        key_pose = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 1.5],
            [0.0, 0.0, 1.0, 2.5],
            [0.0, 0.0, 0.0, 1.0]
        ])
        self.scene.add(key_light, pose=key_pose)

        fill_light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=3.0)
        fill_pose = np.array([
            [-1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 2.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        self.scene.add(fill_light, pose=fill_pose)
        
        # === FAȚĂ - iluminare moderată ===
        face_spot = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=60.0,
            innerConeAngle=np.pi/8,
            outerConeAngle=np.pi/3
        )
        self.scene.add(face_spot, pose=np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 1.60],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))
        
        # ========================================================================
        # === SISTEM DE ILUMINARE DEDICAT EXCLUSIV PENTRU MÂINI ===
        # === INTENSITATE MASIVĂ pentru vizibilitate PERFECTĂ a gesturilor ===
        # ========================================================================

        # SPOTLIGHT PRINCIPAL MÂNA STÂNGĂ - frontal
        left_hand_spot_front = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=250.0,  # MASIV pentru claritate extremă
            innerConeAngle=np.pi/12,
            outerConeAngle=np.pi/2.2
        )
        self.scene.add(left_hand_spot_front, pose=np.array([
            [1.0, 0.0, 0.0, -0.45],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.2],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # SPOTLIGHT PRINCIPAL MÂNA DREAPTĂ - frontal
        right_hand_spot_front = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=250.0,  # MASIV pentru claritate extremă
            innerConeAngle=np.pi/12,
            outerConeAngle=np.pi/2.2
        )
        self.scene.add(right_hand_spot_front, pose=np.array([
            [1.0, 0.0, 0.0, 0.45],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.2],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Spotlight secundar mâna stângă - lateral
        left_hand_spot_side = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=180.0,
            innerConeAngle=np.pi/10,
            outerConeAngle=np.pi/2
        )
        self.scene.add(left_hand_spot_side, pose=np.array([
            [0.866, 0.5, 0.0, -0.7],
            [-0.5, 0.866, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Spotlight secundar mâna dreaptă - lateral
        right_hand_spot_side = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=180.0,
            innerConeAngle=np.pi/10,
            outerConeAngle=np.pi/2
        )
        self.scene.add(right_hand_spot_side, pose=np.array([
            [0.866, -0.5, 0.0, 0.7],
            [0.5, 0.866, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # LUMINI PENTRU DEGETE - intensitate EXTREMĂ pentru fiecare deget
        # Degete mâna stângă - poziție frontal-sus
        left_fingers_1 = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=150.0)
        self.scene.add(left_fingers_1, pose=np.array([
            [1.0, 0.0, 0.0, -0.42],
            [0.0, 1.0, 0.0, 1.10],
            [0.0, 0.0, 1.0, 0.85],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Degete mâna dreaptă - poziție frontal-sus
        right_fingers_1 = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=150.0)
        self.scene.add(right_fingers_1, pose=np.array([
            [1.0, 0.0, 0.0, 0.42],
            [0.0, 1.0, 0.0, 1.10],
            [0.0, 0.0, 1.0, 0.85],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Degete mâna stângă - poziție frontal-aproape
        left_fingers_2 = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=140.0)
        self.scene.add(left_fingers_2, pose=np.array([
            [1.0, 0.0, 0.0, -0.48],
            [0.0, 1.0, 0.0, 0.95],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Degete mâna dreaptă - poziție frontal-aproape
        right_fingers_2 = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=140.0)
        self.scene.add(right_fingers_2, pose=np.array([
            [1.0, 0.0, 0.0, 0.48],
            [0.0, 1.0, 0.0, 0.95],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Palmă mâna stângă - iluminare directă
        left_palm = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=130.0)
        self.scene.add(left_palm, pose=np.array([
            [1.0, 0.0, 0.0, -0.40],
            [0.0, 1.0, 0.0, 0.88],
            [0.0, 0.0, 1.0, 1.10],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Palmă mâna dreaptă - iluminare directă
        right_palm = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=130.0)
        self.scene.add(right_palm, pose=np.array([
            [1.0, 0.0, 0.0, 0.40],
            [0.0, 1.0, 0.0, 0.88],
            [0.0, 0.0, 1.0, 1.10],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Lumină CENTRALĂ pentru ambele mâini - acoperire completă
        center_hands = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=120.0)
        self.scene.add(center_hands, pose=np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.4],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Lumină de SUS pentru mâini - reliefează articulațiile
        top_hands = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=110.0)
        self.scene.add(top_hands, pose=np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 1.35],
            [0.0, 0.0, 1.0, 0.95],
            [0.0, 0.0, 0.0, 1.0]
        ]))
        
        # === CORP - iluminare MINIMĂ pentru a nu distrage atenția de la mâini ===
        body_spot = pyrender.SpotLight(
            color=[1.0, 1.0, 1.0],
            intensity=50.0,  # Redus - focusul e pe mâini
            innerConeAngle=np.pi/6,
            outerConeAngle=np.pi/2
        )
        self.scene.add(body_spot, pose=np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.8],
            [0.0, 0.0, 1.0, 1.8],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        # Lumini pentru brațe - moderate pentru a arăta contextul gesturilor
        left_arm = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=60.0)
        self.scene.add(left_arm, pose=np.array([
            [1.0, 0.0, 0.0, -0.6],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))

        right_arm = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=60.0)
        self.scene.add(right_arm, pose=np.array([
            [1.0, 0.0, 0.0, 0.6],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0]
        ]))
        
    def smplx_params_to_mesh(self, smplx_params):
        with torch.no_grad():
            params_tensor = torch.FloatTensor(smplx_params).unsqueeze(0).to(device)
            body_params = {}
            num_params = params_tensor.shape[1]

            # Parametrii obligatorii (Global Orient, Body Pose)
            body_params['global_orient'] = params_tensor[:, :3] if num_params >= 3 else torch.zeros(1, 3).to(device)
            body_params['body_pose'] = params_tensor[:, 3:66] if num_params >= 66 else torch.zeros(1, 63).to(device)
            
            # Parametrii mâinilor
            body_params['left_hand_pose'] = params_tensor[:, 66:111] if num_params >= 111 else torch.zeros(1, 45).to(device)
            body_params['right_hand_pose'] = params_tensor[:, 111:156] if num_params >= 156 else torch.zeros(1, 45).to(device)
            
            # Parametrii feței (Jaw, Eyes)
            body_params['jaw_pose'] = params_tensor[:, 156:159] if num_params >= 159 else torch.zeros(1, 3).to(device)
            body_params['leye_pose'] = params_tensor[:, 159:162] if num_params >= 162 else torch.zeros(1, 3).to(device)
            body_params['reye_pose'] = params_tensor[:, 162:165] if num_params >= 165 else torch.zeros(1, 3).to(device)
            
            # Parametrii de formă (Shape) și Expresie
            if num_params >= 185:
                 body_params['betas'] = params_tensor[:, 165:175] 
                 body_params['expression'] = params_tensor[:, 175:185] 
            elif num_params == 169:
                 # Presupunem 4 betas la finalul structurii de 169 și completăm cu 6 zerouri
                 body_params['betas'] = torch.cat([params_tensor[:, 165:169], torch.zeros(1, 6).to(device)], dim=1)
                 body_params['expression'] = torch.zeros(1, 10).to(device)
            else:
                 body_params['betas'] = torch.zeros(1, 10).to(device)
                 body_params['expression'] = torch.zeros(1, 10).to(device)

            # Generează mesh
            output = self.smplx_model(**body_params)
            vertices = output.vertices[0].cpu().numpy()
            
            return vertices
    
    def add_smplx_to_scene(self, smplx_params):
        vertices = self.smplx_params_to_mesh(smplx_params)
        faces = self.smplx_model.faces
        
        # Rotim mesh-ul cu 180 grade pe axa X pentru a-l întoarce cu capul în sus
        rotation_matrix = trimesh.transformations.rotation_matrix(
            angle=np.pi,  # 180 grade
            direction=[1, 0, 0],  # Axa X
            point=[0, 0, 0]
        )
        
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh.apply_transform(rotation_matrix)
        
        # Calculează normale pentru iluminare mai bună
        mesh.vertex_normals
        
        material = self.create_skin_material()
        render_mesh = pyrender.Mesh.from_trimesh(
            mesh, 
            material=material, 
            smooth=True  # Asigură shading neted
        )
        
        self.scene.add(render_mesh)
    
    def setup_camera(self, distance=2.0):
        """Cameră OPTIMIZATĂ pentru limbaj semnale - FOCUS pe MÂINI"""
        camera = pyrender.PerspectiveCamera(
            yfov=np.pi / 2.5,  # Câmp vizual LARG pentru gesturi complete
            aspectRatio=self.width/self.height
        )

        # Cameră frontală centrată pentru vizibilitate MAXIMĂ a gesturilor
        camera_pose = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.40],  # Poziționată ușor sus pentru a vedea fața și mâinile
            [0.0, 0.0, 1.0, distance],  # Mai aproape pentru detalii
            [0.0, 0.0, 0.0, 1.0]
        ])

        self.scene.add(camera, pose=camera_pose)
    
    def render_frame(self):
        """Randează frame cu claritate MAXIMĂ - FĂRĂ umbre întunecate"""
        # Flag-uri pentru randare ULTRA-CLARĂ - FĂRĂ UMBRE pentru claritate maximă
        flags = (pyrender.RenderFlags.ALL_SOLID |             # Toate mesh-urile solide
                 pyrender.RenderFlags.VERTEX_NORMALS |        # Normale vertex pentru smooth shading
                 pyrender.RenderFlags.FLAT)                   # Flat shading pentru claritate

        color, depth = self.renderer.render(self.scene, flags=flags)

        # Post-procesare AGRESIVĂ pentru claritate EXTREMĂ
        color = self.enhance_contrast(color)

        return color
    
    def enhance_contrast(self, image):
        """Post-procesare cu CONTUR NEGRU pentru mâini și degete - vizibilitate MAXIMĂ"""
        # Convertește la float
        img_float = image.astype(np.float32) / 255.0

        # Contrast MODERAT pentru a păstra detaliile fine ale degetelor
        contrast_factor = 1.30
        img_float = (img_float - 0.5) * contrast_factor + 0.5

        # Luminozitate moderată - mâinile sunt deja foarte luminate
        brightness_factor = 1.10
        img_float = img_float * brightness_factor

        # Sharpening FOCUSAT pentru detalii mâini
        img_uint8 = np.clip(img_float * 255, 0, 255).astype(np.uint8)

        # Kernel de sharpening pentru detalii fine (degete, articulații)
        kernel_sharp = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ])
        img_sharp = cv2.filter2D(img_uint8, -1, kernel_sharp)

        # Mix 60% sharp pentru claritate fără artefacte
        img_enhanced = cv2.addWeighted(img_uint8, 0.4, img_sharp, 0.6, 0)

        # Saturație crescută pentru a face mâinile să iasă în evidență
        img_hsv = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2HSV).astype(np.float32)
        img_hsv[:, :, 1] = np.clip(img_hsv[:, :, 1] * 1.25, 0, 255)  # Saturație moderată
        img_hsv[:, :, 2] = np.clip(img_hsv[:, :, 2] * 1.05, 0, 255)  # Value ușor crescut
        img_enhanced = cv2.cvtColor(img_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

        # ========================================================================
        # === DETECTARE CONTUR NEGRU DOAR pentru MÂINI (zone luminoase) ===
        # === Focus EXCLUSIV pe mâini pentru vizibilitate gesturilor ===
        # ========================================================================

        # Convertește la grayscale pentru detectare
        gray = cv2.cvtColor(img_enhanced, cv2.COLOR_RGB2GRAY)

        # DETECTARE MÂINI bazată pe luminozitate (mâinile sunt foarte luminate)
        # Mâinile au culoarea [1.0, 0.95, 0.85] = foarte deschis
        # Prag pentru a selecta DOAR zonele foarte luminoase (mâinile)
        _, hands_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # Curăță masca - elimină zgomotul
        kernel_morph = np.ones((3, 3), np.uint8)
        hands_mask = cv2.morphologyEx(hands_mask, cv2.MORPH_CLOSE, kernel_morph)
        hands_mask = cv2.morphologyEx(hands_mask, cv2.MORPH_OPEN, kernel_morph)

        # Detectare margini DOAR în zonele mâinilor
        # Sobel pentru contururi organice
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        edges_sobel = np.sqrt(sobelx**2 + sobely**2)
        edges_sobel = np.clip(edges_sobel, 0, 255).astype(np.uint8)

        # Canny pentru detalii fine (degete, articulații)
        edges_canny = cv2.Canny(gray, 20, 80)

        # Combină detectările
        edges = cv2.addWeighted(edges_sobel, 0.7, edges_canny, 0.3, 0)

        # APLICĂ MASCA - păstrează DOAR contururile din zonele mâinilor
        edges_hands_only = cv2.bitwise_and(edges, edges, mask=hands_mask)

        # Dilată contururile pentru a fi MAI GROASE și FOARTE VIZIBILE
        kernel_dilate = np.ones((3, 3), np.uint8)
        edges_thick = cv2.dilate(edges_hands_only, kernel_dilate, iterations=2)

        # Prag pentru contururi clare
        _, edges_binary = cv2.threshold(edges_thick, 30, 255, cv2.THRESH_BINARY)

        # Crează un layer de contur negru
        # Unde avem margini, punem NEGRU (0), altfel păstrăm originalul (255)
        contour_layer = np.zeros_like(img_enhanced)

        # Aplică conturul negru DOAR pe marginile detectate
        for i in range(3):  # RGB channels
            contour_layer[:, :, i] = np.where(edges_binary > 0, 0, 255)

        # Combină imaginea originală cu conturul negru
        # Unde edges_binary > 0, punem NEGRU; altfel păstrăm originalul
        img_final = np.copy(img_enhanced)
        mask_3channel = np.stack([edges_binary] * 3, axis=-1) > 0
        img_final[mask_3channel] = 0  # NEGRU pe contururi

        return img_final
    
    def cleanup(self):
        self.renderer.delete()


def enhance_existing_video(pkl_file_path, output_path=None):
    print(f"\n{'='*60}")
    print(f"ÎMBUNĂTĂȚIRE AVATAR DE ÎNALTĂ CALITATE (HD)")
    print(f"{'='*60}\n")
    print(f"Încarcă date din: {pkl_file_path}")
    
    try:
        # Încearcă mai întâi cu torch.load pentru a gestiona tensori salvați pe CUDA
        try:
            data = torch.load(pkl_file_path, map_location=torch.device('cpu'), weights_only=False)
        except:
            # Dacă torch.load eșuează, încearcă cu pickle standard
            with open(pkl_file_path, 'rb') as f:
                # Patch pickle pentru a gestiona torch tensori salvați pe CUDA
                class CPU_Unpickler(pickle.Unpickler):
                    def find_class(self, module, name):
                        if module == 'torch.storage' and name == '_load_from_bytes':
                            return lambda b: torch.load(io.BytesIO(b), map_location='cpu', weights_only=False)
                        return super().find_class(module, name)

                data = CPU_Unpickler(f).load()
                # Dacă data este un dict cu tensori torch, mută-i pe CPU
                if hasattr(data, 'keys'):
                    for key in list(data.keys()):
                        if torch.is_tensor(data[key]):
                            data[key] = data[key].cpu()
    except FileNotFoundError:
        print(f"EROARE FATALĂ: Fișierul PKL nu a fost găsit: {pkl_file_path}")
        return
    except KeyError:
        print(f"EROARE: Fișierul PKL nu conține cheia 'smplx'. Asigură-te că este un fișier de parametri SMPL-X valid.")
        return
        
    print(f"✓ Date încărcate")
    
    all_smplx_params = data['smplx']
    total_frames = len(all_smplx_params)
    
    print(f"  - Frame-uri: {total_frames}")
    print(f"  - Parametri SMPL-X per frame: {all_smplx_params.shape[1]}")
    
    if output_path is None:
        output_path = pkl_file_path.replace('.pkl', '_enhanced_HD.mp4')
    
    print(f"\nInițializare renderer HD...")
    renderer = EnhancedAvatarRenderer(
        width=1920, 
        height=1080,
    )
    
    print(f"\nProcesare {total_frames} frame-uri...")
    frames = []
    
    for frame_idx in range(total_frames):
        renderer.create_scene()
        renderer.setup_professional_lighting()
        renderer.setup_camera(distance=2.0)  # Mai aproape pentru mâini mari și clare

        smplx_params = all_smplx_params[frame_idx]

        renderer.add_smplx_to_scene(smplx_params)
        
        color = renderer.render_frame()
        frames.append(color)
        
        if frame_idx % 10 == 0 or frame_idx == total_frames - 1:
            progress = (frame_idx + 1) / total_frames * 100
            print(f"  Progres: {frame_idx + 1}/{total_frames} ({progress:.1f}%)")
    
    print(f"\n{'='*60}")
    print(f"Salvare video HD: {output_path}")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (renderer.width, renderer.height))
    
    for frame in frames:
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    out.release()
    renderer.cleanup()
    
    print(f"✓ Video îmbunătățit salvat la: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("Utilizare: python enhance_avatar.py <cale_fisier.pkl>")
        print("\nExemplu:")
        print('  python enhance_avatar.py "calea/completa/catre/fisier_valid.pkl"')
        sys.exit(1)
    
    pkl_file = sys.argv[1]
    
    enhance_existing_video(pkl_file)