import os
import sys
import numpy as np
import cv2
import warnings 
import re 
import torch
import copy
import trimesh
import pickle
import json
import pandas as pd
from tqdm import tqdm
from argparse import ArgumentParser

# ==============================================================================
# 1. ROBUSTIZAREA INIȚIALIZĂRII PYRENDER ȘI A MEDIULUI
# ==============================================================================
# Încercăm diferite backend-uri pentru randarea headless
BACKENDS = ['egl', 'osmesa', 'angle']
pyrender_loaded = False
for backend in BACKENDS:
    try:
        os.environ['PYOPENGL_PLATFORM'] = backend
        import pyrender
        pyrender_loaded = True
        print(f"Folosesc backend-ul {backend} pentru pyrender")
        break
    except Exception:
        print(f"Backend-ul {backend} nu este disponibil. Încerc următorul.")
        continue

if not pyrender_loaded:
    warnings.warn("AVERTISMENT: Nu s-a putut încărca pyrender cu niciun backend (egl/osmesa/angle). Randarea 3D poate eșua în medii headless.")

# Setări generale
torch.manual_seed(3407)
device = torch.device('cpu') # Forțăm CPU

# Asigurăm că importurile pachetelor funcționează indiferent de CWD
_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_pkg_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Importuri specifice (necesită structura de director sign_avatars)
try:
    from sign_avatars.common.utils.human_models import smpl_x
except ImportError as e:
    warnings.warn(f"AVERTISMENT: Nu s-a putut importa modulul SMPL-X din structura așteptată (sign_avatars.common.utils.human_models): {e}")
    class MockSmplX:
        joint_idx = list(range(100))
        root_joint_idx = 0
        face = np.array([[0, 1, 2], [3, 4, 5]])
        layer = {'neutral': lambda **kwargs: type('MockLayer', (), {'to': lambda x: x})()}
    
    if 'smpl_x' not in locals():
        smpl_x = MockSmplX()

print('Inițializare...')

# ==============================================================================
# 2. PARAMETRI ȘI ÎNCĂRCARE DATE
# ==============================================================================
predefined_height, predefined_width = 720, 1280
pred_focals = [14921.82254791, 14921.82254791]
pred_princpts = [620.60418701, 413.40108109]
input_body_shape = (256, 192)
output_hm_shape = (16, 16, 12)
focal = (5000, 5000)
princpt = (input_body_shape[1] / 2, input_body_shape[0] / 2)

# Încărcare date text
text_dict = {}
try:
    with open(os.path.join(_pkg_dir, 'datasets', 'hamnosys2motion', 'data.json'), 'r') as f:
        hamnosys_text_list = json.load(f)
    for i in hamnosys_text_list.keys():
        text_dict[i] = hamnosys_text_list[i]['hamnosys_text']
except Exception as e:
    warnings.warn(f"Avertisment la încărcarea data.json: {e}")

try:
    csv_file_path = os.path.join(_pkg_dir, 'datasets', 'language2motion', 'text', 'how2sign_realigned_train.csv')
    text_all = pd.read_csv(csv_file_path, sep='\t', names=["VIDEO_ID", "VIDEO_NAME", "SENTENCE_ID", "SENTENCE_NAME", "START_REALIGNED","END_REALIGNED","SENTENCE"])
    sentence_name_all = np.array(text_all["SENTENCE_NAME"])
    text_all = np.array(text_all["SENTENCE"])
    for idx, i in enumerate(sentence_name_all):
        text_dict[i] = text_all[idx]
except Exception as e:
    warnings.warn(f"Avertisment la încărcarea CSV: {e}")

# Inițializare model SMPL-X
smplx_layer = copy.deepcopy(smpl_x.layer['neutral']).to(device)

# Încărcare imagine fundal
try:
    background = cv2.imread(os.path.join(_pkg_dir, 'assets', 'blender.png'))
    if background is None:
        warnings.warn("Avertisment: Nu s-a putut încărca imaginea de fundal! Folosesc fundal negru.")
        background = np.zeros((predefined_height, predefined_width, 3), dtype=np.uint8)
except Exception as e:
    warnings.warn(f"Eroare la încărcarea imaginii de fundal: {e}. Folosesc fundal negru.")
    background = np.zeros((predefined_height, predefined_width, 3), dtype=np.uint8)

# Parametri text
org = (10, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 1
color = (255, 255, 255)
thickness = 2

print('Inițializare completă.')

# ==============================================================================
# 3. FUNCȚII DE UTILITATE
# ==============================================================================

def put_text_with_newline(image, text, org, font, font_scale, color, thickness, line_type=cv2.LINE_AA):
    """Funcție îmbunătățită pentru afișarea textului pe mai multe linii"""
    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_height = text_size[1] * 1.2
    img_width = image.shape[1]
    x, y = org
    
    max_text_width = img_width / 3
    lines = []
    line = ""
    for word in text.split(" "):
        current_line_size, _ = cv2.getTextSize(line + (" " if line else "") + word, font, font_scale, thickness)
        if current_line_size[0] > max_text_width and line:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    
    for i, line in enumerate(lines):
        y_offset = int(i * text_height)
        cv2.putText(image, line, (x, int(y + y_offset)), font, font_scale, color, thickness, line_type)

def get_img_list(folder_name, from_url=False):
    """Obține lista de cadre dintr-un video"""
    if from_url:
        print('Versiunea curentă nu suportă generare online. Descarcă videourile.')
        return []
    
    if 'args' not in globals() or not getattr(globals()['args'], 'video_path', None):
         warnings.warn("AVERTISMENT: args.video_path nu este setat. Nu pot încărca video-ul sursă.")
         return []

    video_path = os.path.join(globals()['args'].video_path, folder_name + '.mp4')
    if not os.path.exists(video_path):
        print(f"Eroare: Nu s-a găsit video-ul {video_path}")
        return []
        
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Eroare: Nu s-a putut deschide video-ul {folder_name}")
        return []
        
    frames = []
    while True:
        ret, frame = video.read()
        if not ret:
            break
        frames.append(frame)
    
    video.release()
    return frames

def get_coord(root_pose, body_pose, lhand_pose, rhand_pose, jaw_pose, shape, expr, cam_trans, 
              mode='test', zero_global=False, mesh=False):
    """Calculează coordonatele 3D și proiecțiile 2D"""
    batch_size = root_pose.shape[0]
    zero_pose = torch.zeros((1, 3)).float().to(device).repeat(batch_size, 1)
    
    try:
        if not zero_global:
            output = smplx_layer(
                betas=shape.to(device),
                body_pose=body_pose.to(device),
                global_orient=root_pose.to(device),
                right_hand_pose=rhand_pose.to(device),
                left_hand_pose=lhand_pose.to(device),
                jaw_pose=jaw_pose.to(device),
                leye_pose=zero_pose,
                reye_pose=zero_pose,
                expression=expr.to(device)
            )
        else:
            raise ValueError("zero_global nu este suportat")
    except Exception as e:
        print(f"Eroare la generarea mesh-ului: {e}")
        raise

    mesh_cam = output.vertices
    joint_cam = output.joints[:, smpl_x.joint_idx, :]
    
    if mesh:
        render_mesh_cam = mesh_cam + cam_trans.to(device)[:, None, :]
        return render_mesh_cam
    
    x = (joint_cam[:, :, 0] + cam_trans.to(device)[:, None, 0]) / (joint_cam[:, :, 2] + cam_trans.to(device)[:, None, 2] + 1e-4) * focal[0] + princpt[0]
    y = (joint_cam[:, :, 1] + cam_trans.to(device)[:, None, 1]) / (joint_cam[:, :, 2] + cam_trans.to(device)[:, None, 2] + 1e-4) * focal[1] + princpt[1]
    x = x / input_body_shape[1] * output_hm_shape[2]
    y = y / input_body_shape[0] * output_hm_shape[1]
    joint_proj = torch.stack((x, y), 2)
    return joint_proj

import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')  # Backend non-GUI
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def render_simple(img, mesh, face, cam_param):
    """
    Renderează mesh-ul 3D folosind matplotlib (funcționează pe Windows fără PyOpenGL)
    """
    try:
        # Creează figura matplotlib
        fig = plt.figure(figsize=(img.shape[1]/100, img.shape[0]/100), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        
        # Extrage vertices și creează fețele mesh-ului
        vertices = mesh
        faces_vertices = vertices[face]
        
        # Creează colecția de poligoane 3D
        mesh_collection = Poly3DCollection(
            faces_vertices,
            alpha=0.9,
            facecolor='lightblue',
            edgecolor='none',
            linewidths=0
        )
        ax.add_collection3d(mesh_collection)
        
        # Setează limitele axelor
        x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
        y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
        z_min, z_max = vertices[:, 2].min(), vertices[:, 2].max()
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_zlim(z_min, z_max)
        
        # Ascunde axele pentru aspect curat
        ax.set_axis_off()
        ax.view_init(elev=10, azim=-90)
        
        # Setează culoarea de fundal
        ax.set_facecolor((0, 0, 0))
        fig.patch.set_facecolor('black')
        
        # Renderează în buffer
        fig.canvas.draw()
        
        # Convertește în numpy array
        data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        
        plt.close(fig)
        
        # Redimensionează la dimensiunea imaginii originale
        if data.shape[:2] != img.shape[:2]:
            data = cv2.resize(data, (img.shape[1], img.shape[0]))
        
        # Combină cu imaginea de fundal (overlay simplu)
        # Detectează pixelii care nu sunt negri din rendering
        mask = np.any(data > 10, axis=2)
        
        img_out = img.copy()
        img_out[mask] = data[mask]
        
        return img_out.astype(np.uint8)
        
    except Exception as e:
        print(f"❌ EROARE la rendering matplotlib: {e}")
        import traceback
        traceback.print_exc()
        return img.astype(np.uint8)


def render_projection(img, mesh, face, cam_param):
    """
    Renderare simplă prin proiecție 2D (cea mai rapidă și mai sigură)
    """
    try:
        focal = cam_param['focal']
        princpt = cam_param['princpt']
        
        # Proiectează vertices-urile pe planul 2D
        z = mesh[:, 2]
        z[z == 0] = 1e-5  # Evită diviziunea prin zero
        
        x_2d = (mesh[:, 0] / z * focal[0] + princpt[0]).astype(int)
        y_2d = (mesh[:, 1] / z * focal[1] + princpt[1]).astype(int)
        
        # Creează imagine overlay
        overlay = img.copy()
        
        # Desenează fețele mesh-ului
        for triangle in face:
            pts = np.array([
                [x_2d[triangle[0]], y_2d[triangle[0]]],
                [x_2d[triangle[1]], y_2d[triangle[1]]],
                [x_2d[triangle[2]], y_2d[triangle[2]]]
            ], dtype=np.int32)
            
            # Verifică dacă punctele sunt în limitele imaginii
            if (pts[:, 0].min() >= 0 and pts[:, 0].max() < img.shape[1] and
                pts[:, 1].min() >= 0 and pts[:, 1].max() < img.shape[0]):
                cv2.fillPoly(overlay, [pts], color=(108, 184, 204))
        
        # Blend cu imaginea originală
        alpha = 0.7
        img_out = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)
        
        return img_out.astype(np.uint8)
        
    except Exception as e:
        print(f"❌ EROARE la rendering prin proiecție: {e}")
        import traceback
        traceback.print_exc()
        return img.astype(np.uint8)
    

# Funcție wrapper care încearcă ambele metode
def render(img, mesh, face, cam_param):
    """
    Funcție de rendering robustă care încearcă mai multe metode
    """
    # Încearcă mai întâi proiecția simplă (cea mai rapidă)
    try:
        return render_projection(img, mesh, face, cam_param)
    except Exception as e:
        print(f"⚠️ Proiecția simplă a eșuat, încerc matplotlib: {e}")
        try:
            return render_simple(img, mesh, face, cam_param)
        except Exception as e2:
            print(f"❌ Ambele metode au eșuat: {e2}")
            return img.astype(np.uint8)
# ==============================================================================
# 4. FUNCȚIA PRINCIPALĂ DE PROCESARE
# ==============================================================================

def process_single_video(file_name, result_path):
    """Procesează un singur video"""
    global args
    print(f'Procesez: {file_name}')
    video_name = os.path.basename(file_name).split('.pkl')[0]
    
    # Încărcare date
    results_dict = None
    try:
        with open(file_name, 'rb') as f:
            results_dict = torch.load(f, map_location=torch.device('cpu'), weights_only=False)
    except Exception as e:
        warnings.warn(f"Eroare la încărcarea cu torch.load(): {e}. Încerc pickle...")
        try:
            with open(file_name, 'rb') as f:
                results_dict = pickle.load(f)
        except Exception as e2:
            raise RuntimeError(f"FATAL: Nu s-a putut încărca fișierul {file_name}. Erori: {e}, {e2}")

    focals = results_dict.get('focal', pred_focals)
    princpts = results_dict.get('princpt', pred_princpts)
    height = results_dict.get('height', predefined_height)
    width = results_dict.get('width', predefined_width)
    
    if 'smplx' not in results_dict:
        raise RuntimeError(f"Fișierul {file_name} nu conține date SMPL-X necesare!")
    
    all_pose = results_dict['smplx']
    try:
        all_pose = torch.tensor(all_pose, dtype=torch.float32).to(device)
    except Exception as e:
        raise RuntimeError(f"Eroare la conversia datelor SMPL-X în tensor: {e}")

    if all_pose.numel() == 0:
        raise RuntimeError(f"Date SMPL-X goale în {file_name}")

    # Separare pose-uri
    g = all_pose[:, :3]
    b = all_pose[:, 3:66]
    l = all_pose[:, 66:111]
    r = all_pose[:, 111:156]
    j = all_pose[:, 156:159]
    s = all_pose[:, 159:169]
    exp = all_pose[:, 169:179]
    cam_trans = all_pose[:, 179:182]

    # Generare mesh-uri
    try:
        meshes = get_coord(g, b, l, r, j, s, exp, cam_trans, mesh=True).cpu().numpy()
    except Exception as e:
        raise RuntimeError(f"Eroare la generarea mesh-urilor: {e}")

    total_valid_index = results_dict.get('total_valid_index', range(len(meshes)))
    bar_iterable = tqdm(total_valid_index) if os.path.isdir(args.pkl_file_path) else total_valid_index
    
    # Încărcare imagini pentru overlay
    raw_img_list = []
    if args.overlay:
        raw_img_list = get_img_list(video_name)
        if not raw_img_list:
            warnings.warn("AVERTISMENT: Overlay solicitat, dar nu s-a putut încărca video-ul sursă. Trec la randare pe fundal static.")
            args.overlay = False

    # Procesare text pentru afișare
    video_name_cleaned = video_name.lstrip('_-')
    match = re.search(r'([a-zA-Z0-9_-]+)_\d+-\d+', video_name_cleaned)
    video_id_for_text = match.group(1).replace('/', '') if match else video_name_cleaned.replace('/', '')
    text = text_dict.get(video_id_for_text, "Text indisponibil")

    # Procesare frame-uri și colectare
    img_list = []
    size = (predefined_width, predefined_height) 

    for idx, index in enumerate(bar_iterable):
        if idx >= len(meshes):
            warnings.warn(f"Indexul mesh-ului {idx} depășește lungimea ({len(meshes)}). Sărit.")
            continue

        try:
            if args.overlay and index < len(raw_img_list):
                raw_img = raw_img_list[index]
                img = render(raw_img.copy(), meshes[idx], smpl_x.face, 
                             {'focal': focals, 'princpt': princpts})
                img = np.array(np.concatenate((raw_img, img), axis=1), dtype=np.uint8)
                size = (2 * width, height)
            else:
                img = render(background.copy(), meshes[idx], smpl_x.face,
                             {'focal': pred_focals, 'princpt': pred_princpts})
                size = (predefined_width, predefined_height)
            
            put_text_with_newline(img, text, org, font, font_scale, color, thickness)
            img_list.append(img)
            
        except Exception as e:
            warnings.warn(f"Eroare la procesarea frame-ului {idx} ({index}): {e}")
            continue
    
    if not img_list:
        print(f"Avertisment: Nu au fost generate cadre pentru {video_name}. Sări peste salvare.")
        return

    # ========================================================================
    # SALVARE CADRE CA IMAGINI PNG (Metoda cea mai sigură)
    # ========================================================================
    print(f"\n📁 Salvez {len(img_list)} cadre ca imagini PNG...")
    image_output_dir = os.path.join(result_path, f'{video_name}_frames')
    os.makedirs(image_output_dir, exist_ok=True)
    
    for i, frame in enumerate(tqdm(img_list, desc="Salvare cadre")):
        frame_path = os.path.join(image_output_dir, f'frame_{i:04d}.png')
        success = cv2.imwrite(frame_path, frame)
        if not success:
            warnings.warn(f"Eroare la salvarea cadrului {i}")
    
    print(f"✓ Cadre salvate în: {image_output_dir}")
    print(f"\n🎬 Pentru a crea video-ul, rulează:")
    print(f"   ffmpeg -framerate 24 -i \"{image_output_dir}\\frame_%04d.png\" -c:v libx264 -pix_fmt yuv420p \"{result_path}\\{video_name}.mp4\"")

# ==============================================================================
# 5. EXECUȚIE MAIN
# ==============================================================================

if __name__ == "__main__":
    parser = ArgumentParser(description='Vizualizare SMPL-X pentru traducere în limbajul semnelor')
    
    parser.add_argument(
        '--pkl_file_path',
        type=str,
        required=True,
        help='Calea către fișierul .pkl sau directorul cu fișiere .pkl'
    )
    
    parser.add_argument(
        '--video_path',
        type=str,
        default=None,
        help='Calea către video-urile sursă (pentru overlay)'
    )
    
    parser.add_argument(
        '--overlay',
        action='store_true',
        help='Activează modul overlay pentru randare'
    )

    args = parser.parse_args()

    result_path = './render_results_overlay/' if args.overlay else './render_results/'
    os.makedirs(result_path, exist_ok=True)

    if os.path.isdir(args.pkl_file_path):
        print(f"Procesare director: {args.pkl_file_path}")
        for file_name in tqdm(os.listdir(args.pkl_file_path)):
            if file_name.endswith(('.pkl', '.pt')):
                try:
                    pkl_path = os.path.join(args.pkl_file_path, file_name)
                    process_single_video(pkl_path, result_path)
                except Exception as e:
                    print(f"Eroare la procesarea {file_name}: {e}")
    else:
        print(f"Procesare fișier: {args.pkl_file_path}")
        try:
            process_single_video(args.pkl_file_path, result_path)
        except Exception as e:
            print(f"Eroare la procesarea fișierului: {e}")