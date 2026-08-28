import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { Colors } from '../theme';
import { ArrowLeftIcon } from '../components/Icons';
import ApiService from '../services/ApiService';
import { KeypointFrame, initHolistic, isExpoWebViewContext } from '../hooks/useMediaPipe';

const Svg = 'svg' as any;
const Path = 'path' as any;

const CheckIcon = ({ size = 22, color = '#fff' }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M5 12l5 5L19 7" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

interface FocusedWord {
  en: string;
  ro: string;
  emoji: string;
  description: string;
}

interface LearnScreenProps {
  onBack?: () => void;
}

const WORD_COLORS: Record<string, string> = {
  hello: '#2D9CDB',
  love:  '#EB5757',
  stop:  '#F2994A',
  drink: '#27AE60',
  yes:   '#9B51E0',
};

const LearnScreen: React.FC<LearnScreenProps> = ({ onBack }) => {
  const [words, setWords] = React.useState<FocusedWord[]>([]);
  const [isActive, setIsActive] = React.useState(false);
  const [recognizedWord, setRecognizedWord] = React.useState<string | null>(null);
  const [lastConfidence, setLastConfidence] = React.useState(0);
  const [cameraReady, setCameraReady] = React.useState(false);
  const [cameraError, setCameraError] = React.useState('');
  const [targetWord, setTargetWord] = React.useState<string | null>(null);

  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const frameBuffer = React.useRef<KeypointFrame[]>([]);
  const cleanupRef = React.useRef<(() => void) | null>(null);
  const intervalRef = React.useRef<any>(null);
  const flashAnim = React.useRef(new Animated.Value(0)).current;

  
  React.useEffect(() => {
    ApiService.getFocusedWords()
      .then(r => setWords(r.words))
      .catch(() => {
        setWords([
          { en: 'hello', ro: 'salut',   emoji: '👋', description: 'Mână deschisă lângă frunte' },
          { en: 'love',  ro: 'iubire',  emoji: '🤍', description: 'Brațe încrucișate pe piept' },
          { en: 'stop',  ro: 'stop',    emoji: '✋', description: 'Palmă care taie cealaltă palmă' },
          { en: 'drink', ro: 'a bea',   emoji: '🥤', description: 'Pumn în C dus la gură' },
          { en: 'yes',   ro: 'da',      emoji: '✅', description: 'Pumn care se mișcă sus-jos' },
        ]);
      });
  }, []);

  
  const flashSuccess = React.useCallback(() => {
    flashAnim.setValue(1);
    Animated.timing(flashAnim, { toValue: 0, duration: 900, useNativeDriver: false }).start();
  }, [flashAnim]);

  
  React.useEffect(() => {
    if (!isActive) return;
    let cancelled = false;
    (async () => {
      try {
        if (isExpoWebViewContext()) { setCameraError('Camera nu este disponibilă în Expo.'); return; }
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 } });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        video.srcObject = stream;
        await video.play();
        const cleanup = await initHolistic(video, canvas, (frame: KeypointFrame) => {
          if (!cancelled) {
            frameBuffer.current = [...frameBuffer.current.slice(-119), frame];
            const hasHands = frame.some(kp => kp[0] !== 0 || kp[1] !== 0);
            if (!hasHands) return;
          }
        });
        cleanupRef.current = () => {
          cleanup?.();
          stream.getTracks().forEach(t => t.stop());
        };
        if (!cancelled) setCameraReady(true);
      } catch (e: any) {
        if (!cancelled) setCameraError(e?.message || 'Eroare cameră');
      }
    })();
    return () => {
      cancelled = true;
      cleanupRef.current?.();
      cleanupRef.current = null;
      setCameraReady(false);
    };
  }, [isActive]);

  
  React.useEffect(() => {
    if (!isActive || !cameraReady) return;
    intervalRef.current = setInterval(async () => {
      const frames = frameBuffer.current;
      if (frames.length < 15) return;
      const snapshot = frames.slice(-120);
      frameBuffer.current = frames.slice(-30);
      try {
        const result = await ApiService.recognizeFocused(snapshot);
        if (result.success && result.word) {
          setRecognizedWord(result.word);
          setLastConfidence(Math.round((result.confidence ?? 0) * 100));
          flashSuccess();
        }
      } catch {}
    }, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isActive, cameraReady, flashSuccess]);

  const handleStart = () => {
    setRecognizedWord(null);
    setIsActive(true);
  };

  const handleStop = () => {
    setIsActive(false);
    setRecognizedWord(null);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const bgColor = flashAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['rgba(0,0,0,0)', 'rgba(39,174,96,0.25)'],
  });

  return (
    <View style={styles.container}>
      {}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backBtn} activeOpacity={0.7}>
          <ArrowLeftIcon color="#fff" size={20} />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Învață 5 Semne</Text>
          <Text style={styles.headerSub}>Recunoaștere precisă</Text>
        </View>
      </View>

      {}
      <View style={styles.cardsRow}>
        {words.map(w => {
          const isMatch = recognizedWord === w.en;
          const isTarget = targetWord === w.en;
          const color = WORD_COLORS[w.en] ?? Colors.violet;
          return (
            <TouchableOpacity
              key={w.en}
              activeOpacity={0.8}
              onPress={() => setTargetWord(isTarget ? null : w.en)}
              style={[
                styles.card,
                { borderColor: isMatch ? '#27AE60' : isTarget ? color : Colors.rule },
                isMatch && styles.cardMatch,
              ]}
            >
              <Text style={styles.cardEmoji}>{w.emoji}</Text>
              <Text style={[styles.cardRo, isMatch && { color: '#27AE60' }]}>{w.ro}</Text>
              <Text style={styles.cardEn}>{w.en}</Text>
              {isMatch && (
                <View style={styles.checkBadge}>
                  <CheckIcon size={14} color="#fff" />
                </View>
              )}
            </TouchableOpacity>
          );
        })}
      </View>

      {}
      {targetWord && words.find(w => w.en === targetWord) && (
        <View style={[styles.hint, { borderColor: WORD_COLORS[targetWord] ?? Colors.violet }]}>
          <Text style={styles.hintEmoji}>{words.find(w => w.en === targetWord)?.emoji}</Text>
          <View style={{ flex: 1 }}>
            <Text style={[styles.hintTitle, { color: WORD_COLORS[targetWord] ?? Colors.violet }]}>
              {words.find(w => w.en === targetWord)?.ro.toUpperCase()}
            </Text>
            <Text style={styles.hintDesc}>{words.find(w => w.en === targetWord)?.description}</Text>
          </View>
        </View>
      )}

      {}
      <Animated.View style={[styles.cameraWrap, { backgroundColor: bgColor }]}>
        <View style={styles.cameraInner}>
          {isActive ? (
            <>
              <video ref={videoRef as any} style={styles.video as any} muted playsInline autoPlay />
              <canvas ref={canvasRef as any} style={styles.canvas as any} />
              {!cameraReady && !cameraError && (
                <View style={styles.overlay}>
                  <ActivityIndicator size="large" color={Colors.teal} />
                  <Text style={styles.overlayText}>Se pornește camera...</Text>
                </View>
              )}
              {cameraError ? (
                <View style={styles.overlay}>
                  <Text style={styles.errorText}>{cameraError}</Text>
                </View>
              ) : recognizedWord ? (
                <View style={styles.resultOverlay}>
                  <Text style={styles.resultEmoji}>
                    {words.find(w => w.en === recognizedWord)?.emoji ?? '✅'}
                  </Text>
                  <Text style={styles.resultWord}>
                    {words.find(w => w.en === recognizedWord)?.ro ?? recognizedWord}
                  </Text>
                  <Text style={styles.resultConf}>{lastConfidence}% încredere</Text>
                </View>
              ) : cameraReady ? (
                <View style={styles.listeningOverlay}>
                  <Text style={styles.listeningText}>
                    {targetWord
                      ? `Fă semnul pentru "${words.find(w => w.en === targetWord)?.ro ?? targetWord}"`
                      : 'Fă un semn din cele 5...'}
                  </Text>
                </View>
              ) : null}
            </>
          ) : (
            <View style={styles.idleOverlay}>
              <Text style={styles.idleIcon}>🤟</Text>
              <Text style={styles.idleText}>Apasă Start și fă unul din cele 5 semne</Text>
            </View>
          )}
        </View>
      </Animated.View>

      {}
      <View style={styles.controls}>
        {!isActive ? (
          <TouchableOpacity style={styles.startBtn} onPress={handleStart} activeOpacity={0.85}>
            <Text style={styles.startBtnText}>▶  Start recunoaștere</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.stopBtn} onPress={handleStop} activeOpacity={0.85}>
            <Text style={styles.stopBtnText}>■  Stop</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

export default LearnScreen;

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: Colors.bg },
  header:          { flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: Colors.teal, paddingHorizontal: 16, paddingTop: 48, paddingBottom: 16 },
  backBtn:         { width: 36, height: 36, borderRadius: 10, backgroundColor: 'rgba(255,255,255,0.15)', justifyContent: 'center', alignItems: 'center' },
  headerTitle:     { color: '#fff', fontSize: 18, fontWeight: '800' },
  headerSub:       { color: 'rgba(255,255,255,0.75)', fontSize: 12 },

  cardsRow:        { flexDirection: 'row', paddingHorizontal: 12, paddingTop: 14, gap: 8, flexWrap: 'wrap', justifyContent: 'center' },
  card:            { width: 60, alignItems: 'center', paddingVertical: 10, paddingHorizontal: 6, backgroundColor: Colors.card, borderRadius: 14, borderWidth: 2, position: 'relative' },
  cardMatch:       { backgroundColor: 'rgba(39,174,96,0.12)', borderColor: '#27AE60' },
  cardEmoji:       { fontSize: 22, marginBottom: 4 },
  cardRo:          { color: Colors.ink, fontSize: 10, fontWeight: '700', textAlign: 'center' },
  cardEn:          { color: Colors.sub, fontSize: 9, textAlign: 'center' },
  checkBadge:      { position: 'absolute', top: -6, right: -6, width: 20, height: 20, borderRadius: 10, backgroundColor: '#27AE60', justifyContent: 'center', alignItems: 'center' },

  hint:            { flexDirection: 'row', alignItems: 'center', marginHorizontal: 16, marginTop: 10, backgroundColor: Colors.card, borderRadius: 14, borderWidth: 2, padding: 12, gap: 12 },
  hintEmoji:       { fontSize: 28 },
  hintTitle:       { fontSize: 13, fontWeight: '800' },
  hintDesc:        { fontSize: 12, color: Colors.sub, marginTop: 2 },

  cameraWrap:      { flex: 1, marginHorizontal: 16, marginTop: 12, borderRadius: 20, overflow: 'hidden' },
  cameraInner:     { flex: 1, position: 'relative', backgroundColor: '#111', borderRadius: 20, overflow: 'hidden' },
  video:           { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover', transform: [{ scaleX: -1 }] } as any,
  canvas:          { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' } as any,

  overlay:         { ...StyleSheet.absoluteFillObject, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)', gap: 10 },
  overlayText:     { color: '#fff', fontSize: 14 },
  errorText:       { color: '#FF6B6B', fontSize: 14, textAlign: 'center', paddingHorizontal: 20 },

  resultOverlay:   { position: 'absolute', bottom: 16, left: 0, right: 0, alignItems: 'center' },
  resultEmoji:     { fontSize: 40 },
  resultWord:      { color: '#27AE60', fontSize: 26, fontWeight: '900', marginTop: 4 },
  resultConf:      { color: 'rgba(255,255,255,0.7)', fontSize: 12, marginTop: 2 },

  listeningOverlay:{ position: 'absolute', bottom: 12, left: 12, right: 12, backgroundColor: 'rgba(0,0,0,0.55)', borderRadius: 10, padding: 10, alignItems: 'center' },
  listeningText:   { color: 'rgba(255,255,255,0.85)', fontSize: 13 },

  idleOverlay:     { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  idleIcon:        { fontSize: 48 },
  idleText:        { color: Colors.sub, fontSize: 14, textAlign: 'center', paddingHorizontal: 30 },

  controls:        { paddingHorizontal: 16, paddingVertical: 12 },
  startBtn:        { backgroundColor: Colors.teal, borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  startBtnText:    { color: '#fff', fontSize: 16, fontWeight: '800' },
  stopBtn:         { backgroundColor: '#EB5757', borderRadius: 14, paddingVertical: 14, alignItems: 'center' },
  stopBtnText:     { color: '#fff', fontSize: 16, fontWeight: '800' },
});
