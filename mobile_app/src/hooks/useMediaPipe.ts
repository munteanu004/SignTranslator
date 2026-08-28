






declare global {
  interface Window {
    Holistic: any;
    Camera: any;
    __EXPO_NATIVE_CONTAINER__?: boolean;
  }
}

interface NormalizedLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

export type KeypointFrame = number[][]; 

type CleanupFn = () => void;

export function isExpoWebViewContext(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  const win = window as any;
  const userAgent = (typeof navigator !== 'undefined' ? navigator.userAgent || '' : '').toLowerCase();
  const referrer = (typeof document !== 'undefined' ? document.referrer || '' : '').toLowerCase();

  return Boolean(
    win.__EXPO_NATIVE_CONTAINER__ === true ||
    win.ReactNativeWebView ||
    userAgent.includes(' expo') ||
    userAgent.includes('expo/') ||
    userAgent.includes('; wv') ||
    (userAgent.includes('version/') && userAgent.includes('chrome/') && userAgent.includes('mobile safari/')) ||
    referrer.startsWith('android-app://')
  );
}

function getCameraSupportError(): string | null {
  if (typeof window === 'undefined') {
    return 'Camera nu este disponibila in acest mediu.';
  }

  if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'INSECURE_CONTEXT';
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    return 'Browserul nu expune accesul la camera. Incearca in Chrome sau Safari.';
  }

  if (!window.Holistic || !window.Camera) {
    return 'Scripturile MediaPipe nu au fost incarcate. Reincarca pagina.';
  }

  return null;
}





export function extractKeypoints(results: any): KeypointFrame {
  const joints: number[][] = [];

  
  for (let i = 0; i < 33; i++) {
    if (results.poseLandmarks && results.poseLandmarks[i]) {
      const lm = results.poseLandmarks[i];
      joints.push([lm.x, lm.y, lm.z || 0]);
    } else {
      joints.push([0, 0, 0]);
    }
  }

  
  for (let i = 0; i < 21; i++) {
    if (results.leftHandLandmarks && results.leftHandLandmarks[i]) {
      const lm = results.leftHandLandmarks[i];
      joints.push([lm.x, lm.y, lm.z || 0]);
    } else {
      joints.push([0, 0, 0]);
    }
  }

  
  for (let i = 0; i < 21; i++) {
    if (results.rightHandLandmarks && results.rightHandLandmarks[i]) {
      const lm = results.rightHandLandmarks[i];
      joints.push([lm.x, lm.y, lm.z || 0]);
    } else {
      joints.push([0, 0, 0]);
    }
  }

  return joints; 
}

export type RawHandLandmarks = [number, number][];





export async function initHolistic(
  videoElement: HTMLVideoElement,
  onFrame: (keypoints: KeypointFrame) => void,
  onRawLandmarks?: (left: RawHandLandmarks, right: RawHandLandmarks) => void,
): Promise<CleanupFn> {
  const supportError = getCameraSupportError();
  if (supportError) {
    throw new Error(supportError);
  }

  
  try {
    const testStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    testStream.getTracks().forEach(t => t.stop());
  } catch (err: any) {
    const name: string = err?.name || '';
    if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
      throw new Error('PERMISSION_DENIED');
    }
    if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
      throw new Error('NO_CAMERA');
    }
    throw new Error(err?.message || 'Camera access failed');
  }

  
  const origAlert = window.alert;
  window.alert = () => {};

  let camera: any;
  let holistic: any;
  
  let destroyed = false;

  try {
    holistic = new window.Holistic({
      locateFile: (file: string) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`,
    });

    holistic.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    holistic.onResults((results: any) => {
      if (destroyed) return;
      const kp = extractKeypoints(results);
      onFrame(kp);
      if (onRawLandmarks) {
        const left: RawHandLandmarks = results.leftHandLandmarks
          ? results.leftHandLandmarks.map((lm: any) => [lm.x, lm.y] as [number, number])
          : [];
        const right: RawHandLandmarks = results.rightHandLandmarks
          ? results.rightHandLandmarks.map((lm: any) => [lm.x, lm.y] as [number, number])
          : [];
        onRawLandmarks(left, right);
      }
    });

    camera = new window.Camera(videoElement, {
      onFrame: async () => {
        if (destroyed) return;
        try {
          await holistic.send({ image: videoElement });
        } catch {
          
        }
      },
      width: 640,
      height: 480,
    });

    await Promise.resolve(camera.start());
  } finally {
    window.alert = origAlert;
  }

  return () => {
    destroyed = true;
    try { camera?.stop(); } catch {}
    
    setTimeout(() => { try { holistic?.close(); } catch {} }, 200);
  };
}
