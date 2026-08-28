import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { Colors } from '../theme';
import { CameraIcon, TextIcon, ArrowLeftIcon, PlayIcon, HandIcon, TrashIcon } from '../components/Icons';

export interface HistoryEntry {
  id: string;
  type: 'sign-to-text' | 'text-to-sign';
  words?: string[];
  text?: string;
  outputText?: string;
  confidence?: number | null;
  timestamp: string;
}

interface HistoryScreenProps {
  history: HistoryEntry[];
  onDelete: (id: string) => void;
  onClearAll: () => void;
  onReplay: (entry: HistoryEntry) => void;
  onBack?: () => void;
}

const HistoryScreen: React.FC<HistoryScreenProps> = ({
  history,
  onDelete,
  onClearAll,
  onReplay,
  onBack,
}) => {
  const [filter, setFilter] = React.useState<'all' | 'sign-to-text' | 'text-to-sign'>('all');
  const [confirmClear, setConfirmClear] = React.useState(false);

  const filtered = history.filter(item => filter === 'all' || item.type === filter);

  const handleClear = () => {
    if (confirmClear) {
      onClearAll();
      setConfirmClear(false);
      return;
    }
    setConfirmClear(true);
    setTimeout(() => setConfirmClear(false), 3000);
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return 'Acum';
    if (diff < 3600) return `${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return d.toLocaleDateString('ro-RO', { day: 'numeric', month: 'short' });
  };

  return (
    <View style={styles.container}>
      <View style={[styles.header, { background: 'linear-gradient(145deg,#1E1540,#2D1B69)' } as any]}>
        <View style={styles.headerTop}>
          <View style={styles.headerLeft}>
            {onBack && (
              <TouchableOpacity onPress={onBack} style={styles.backButton} activeOpacity={0.85}>
                <ArrowLeftIcon color="#FFFFFF" size={18} />
              </TouchableOpacity>
            )}
            <View>
              <Text style={styles.headerTitle}>Istoric</Text>
              <Text style={styles.headerSub}>{history.length} traduceri salvate</Text>
            </View>
          </View>

          {history.length > 0 && (
            <TouchableOpacity
              onPress={handleClear}
              activeOpacity={0.85}
              style={[styles.clearButton, confirmClear && styles.clearButtonDanger]}>
              <Text style={[styles.clearButtonText, confirmClear && styles.clearButtonTextDanger]}>
                {confirmClear ? 'Confirmi?' : 'Sterge tot'}
              </Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.filterRow}>
          {[
            { id: 'all' as const, label: 'Toate' },
            { id: 'sign-to-text' as const, label: 'Semn → Text' },
            { id: 'text-to-sign' as const, label: 'Text → Semn' },
          ].map(item => (
            <TouchableOpacity
              key={item.id}
              onPress={() => setFilter(item.id)}
              activeOpacity={0.85}
              style={[styles.filterPill, filter === item.id && styles.filterPillActive]}>
              <Text style={[styles.filterPillText, filter === item.id && styles.filterPillTextActive]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {filtered.length === 0 ? (
        <View style={styles.emptyState}>
          <View style={styles.emptyIconBox}>
            <HandIcon size={40} />
          </View>
          <Text style={styles.emptyTitle}>Niciun istoric</Text>
          <Text style={styles.emptySub}>Traducerile tale vor apărea aici{'\n'}după prima utilizare</Text>
          <TouchableOpacity activeOpacity={0.88} onPress={onBack} style={styles.emptyButton}>
            <Text style={styles.emptyButtonText}>Începe o traducere</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView style={styles.list} contentContainerStyle={styles.listContent} showsVerticalScrollIndicator={false}>
          {filtered.map((entry, index) => {
            const isCamera = entry.type === 'sign-to-text';
            return (
              <View key={entry.id} style={styles.card}>
                <View style={styles.cardRow}>
                  <View style={[styles.typeIconBox, { backgroundColor: isCamera ? '#EDE9FE' : '#CCFBF1' }]}>
                    {isCamera ? <CameraIcon color={Colors.violet} size={20} /> : <TextIcon color={Colors.teal} size={20} />}
                  </View>

                  <View style={styles.cardContent}>
                    <View style={styles.cardHeader}>
                      <View style={[styles.typePill, { backgroundColor: isCamera ? '#EDE9FE' : '#CCFBF1' }]}>
                        <Text style={[styles.typePillText, { color: isCamera ? Colors.violet : Colors.teal }]}>
                          {isCamera ? 'Semn → Text' : 'Text → Semn'}
                        </Text>
                      </View>
                      <Text style={styles.timeText}>{formatTime(entry.timestamp)}</Text>
                    </View>

                    {entry.words && entry.words.length > 0 && (
                      <View style={styles.wordsWrap}>
                        {entry.words.map((word, wordIndex) => (
                          <View key={`${entry.id}-${wordIndex}`} style={styles.wordChip}>
                            <Text style={styles.wordChipText}>{word}</Text>
                          </View>
                        ))}
                      </View>
                    )}

                    {entry.type === 'text-to-sign' && entry.text ? (
                      <Text style={styles.quoteText}>"{entry.text}"</Text>
                    ) : null}
                  </View>
                </View>

                <View style={styles.actionRow}>
                  <TouchableOpacity activeOpacity={0.85} onPress={() => onReplay(entry)} style={styles.replayButton}>
                    <PlayIcon color={Colors.violet} size={13} />
                    <Text style={styles.replayButtonText}>Reia</Text>
                  </TouchableOpacity>
                  <TouchableOpacity activeOpacity={0.85} onPress={() => onDelete(entry.id)} style={styles.deleteButton}>
                    <TrashIcon color={Colors.red} size={16} />
                  </TouchableOpacity>
                </View>
              </View>
            );
          })}
        </ScrollView>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    paddingBottom: 16,
  },
  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 24,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerLeft: {
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
    color: 'rgba(255,255,255,0.45)',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 1,
  },
  clearButton: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    paddingHorizontal: 13,
    paddingVertical: 7,
  },
  clearButtonDanger: {
    backgroundColor: 'rgba(220,38,38,0.2)',
    borderColor: 'rgba(220,38,38,0.4)',
  },
  clearButtonText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 11,
    fontWeight: '700',
  },
  clearButtonTextDanger: {
    color: '#FCA5A5',
  },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
  },
  filterPill: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 99,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  filterPillActive: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderColor: 'rgba(255,255,255,0.3)',
  },
  filterPillText: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 11,
    fontWeight: '700',
  },
  filterPillTextActive: {
    color: '#FFFFFF',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingTop: 60,
  },
  emptyIconBox: {
    width: 72,
    height: 72,
    borderRadius: 22,
    backgroundColor: Colors.violetL,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyTitle: {
    color: Colors.ink,
    fontSize: 16,
    fontWeight: '800',
  },
  emptySub: {
    color: Colors.sub,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 6,
    lineHeight: 21,
    textAlign: 'center',
  },
  emptyButton: {
    backgroundColor: Colors.violet,
    borderRadius: 14,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 20,
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 18,
    elevation: 3,
  },
  emptyButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 112,
  },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  cardRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  typeIconBox: {
    width: 44,
    height: 44,
    borderRadius: 13,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  cardContent: {
    flex: 1,
    minWidth: 0,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  typePill: {
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  typePillText: {
    fontSize: 10,
    fontWeight: '700',
  },
  timeText: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '600',
  },
  wordsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 5,
  },
  wordChip: {
    backgroundColor: '#F3F0FF',
    borderRadius: 8,
    paddingHorizontal: 9,
    paddingVertical: 3,
  },
  wordChipText: {
    color: Colors.violet,
    fontSize: 12,
    fontWeight: '700',
  },
  quoteText: {
    color: Colors.sub,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 6,
    paddingLeft: 8,
    borderLeftWidth: 3,
    borderLeftColor: Colors.teal,
    lineHeight: 19,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
  },
  replayButton: {
    flex: 1,
    backgroundColor: Colors.violetL,
    borderRadius: 11,
    paddingVertical: 8,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    gap: 5,
  },
  replayButtonText: {
    color: Colors.violet,
    fontSize: 12,
    fontWeight: '700',
  },
  deleteButton: {
    width: 38,
    borderRadius: 11,
    backgroundColor: '#FEE2E2',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default HistoryScreen;
