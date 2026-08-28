"""
Extrage keypoints din videoclipurile EXTRA (cele 10,966 care nu sunt in dataset.json).
Ruleaza in paralel cu fine-tuning-ul pe Kaggle.
"""
import os
import json
import time
import numpy as np
import cv2
import mediapipe as mp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RO_DATASET_JSON = os.path.join(SCRIPT_DIR, "ro-sign-language-recognition", "datasets", "processed_dataset", "dataset.json")
RO_VIDEOS_DIR = os.path.join(SCRIPT_DIR, "ro-sign-language-recognition", "datasets", "processed_dataset", "videos")
EXTRA_CACHE_DIR = os.path.join(SCRIPT_DIR, "ro_cache_extra")

NUM_JOINTS = 75


def main():
    os.makedirs(EXTRA_CACHE_DIR, exist_ok=True)

    # Video IDs din dataset.json (cele deja etichetate)
    with open(RO_DATASET_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    labeled_vids = set()
    for e in data:
        for inst in e['instances']:
            labeled_vids.add(inst['video_id'])

    # Gaseste videouri EXTRA (nu sunt in JSON)
    all_mp4 = [f.replace('.mp4', '') for f in os.listdir(RO_VIDEOS_DIR) if f.endswith('.mp4')]
    extra_vids = [(v, os.path.join(RO_VIDEOS_DIR, f"{v}.mp4")) for v in all_mp4 if v not in labeled_vids]

    cached = len([f for f in os.listdir(EXTRA_CACHE_DIR) if f.endswith('.npz')])
    to_process = [(v, vp) for v, vp in extra_vids if not os.path.exists(os.path.join(EXTRA_CACHE_DIR, f"{v}.npz"))]

    print(f"Total videouri extra: {len(extra_vids)}")
    print(f"Deja in cache: {cached}")
    print(f"De procesat: {len(to_process)}")

    if not to_process:
        print("Totul e deja in cache!")
        return

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

        for idx, (vid, vp) in enumerate(to_process):
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

                    if results.pose_landmarks:
                        for i, lm in enumerate(results.pose_landmarks.landmark):
                            if i < 33:
                                j[i] = [lm.x, lm.y, lm.z]
                                v[i] = 1.0

                    if results.left_hand_landmarks:
                        for i, lm in enumerate(results.left_hand_landmarks.landmark):
                            if i < 21:
                                j[33 + i] = [lm.x, lm.y, lm.z]
                                v[33 + i] = 1.0

                    if results.right_hand_landmarks:
                        for i, lm in enumerate(results.right_hand_landmarks.landmark):
                            if i < 21:
                                j[54 + i] = [lm.x, lm.y, lm.z]
                                v[54 + i] = 1.0

                    all_joints.append(j)
                    all_vis.append(v)

                cap.release()

                if all_joints:
                    cp = os.path.join(EXTRA_CACHE_DIR, f"{vid}.npz")
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

            if (idx + 1) % 50 == 0 or idx == len(to_process) - 1:
                elapsed = time.time() - t0
                speed = (idx + 1) / elapsed
                remaining = len(to_process) - idx - 1
                eta = remaining / speed / 60 if speed > 0 else 0
                print(f"[{idx+1}/{len(to_process)}] OK:{ok} Erori:{err} | "
                      f"{speed:.2f} vid/s | ETA: {eta:.0f} min")

    total = len([f for f in os.listdir(EXTRA_CACHE_DIR) if f.endswith('.npz')])
    print(f"\nGATA! Total cache extra: {total}")
    print(f"Timp total: {(time.time()-t0)/60:.1f} minute")


if __name__ == "__main__":
    main()
