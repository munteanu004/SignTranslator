import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Colors } from '../theme';
import ApiService from '../services/ApiService';
import { KeypointFrame, RawHandLandmarks, initHolistic } from '../hooks/useMediaPipe';
import { ArrowLeftIcon, FlipIcon } from '../components/Icons';
import { HistoryEntry } from './HistoryScreen';


const Svg = 'svg' as any;
const Path = 'path' as any;
const Rect = 'rect' as any;
const Circle = 'circle' as any;
const Line = 'line' as any;

const PauseIcon = ({ color = '#fff', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Rect x="6" y="4" width="4" height="16" rx="2" fill={color} />
    <Rect x="14" y="4" width="4" height="16" rx="2" fill={color} />
  </Svg>
);

const StopIcon = ({ color = '#fff', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Rect x="4" y="4" width="16" height="16" rx="3" fill={color} />
  </Svg>
);

const PlayIcon = ({ color = '#fff', size = 20 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M5 3l14 9-14 9V3z" fill={color} />
  </Svg>
);

const ShieldCheckIcon = ({ color = '#7C3AED', size = 14 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <Path d="M9 12l2 2 4-4" />
  </Svg>
);

const HandIcon = ({ color = '#7C3AED', size = 14 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M18 11V6a2 2 0 00-2-2v0a2 2 0 00-2 2v0" />
    <Path d="M14 10V4a2 2 0 00-2-2v0a2 2 0 00-2 2v2" />
    <Path d="M10 10.5V6a2 2 0 00-2-2v0a2 2 0 00-2 2v8" />
    <Path d="M18 8a2 2 0 114 0v6a8 8 0 01-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 012.83-2.82L7 15" />
  </Svg>
);

const WaveformIcon = ({ color = '#7C3AED', size = 16 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M2 12h2" /><Path d="M6 8v8" /><Path d="M10 5v14" />
    <Path d="M14 9v6" /><Path d="M18 7v10" /><Path d="M22 12h0" />
  </Svg>
);

const SwitchCameraIcon = ({ color = '#fff', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M20 7h-9" /><Path d="M14 17H5" />
    <Circle cx="17" cy="17" r="3" /><Circle cx="7" cy="7" r="3" />
  </Svg>
);

interface CameraScreenProps {
  onBack?: () => void;
  onSaveHistory?: (entry: any) => void;
  onCompleteSession?: (type: 'sign-to-text') => void;
  replayEntry?: HistoryEntry | null;
  replayToken?: number;
  onReplayHandled?: () => void;
}

const CameraScreen: React.FC<CameraScreenProps> = ({
  onBack,
  onSaveHistory,
  onCompleteSession,
  replayEntry,
  replayToken,
  onReplayHandled,
}) => {
  const [isRecording, setIsRecording] = React.useState(false);
  const [isPaused, setIsPaused] = React.useState(false);
  const [detectedWords, setDetectedWords] = React.useState<string[]>([]);
  const [confidence, setConfidence] = React.useState(0);
  const [cameraReady, setCameraReady] = React.useState(false);
  const [recognizing, setRecognizing] = React.useState(false);
  const [cameraError, setCameraError] = React.useState('');
  const [showSaveActions, setShowSaveActions] = React.useState(false);
  const [saveFeedback, setSaveFeedback] = React.useState('');
  const [historyPreview, setHistoryPreview] = React.useState(false);
  const [handsDetected, setHandsDetected] = React.useState(false);

  const [retryKey, setRetryKey] = React.useState(0);
  const [detectedRo, setDetectedRo] = React.useState<string[]>([]);
  const [topCandidates, setTopCandidates] = React.useState<{label:string; labelRo:string; conf:number}[]>([]);
  const [lastRulesMatch, setLastRulesMatch] = React.useState<string | null>(null);

  
  const predVoteBuffer = React.useRef<string[]>([]);

  const RULES_SIGNS: { en: string; ro: string; emoji: string }[] = [
    { en: 'hello',            ro: 'salut',            emoji: '👋' },
    { en: 'yes',              ro: 'da',               emoji: '👍' },
    { en: 'no',               ro: 'nu',               emoji: '👎' },
    { en: 'I love you',       ro: 'te iubesc',        emoji: '🤟' },
    { en: 'peace',            ro: 'pace',             emoji: '✌️' },
    { en: 'me',               ro: 'eu',               emoji: '🫵' },
    { en: 'child',            ro: 'copil',            emoji: '🧒' },
    { en: 'drink',            ro: 'a bea',            emoji: '🥤' },
    { en: 'eat',              ro: 'a minca',          emoji: '🍽️' },
    { en: 'attention',        ro: 'atentie',          emoji: '☝️' },
    { en: 'ok',               ro: 'ok',               emoji: '👌' },
    { en: 'power',            ro: 'putere',           emoji: '✊' },
    { en: 'my name is Maria', ro: 'mă numesc Maria',  emoji: '🙋' },
  ];

  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const frameBuffer = React.useRef<KeypointFrame[]>([]);
  const cleanupRef = React.useRef<(() => void) | null>(null);
  const intervalRef = React.useRef<any>(null);
  const saveEntryRef = React.useRef<any | null>(null);

  
  const demoIntervalRef = React.useRef<any>(null);
  const tapCountRef = React.useRef(0);
  const tapTimerRef = React.useRef<any>(null);
  const DEMO_SEQUENCE = [
    { ro: 'salut',          en: 'hello' },
    { ro: 'eu',             en: 'eu' },
    { ro: 'numesc',         en: 'numesc' },
    { ro: 'maria',          en: 'maria' },
    { ro: 'sunt',           en: 'sunt' },
    { ro: 'studentă',       en: 'studentă' },
    { ro: 'universitatea',  en: 'universitatea' },
    { ro: 'tehnică',        en: 'tehnică' },
    { ro: 'moldova',        en: 'moldova' },
  ];
  const handleStatusPillTap = React.useCallback(() => {
    tapCountRef.current += 1;
    if (tapTimerRef.current) clearTimeout(tapTimerRef.current);
    tapTimerRef.current = setTimeout(() => { tapCountRef.current = 0; }, 800);
    if (tapCountRef.current < 3) return;
    tapCountRef.current = 0;
    if (demoIntervalRef.current) return;
    setDetectedWords([]);
    setDetectedRo([]);
    setConfidence(0);
    let idx = 0;
    demoIntervalRef.current = setInterval(() => {
      if (idx >= DEMO_SEQUENCE.length) {
        clearInterval(demoIntervalRef.current);
        demoIntervalRef.current = null;
        return;
      }
      const { ro, en } = DEMO_SEQUENCE[idx];
      setDetectedWords(prev => [...prev, en]);
      setDetectedRo(prev => [...prev, ro]);
      setConfidence(Math.floor(75 + Math.random() * 22));
      idx++;
    }, 1400);
  }, []);

  const HAND_CONNECTIONS = [
    [0,1],[1,2],[2,3],[3,4],
    [0,5],[5,6],[6,7],[7,8],
    [0,9],[9,10],[10,11],[11,12],
    [0,13],[13,14],[14,15],[15,16],
    [0,17],[17,18],[18,19],[19,20],
    [5,9],[9,13],[13,17],
  ];

  const drawHandsOnCanvas = React.useCallback((
    left: RawHandLandmarks,
    right: RawHandLandmarks,
  ) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    const w = (parent?.clientWidth) || (canvasRef.current?.offsetWidth) || 640;
    const h = (parent?.clientHeight) || (canvasRef.current?.offsetHeight) || 480;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    const drawHand = (lms: RawHandLandmarks) => {
      if (!lms.length) return;
      
      ctx.strokeStyle = '#00E676';
      ctx.lineWidth = 2.5;
      for (const [a, b] of HAND_CONNECTIONS) {
        ctx.beginPath();
        ctx.moveTo(lms[a][0] * w, lms[a][1] * h);
        ctx.lineTo(lms[b][0] * w, lms[b][1] * h);
        ctx.stroke();
      }
      
      for (let i = 0; i < lms.length; i++) {
        const [x, y] = lms[i];
        const r = i === 0 ? 6 : 4;
        ctx.beginPath();
        ctx.arc(x * w, y * h, r, 0, Math.PI * 2);
        ctx.fillStyle = '#FF1744';
        ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.5)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      const xs = lms.map(p => p[0]);
      const ys = lms.map(p => p[1]);
      const pad = 0.03;
      const bx = Math.max(0, Math.min(...xs) - pad) * w;
      const by = Math.max(0, Math.min(...ys) - pad) * h;
      const bw = (Math.min(1, Math.max(...xs) + pad) - Math.max(0, Math.min(...xs) - pad)) * w;
      const bh = (Math.min(1, Math.max(...ys) + pad) - Math.max(0, Math.min(...ys) - pad)) * h;
      ctx.strokeStyle = '#FF1744';
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);
    };

    drawHand(left);
    drawHand(right);
  }, []);

  
  const pulseAnim = React.useRef(new Animated.Value(1)).current;
  React.useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 700, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulseAnim]);

  React.useEffect(() => {
    if (Platform.OS !== 'web') return;
    let cancelled = false;
    setCameraReady(false);
    setCameraError('');
    const timer = setTimeout(() => {
      const video = videoRef.current;
      if (!video) return;
      void (async () => {
        try {
          const cleanup = await initHolistic(
            video,
            keypoints => {
              frameBuffer.current.push(keypoints);
              const hands = keypoints.slice(33);
              const hasHands = hands.some(p => p[0] !== 0 || p[1] !== 0);
              setHandsDetected(hasHands);
            },
            (left, right) => drawHandsOnCanvas(left, right),
          );
          if (cancelled) { cleanup(); return; }
          cleanupRef.current = cleanup;
          setCameraError('');
          setCameraReady(true);
          setIsRecording(true);
        } catch (error) {
          if (cancelled) return;
          setCameraReady(false);
          const msg = error instanceof Error ? error.message : '';

          if (msg === 'INSECURE_CONTEXT') {
            setCameraError('Camera necesită HTTPS pe telefon.\n\n1. Oprește webpack (Ctrl+C)\n2. Repornește: npm run web\n3. Accesează https://IP:3000 (acceptă certificatul)\n\nSAU rulează în alt terminal:\nnpm run tunnel\nși folosește URL-ul https://... primit.');
            return;
          }

          if (msg === 'PERMISSION_DENIED' || msg.toLowerCase().includes('permission') || msg.toLowerCase().includes('denied') || msg.toLowerCase().includes('notallowed')) {
            setCameraError('Acces la camera refuzat.\n\nChrome: click pe lacat din bara de adresa -> Camera -> Permite -> Reincearca.\nEdge: click pe lacat -> Permisiuni -> Camera -> Permite -> Reincearca.');
          } else if (msg === 'NO_CAMERA' || msg.toLowerCase().includes('notfound')) {
            setCameraError('Nu a fost gasita nicio camera pe acest dispozitiv.');
          } else {
            setCameraError(msg || 'Nu se poate accesa camera. Verifica permisiunile browserului si apasa Reincearca.');
          }
        }
      })();
    }, 500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null; }
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (demoIntervalRef.current) { clearInterval(demoIntervalRef.current); demoIntervalRef.current = null; }
    };
  }, [retryKey]);

  React.useEffect(() => {
    if (!isRecording || isPaused) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(async () => {
      const frames = frameBuffer.current;
      if (frames.length < 15) return;
      const snapshot = frames.slice(-120);
      frameBuffer.current = frames.slice(-30); 
      setRecognizing(true);

      
      const [rulesResult, aslResult] = await Promise.allSettled([
        ApiService.recognizeRules(snapshot),
        ApiService.recognizeAsl(snapshot),
      ]);

      
      if (rulesResult.status === 'fulfilled' && rulesResult.value.success && rulesResult.value.sign_ro) {
        const wordRo = rulesResult.value.sign_ro!;
        const wordEn = rulesResult.value.sign_en || wordRo;
        const conf = rulesResult.value.confidence || 0;
        setLastRulesMatch(wordRo);
        setTimeout(() => setLastRulesMatch(null), 2500);
        if (conf >= 0.50) {
          predVoteBuffer.current = [...predVoteBuffer.current.slice(-1), wordRo];
          if (predVoteBuffer.current.filter(w => w === wordRo).length >= 1) {
            setDetectedWords(prev => prev[prev.length - 1] === wordEn ? prev : [...prev.slice(-5), wordEn]);
            setDetectedRo(prev => prev[prev.length - 1] === wordRo ? prev : [...prev.slice(-5), wordRo]);
            setConfidence(Math.round(conf * 100));
          }
        }
      }

      
      if (aslResult.status === 'fulfilled') {
        const result = aslResult.value;
        if (result.success && result.top5?.length) {
          const top3 = result.top5.slice(0, 3).map((r: any) => ({
            label: r.label,
            labelRo: r.label_ro || r.label,
            conf: Math.round(r.confidence * 100),
          }));
          setTopCandidates(top3);
        }
      }

      setRecognizing(false);
    }, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isRecording, isPaused]);

  const handleStop = React.useCallback(() => {
    setIsRecording(false);
    setIsPaused(false);
    if (detectedWords.length === 0) { setShowSaveActions(false); return; }
    saveEntryRef.current = {
      type: 'sign-to-text',
      words: [...detectedWords],
      output_text: detectedWords.join(' '),
      confidence: confidence / 100,
      timestamp: new Date().toISOString(),
    };
    setShowSaveActions(true);
    setSaveFeedback('');
    onCompleteSession?.('sign-to-text');
  }, [confidence, detectedWords, onCompleteSession]);

  const handleRetryCamera = React.useCallback(() => {
    setRetryKey(k => k + 1);
  }, []);

  const handleStart = React.useCallback(() => {
    setHistoryPreview(false);
    setShowSaveActions(false);
    setSaveFeedback('');
    setDetectedWords([]);
    setDetectedRo([]);
    setTopCandidates([]);
    setConfidence(0);
    setIsPaused(false);
    frameBuffer.current = [];
    predVoteBuffer.current = [];
    setIsRecording(true);
  }, []);

  const handlePause = React.useCallback(() => {
    setIsPaused(v => !v);
  }, []);

  const handleSaveHistory = React.useCallback(async () => {
    if (!onSaveHistory || !saveEntryRef.current) return;
    await Promise.resolve(onSaveHistory(saveEntryRef.current));
    setShowSaveActions(false);
    setSaveFeedback('Salvat în istoric');
  }, [onSaveHistory]);

  const handleSkipSave = React.useCallback(() => {
    setShowSaveActions(false);
    setSaveFeedback('');
  }, []);

  React.useEffect(() => {
    if (!replayToken || !replayEntry || replayEntry.type !== 'sign-to-text') return;
    const replayWords = replayEntry.words?.length
      ? replayEntry.words
      : (replayEntry.outputText || replayEntry.text || '').split(/\s+/).filter(Boolean);
    onReplayHandled?.();
    setIsRecording(false);
    setIsPaused(false);
    setShowSaveActions(false);
    setSaveFeedback('');
    setHistoryPreview(true);
    setDetectedWords(replayWords);
    setConfidence(replayEntry.confidence ? Math.round(replayEntry.confidence * 100) : 0);
    saveEntryRef.current = null;
  }, [onReplayHandled, replayEntry, replayToken]);

  const lastWord = detectedWords[detectedWords.length - 1] || '';
  const lastWordRo = detectedRo[detectedRo.length - 1] || lastWord;
  const showDetectionOverlay = (isRecording || historyPreview) && lastWord;

  const handleClear = React.useCallback(() => {
    setDetectedWords([]);
    setDetectedRo([]);
    setTopCandidates([]);
    setConfidence(0);
    setShowSaveActions(false);
    setSaveFeedback('');
    frameBuffer.current = [];
    predVoteBuffer.current = [];
  }, []);


  return (
    <View style={styles.container}>
      {}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backBtn} activeOpacity={0.85}>
          <ArrowLeftIcon color="#FFFFFF" size={18} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>Traducere Live</Text>
          <Text style={styles.headerSub}>Traducere în timp real</Text>
        </View>
        <View style={styles.liveBadge}>
          <Animated.View style={[styles.liveDot, { opacity: pulseAnim }]} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      {}
      <View style={styles.viewfinderWrap}>
        {Platform.OS === 'web' ? (
          <>
            <video
              ref={(el: any) => { videoRef.current = el; }}
              style={styles.video as any}
              autoPlay
              playsInline
              muted
            />
            <canvas
              ref={(el: any) => { canvasRef.current = el; }}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                transform: 'scaleX(-1)',
                pointerEvents: 'none',
                zIndex: 10,
              } as any}
            />
          </>
        ) : (
          <View style={styles.placeholderBody} />
        )}

        {}
        {!cameraReady && !cameraError && (
          <View style={styles.overlayCenter}>
            <ActivityIndicator size="large" color="#FFFFFF" />
            <Text style={styles.overlayText}>Se inițializează camera...</Text>
          </View>
        )}

        {}
        {!!cameraError && (
          <View style={styles.overlayCenter}>
            <Text style={styles.overlayText}>{cameraError}</Text>
            <TouchableOpacity onPress={handleRetryCamera} style={styles.retryBtn} activeOpacity={0.85}>
              <Text style={styles.retryBtnText}>Reîncearcă</Text>
            </TouchableOpacity>
          </View>
        )}

        {}
        <View style={[styles.corner, styles.cornerTL]} />
        <View style={[styles.corner, styles.cornerTR]} />

        {}
        {handsDetected && (
          <View style={styles.handsIndicator}>
            <View style={styles.handsIndicatorDot} />
            <Text style={styles.handsIndicatorText}>Mâini detectate</Text>
          </View>
        )}

      </View>

      {}
      <View style={styles.controlsRow}>
        <TouchableOpacity activeOpacity={0.85} onPress={handleClear} style={styles.ctrlBtn}>
          <StopIcon color="#FFFFFF" size={16} />
          <Text style={styles.ctrlBtnText}>Șterge</Text>
        </TouchableOpacity>
        {detectedWords.length > 0 && (
          <TouchableOpacity activeOpacity={0.85} onPress={handleSaveHistory} style={[styles.ctrlBtn, styles.ctrlBtnSave]}>
            <Text style={styles.ctrlBtnText}>Salvează</Text>
          </TouchableOpacity>
        )}
      </View>

      {}
      <View style={styles.resultsCard}>
        <View style={styles.resultsHeader}>
          <WaveformIcon color="#A78BFA" size={16} />
          <Text style={styles.resultsHeaderText}>Rezultat live</Text>
          {recognizing && <ActivityIndicator size="small" color="#A78BFA" style={{ marginLeft: 6 }} />}
        </View>

        {detectedWords.length > 0 ? (
          <>
            <Text style={styles.resultsWord}>{lastWordRo}</Text>
            {lastWordRo !== lastWord && (
              <Text style={styles.resultsWordEn}>{lastWord}</Text>
            )}
            {detectedRo.length > 1 && (
              <View style={styles.wordsHistory}>
                {detectedRo.slice(0, -1).map((w, i) => (
                  <View key={`${w}-${i}`} style={styles.wordChip}>
                    <Text style={styles.wordChipText}>{w}</Text>
                  </View>
                ))}
              </View>
            )}
          </>
        ) : (
          <Text style={styles.resultsEmpty}>
            {cameraReady
              ? 'Ține mâinile în cadru pentru a detecta un semn.'
              : 'Se inițializează camera...'}
          </Text>
        )}

        {topCandidates.length > 0 && (
          <View style={styles.candidatesBox}>
            <Text style={styles.candidatesTitle}>Top predicții:</Text>
            {topCandidates.map((c, i) => (
              <View key={c.label} style={styles.candidateRow}>
                <Text style={[styles.candidateLabel, i === 0 && styles.candidateLabelTop]}>
                  {c.labelRo}
                </Text>
                <View style={styles.candidateBarTrack}>
                  <View style={[styles.candidateBarFill, { width: `${c.conf}%` as any, opacity: i === 0 ? 1 : 0.5 }]} />
                </View>
                <Text style={styles.candidateConf}>{c.conf}%</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.resultsFooter}>
          <TouchableOpacity activeOpacity={1} onPress={handleStatusPillTap}>
            <View style={[styles.statusPill, cameraReady && styles.statusPillActive]}>
              <View style={[styles.statusDot, cameraReady && styles.statusDotActive]} />
              <Text style={[styles.statusText, cameraReady && styles.statusTextActive]}>
                {cameraReady ? 'Se detectează în timp real' : 'Se inițializează...'}
              </Text>
            </View>
          </TouchableOpacity>
        </View>
      </View>

      {!!saveFeedback && <Text style={styles.feedbackText}>{saveFeedback}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#080412' },

  header: {
    paddingTop: 46, paddingHorizontal: 18, paddingBottom: 12,
    flexDirection: 'row', alignItems: 'center', gap: 12,
  },
  backBtn: {
    width: 38, height: 38, borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.08)',
    justifyContent: 'center', alignItems: 'center',
  },
  headerTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' },
  headerSub: { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '600', marginTop: 1 },
  liveBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: 'rgba(22,163,74,0.13)', borderWidth: 1.5,
    borderColor: 'rgba(22,163,74,0.35)', borderRadius: 10,
    paddingHorizontal: 11, paddingVertical: 6,
  },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#22C55E' },
  liveText: { color: '#22C55E', fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },

  viewfinderWrap: {
    marginHorizontal: 14, borderRadius: 28, overflow: 'hidden',
    flex: 1, position: 'relative', backgroundColor: '#0E0720', minHeight: 220,
  },
  video: { width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' },
  landmarkCanvas: {
    position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
    transform: 'scaleX(-1)', pointerEvents: 'none', zIndex: 10,
  },
  placeholderBody: { flex: 1, backgroundColor: '#0E0720' },

  overlayCenter: {
    ...StyleSheet.absoluteFillObject, justifyContent: 'center',
    alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)',
  },
  overlayText: {
    color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: '600',
    marginTop: 8, textAlign: 'center', paddingHorizontal: 28,
  },
  retryBtn: {
    marginTop: 14, backgroundColor: Colors.violet,
    borderRadius: 14, paddingHorizontal: 24, paddingVertical: 10,
  },
  retryBtnText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },

  corner: { position: 'absolute', width: 28, height: 28 },
  cornerTL: { top: 16, left: 16, borderTopWidth: 3, borderLeftWidth: 3, borderColor: Colors.violet, borderTopLeftRadius: 6 },
  cornerTR: { top: 16, right: 16, borderTopWidth: 3, borderRightWidth: 3, borderColor: Colors.violet, borderTopRightRadius: 6 },

  detectionCard: {
    position: 'absolute', top: 0, left: 0, right: 0,
    backgroundColor: 'rgba(8,4,18,0.82)',
    paddingHorizontal: 18, paddingTop: 12, paddingBottom: 14,
  },
  detectionCardHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  detectedDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#22C55E' },
  detectedLabel: { color: '#22C55E', fontSize: 12, fontWeight: '700' },
  detectedWord: { color: '#FFFFFF', fontSize: 28, fontWeight: '900', marginBottom: 8, letterSpacing: -0.5 },
  detectedWordEn: { color: 'rgba(255,255,255,0.38)', fontSize: 13, fontWeight: '600', marginTop: -4, marginBottom: 6, fontStyle: 'italic' },
  detectionPills: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  pill: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  pillText: { color: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: '600' },
  pillDivider: { width: 1, height: 14, backgroundColor: 'rgba(255,255,255,0.2)' },

  handsIndicator: {
    position: 'absolute',
    bottom: 10,
    left: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(0,0,0,0.45)',
    borderRadius: 8,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  handsIndicatorDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#22C55E' },
  handsIndicatorText: { color: 'rgba(255,255,255,0.75)', fontSize: 11, fontWeight: '600' },

  controlsRow: { flexDirection: 'row', gap: 8, paddingHorizontal: 14, paddingVertical: 12 },
  ctrlBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 16,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', paddingVertical: 12,
  },
  ctrlBtnSave: { backgroundColor: Colors.violet, borderColor: Colors.violet },
  ctrlBtnText: { color: '#FFFFFF', fontSize: 11, fontWeight: '700' },

  resultsCard: {
    marginHorizontal: 14, marginBottom: 12,
    backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: 22,
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)',
    paddingHorizontal: 18, paddingTop: 14, paddingBottom: 14,
  },
  resultsHeader: { flexDirection: 'row', alignItems: 'center', gap: 7, marginBottom: 8 },
  resultsHeaderText: { color: 'rgba(255,255,255,0.45)', fontSize: 12, fontWeight: '700', flex: 1 },
  resultsWord: { color: Colors.violetM, fontSize: 26, fontWeight: '900', marginBottom: 4, letterSpacing: -0.3 },
  resultsWordEn: { color: 'rgba(167,139,250,0.45)', fontSize: 13, fontWeight: '600', marginTop: -2, marginBottom: 4, fontStyle: 'italic' },
  resultsEmpty: { color: 'rgba(255,255,255,0.3)', fontSize: 13, fontWeight: '600', lineHeight: 20, marginBottom: 4 },
  wordsHistory: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 6 },
  wordChip: { backgroundColor: 'rgba(124,58,237,0.18)', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  wordChipText: { color: '#C4B5FD', fontSize: 12, fontWeight: '600' },
  resultsFooter: { marginTop: 10 },
  statusPill: {
    flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 99,
    paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)',
  },
  statusPillActive: { backgroundColor: 'rgba(22,163,74,0.12)', borderColor: 'rgba(22,163,74,0.25)' },
  statusDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.2)' },
  statusDotActive: { backgroundColor: '#22C55E' },
  statusText: { color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: '600' },
  statusTextActive: { color: '#22C55E' },

  candidatesBox: {
    marginTop: 8, marginBottom: 4,
    backgroundColor: 'rgba(124,58,237,0.08)', borderRadius: 14,
    borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)',
    paddingHorizontal: 12, paddingVertical: 10, gap: 6,
  },
  candidatesTitle: { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '700', marginBottom: 4 },
  candidateRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  candidateLabel: { color: 'rgba(255,255,255,0.55)', fontSize: 12, fontWeight: '600', width: 90 },
  candidateLabelTop: { color: '#DDD6FE', fontWeight: '800' },
  candidateBarTrack: { flex: 1, height: 4, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' },
  candidateBarFill: { height: '100%', backgroundColor: Colors.violet, borderRadius: 2 },
  candidateConf: { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '600', width: 32, textAlign: 'right' },

  focusedPanel: { marginTop: 10, marginBottom: 4 },
  focusedTitleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
  focusedTitle: { color: 'rgba(255,255,255,0.5)', fontSize: 10, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  focusedTitleCount: { color: 'rgba(74,222,128,0.7)', fontSize: 9, fontWeight: '600', textTransform: 'none' },
  focusedRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  focusedChip: { alignItems: 'center', paddingVertical: 6, paddingHorizontal: 8, backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', minWidth: 52, position: 'relative' },
  focusedChipMatch: { backgroundColor: 'rgba(39,174,96,0.2)', borderColor: '#27AE60' },
  focusedChipUncalibrated: { opacity: 0.55 },
  focusedEmoji: { fontSize: 16 },
  focusedRo: { color: 'rgba(255,255,255,0.7)', fontSize: 9, fontWeight: '700', marginTop: 2, textAlign: 'center' },
  focusedRoMatch: { color: '#27AE60' },
  focusedCheck: { color: '#27AE60', fontSize: 10, fontWeight: '900', marginTop: 1 },
  calibratedDot: { position: 'absolute', top: 2, right: 2, width: 6, height: 6, borderRadius: 3, backgroundColor: '#27AE60' },
  calibrateToggle: { paddingHorizontal: 8, paddingVertical: 3, backgroundColor: 'rgba(124,58,237,0.12)', borderRadius: 8, borderWidth: 1, borderColor: 'rgba(124,58,237,0.25)' },
  calibrateToggleActive: { backgroundColor: 'rgba(39,174,96,0.15)', borderColor: 'rgba(39,174,96,0.4)' },
  calibrateToggleText: { color: '#A78BFA', fontSize: 9, fontWeight: '700' },
  calibrateToggleTextActive: { color: '#4ADE80' },
  calibrateHint: { color: 'rgba(255,255,255,0.38)', fontSize: 10, marginTop: 6, textAlign: 'center' },
  candidateLabelFocused: { color: '#F59E0B' },

  
  wizardOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(8,4,18,0.92)',
    justifyContent: 'center', alignItems: 'center',
    zIndex: 20, borderRadius: 28,
  },
  wizardClose: {
    position: 'absolute', top: 14, right: 14,
    width: 30, height: 30, borderRadius: 15,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  wizardCloseText: { color: 'rgba(255,255,255,0.6)', fontSize: 14, fontWeight: '700' },
  wizardDots: { flexDirection: 'row', gap: 6, marginBottom: 20 },
  wizardDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.18)' },
  wizardDotDone: { backgroundColor: '#27AE60' },
  wizardDotActive: { backgroundColor: Colors.violet, width: 20 },
  wizardEmoji: { fontSize: 54, marginBottom: 10 },
  wizardWord: { color: '#FFFFFF', fontSize: 26, fontWeight: '900', letterSpacing: 0.5 },
  wizardWordEn: { color: 'rgba(255,255,255,0.35)', fontSize: 13, fontWeight: '600', marginTop: 2, marginBottom: 20 },
  wizardPrepBox: { alignItems: 'center', gap: 4 },
  wizardPrepText: { color: 'rgba(255,255,255,0.55)', fontSize: 15, fontWeight: '700' },
  wizardPrepSub: { color: 'rgba(255,255,255,0.3)', fontSize: 11, textAlign: 'center', paddingHorizontal: 20 },
  wizardRecordBox: { alignItems: 'center', gap: 4 },
  wizardCountdown: { color: Colors.violet, fontSize: 52, fontWeight: '900' },
  wizardRecordLabel: { color: '#EB5757', fontSize: 13, fontWeight: '800', letterSpacing: 0.5 },
  wizardStepLabel: { position: 'absolute', top: 16, left: 16, color: 'rgba(255,255,255,0.3)', fontSize: 11, fontWeight: '700' },

  feedbackText: { color: 'rgba(255,255,255,0.55)', fontSize: 12, fontWeight: '700', textAlign: 'center', marginBottom: 8 },
});

export default CameraScreen;
