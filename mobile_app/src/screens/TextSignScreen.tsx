import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Image,
} from 'react-native';
import { Colors } from '../theme';
import { ArrowLeftIcon, PlayIcon } from '../components/Icons';
import { HistoryEntry } from './HistoryScreen';
import ApiService from '../services/ApiService';
import { getApiBaseUrl } from '../config/network';

const RangeInput = 'input' as any;

type FrameItem = { word: string; image: string };

interface TextSignScreenProps {
  onBack?: () => void;
  onSaveHistory?: (entry: any) => void;
  onCompleteSession?: (type: 'text-to-sign') => void;
  replayEntry?: HistoryEntry | null;
  replayToken?: number;
  onReplayHandled?: () => void;
  initialText?: string;
  exactLookup?: string;
  exactLookupType?: 'english' | 'romanian';
  initialPlaybackToken?: number;
  onInitialPlaybackHandled?: () => void;
  initialSpeed?: number;
}

const TextSignScreen: React.FC<TextSignScreenProps> = ({
  onBack,
  onSaveHistory,
  onCompleteSession,
  replayEntry,
  replayToken,
  onReplayHandled,
  initialText,
  exactLookup,
  exactLookupType,
  initialPlaybackToken,
  onInitialPlaybackHandled,
  initialSpeed,
}) => {
  const [text, setText] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSigning, setIsSigning] = React.useState(false);
  const [currentWord, setCurrentWord] = React.useState('');
  const [errorMessage, setErrorMessage] = React.useState('');
  const [speed, setSpeed] = React.useState(initialSpeed ?? 1);
  const [loops, setLoops] = React.useState(1);
  const [loopCount, setLoopCount] = React.useState(0);
  const [finished, setFinished] = React.useState(false);
  const [wordIndex, setWordIndex] = React.useState(0);
  const [showSaveActions, setShowSaveActions] = React.useState(false);
  const [saveFeedback, setSaveFeedback] = React.useState('');
  const [currentFrameImage, setCurrentFrameImage] = React.useState('');

  const queueRef = React.useRef<FrameItem[]>([]);
  const archiveRef = React.useRef<FrameItem[]>([]);
  const frameTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestKeyRef = React.useRef(0);
  const streamDoneRef = React.useRef(false);
  const seenWordsRef = React.useRef<string[]>([]);
  const loopCountRef = React.useRef(0);
  const saveEntryRef = React.useRef<any | null>(null);
  const shouldPromptSaveRef = React.useRef(false);
  const shouldReportProgressRef = React.useRef(false);
  const exactLookupRef = React.useRef<{ value?: string; type?: 'english' | 'romanian' }>({});

  const words = React.useMemo(() => text.trim().split(/\s+/).filter(Boolean), [text]);

  const stopAll = React.useCallback(() => {
    requestKeyRef.current += 1;
    if (frameTimerRef.current !== null) {
      clearTimeout(frameTimerRef.current);
      frameTimerRef.current = null;
    }
    queueRef.current = [];
    archiveRef.current = [];
    seenWordsRef.current = [];
    streamDoneRef.current = false;
    setIsSigning(false);
    setCurrentWord('');
    setCurrentFrameImage('');
    setLoopCount(0);
    loopCountRef.current = 0;
    setWordIndex(0);
  }, []);

  const scheduleLoop = React.useCallback((currentSpeed: number, currentLoops: number) => {
    const msPerFrame = 1000 / (12 * currentSpeed);

    const tick = () => {
      if (queueRef.current.length > 0) {
        const frame = queueRef.current.shift()!;
        setCurrentFrameImage(frame.image);
        setCurrentWord(frame.word);
        if (seenWordsRef.current[seenWordsRef.current.length - 1] !== frame.word) {
          seenWordsRef.current = [...seenWordsRef.current, frame.word];
          const idx = words.findIndex(word => word.toLowerCase() === frame.word.toLowerCase());
          if (idx >= 0) setWordIndex(idx);
        }
      }

      if (streamDoneRef.current && queueRef.current.length === 0) {
        if (loopCountRef.current + 1 < currentLoops && archiveRef.current.length > 0) {
          queueRef.current = archiveRef.current.map(frame => ({ ...frame }));
          seenWordsRef.current = [];
          setCurrentWord('');
          setWordIndex(0);
          loopCountRef.current += 1;
          setLoopCount(loopCountRef.current);
          streamDoneRef.current = true;
        } else {
          setIsSigning(false);
          setFinished(true);
          setCurrentWord('');
          setCurrentFrameImage('');
          if (shouldPromptSaveRef.current && saveEntryRef.current) {
            setShowSaveActions(true);
          }
          frameTimerRef.current = null;
          return;
        }
      }

      frameTimerRef.current = setTimeout(tick, msPerFrame);
    };

    frameTimerRef.current = setTimeout(tick, msPerFrame);
  }, [words]);

  const startPlayback = React.useCallback(async (inputText: string, options?: { promptSave?: boolean; reportProgress?: boolean; lookup?: string; lookupType?: 'english' | 'romanian' }) => {
    const cleanText = inputText.trim();
    if (!cleanText || isLoading || isSigning) return;

    stopAll();
    const requestKey = requestKeyRef.current;
    setIsLoading(true);
    setFinished(false);
    setErrorMessage('');
    setLoopCount(0);
    setWordIndex(0);
    setShowSaveActions(false);
    setSaveFeedback('');

    shouldPromptSaveRef.current = options?.promptSave ?? true;
    shouldReportProgressRef.current = options?.reportProgress ?? true;
    exactLookupRef.current = {
      value: options?.lookup,
      type: options?.lookupType,
    };
    saveEntryRef.current = {
      type: 'text-to-sign',
      text: cleanText,
      words: cleanText.split(/\s+/).filter(Boolean),
      timestamp: new Date().toISOString(),
    };

    const playbackText = (options?.lookup || cleanText).trim();

    try {
      const response = await ApiService.getSignAvatarFrames(
        cleanText,
        options?.lookup,
        cleanText,
      );
      if (requestKeyRef.current !== requestKey) return;

      const frames = Array.isArray(response?.frames)
        ? response.frames
            .filter((frame: any) => typeof frame?.image === 'string' && frame.image.length > 0)
            .map((frame: any) => ({
              word: frame.word || cleanText,
              image: frame.image,
            }))
        : [];

      if (frames.length === 0) {
        throw new Error('Nu am primit cadre de animație de la server.');
      }

      queueRef.current = frames.map(frame => ({ ...frame }));
      archiveRef.current = frames.map(frame => ({ ...frame }));
      streamDoneRef.current = true;
      setIsLoading(false);
      setIsSigning(true);
      if (shouldReportProgressRef.current) {
        shouldReportProgressRef.current = false;
        onCompleteSession?.('text-to-sign');
      }
      scheduleLoop(speed, loops);
    } catch (error: any) {
      if (requestKeyRef.current !== requestKey) return;
      const backendMessage =
        error?.response?.data?.error ||
        error?.message ||
        'Conexiunea la server a eșuat. Verifică backend-ul.';
      setErrorMessage(String(backendMessage));
      setIsLoading(false);
      stopAll();
    }
  }, [isLoading, isSigning, loops, onCompleteSession, scheduleLoop, speed, stopAll]);

  const handlePlay = React.useCallback(() => {
    startPlayback(text, {
      promptSave: true,
      reportProgress: true,
      lookup: exactLookupRef.current.value,
      lookupType: exactLookupRef.current.type,
    });
  }, [startPlayback, text]);

  const handleReplayPlayback = React.useCallback(() => {
    startPlayback(text, {
      promptSave: false,
      reportProgress: false,
      lookup: exactLookupRef.current.value,
      lookupType: exactLookupRef.current.type,
    });
  }, [startPlayback, text]);

  const handleSaveHistory = React.useCallback(async () => {
    if (!onSaveHistory || !saveEntryRef.current) return;
    await Promise.resolve(onSaveHistory(saveEntryRef.current));
    setShowSaveActions(false);
    setSaveFeedback('Salvat în istoric');
  }, [onSaveHistory]);

  const handleSkipSave = React.useCallback(() => {
    setShowSaveActions(false);
    setSaveFeedback('Nu a fost salvat');
  }, []);

  React.useEffect(() => {
    if (!replayToken || !replayEntry || replayEntry.type !== 'text-to-sign') return;
    const replayText = replayEntry.text?.trim();
    onReplayHandled?.();
    if (!replayText) return;
    setText(replayText);
    exactLookupRef.current = {};
    startPlayback(replayText, { promptSave: false, reportProgress: false });
  }, [onReplayHandled, replayEntry, replayToken, startPlayback]);

  React.useEffect(() => {
    if (!initialPlaybackToken || !initialText?.trim()) return;
    setText(initialText);
    exactLookupRef.current = {
      value: exactLookup,
      type: exactLookupType,
    };
    onInitialPlaybackHandled?.();
    startPlayback(initialText, {
      promptSave: false,
      reportProgress: false,
      lookup: exactLookup,
      lookupType: exactLookupType,
    });
  }, [
    exactLookup,
    exactLookupType,
    initialPlaybackToken,
    initialText,
    onInitialPlaybackHandled,
    startPlayback,
  ]);

  React.useEffect(() => () => stopAll(), [stopAll]);

  return (
    <View style={styles.container}>
      <View style={[styles.header, { background: 'linear-gradient(145deg,#134E4A,#0F766E)' } as any]}>
        <View style={styles.headerRow}>
          {onBack && (
            <TouchableOpacity onPress={onBack} style={styles.backButton} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>
          )}
          <View>
            <Text style={styles.headerTitle}>Text → Semn</Text>
            <Text style={styles.headerSub}>Avatar 3D animat</Text>
          </View>
        </View>
      </View>

      {}
      <View style={styles.stageWrap}>
        <View style={[styles.stage, { background: 'linear-gradient(160deg,#1E1540 0%,#111827 100%)' } as any]}>
          {isSigning && loops > 1 && (
            <View style={styles.loopIndicator}>
              <Text style={styles.loopIndicatorText}>{loopCount + 1} / {loops}</Text>
            </View>
          )}

          {!isSigning && words.length === 0 && (
            <View style={styles.stageHint}>
              <Text style={styles.stageHintText}>Scrie un text mai jos</Text>
            </View>
          )}

          <View style={styles.canvas}>
            {!!currentFrameImage && (
              <Image source={{ uri: currentFrameImage }} style={styles.frameImage} resizeMode="cover" />
            )}
          </View>

          {isLoading && (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color={Colors.teal} />
              <Text style={styles.loadingText}>Se semnează...</Text>
            </View>
          )}

          {errorMessage && !isLoading && !isSigning && (
            <View style={styles.errorOverlay}>
              <Text style={styles.errorText}>{errorMessage}</Text>
            </View>
          )}

          {isSigning && words.length > 0 && (
            <View style={styles.progressRow}>
              {words.map((_, index) => (
                <View
                  key={`${index}-${words.length}`}
                  style={[
                    styles.progressDot,
                    index < wordIndex && styles.progressDotDone,
                    index === wordIndex && styles.progressDotActive,
                  ]}
                />
              ))}
            </View>
          )}

          <Text style={[styles.stageStatus, (isSigning || finished) && styles.stageStatusActive]}>
            {isSigning ? 'Se semnează...' : finished ? 'Finalizat' : 'Apasă play pentru a începe'}
          </Text>
        </View>
      </View>

      {}
      <View style={styles.bottomPanel}>
        {}
        <View style={styles.controlsRow}>
          <View style={styles.controlHalf}>
            <Text style={styles.controlLabel}>Repetări: <Text style={styles.controlVal}>{loops === 99 ? 'Inf' : `${loops}x`}</Text></Text>
            <View style={styles.repeatRow}>
              {[1, 2, 3, 5, 99].map(value => (
                <TouchableOpacity
                  key={value}
                  activeOpacity={0.85}
                  onPress={() => setLoops(value)}
                  style={[styles.repeatButton, loops === value && styles.repeatButtonActive]}>
                  <Text style={[styles.repeatButtonText, loops === value && styles.repeatButtonTextActive]}>
                    {value === 99 ? 'Inf' : `${value}x`}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.controlHalf}>
            <Text style={styles.controlLabel}>Viteză: <Text style={[styles.controlVal, styles.controlValueTeal]}>{speed}x</Text></Text>
            <View style={styles.sliderWrap}>
              <View style={styles.sliderTrack}>
                <View style={[styles.sliderFill, { width: `${((speed - 0.5) / 1.5) * 100}%` } as any]} />
              </View>
              <RangeInput
                type="range"
                min={0.5}
                max={2}
                step={0.5}
                value={speed}
                onChange={(e: any) => setSpeed(Number(e.target.value))}
                style={styles.sliderInput as any}
              />
            </View>
          </View>
        </View>

        {}
        <View style={styles.inputRow}>
          <View style={styles.inputCard}>
            <TextInput
              value={text}
              onChangeText={value => {
                setText(value);
                setShowSaveActions(false);
                setSaveFeedback('');
                exactLookupRef.current = {};
              }}
              placeholder="Scrie un text în română..."
              placeholderTextColor={Colors.sub}
              style={styles.input}
            />
          </View>

          <TouchableOpacity
            activeOpacity={0.9}
            onPress={handlePlay}
            disabled={!words.length || isSigning || isLoading}
            style={[styles.playButton, (!words.length || isSigning || isLoading) && styles.playButtonDisabled]}>
            <PlayIcon color="#FFFFFF" size={18} />
          </TouchableOpacity>
        </View>

        {}
        {finished && !isSigning && words.length > 0 && (
          <TouchableOpacity activeOpacity={0.85} onPress={handleReplayPlayback} style={styles.replayButton}>
            <Text style={styles.replayButtonText}>↺ Replay</Text>
          </TouchableOpacity>
        )}

        {showSaveActions && (
          <View style={styles.saveActionsRow}>
            <TouchableOpacity activeOpacity={0.85} onPress={handleSkipSave} style={styles.skipSaveButton}>
              <Text style={styles.skipSaveButtonText}>Nu salva</Text>
            </TouchableOpacity>
            <TouchableOpacity activeOpacity={0.85} onPress={handleSaveHistory} style={styles.saveHistoryButton}>
              <Text style={styles.saveHistoryButtonText}>Salvează</Text>
            </TouchableOpacity>
          </View>
        )}

        {!!saveFeedback && <Text style={styles.saveFeedbackText}>{saveFeedback}</Text>}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 20,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  backButton: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '800',
  },
  headerSub: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 1,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 18,
  },
  stageWrap: {
    flex: 1,
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 10,
  },
  stage: {
    flex: 1,
    borderRadius: 28,
    overflow: 'hidden',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    alignItems: 'center',
    position: 'relative',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 32,
    elevation: 4,
  },
  loopIndicator: {
    position: 'absolute',
    top: 14,
    left: 16,
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 11,
    paddingVertical: 4,
    zIndex: 3,
  },
  loopIndicatorText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 11,
    fontWeight: '700',
  },
  wordBubble: {
    position: 'absolute',
    top: 16,
    alignSelf: 'center',
    backgroundColor: Colors.teal,
    borderRadius: 14,
    paddingHorizontal: 18,
    paddingVertical: 6,
    zIndex: 3,
    shadowColor: Colors.teal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
    elevation: 4,
  },
  wordBubbleText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '800',
  },
  stageHint: {
    position: 'absolute',
    top: 18,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    paddingHorizontal: 14,
    paddingVertical: 5,
    zIndex: 2,
  },
  stageHintText: {
    color: 'rgba(255,255,255,0.3)',
    fontSize: 11,
    fontWeight: '600',
  },
  canvas: {
    width: '100%',
    flex: 1,
    marginTop: 10,
    overflow: 'hidden',
    borderRadius: 14,
    backgroundColor: 'rgba(0,0,0,0.15)',
    position: 'relative',
  },
  frameImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  videoFrame: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    backgroundColor: '#130f1f',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.35)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
    marginTop: 8,
  },
  errorOverlay: {
    position: 'absolute',
    bottom: 44,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(220,38,38,0.15)',
    borderColor: 'rgba(220,38,38,0.3)',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  progressRow: {
    flexDirection: 'row',
    gap: 5,
    marginTop: 8,
  },
  progressDot: {
    width: 16,
    height: 5,
    borderRadius: 99,
    backgroundColor: 'rgba(255,255,255,0.15)',
  },
  progressDotActive: {
    backgroundColor: '#FFFFFF',
  },
  progressDotDone: {
    backgroundColor: Colors.teal,
  },
  stageStatus: {
    color: 'rgba(255,255,255,0.25)',
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.9,
    marginTop: 10,
  },
  stageStatusActive: {
    color: Colors.teal,
  },
  bottomPanel: {
    backgroundColor: Colors.card,
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 14,
  },
  controlsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 10,
  },
  controlHalf: {
    flex: 1,
  },
  controlLabel: {
    color: Colors.ink,
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 6,
  },
  controlVal: {
    color: Colors.violet,
    fontSize: 12,
    fontWeight: '800',
  },
  inputRow: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
  },
  controlCard: {
    marginHorizontal: 16,
    marginTop: 12,
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    paddingHorizontal: 16,
    paddingVertical: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },
  controlTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  controlTitle: {
    color: Colors.ink,
    fontSize: 13,
    fontWeight: '700',
  },
  controlValue: {
    color: Colors.violet,
    fontSize: 13,
    fontWeight: '800',
  },
  controlValueTeal: {
    color: Colors.teal,
  },
  repeatRow: {
    flexDirection: 'row',
    gap: 8,
  },
  repeatButton: {
    flex: 1,
    borderRadius: 12,
    backgroundColor: Colors.violetL,
    paddingVertical: 9,
    justifyContent: 'center',
    alignItems: 'center',
  },
  repeatButtonActive: {
    backgroundColor: Colors.violet,
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 2,
  },
  repeatButtonText: {
    color: Colors.violet,
    fontSize: 13,
    fontWeight: '800',
  },
  repeatButtonTextActive: {
    color: '#FFFFFF',
  },
  sliderWrap: {
    position: 'relative',
    height: 52,
    justifyContent: 'center',
  },
  sliderTrack: {
    height: 6,
    borderRadius: 99,
    backgroundColor: Colors.tealL,
    overflow: 'hidden',
  },
  sliderFill: {
    height: '100%',
    borderRadius: 99,
    backgroundColor: Colors.teal,
  },
  sliderInput: {
    position: 'absolute',
    left: 0,
    right: 0,
    width: '100%',
    opacity: 0,
    height: 36,
    margin: 0,
  },
  sliderLabels: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 30,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  sliderLabel: {
    color: Colors.sub,
    fontSize: 10,
    fontWeight: '600',
  },
  sliderLabelActive: {
    color: Colors.teal,
    fontWeight: '800',
  },
  inputWrap: {
    paddingHorizontal: 16,
    paddingTop: 12,
    flex: 1,
  },
  inputCard: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: Colors.rule,
    paddingHorizontal: 12,
    paddingVertical: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },
  input: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '600',
  },
  playButton: {
    width: 48,
    height: 48,
    backgroundColor: Colors.teal,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
    shadowColor: Colors.teal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 3,
  },
  playButtonDisabled: {
    backgroundColor: '#D1D5DB',
    shadowOpacity: 0,
    elevation: 0,
  },
  playButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  replayButton: {
    marginTop: 8,
    backgroundColor: Colors.violetL,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    paddingVertical: 10,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
  },
  replayButtonIcon: {
    color: Colors.violet,
    fontSize: 12,
    fontWeight: '800',
  },
  replayButtonText: {
    color: Colors.violet,
    fontSize: 14,
    fontWeight: '800',
  },
  saveActionsCard: {
    marginHorizontal: 16,
    marginTop: 10,
    backgroundColor: Colors.card,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    paddingHorizontal: 14,
    paddingVertical: 14,
  },
  saveActionsTitle: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '800',
  },
  saveActionsRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 8,
  },
  skipSaveButton: {
    flex: 1,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  skipSaveButtonText: {
    color: Colors.sub,
    fontSize: 13,
    fontWeight: '700',
  },
  saveHistoryButton: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.violet,
  },
  saveHistoryButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  saveFeedbackText: {
    marginTop: 10,
    marginHorizontal: 18,
    color: Colors.sub,
    fontSize: 12,
    fontWeight: '700',
    textAlign: 'center',
  },
});

export default TextSignScreen;
