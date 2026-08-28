import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
} from 'react-native';
import { Colors } from '../theme';
import { ArrowLeftIcon, SearchIcon, PlayIcon, HandIcon } from '../components/Icons';
import type { DictionaryCategory, DictionaryEntry } from '../services/ApiService';
import dictionaryCatalog from '../data/dictionaryCatalog.json';

const LEVEL_BG: Record<string, string> = {
  Usor: Colors.greenL,
  Mediu: Colors.amberL,
  Dificil: '#FEE2E2',
};

interface DictionaryScreenProps {
  onBack?: () => void;
  onPracticeSign?: (entry: DictionaryEntry) => void;
}

const DictionaryScreen: React.FC<DictionaryScreenProps> = ({ onBack, onPracticeSign }) => {
  const [query, setQuery] = React.useState('');
  const [category, setCategory] = React.useState('Toate');
  const [openWord, setOpenWord] = React.useState<string | null>(null);
  const [entries, setEntries] = React.useState<DictionaryEntry[]>([]);
  const [categories, setCategories] = React.useState<DictionaryCategory[]>([{ name: 'Toate', count: 0 }]);
  const [catalogTotal, setCatalogTotal] = React.useState(1240);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      const catalogEntries = (dictionaryCatalog.entries || []) as DictionaryEntry[];
      const normalizedQuery = query.trim().toLocaleLowerCase('ro-RO');

      const filteredEntries = catalogEntries.filter(entry => {
        const matchesCategory = category === 'Toate' || entry.category === category;
        if (!matchesCategory) {
          return false;
        }

        if (!normalizedQuery) {
          return true;
        }

        const haystack = [
          entry.word,
          entry.lookup,
          entry.category,
        ]
          .join(' ')
          .toLocaleLowerCase('ro-RO');

        return haystack.includes(normalizedQuery);
      });

      const categoryMap = new Map<string, number>();
      catalogEntries.forEach(entry => {
        categoryMap.set(entry.category, (categoryMap.get(entry.category) || 0) + 1);
      });

      const nextCategories: DictionaryCategory[] = [
        { name: 'Toate', count: catalogEntries.length },
        ...Array.from(categoryMap.entries())
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ro-RO'))
          .map(([name, count]) => ({ name, count })),
      ];

      setEntries(filteredEntries);
      setCategories(nextCategories);
      setCatalogTotal(catalogEntries.length);
      setTotal(filteredEntries.length);
      setLoading(false);
    }, 180);

    return () => clearTimeout(timer);
  }, [category, query]);

  return (
    <View style={styles.container}>
      <View style={[styles.header, { background: 'linear-gradient(145deg,#1E3A5F,#1D4ED8)' } as any]}>
        <View style={styles.headerTop}>
          {onBack && (
            <TouchableOpacity onPress={onBack} style={styles.backButton} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>
          )}
          <View>
            <Text style={styles.headerTitle}>Dicționar LSR</Text>
            <Text style={styles.headerSub}>{catalogTotal.toLocaleString('ro-RO')} de semne</Text>
          </View>
        </View>

        <View style={styles.searchBox}>
          <SearchIcon color="rgba(255,255,255,0.5)" size={18} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Caută un semn..."
            placeholderTextColor="rgba(255,255,255,0.4)"
            style={styles.searchInput}
          />
        </View>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll} contentContainerStyle={styles.categoryContent}>
        {categories.map(item => (
          <TouchableOpacity
            key={item.name}
            activeOpacity={0.85}
            onPress={() => setCategory(item.name)}
            style={[styles.categoryPill, category === item.name && styles.categoryPillActive]}>
            <Text style={[styles.categoryText, category === item.name && styles.categoryTextActive]}>
              {item.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.resultsText}>{loading ? 'Se încarcă...' : `${total} semne cu animație`}</Text>

      {loading ? (
        <View style={styles.loadingWrap}>
          <Text style={styles.emptyText}>Se încarcă dicționarul...</Text>
        </View>
      ) : (
        <ScrollView style={styles.list} contentContainerStyle={styles.listContent} showsVerticalScrollIndicator={false}>
          {entries.length === 0 && (
            <View style={styles.emptyWrap}>
              <Text style={styles.emptyText}>Nu am găsit semne pentru căutarea ta.</Text>
            </View>
          )}
          {entries.map((sign, index) => {
            const open = openWord === sign.id;
            return (
              <TouchableOpacity
                key={`${sign.id}-${index}`}
                activeOpacity={0.9}
                onPress={() => setOpenWord(open ? null : sign.id)}
                style={[styles.card, open && styles.cardOpen]}>
                <View style={styles.cardTop}>
                  <View style={styles.cardIconBox}>
                    <HandIcon size={28} />
                  </View>

                  <View style={styles.cardTextWrap}>
                    <Text style={styles.cardTitle}>{sign.word}</Text>
                    <Text style={styles.cardMeta}>{sign.category}</Text>
                  </View>

                  <View style={styles.badgeCol}>
                    <View style={[styles.levelBadge, { backgroundColor: LEVEL_BG[sign.level] || Colors.greenL }]}>
                      <Text style={[styles.levelBadgeText, { color: sign.level === 'Dificil' ? Colors.red : sign.level === 'Mediu' ? Colors.amber : Colors.green }]}>
                        {sign.level}
                      </Text>
                    </View>
                    <View style={styles.xpBadge}>
                      <Text style={styles.xpBadgeText}>+{sign.xp} XP</Text>
                    </View>
                  </View>
                </View>

                {open && (
                  <View style={styles.expandedArea}>
                    <TouchableOpacity
                      activeOpacity={0.85}
                      style={styles.previewBox}
                      onPress={() => onPracticeSign?.(sign)}>
                      <HandIcon size={44} />
                      <Text style={styles.previewLabel}>Apasă pentru animația avatarului</Text>
                    </TouchableOpacity>

                    <View style={styles.actionRow}>
                      <TouchableOpacity
                        activeOpacity={0.85}
                        style={styles.practiceButton}
                        onPress={() => onPracticeSign?.(sign)}>
                        <PlayIcon color="#FFFFFF" size={14} />
                        <Text style={styles.practiceButtonText}>Practică</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </TouchableOpacity>
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
  },
  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 22,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
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
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  searchInput: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  categoryScroll: {
    paddingTop: 12,
    paddingBottom: 4,
    flexShrink: 0,
    flexGrow: 0,
  },
  categoryContent: {
    gap: 8,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  categoryPill: {
    backgroundColor: Colors.card,
    borderRadius: 99,
    paddingHorizontal: 18,
    paddingVertical: 7,
    borderWidth: 1.5,
    borderColor: Colors.rule,
  },
  categoryPillActive: {
    backgroundColor: '#1D4ED8',
    borderColor: '#1D4ED8',
    shadowColor: '#1D4ED8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 2,
  },
  categoryText: {
    color: Colors.sub,
    fontSize: 13,
    fontWeight: '700',
  },
  categoryTextActive: {
    color: '#FFFFFF',
  },
  resultsText: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 4,
  },
  loadingWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyWrap: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  emptyText: {
    color: Colors.sub,
    fontSize: 14,
    fontWeight: '700',
    textAlign: 'center',
  },
  list: {
    flex: 1,
  },
  listContent: {
    paddingHorizontal: 16,
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
  cardOpen: {
    borderColor: '#1D4ED8',
    shadowColor: '#1D4ED8',
    shadowOpacity: 0.1,
    shadowRadius: 20,
    elevation: 2,
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  cardIconBox: {
    width: 50,
    height: 50,
    borderRadius: 14,
    backgroundColor: Colors.violetL,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  cardTextWrap: {
    flex: 1,
  },
  cardTitle: {
    color: Colors.ink,
    fontSize: 15,
    fontWeight: '800',
  },
  cardSub: {
    color: Colors.sub,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 2,
  },
  cardMeta: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '600',
    marginTop: 3,
  },
  badgeCol: {
    alignItems: 'flex-end',
    gap: 5,
  },
  levelBadge: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  levelBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  xpBadge: {
    backgroundColor: Colors.violetL,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  xpBadgeText: {
    color: Colors.violet,
    fontSize: 11,
    fontWeight: '700',
  },
  expandedArea: {
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
  },
  previewBox: {
    backgroundColor: Colors.violetL,
    borderRadius: 16,
    height: 96,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: Colors.violetM,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 6,
    marginBottom: 12,
  },
  previewLabel: {
    color: Colors.violetM,
    fontSize: 10,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  practiceButton: {
    flex: 1,
    backgroundColor: Colors.violet,
    borderRadius: 13,
    paddingVertical: 10,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 14,
    elevation: 2,
  },
  practiceButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
});

export default DictionaryScreen;
