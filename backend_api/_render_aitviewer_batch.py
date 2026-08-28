"""Long-lived aitviewer render server. Started once by api_server, stays running.
Protocol (line-delimited JSON via stdin/stdout):
  IN:  {"poses": [[...], ...], "jpeg_quality": 88}
  OUT: {"uris": ["data:image/jpeg;base64,...", ...]}
  IN:  {"quit": true}  -> exits
"""
import sys, io, json, base64, math, pickle, numpy as np
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
for p in [
    str(PROJECT_ROOT),
    str(PROJECT_ROOT / "sign_avatars" / "visualizer"),
    str(PROJECT_ROOT / "sign_avatars" / "common" / "utils"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

_MODEL_FILES = PROJECT_ROOT / "sign_avatars" / "common" / "utils" / "human_model_files" / "smplx"

        
_SKIN  = [0.85, 0.70, 0.55, 1.0]                                           
_SHIRT = [0.30, 0.58, 0.90, 1.0]                     
_PANTS = [0.10, 0.20, 0.52, 1.0]                      
_SHOES = [0.08, 0.08, 0.10, 1.0]                     


def build_clothing_colors():
    """Build per-vertex clothing colors using SMPL-X skinning joint weights.

    Each vertex is assigned to the body region whose dominant skinning joint
    belongs to. Face and hand vertex IDs always override to skin color.

    Joint groups:
      skin  — neck(12), head(15), elbows(18,19), wrists(20,21), hands/face(22+)
      shirt — spine1-3(3,6,9), collars(13,14), shoulders(16,17)
      pants — pelvis(0), hips(1,2), knees(4,5), ankles(7,8)
      shoes — feet(10,11)
    """
    npz_data = np.load(str(_MODEL_FILES / "SMPLX_NEUTRAL.npz"))
    W        = npz_data["weights"]                       
    dom      = np.argmax(W, axis=1)                                              

                                                                    
    joint_region = np.zeros(55, dtype=np.int8)                   
    for j in [3, 6, 9, 13, 14, 16, 17]: joint_region[j] = 1          
    for j in [0, 1, 2, 4, 5, 7, 8]:     joint_region[j] = 2          
    for j in [10, 11]:                   joint_region[j] = 3          

    label = joint_region[dom]             

                                                                                 
    face_ids = np.load(str(_MODEL_FILES / "SMPL-X__FLAME_vertex_ids.npy"))
    with open(str(_MODEL_FILES / "MANO_SMPLX_vertex_ids.pkl"), "rb") as f:
        mano = pickle.load(f, encoding="latin1")
    hand_ids = np.concatenate([np.array(mano["left_hand"]), np.array(mano["right_hand"])])
    label[face_ids] = 0
    label[hand_ids] = 0

    colors = np.tile(_SKIN, (len(label), 1)).astype(np.float32)
    colors[label == 1] = _SHIRT
    colors[label == 2] = _PANTS
    colors[label == 3] = _SHOES
    return colors


def main():
    import cv2
    from aitviewer.configuration import CONFIG as C
    from aitviewer.headless import HeadlessRenderer
    from aitviewer.models.smpl import SMPLLayer
    from aitviewer.renderables.smpl import SMPLSequence
    from aitviewer.utils.so3 import aa2rot_numpy

    smplx_models = PROJECT_ROOT / "sign_avatars" / "common" / "utils" / "human_model_files"
    C.smplx_models = str(smplx_models.resolve())
    C.device = "cpu"

    renderer = HeadlessRenderer(size=(512, 512))
    renderer.scene.light_mode = "dark"
    renderer.auto_set_camera_target = False
    renderer.scene.camera.position = np.array([0, 0.92, 1.65])
    renderer.scene.camera.target   = np.array([0, 0.82, 0])
    renderer.auto_set_floor = False
    renderer.scene.floor.enabled   = False
    renderer.scene.origin.enabled  = False
    renderer.shadows_enabled = False

    smpl_layer = SMPLLayer(model_type="smplx", gender="neutral", flat_hand_mean=False, device=C.device)
    rotation = aa2rot_numpy(np.array([1, 0, 0]) * math.pi)
    clothing = build_clothing_colors()

                  
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            print(json.dumps({"error": "bad json"}), flush=True)
            continue

        if data.get("quit"):
            break

        poses = np.asarray(data["poses"], dtype=np.float32)
        jpeg_q = int(data.get("jpeg_quality", 88))

        if poses.ndim != 2 or poses.shape[1] < 156:
            print(json.dumps({"uris": []}), flush=True)
            continue

        T = len(poses)
        seq = SMPLSequence(
            poses_body=poses[:, 3:66],
            poses_root=poses[:, :3],
            poses_left_hand=poses[:, 66:111],
            poses_right_hand=poses[:, 111:156],
            betas=poses[:, 159:169] if poses.shape[1] >= 169 else np.zeros((T, 10), np.float32),
            smpl_layer=smpl_layer,
            color=tuple(_SKIN[:3]) + (1.0,),
            rotation=rotation,
        )
        try:
            seq.mesh_seq.vertex_colors = clothing
        except Exception:
            pass

        renderer.scene.add(seq)
        uris = []
        try:
            for fi in range(T):
                seq.current_frame_id = fi
                pil_img = renderer.get_frame()
                bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                ok, enc = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_q])
                if ok:
                    uris.append("data:image/jpeg;base64," + base64.b64encode(enc.tobytes()).decode("ascii"))
        finally:
            renderer.scene.remove(seq)

        print(json.dumps({"uris": uris}), flush=True)


if __name__ == "__main__":
    main()
