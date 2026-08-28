"""
Extrage keypoints din videoclipurile romanesti folosind MediaPipe Holistic.
Ruleaza local pe Windows: python extract_keypoints_local.py

Dupa ce termina, comprima folderul ro_cache/ si incarca-l pe Kaggle ca dataset.
"""
import os
import json
import time
import numpy as np
import cv2
import mediapipe as mp

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RO_DATASET_JSON = os.path.join(SCRIPT_DIR, "ro-sign-language-recognition", "datasets", "processed_dataset", "dataset.json")
RO_VIDEOS_DIR = os.path.join(SCRIPT_DIR, "ro-sign-language-recognition", "datasets", "processed_dataset", "videos")
CACHE_DIR = os.path.join(SCRIPT_DIR, "ro_cache")

NUM_JOINTS = 75  # 33 pose + 21 left hand + 21 right hand


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Load dataset
    print("Incarc dataset.json...")
    with open(RO_DATASET_JSON, 'r', encoding='utf-8') as f:
        ro_data = json.load(f)

    # Collect all video instances
    to_process = []
    for entry in ro_data:
        for inst in entry['instances']:
            vid = inst['video_id']
            vp = os.path.join(RO_VIDEOS_DIR, f"{vid}.mp4")
            cp = os.path.join(CACHE_DIR, f"{vid}.npz")
            if not os.path.exists(cp) and os.path.exists(vp):
                to_process.append((vid, vp, cp))

    cached = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.npz')])
    print(f"De procesat: {len(to_process)} videouri")
    print(f"Deja in cache: {cached}")

    if not to_process:
        print("Totul e deja in cache! Nimic de facut.")
        return

    # Initialize MediaPipe Holistic
    mp_holistic = mp.solutions.holistic
    ok = 0
    err = 0
    t0 = time.time()

    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as holistic:

        for idx, (vid, vp, cp) in enumerate(to_process):
            try:
                cap = cv2.VideoCapture(vp)
                if not cap.isOpened():
                    err += 1
                    continue

                all_joints = []
                all_vis = []

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = holistic.process(rgb)

                    j = np.zeros((NUM_JOINTS, 3), dtype=np.float32)
                    v = np.zeros(NUM_JOINTS, dtype=np.float32)

                    # Pose - 33 landmarks
                    if results.pose_landmarks:
                        for i, lm in enumerate(results.pose_landmarks.landmark):
                            if i < 33:
                                j[i] = [lm.x, lm.y, lm.z]
                                v[i] = 1.0

                    # Left hand - 21 landmarks
                    if results.left_hand_landmarks:
                        for i, lm in enumerate(results.left_hand_landmarks.landmark):
                            if i < 21:
                                j[33 + i] = [lm.x, lm.y, lm.z]
                                v[33 + i] = 1.0

                    # Right hand - 21 landmarks
                    if results.right_hand_landmarks:
                        for i, lm in enumerate(results.right_hand_landmarks.landmark):
                            if i < 21:
                                j[54 + i] = [lm.x, lm.y, lm.z]
                                v[54 + i] = 1.0

                    all_joints.append(j)
                    all_vis.append(v)

                cap.release()

                if all_joints:
                    np.savez_compressed(cp,
                        joints=np.array(all_joints, dtype=np.float32),
                        vis=np.array(all_vis, dtype=np.float32))
                    ok += 1
                else:
                    err += 1

            except Exception as ex:
                err += 1
                if idx < 5:
                    print(f"  Eroare la {vid}: {ex}")

            # Progress every 50 videos
            if (idx + 1) % 50 == 0 or idx == len(to_process) - 1:
                elapsed = time.time() - t0
                speed = (idx + 1) / elapsed
                remaining = len(to_process) - idx - 1
                eta = remaining / speed / 60 if speed > 0 else 0
                print(f"[{idx+1}/{len(to_process)}] OK:{ok} Erori:{err} | "
                      f"{speed:.2f} vid/s | ETA: {eta:.0f} min")

    total = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.npz')])
    print(f"\n{'='*50}")
    print(f"GATA! Total fisiere cache: {total}")
    print(f"Timp total: {(time.time()-t0)/60:.1f} minute")
    print(f"Folder cache: {CACHE_DIR}")
    print(f"\nPasul urmator:")
    print(f"1. Comprima folderul ro_cache/ intr-un ZIP")
    print(f"2. Urca-l pe Kaggle ca dataset nou (ex: 'ro-keypoints-cache')")
    print(f"3. In notebook, seteaza CACHE_DIR la path-ul Kaggle")


if __name__ == "__main__":
    main()
