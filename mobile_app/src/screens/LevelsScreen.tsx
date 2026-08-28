import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { Colors } from '../theme';
import { GamificationStatus } from '../services/ApiService';
import {
  ArrowLeftIcon,
  ChevronRightIcon,
  StarIcon,
  SeedIcon,
  MountainIcon,
  BookBadgeIcon,
  LockIcon,
  BoltIcon,
  TargetIcon,
  CrownIcon,
  GemIcon,
  CheckIcon,
  HandIcon,
} from '../components/Icons';

interface LevelsScreenProps {
  gamification: GamificationStatus | null;
  onBack: () => void;
}

const LEVEL_XP = [0, 0, 100, 250, 500, 1000, 1800, 2800, 4000, 5500, 7500];

const LEVEL_META = [
  null,
  { name: 'Începător', icon: 'seed' },
  { name: 'Începător', icon: 'mountain' },
  { name: 'Elementar', icon: 'book' },
  { name: 'Elementar', icon: 'bolt' },
  { name: 'Intermediar', icon: 'book' },
  { name: 'Intermediar', icon: 'target' },
  { name: 'Avansat', icon: 'target' },
  { name: 'Avansat', icon: 'crown' },
  { name: 'Expert', icon: 'crown' },
  { name: 'Legendă', icon: 'gem' },
] as const;

function LevelMetaIcon({ icon, color, size }: { icon?: string; color: string; size: number }) {
  switch (icon) {
    case 'seed':
      return <SeedIcon color={color} size={size} />;
    case 'mountain':
      return <MountainIcon color={color} size={size} />;
    case 'book':
      return <BookBadgeIcon color={color} size={size} />;
    case 'lock':
      return <LockIcon color={color} size={size} />;
    case 'bolt':
      return <BoltIcon color={color} size={size} />;
    case 'target':
      return <TargetIcon color={color} size={size} />;
    case 'crown':
      return <CrownIcon color={color} size={size} />;
    case 'gem':
      return <GemIcon color={color} size={size} />;
    default:
      return <StarIcon color={color} size={size} />;
  }
}

function clampLevel(level: number): number {
  return Math.min(Math.max(level, 1), LEVEL_META.length - 1);
}

const LevelsScreen: React.FC<LevelsScreenProps> = ({ gamification, onBack }) => {
  const xp = gamification?.xp ?? 0;
  const currentLevel = clampLevel(gamification?.level ?? 1);
  const minXp = LEVEL_XP[currentLevel];
  const hasNextLevel = currentLevel < LEVEL_META.length - 1;
  const nextXp = hasNextLevel ? LEVEL_XP[currentLevel + 1] : null;
  const inLevelXp = Math.max(0, xp - minXp);
  const levelSpan = hasNextLevel && nextXp ? Math.max(1, nextXp - minXp) : Math.max(1, inLevelXp);
  const progressPct = hasNextLevel && nextXp ? Math.max(0, Math.min(100, (inLevelXp / levelSpan) * 100)) : 100;
  const xpRemaining = hasNextLevel && nextXp ? Math.max(0, nextXp - xp) : 0;
  const footerText = hasNextLevel
    ? `Mai ai ${xpRemaining} XP până la Nivel ${currentLevel + 1}`
    : 'Ai atins nivelul maxim';
  const currentMeta = LEVEL_META[currentLevel] || LEVEL_META[1];

  const stages = React.useMemo(() => {
    return LEVEL_META.slice(1).map((meta, index) => {
      const level = index + 1;
      const startXp = LEVEL_XP[level];
      const nextLevelStart = LEVEL_XP[level + 1];
      const endXp = typeof nextLevelStart === 'number' ? nextLevelStart - 1 : null;
      const unlocked = currentLevel > level;
      const current = currentLevel === level;
      const locked = currentLevel < level;
      const barPct = unlocked
        ? 100
        : current
          ? (typeof nextLevelStart === 'number'
            ? Math.max(0, Math.min(100, ((xp - startXp) / Math.max(1, nextLevelStart - startXp)) * 100))
            : 100)
          : 0;

      return {
        level,
        meta,
        startXp,
        endXp,
        rangeLabel: endXp === null ? `${startXp}+ XP` : `${startXp} - ${endXp} XP`,
        unlocked,
        current,
        locked,
        barPct,
      };
    });
  }, [currentLevel, xp]);

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.headerShell}>
          <View style={styles.headerTop}>
            <TouchableOpacity onPress={onBack} style={styles.backButton} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>
          </View>

          <Text style={styles.title}>Etape Nivel</Text>
          <Text style={styles.subtitle}>Vezi toate pragurile și progresul tău</Text>

          <View style={styles.heroCard}>
            <View style={styles.heroRow}>
              <View style={styles.heroBadge}>
                <View style={styles.heroVisualGlow} />
                <View style={styles.heroVisualCircle}>
                  <HandIcon size={46} />
                </View>
                <View style={styles.heroBadgeLevel}>
                  <Text style={styles.heroBadgeLevelText}>{currentLevel}</Text>
                </View>
              </View>

              <View style={styles.heroMain}>
                <View style={styles.heroTitleRow}>
                  <Text style={styles.heroTitle}>Nivel {currentLevel} - {currentMeta?.name}</Text>
                  <Text style={styles.heroXp}>{inLevelXp} / {levelSpan} XP</Text>
                </View>

                <View style={styles.heroTrack}>
                  <View style={[styles.heroFill, { width: `${progressPct}%` } as any]} />
                </View>

                <View style={styles.heroInfoRow}>
                  <StarIcon size={14} color="#FCD34D" />
                  <Text style={styles.heroInfoText}>XP total: {xp}</Text>
                </View>

                <View style={styles.heroFooter}>
                  <BoltIcon color="#C4B5FD" size={14} />
                  <Text style={styles.heroFooterText}>{footerText}</Text>
                  <ChevronRightIcon color="#A78BFA" size={14} />
                </View>
              </View>
            </View>
          </View>
        </View>

        <View style={styles.cardsWrap}>
          {stages.map(stage => {
            const statusLabel = stage.unlocked ? 'Deblocat' : stage.current ? 'Curent' : 'Blocat';
            return (
              <View
                key={stage.level}
                style={[
                  styles.stageCard,
                  stage.current && styles.stageCardCurrent,
                  stage.locked && styles.stageCardLocked,
                ]}>
                <View style={styles.stageTopRow}>
                  <View style={[styles.stageIconWrap, stage.locked && styles.stageIconWrapLocked]}>
                    <View style={[styles.stageIconPlate, stage.current && styles.stageIconPlateCurrent, stage.locked && styles.stageIconPlateLocked]}>
                      <LevelMetaIcon
                        icon={stage.meta?.icon}
                        color={stage.locked ? '#94A3B8' : stage.current ? '#8B5CF6' : '#22C55E'}
                        size={22}
                      />
                    </View>
                    <View style={[styles.stageIconLevel, stage.current && styles.stageIconLevelCurrent, stage.locked && styles.stageIconLevelLocked]}>
                      <Text style={styles.stageIconLevelText}>{stage.level}</Text>
                    </View>
                  </View>

                  <View style={styles.stageTextWrap}>
                    <Text style={styles.stageTitle}>Nivel {stage.level}</Text>
                    <Text style={styles.stageSubtitle}>{stage.meta?.name}</Text>
                    <Text style={styles.stageRange}>{stage.rangeLabel}</Text>
                  </View>

                  <View
                    style={[
                      styles.statusPill,
                      stage.unlocked && styles.statusPillUnlocked,
                      stage.current && styles.statusPillCurrent,
                      stage.locked && styles.statusPillLocked,
                    ]}>
                    <View style={styles.statusPillIconWrap}>
                      {stage.unlocked ? <CheckIcon color="#16A34A" size={10} /> : stage.current ? <StarIcon color="#7C3AED" size={10} /> : <LockIcon color="#6B7280" size={10} />}
                    </View>
                    <Text
                      style={[
                        styles.statusPillText,
                        stage.unlocked && styles.statusPillTextUnlocked,
                        stage.current && styles.statusPillTextCurrent,
                        stage.locked && styles.statusPillTextLocked,
                      ]}>
                      {statusLabel}
                    </Text>
                  </View>
                </View>

                <View style={[styles.stageTrack, stage.current && styles.stageTrackCurrent, stage.locked && styles.stageTrackLocked]}>
                  <View
                    style={[
                      styles.stageFill,
                      stage.current && styles.stageFillCurrent,
                      stage.locked && styles.stageFillLocked,
                      { width: `${stage.barPct}%` } as any,
                    ]}
                  />
                </View>
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#120729',
  },
  scroll: {
    flex: 1,
  },
  content: {
    paddingBottom: 28,
    backgroundColor: '#F7F5FF',
  },
  headerShell: {
    backgroundColor: '#1C0C41',
    paddingTop: 54,
    paddingHorizontal: 16,
    paddingBottom: 18,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    width: 34,
    height: 34,
    borderRadius: 12,
    backgroundColor: 'rgba(167,139,250,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    marginTop: 10,
    textAlign: 'center',
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '900',
  },
  subtitle: {
    marginTop: 6,
    textAlign: 'center',
    color: 'rgba(255,255,255,0.62)',
    fontSize: 11,
    fontWeight: '600',
  },
  heroCard: {
    marginTop: 16,
    borderRadius: 22,
    padding: 14,
    backgroundColor: '#2A145A',
    borderWidth: 1.5,
    borderColor: '#A855F7',
    shadowColor: '#A855F7',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.65,
    shadowRadius: 18,
    elevation: 8,
  },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  heroBadge: {
    width: 58,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  heroVisualGlow: {
    position: 'absolute',
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: 'rgba(216,180,254,0.3)',
  },
  heroVisualCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1.2,
    borderColor: 'rgba(255,255,255,0.22)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  heroBadgeLevel: {
    marginTop: -10,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#7C3AED',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  heroBadgeLevelText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '900',
  },
  heroMain: {
    flex: 1,
  },
  heroTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  heroTitle: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '900',
  },
  heroXp: {
    color: 'rgba(255,255,255,0.78)',
    fontSize: 11,
    fontWeight: '800',
  },
  heroTrack: {
    marginTop: 12,
    height: 9,
    borderRadius: 999,
    backgroundColor: 'rgba(16, 8, 37, 0.65)',
    overflow: 'hidden',
  },
  heroFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: '#A855F7',
  },
  heroInfoRow: {
    marginTop: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  heroInfoText: {
    color: '#E9D5FF',
    fontSize: 12,
    fontWeight: '700',
  },
  heroFooter: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.08)',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  heroFooterText: {
    flex: 1,
    color: '#C4B5FD',
    fontSize: 11,
    fontWeight: '700',
  },
  cardsWrap: {
    paddingHorizontal: 14,
    paddingTop: 14,
    gap: 12,
  },
  stageCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E9E5FF',
    shadowColor: '#1E1540',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.06,
    shadowRadius: 14,
    elevation: 2,
  },
  stageCardCurrent: {
    borderColor: '#C4B5FD',
    backgroundColor: '#FBF8FF',
  },
  stageCardLocked: {
    backgroundColor: '#F8FAFC',
  },
  stageTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  stageIconWrap: {
    width: 44,
    alignItems: 'center',
  },
  stageIconWrapLocked: {
    opacity: 0.75,
  },
  stageIconPlate: {
    width: 44,
    height: 50,
    borderRadius: 15,
    backgroundColor: '#ECFDF3',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stageIconPlateCurrent: {
    backgroundColor: '#F3E8FF',
  },
  stageIconPlateLocked: {
    backgroundColor: '#E5E7EB',
  },
  stageIconLevel: {
    marginTop: -10,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#22C55E',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 6,
  },
  stageIconLevelCurrent: {
    backgroundColor: '#7C3AED',
  },
  stageIconLevelLocked: {
    backgroundColor: '#94A3B8',
  },
  stageIconLevelText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '900',
  },
  stageTextWrap: {
    flex: 1,
  },
  stageTitle: {
    color: Colors.ink,
    fontSize: 15,
    fontWeight: '900',
  },
  stageSubtitle: {
    marginTop: 2,
    color: Colors.sub,
    fontSize: 12,
    fontWeight: '700',
  },
  stageRange: {
    marginTop: 5,
    color: '#64748B',
    fontSize: 12,
    fontWeight: '600',
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  statusPillUnlocked: {
    backgroundColor: '#DCFCE7',
  },
  statusPillCurrent: {
    backgroundColor: '#E9D5FF',
  },
  statusPillLocked: {
    backgroundColor: '#E5E7EB',
  },
  statusPillIconWrap: {
    width: 10,
    height: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusPillText: {
    fontSize: 11,
    fontWeight: '800',
  },
  statusPillTextUnlocked: {
    color: '#16A34A',
  },
  statusPillTextCurrent: {
    color: '#7C3AED',
  },
  statusPillTextLocked: {
    color: '#6B7280',
  },
  stageTrack: {
    marginTop: 12,
    height: 5,
    borderRadius: 999,
    backgroundColor: '#DCFCE7',
    overflow: 'hidden',
  },
  stageTrackCurrent: {
    backgroundColor: '#E9D5FF',
  },
  stageTrackLocked: {
    backgroundColor: '#E2E8F0',
  },
  stageFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: '#22C55E',
  },
  stageFillCurrent: {
    backgroundColor: '#8B5CF6',
  },
  stageFillLocked: {
    backgroundColor: '#CBD5E1',
  },
});

export default LevelsScreen;
