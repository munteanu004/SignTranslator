"""
Script de randare avatar folosind metoda SignAvatar
Cu FOCUS pe mâini clare și contur negru pentru vizibilitate maximă
"""

import sys
import io
import os
import numpy as np
import cv2
import torch
import copy
import pickle

# Setare encoding UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import SMPL-X
import importlib.util
module_path = os.path.join(os.path.dirname(__file__), 'common', 'utils', 'human_models.py')
spec = importlib.util.spec_from_file_location("human_models_temp", module_path)
human_models_temp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(human_models_temp)
smpl_x = human_models_temp.SMPLX()

device = torch.device('cpu')
smplx_layer = copy.deepcopy(smpl_x.layer['neutral']).to(device)

# Parametri cameră
focal = (5000, 5000)
princpt = (960, 540)  # Centru pentru 1920x1080


def render_with_hand_outline(img, mesh, face, cam_param):
    """
    Randare cu contur negru DOAR pe mâini (zone luminoase)
    """
    focal = cam_param['focal']
    princpt = cam_param['princpt']

    # Proiectează vertices pe 2D
    z = mesh[:, 2]
    z[z == 0] = 1e-5

    x_2d = (mesh[:, 0] / z * focal[0] + princpt[0]).astype(int)
    y_2d = (mesh[:, 1] / z * focal[1] + princpt[1]).astype(int)

    # Creează o mască pentru mâini (indexuri 5361-7580 pentru mâna stângă, 8245-10464 pentru mâna dreaptă în SMPL-X)
    # Acestea sunt aproximative - mâinile în SMPL-X
    hand_vertices_left = range(5361, 7580)
    hand_vertices_right = range(8245, 10464)

    # Creează overlay
    overlay = img.copy()
    hand_overlay = np.zeros_like(img)
    body_overlay = np.zeros_like(img)

    # Desenează corpul (fără mâini) - culoare normală
    for idx, triangle in enumerate(face):
        # Verifică dacă vreun vertex din triunghi este mână
        is_hand = any(v in hand_vertices_left or v in hand_vertices_right for v in triangle)

        pts = np.array([
            [x_2d[triangle[0]], y_2d[triangle[0]]],
            [x_2d[triangle[1]], y_2d[triangle[1]]],
            [x_2d[triangle[2]], y_2d[triangle[2]]]
        ], dtype=np.int32)

        if (pts[:, 0].min() >= 0 and pts[:, 0].max() < img.shape[1] and
            pts[:, 1].min() >= 0 and pts[:, 1].max() < img.shape[0]):

            if is_hand:
                # Mâini - culoare MULT mai deschisă (aproape alb-galben)
                cv2.fillPoly(hand_overlay, [pts], color=(255, 240, 210))
            else:
                # Corp - culoare normală
                cv2.fillPoly(body_overlay, [pts], color=(200, 150, 130))

    # Combină: corp + mâini
    mask_hands = np.any(hand_overlay > 0, axis=2)
    mask_body = np.any(body_overlay > 0, axis=2)

    result = img.copy()
    result[mask_body] = cv2.addWeighted(body_overlay, 0.85, img, 0.15, 0)[mask_body]
    result[mask_hands] = hand_overlay[mask_hands]

    # ====== DETECTARE CONTUR DOAR PE MÂINI ======
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)

    # Detectare mâini prin threshold (zone foarte luminoase)
    _, hands_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Curățare mască
    kernel = np.ones((3, 3), np.uint8)
    hands_mask = cv2.morphologyEx(hands_mask, cv2.MORPH_CLOSE, kernel)
    hands_mask = cv2.morphologyEx(hands_mask, cv2.MORPH_OPEN, kernel)

    # Detectare margini
    edges_canny = cv2.Canny(gray, 30, 100)
    edges_sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    edges_sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    edges_sobel = np.sqrt(edges_sobel_x**2 + edges_sobel_y**2)
    edges_sobel = np.clip(edges_sobel, 0, 255).astype(np.uint8)

    # Combină
    edges = cv2.addWeighted(edges_canny, 0.4, edges_sobel, 0.6, 0)

    # Aplică masca mâini
    edges_hands = cv2.bitwise_and(edges, edges, mask=hands_mask)

    # Îngroașă contururile
    kernel_dilate = np.ones((3, 3), np.uint8)
    edges_thick = cv2.dilate(edges_hands, kernel_dilate, iterations=2)

    # Aplică contur NEGRU
    _, edges_binary = cv2.threshold(edges_thick, 20, 255, cv2.THRESH_BINARY)
    result[edges_binary > 0] = [0, 0, 0]  # NEGRU

    return result


def process_pkl_file(pkl_path, output_path):
    """Procesează fișier PKL și creează video cu mâini conturate"""
    print(f"\n{'='*60}")
    print(f"RANDARE AVATAR SIGNAVATAR - MÂINI CU CONTUR")
    print(f"{'='*60}\n")
    print(f"Încarcă: {pkl_path}")

    # Încarcă date (cu suport pentru CUDA → CPU)
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

    all_pose = torch.tensor(data['smplx'], dtype=torch.float32).to(device)

    # Separare componente
    g = all_pose[:, :3]
    b = all_pose[:, 3:66]
    l = all_pose[:, 66:111]
    r = all_pose[:, 111:156]
    j = all_pose[:, 156:159]
    s = all_pose[:, 159:169]
    exp = all_pose[:, 169:179]
    cam_trans = all_pose[:, 179:182]

    print(f"✓ Date încărcate: {len(all_pose)} frame-uri")

    # Generare meshuri
    print(f"Generare meshuri 3D...")
    zero_pose = torch.zeros((len(all_pose), 3)).float().to(device)

    output = smplx_layer(
        betas=s,
        body_pose=b,
        global_orient=g,
        right_hand_pose=r,
        left_hand_pose=l,
        jaw_pose=j,
        leye_pose=zero_pose,
        reye_pose=zero_pose,
        expression=exp
    )

    meshes = (output.vertices + cam_trans[:, None, :]).cpu().numpy()

    print(f"✓ {len(meshes)} meshuri generate")

    # Randare frame-uri
    print(f"\nRandare frame-uri cu contur pe mâini...")
    frames = []
    background = np.zeros((1080, 1920, 3), dtype=np.uint8)
    background[:] = [25, 30, 38]  # Fundal întunecat

    for idx, mesh in enumerate(meshes):
        img = render_with_hand_outline(
            background.copy(),
            mesh,
            smpl_x.face,
            {'focal': focal, 'princpt': princpt}
        )
        frames.append(img)

        if idx % 10 == 0 or idx == len(meshes) - 1:
            print(f"  Progres: {idx+1}/{len(meshes)} ({(idx+1)/len(meshes)*100:.1f}%)")

    # Salvare video
    print(f"\nSalvare video: {output_path}")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 30.0, (1920, 1080))

    for frame in frames:
        out.write(frame)

    out.release()
    print(f"✓ Video salvat: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python render_signavatar.py <fisier.pkl>")
        sys.exit(1)

    pkl_file = sys.argv[1]
    output_file = pkl_file.replace('.pkl', '_signavatar_HD.mp4')

    process_pkl_file(pkl_file, output_file)
