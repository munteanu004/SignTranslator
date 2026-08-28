import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Animated,
  useWindowDimensions,
} from 'react-native';
import { CameraView } from 'expo-camera';
import Svg, { Circle, Line, G, Rect } from 'react-native-svg';
import Constants from 'expo-constants';

const VIOLET   = '#7C3AED';
const VIOLET_M = '#A78BFA';
const DARK     = '#080412';
const GREEN    = '#22C55E';

// MediaPipe hand connections (wrist=0, fingers tip→base)
const HAND_CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],       // thumb
  [0,5],[5,6],[6,7],[7,8],       // index
  [0,9],[9,10],[10,11],[11,12],  // middle
  [0,13],[13,14],[14,15],[15,16],// ring
  [0,17],[17,18],[18,19],[19,20],// pinky
  [5,9],[9,13],[13,17],          // palm
];

function HandSkeleton({ landmarks, width, height, color = GREEN }) {
  if (!landmarks || landmarks.length === 0) return null;
  const xs = landmarks.map(l => l[0]);
  const ys = landmarks.map(l => l[1]);
  const pad = 0.03;
  const bx = Math.max(0, Math.min(...xs) - pad) * width;
  const by = Math.max(0, Math.min(...ys) - pad) * height;
  const bw = (Math.min(1, Math.max(...xs) + pad) - Math.max(0, Math.min(...xs) - pad)) * width;
  const bh = (Math.min(1, Math.max(...ys) + pad) - Math.max(0, Math.min(...ys) - pad)) * height;
  return (
    <G>
      <Rect x={bx} y={by} width={bw} height={bh}
        stroke="#FF1744" strokeWidth={2} fill="none" strokeOpacity={0.9} />
      {HAND_CONNECTIONS.map(([a, b], i) => {
        const pa = landmarks[a];
        const pb = landmarks[b];
        if (!pa || !pb) return null;
        return (
          <Line
            key={i}
            x1={pa[0] * width} y1={pa[1] * height}
            x2={pb[0] * width} y2={pb[1] * height}
            stroke={color} strokeWidth={2} strokeOpacity={0.85}
          />
        );
      })}
      {landmarks.map((lm, i) => (
        <Circle
          key={i}
          cx={lm[0] * width} cy={lm[1] * height}
          r={i === 0 ? 6 : 4}
          fill="#FF1744"
          fillOpacity={0.95}
          stroke="rgba(0,0,0,0.4)"
          strokeWidth={1}
        />
      ))}
    </G>
  );
}

function getApiBase() {
  try {
    const hostUri =
      Constants.expoConfig?.hostUri ||
      Constants.manifest2?.extra?.expoGo?.debuggerHost ||
      Constants.manifest?.debuggerHost ||
      '';
    const ip = hostUri.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      return `http://${ip}:5000/api`;
    }
  } catch {}
  return 'http://localhost:5000/api';
}

const SESSION_ID = `expo_${Date.now()}`;

export default function NativeCameraScreen({ onClose, onResult }) {
  const cameraRef = useRef(null);
  const { width: winWidth } = useWindowDimensions();

  const [isRecording, setIsRecording]         = useState(false);
  const [isPaused, setIsPaused]               = useState(false);
  const [lastWordRo, setLastWordRo]           = useState('');
  const [lastWordEn, setLastWordEn]           = useState('');
  const [confidence, setConfidence]           = useState(0);
  const [handsDetected, setHandsDetected]     = useState(false);
  const [words, setWords]                     = useState([]);
  const [wordsRo, setWordsRo]                 = useState([]);
  const [topCandidates, setTopCandidates]     = useState([]);
  const [facing, setFacing]                   = useState('front');
  const [recognizing, setRecognizing]         = useState(false);
  const [showSaveActions, setShowSaveActions] = useState(false);
  const [saveFeedback, setSaveFeedback]       = useState('');
  const [statusMsg, setStatusMsg]             = useState('Ține mâinile în cadru...');
  const [landmarks, setLandmarks]             = useState({ left_hand: [], right_hand: [] });
  const [viewSize, setViewSize]               = useState({ width: 1, height: 1 });

  const intervalRef = useRef(null);
  const pulseAnim   = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.3, duration: 700, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1,   duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulseAnim]);

  const captureAndRecognize = useCallback(async () => {
    if (!cameraRef.current) return;
    setRecognizing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.6,
        base64: true,
        skipProcessing: true,
        shutterSound: false,
        animateShutter: false,
      });
      if (!photo.base64) return;

      const API = getApiBase();
      const res = await fetch(`${API}/recognize-frame`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: `data:image/jpeg;base64,${photo.base64}`,
          session_id: SESSION_ID,
        }),
      });
      const json = await res.json();

      if (!res.ok || json.error) {
        setStatusMsg(`Eroare: ${json.error || res.status}`);
        return;
      }

      setHandsDetected(json.hands_detected ?? false);

      // Update skeleton overlay
      if (json.landmarks) {
        setLandmarks(json.landmarks);
      }

      if (json.top5?.length) {
        setTopCandidates(
          json.top5.slice(0, 3).map(r => ({
            label: r.label,
            conf: Math.round(r.confidence * 100),
          }))
        );
      }

      if (json.buffered_frames < 5) {
        setStatusMsg(`Acumulez cadre... (${json.buffered_frames ?? 0}/5)`);
      } else if (!json.hands_detected) {
        setStatusMsg('Ține mâinile în cadru');
      } else {
        setStatusMsg(`${json.buffered_frames ?? 0} cadre procesate`);
      }

      if (json.success && json.gloss_en && json.confidence > 0.10) {
        const ro = json.gloss_ro || json.gloss_en;
        const en = json.gloss_en;
        setLastWordRo(ro);
        setLastWordEn(en);
        setConfidence(Math.round(json.confidence * 100));
        setWords(prev  => prev[prev.length - 1] === en ? prev : [...prev.slice(-5), en]);
        setWordsRo(prev => prev[prev.length - 1] === ro ? prev : [...prev.slice(-5), ro]);
        onResult?.({ gloss_en: en, gloss_ro: ro, confidence: json.confidence });
      }
    } catch (err) {
      setStatusMsg('Eroare conexiune: ' + err.message);
    } finally {
      setRecognizing(false);
    }
  }, [onResult]);

  const handleStart = useCallback(async () => {
    const API = getApiBase();
    await fetch(`${API}/recognize-frame/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: SESSION_ID }),
    }).catch(() => {});
    setWords([]); setWordsRo([]); setLastWordRo(''); setLastWordEn('');
    setConfidence(0); setTopCandidates([]); setHandsDetected(false);
    setShowSaveActions(false); setSaveFeedback('');
    setLandmarks({ left_hand: [], right_hand: [] });
    setIsPaused(false);
    setStatusMsg('Ține mâinile în cadru...');
    setIsRecording(true);
  }, []);

  const handleStop = useCallback(() => {
    setIsRecording(false);
    setIsPaused(false);
    clearInterval(intervalRef.current);
    setLandmarks({ left_hand: [], right_hand: [] });
    if (words.length > 0) setShowSaveActions(true);
  }, [words]);

  const handlePause = useCallback(() => setIsPaused(v => !v), []);

  const handleSkipSave = useCallback(() => {
    setShowSaveActions(false); setSaveFeedback('');
  }, []);

  const handleSaveHistory = useCallback(() => {
    setSaveFeedback('Salvat în istoric');
    setShowSaveActions(false);
    onResult?.({ gloss_en: lastWordEn, gloss_ro: lastWordRo, confidence: confidence / 100, words, wordsRo, save: true });
  }, [confidence, lastWordEn, lastWordRo, onResult, words, wordsRo]);

  // Auto-start detection when screen mounts
  useEffect(() => {
    handleStart();
  }, []);

  useEffect(() => {
    if (isRecording && !isPaused) {
      intervalRef.current = setInterval(captureAndRecognize, 700);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [isRecording, isPaused, captureAndRecognize]);

  // Mirror X for front camera (landmarks come from non-mirrored image)
  const mirrorX = (lms) => {
    if (!lms || lms.length === 0) return lms;
    return lms.map(([x, y]) => [1 - x, y]);
  };

  const leftLandmarks  = facing === 'front' ? mirrorX(landmarks.left_hand)  : landmarks.left_hand;
  const rightLandmarks = facing === 'front' ? mirrorX(landmarks.right_hand) : landmarks.right_hand;
  const showDetectionOverlay = isRecording && !!lastWordRo;

  return (
    <View style={styles.container}>

      {/* ── Header ── */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onClose} style={styles.backBtn} activeOpacity={0.85}>
          <Text style={styles.backArrow}>←</Text>
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>Traducere Live</Text>
          <Text style={styles.headerSub}>Traducere în timp real</Text>
        </View>
        <View style={styles.liveBadge}>
          <Animated.View style={[styles.liveDot, { opacity: isRecording && !isPaused ? pulseAnim : 0.35 }]} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      {/* ── Camera viewfinder ── */}
      <View
        style={styles.viewfinderWrap}
        onLayout={e => setViewSize({ width: e.nativeEvent.layout.width, height: e.nativeEvent.layout.height })}>

        <CameraView ref={cameraRef} style={styles.camera} facing={facing} />

        {/* Skeleton SVG overlay */}
        {isRecording && (
          <Svg
            style={StyleSheet.absoluteFill}
            width={viewSize.width}
            height={viewSize.height}
            pointerEvents="none">
            <HandSkeleton
              landmarks={leftLandmarks}
              width={viewSize.width}
              height={viewSize.height}
              color={GREEN}
            />
            <HandSkeleton
              landmarks={rightLandmarks}
              width={viewSize.width}
              height={viewSize.height}
              color={GREEN}
            />
          </Svg>
        )}

        {/* Corner brackets */}
        <View style={[styles.corner, styles.cornerTL]} />
        <View style={[styles.corner, styles.cornerTR]} />

        {/* Idle hint */}
        {!isRecording && !showSaveActions && (
          <View style={styles.idleHint}>
            <Text style={styles.idleHintText}>Ține mâinile în cadru...</Text>
          </View>
        )}

        {/* Hands indicator */}
        {isRecording && (
          <View style={styles.handsIndicator}>
            <View style={[styles.handsDot, { backgroundColor: handsDetected ? GREEN : '#6B7280' }]} />
            <Text style={styles.handsText}>{handsDetected ? 'Mâini detectate' : 'Fără mâini'}</Text>
            {recognizing && <ActivityIndicator size="small" color="rgba(255,255,255,0.6)" style={{ marginLeft: 4 }} />}
          </View>
        )}

        {/* Bottom detection overlay */}
        {showDetectionOverlay && (
          <View style={styles.detectionCard}>
            <View style={styles.detectionCardHeader}>
              <View style={styles.detectedDot} />
              <Text style={styles.detectedLabel}>Semn detectat</Text>
            </View>
            <Text style={styles.detectedWord}>{lastWordRo}</Text>
            {lastWordRo !== lastWordEn && (
              <Text style={styles.detectedWordEn}>{lastWordEn}</Text>
            )}
            <View style={styles.detectionPills}>
              {confidence > 0 && (
                <View style={styles.pill}>
                  <Text style={styles.pillText}>🛡 Încredere {confidence}%</Text>
                </View>
              )}
              {handsDetected && (
                <>
                  <View style={styles.pillDivider} />
                  <View style={styles.pill}>
                    <Text style={styles.pillText}>✋ Mâini detectate</Text>
                  </View>
                </>
              )}
            </View>
          </View>
        )}

        {/* Flip button */}
        <TouchableOpacity
          style={styles.flipBtn}
          onPress={() => setFacing(f => f === 'front' ? 'back' : 'front')}
          activeOpacity={0.85}>
          <Text style={styles.flipText}>⟳</Text>
        </TouchableOpacity>
      </View>

      {/* ── Controls ── */}
      <View style={styles.controlsRow}>
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={handleStart}
          style={styles.ctrlBtn}>
          <Text style={styles.ctrlBtnText}>✕ Șterge</Text>
        </TouchableOpacity>
        {words.length > 0 && (
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={handleSaveHistory}
            style={[styles.ctrlBtn, styles.ctrlBtnSave]}>
            <Text style={styles.ctrlBtnText}>Salvează</Text>
          </TouchableOpacity>
        )}
      </View>

      {showSaveActions && (
        <View style={styles.startRow}>
          <View style={styles.saveCard}>
            <Text style={styles.saveCardTitle}>Salvezi rezultatul în istoric?</Text>
            <View style={styles.saveCardRow}>
              <TouchableOpacity activeOpacity={0.85} onPress={handleSkipSave} style={styles.saveSkipBtn}>
                <Text style={styles.saveSkipText}>Nu salva</Text>
              </TouchableOpacity>
              <TouchableOpacity activeOpacity={0.85} onPress={handleSaveHistory} style={styles.saveSaveBtn}>
                <Text style={styles.saveSaveText}>Salvează</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* ── Results card ── */}
      <View style={styles.resultsCard}>
        <View style={styles.resultsHeader}>
          <Text style={styles.resultsHeaderText}>⠿ Rezultat live</Text>
          {recognizing && <ActivityIndicator size="small" color={VIOLET_M} style={{ marginLeft: 6 }} />}
        </View>

        {wordsRo.length > 0 ? (
          <>
            <Text style={styles.resultsWord}>{lastWordRo}</Text>
            {lastWordRo !== lastWordEn && (
              <Text style={styles.resultsWordEn}>{lastWordEn}</Text>
            )}
            {wordsRo.length > 1 && (
              <View style={styles.wordsHistory}>
                {wordsRo.slice(0, -1).map((w, i) => (
                  <View key={`${w}-${i}`} style={styles.wordChip}>
                    <Text style={styles.wordChipText}>{w}</Text>
                  </View>
                ))}
              </View>
            )}
          </>
        ) : (
          <Text style={styles.resultsEmpty}>
            Ține mâinile în cadru pentru a detecta un semn.
          </Text>
        )}

        {isRecording && !isPaused && topCandidates.length > 0 && (
          <View style={styles.candidatesBox}>
            <Text style={styles.candidatesTitle}>Top predicții:</Text>
            {topCandidates.map((c, i) => (
              <View key={c.label} style={styles.candidateRow}>
                <Text style={[styles.candidateLabel, i === 0 && styles.candidateLabelTop]}>{c.label}</Text>
                <View style={styles.candidateBarTrack}>
                  <View style={[styles.candidateBarFill, { width: `${c.conf}%`, opacity: i === 0 ? 1 : 0.5 }]} />
                </View>
                <Text style={styles.candidateConf}>{c.conf}%</Text>
              </View>
            ))}
          </View>
        )}

        <View style={styles.resultsFooter}>
          <View style={[styles.statusPill, isRecording && !isPaused && styles.statusPillActive]}>
            <View style={[styles.statusDot, isRecording && !isPaused && styles.statusDotActive]} />
            <Text style={[styles.statusText, isRecording && !isPaused && styles.statusTextActive]}>
              {isRecording && !isPaused ? statusMsg : isPaused ? 'Detecție în pauză' : 'Detecția nu este activă'}
            </Text>
          </View>
        </View>
      </View>

      {!!saveFeedback && <Text style={styles.feedbackText}>{saveFeedback}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: DARK },

  header: { paddingTop: 46, paddingHorizontal: 18, paddingBottom: 12, flexDirection: 'row', alignItems: 'center', gap: 12 },
  backBtn: { width: 38, height: 38, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.08)', justifyContent: 'center', alignItems: 'center' },
  backArrow:   { color: '#fff', fontSize: 20, fontWeight: '700' },
  headerTitle: { color: '#fff', fontSize: 18, fontWeight: '800' },
  headerSub:   { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '600', marginTop: 1 },
  liveBadge:   { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(22,163,74,0.13)', borderWidth: 1.5, borderColor: 'rgba(22,163,74,0.35)', borderRadius: 10, paddingHorizontal: 11, paddingVertical: 6 },
  liveDot:     { width: 7, height: 7, borderRadius: 4, backgroundColor: GREEN },
  liveText:    { color: GREEN, fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },

  viewfinderWrap: { marginHorizontal: 14, borderRadius: 28, overflow: 'hidden', flex: 1, minHeight: 220, backgroundColor: '#0E0720', position: 'relative' },
  camera: { flex: 1 },

  corner:   { position: 'absolute', width: 28, height: 28 },
  cornerTL: { top: 16, left: 16,  borderTopWidth: 3, borderLeftWidth: 3,  borderColor: VIOLET, borderTopLeftRadius: 6 },
  cornerTR: { top: 16, right: 16, borderTopWidth: 3, borderRightWidth: 3, borderColor: VIOLET, borderTopRightRadius: 6 },

  idleHint:     { position: 'absolute', bottom: 80, alignSelf: 'center', backgroundColor: 'rgba(0,0,0,0.45)', borderRadius: 12, paddingHorizontal: 16, paddingVertical: 8 },
  idleHintText: { color: 'rgba(255,255,255,0.5)', fontSize: 12, fontWeight: '600' },

  handsIndicator: { position: 'absolute', top: 14, alignSelf: 'center', flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(0,0,0,0.5)', borderRadius: 99, paddingHorizontal: 12, paddingVertical: 5 },
  handsDot:  { width: 8, height: 8, borderRadius: 4 },
  handsText: { color: '#fff', fontSize: 11, fontWeight: '600' },

  detectionCard:       { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(8,4,18,0.82)', paddingHorizontal: 18, paddingTop: 12, paddingBottom: 14 },
  detectionCardHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  detectedDot:         { width: 8, height: 8, borderRadius: 4, backgroundColor: GREEN },
  detectedLabel:       { color: GREEN, fontSize: 12, fontWeight: '700' },
  detectedWord:        { color: '#fff', fontSize: 28, fontWeight: '900', marginBottom: 8, letterSpacing: -0.5 },
  detectedWordEn:      { color: 'rgba(255,255,255,0.38)', fontSize: 13, fontWeight: '600', marginTop: -4, marginBottom: 6, fontStyle: 'italic' },
  detectionPills:      { flexDirection: 'row', alignItems: 'center', gap: 8 },
  pill:                { flexDirection: 'row', alignItems: 'center', gap: 5 },
  pillText:            { color: 'rgba(255,255,255,0.7)', fontSize: 12, fontWeight: '600' },
  pillDivider:         { width: 1, height: 14, backgroundColor: 'rgba(255,255,255,0.2)' },

  flipBtn: { position: 'absolute', bottom: 14, right: 14, width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(0,0,0,0.5)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', justifyContent: 'center', alignItems: 'center' },
  flipText: { color: '#fff', fontSize: 20 },

  controlsRow: { flexDirection: 'row', gap: 8, paddingHorizontal: 14, paddingVertical: 12 },
  ctrlBtn: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)', paddingVertical: 12, paddingHorizontal: 6 },
  ctrlBtnActive:     { backgroundColor: 'rgba(124,58,237,0.18)', borderColor: 'rgba(124,58,237,0.4)' },
  ctrlBtnStop:       { backgroundColor: '#7F1D1D', borderColor: '#991B1B' },
  ctrlBtnSave:       { backgroundColor: VIOLET, borderColor: VIOLET },
  ctrlBtnText:       { color: '#fff', fontSize: 11, fontWeight: '700' },
  ctrlBtnTextActive: { color: '#A78BFA' },

  startRow: { paddingHorizontal: 14, paddingVertical: 12 },
  startBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, backgroundColor: VIOLET, borderRadius: 18, paddingVertical: 15, shadowColor: VIOLET, shadowOffset: { width: 0, height: 6 }, shadowOpacity: 0.4, shadowRadius: 20, elevation: 4 },
  startBtnText: { color: '#fff', fontSize: 15, fontWeight: '800' },

  saveCard:      { backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 18, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)', paddingHorizontal: 16, paddingVertical: 14 },
  saveCardTitle: { color: '#fff', fontSize: 14, fontWeight: '800', marginBottom: 12 },
  saveCardRow:   { flexDirection: 'row', gap: 10 },
  saveSkipBtn:   { flex: 1, borderRadius: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.12)', paddingVertical: 11, alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.04)' },
  saveSkipText:  { color: 'rgba(255,255,255,0.65)', fontSize: 13, fontWeight: '700' },
  saveSaveBtn:   { flex: 1, borderRadius: 12, paddingVertical: 11, alignItems: 'center', backgroundColor: VIOLET },
  saveSaveText:  { color: '#fff', fontSize: 13, fontWeight: '800' },

  resultsCard: { marginHorizontal: 14, marginBottom: 12, backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: 22, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)', paddingHorizontal: 18, paddingTop: 14, paddingBottom: 14 },
  resultsHeader:     { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  resultsHeaderText: { color: 'rgba(255,255,255,0.45)', fontSize: 12, fontWeight: '700', flex: 1 },
  resultsWord:       { color: VIOLET_M, fontSize: 26, fontWeight: '900', marginBottom: 4, letterSpacing: -0.3 },
  resultsWordEn:     { color: 'rgba(167,139,250,0.45)', fontSize: 13, fontWeight: '600', marginTop: -2, marginBottom: 4, fontStyle: 'italic' },
  resultsEmpty:      { color: 'rgba(255,255,255,0.3)', fontSize: 13, fontWeight: '600', lineHeight: 20, marginBottom: 4 },

  wordsHistory: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 6 },
  wordChip:     { backgroundColor: 'rgba(124,58,237,0.18)', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 4 },
  wordChipText: { color: '#C4B5FD', fontSize: 12, fontWeight: '600' },

  resultsFooter:    { marginTop: 10 },
  statusPill:       { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 99, paddingHorizontal: 12, paddingVertical: 6, borderWidth: 1, borderColor: 'rgba(255,255,255,0.07)' },
  statusPillActive: { backgroundColor: 'rgba(22,163,74,0.12)', borderColor: 'rgba(22,163,74,0.25)' },
  statusDot:        { width: 7, height: 7, borderRadius: 4, backgroundColor: 'rgba(255,255,255,0.2)' },
  statusDotActive:  { backgroundColor: GREEN },
  statusText:       { color: 'rgba(255,255,255,0.4)', fontSize: 12, fontWeight: '600' },
  statusTextActive: { color: GREEN },

  feedbackText: { color: 'rgba(255,255,255,0.55)', fontSize: 12, fontWeight: '700', textAlign: 'center', marginBottom: 8 },

  candidatesBox:      { marginTop: 8, marginBottom: 4, backgroundColor: 'rgba(124,58,237,0.08)', borderRadius: 14, borderWidth: 1, borderColor: 'rgba(124,58,237,0.2)', paddingHorizontal: 12, paddingVertical: 10, gap: 6 },
  candidatesTitle:    { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '700', marginBottom: 4, letterSpacing: 0.3 },
  candidateRow:       { flexDirection: 'row', alignItems: 'center', gap: 8 },
  candidateLabel:     { color: 'rgba(255,255,255,0.55)', fontSize: 12, fontWeight: '600', width: 90 },
  candidateLabelTop:  { color: '#DDD6FE', fontWeight: '800' },
  candidateBarTrack:  { flex: 1, height: 4, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' },
  candidateBarFill:   { height: '100%', backgroundColor: VIOLET, borderRadius: 2 },
  candidateConf:      { color: 'rgba(255,255,255,0.38)', fontSize: 11, fontWeight: '600', width: 32, textAlign: 'right' },
});
