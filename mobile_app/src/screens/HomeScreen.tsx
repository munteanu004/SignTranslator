import * as React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image } from 'react-native';
import { Colors } from '../theme';
import { ChallengeData, GamificationStatus } from '../services/ApiService';
import ApiService from '../services/ApiService';
import {
  CameraIcon,
  TextIcon,
  BookIcon,
  FireIcon,
  HandIcon,
  ChevronRightIcon,
  CoinIcon,
  MedalIcon,
  PenIcon,
  BookBadgeIcon,
  LockIcon,
} from '../components/Icons';

interface HomeScreenProps {
  user: { name: string; email: string };
  gamification: GamificationStatus | null;
  onNavigate: (screen: string) => void;
  onOpenProfile: () => void;
  onOpenLevels: () => void;
  onClaimDaily: () => void | Promise<void>;
  onClaimChallenge: (challengeKey: string) => void | Promise<void>;
}

type BadgePreview = {
  key: string;
  label: string;
  done: boolean;
  kind: 'medal' | 'pen' | 'book';
};

const LEVEL_NAMES: Record<number, string> = {
  1: 'Începător',
  2: 'Elementar',
  3: 'Pre-Intermediar',
  4: 'Intermediar',
  5: 'Avansat',
  6: 'Expert',
};

const FALLBACK_CHALLENGES: ChallengeData[] = [
  {
    key: 'live-x5',
    title: 'Traducere live x5',
    desc: '',
    target: 5,
    progress: 5,
    xp_reward: 40,
    completed: true,
    xp_claimed: true,
  },
  {
    key: 'text-x3',
    title: 'Text în semne x3',
    desc: '',
    target: 3,
    progress: 3,
    xp_reward: 30,
    completed: true,
    xp_claimed: false,
  },
];

const FALLBACK_BADGES: BadgePreview[] = [
  { key: 'first', label: 'Prima traducere', done: true, kind: 'medal' },
  { key: 'ten', label: '10 traduceri', done: false, kind: 'pen' },
  { key: 'fifty', label: '50 traduceri', done: false, kind: 'book' },
];

const renderBadgeIcon = (kind: BadgePreview['kind'], done: boolean) => {
  const color = done ? '#F59E0B' : '#9CA3AF';
  const size = done ? 34 : 30;

  if (kind === 'medal') return <MedalIcon color={color} size={size} />;
  if (kind === 'pen') return <PenIcon color={color} size={size} />;
  return <BookBadgeIcon color={color} size={size} />;
};

const HomeScreen: React.FC<HomeScreenProps> = ({
  user,
  gamification,
  onNavigate,
  onOpenProfile,
  onOpenLevels,
  onClaimDaily,
  onClaimChallenge,
}) => {
  const [isClaimingDaily, setIsClaimingDaily] = React.useState(false);
  const [claimingChallengeKey, setClaimingChallengeKey] = React.useState<string | null>(null);

  const firstName = (user.name || 'Utilizator').split(' ')[0] || user.name;
  const initials = (user.name || 'U')
    .split(' ')
    .map(part => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const streak = gamification?.streak ?? 2;
  const xp = gamification?.xp ?? 231;
  const level = gamification?.level ?? 3;
  const currentLevelXp = gamification?.current_level_xp ?? 0;
  const nextLevelXp = gamification?.next_level_xp ?? 250;
  const xpInLevel = Math.max(0, xp - currentLevelXp);
  const xpSpan = Math.max(1, nextLevelXp - currentLevelXp);
  const xpRemaining = Math.max(0, nextLevelXp - xp);
  const progress = Math.min(100, Math.max(0, (xpInLevel / xpSpan) * 100));
  const levelName = LEVEL_NAMES[level] ?? 'Pre-Intermediar';

  const challengeItems = (gamification?.challenges ?? []).slice(0, 2);
  const displayChallenges = challengeItems.length > 0 ? challengeItems : FALLBACK_CHALLENGES;
  const completedCount = displayChallenges.filter(item => item.completed || item.xp_claimed).length;
  const challengeProgress = displayChallenges.length > 0 ? (completedCount / displayChallenges.length) * 100 : 0;

  const badges: BadgePreview[] = (gamification?.achievements ?? []).length
    ? (gamification?.achievements ?? []).slice(0, 3).map((item, index) => ({
        key: item.key,
        label: item.title,
        done: item.earned,
        kind: index === 0 ? 'medal' : index === 1 ? 'pen' : 'book',
      }))
    : FALLBACK_BADGES;

  const canClaimDaily = gamification?.daily_claim?.can_claim ?? false;

  const handleClaimDaily = React.useCallback(async () => {
    if (!canClaimDaily || isClaimingDaily) return;
    setIsClaimingDaily(true);
    try {
      await Promise.resolve(onClaimDaily());
    } finally {
      setIsClaimingDaily(false);
    }
  }, [canClaimDaily, isClaimingDaily, onClaimDaily]);

  const handleClaimChallenge = React.useCallback(async (challengeKey: string) => {
    if (!challengeKey || claimingChallengeKey) return;
    setClaimingChallengeKey(challengeKey);
    try {
      await Promise.resolve(onClaimChallenge(challengeKey));
    } finally {
      setClaimingChallengeKey(null);
    }
  }, [claimingChallengeKey, onClaimChallenge]);

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={[styles.hero, { background: 'linear-gradient(180deg,#7C3AED 0%, #2E1065 100%)' } as any]}>
          <View style={styles.heroOrbLarge} />
          <View style={styles.heroOrbSmall} />

          <View style={styles.heroTopRow}>
            <TouchableOpacity style={styles.profileRow} activeOpacity={0.92} onPress={onOpenProfile}>
              <View style={styles.avatarWrap}>
                {user.avatar_url ? (
                  <Image
                    source={{ uri: ApiService.getAvatarUrl(user.avatar_url) }}
                    style={styles.avatarImage}
                    resizeMode="cover"
                  />
                ) : (
                  <Text style={styles.avatarText}>{initials}</Text>
                )}
              </View>
              <View>
                <Text style={styles.welcomeText}>Bine ai revenit,</Text>
                <Text style={styles.nameText}>{firstName}</Text>
              </View>
            </TouchableOpacity>

            <View style={styles.streakBadge}>
              <FireIcon size={15} />
              <Text style={styles.streakValue}>{streak}</Text>
              <Text style={styles.streakLabel}>zile</Text>
            </View>
          </View>
        </View>

        <View style={styles.content}>
          <TouchableOpacity style={styles.levelCard} activeOpacity={0.95} onPress={onOpenLevels}>
            <View style={styles.levelBadge}>
              <Text style={styles.levelBadgeText}>{level}</Text>
            </View>

            <View style={styles.levelContent}>
              <View style={styles.levelTopRow}>
                <Text numberOfLines={1} style={styles.levelTitle}>Nivel {level} · {levelName}</Text>
                <Text style={styles.levelXpText}>{xp} / {nextLevelXp} XP</Text>
              </View>

              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${progress}%` } as any]} />
              </View>

              <View style={styles.levelBottomRow}>
                <Text numberOfLines={1} style={styles.levelHint}>Mai ai {xpRemaining} XP până la Nivel {level + 1}</Text>
                <TouchableOpacity
                  style={[styles.collectChip, !canClaimDaily && styles.collectChipDone]}
                  activeOpacity={0.9}
                  onPress={handleClaimDaily}
                  disabled={!canClaimDaily || isClaimingDaily}>
                  <CoinIcon color={canClaimDaily ? Colors.teal : Colors.green} size={14} />
                  <Text style={[styles.collectChipText, !canClaimDaily && styles.collectChipTextDone]}>
                    {canClaimDaily ? (isClaimingDaily ? 'Se colectează' : 'Colectează') : 'Colectată'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </TouchableOpacity>

          <Text style={styles.sectionTitle}>Alege modul</Text>

          <View style={styles.modulesRow}>
            <TouchableOpacity
              style={[styles.moduleCard, styles.moduleCardPurple, { background: 'linear-gradient(145deg,#8B2CF5 0%, #5B21B6 100%)' } as any]}
              activeOpacity={0.95}
              onPress={() => onNavigate('Camera')}>
              <View style={styles.moduleIconWrap}>
                <CameraIcon color="#FFFFFF" size={26} />
              </View>
              <View style={styles.moduleHandGlow} />
              <Text style={styles.moduleTitle}>Semnez</Text>
              <View style={styles.moduleActionPill}>
                <Text style={styles.moduleActionText}>Semn → Text</Text>
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.moduleCard, styles.moduleCardTeal, { background: 'linear-gradient(145deg,#14B8A6 0%, #0F766E 100%)' } as any]}
              activeOpacity={0.95}
              onPress={() => onNavigate('TextSign')}>
              <View style={styles.moduleIconWrap}>
                <TextIcon color="#FFFFFF" size={26} />
              </View>
              <View style={styles.moduleTextGlowTop} />
              <View style={styles.moduleTextGlowBottom} />
              <Text style={styles.moduleTitle}>Traduc</Text>
              <View style={styles.moduleActionPill}>
                <Text style={[styles.moduleActionText, styles.moduleActionTextTeal]}>Text → Semn</Text>
              </View>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.dictionaryCard} activeOpacity={0.92} onPress={() => onNavigate('Dictionary')}>
            <View style={styles.dictionaryLeft}>
              <View style={styles.dictionaryIconWrap}>
                <BookIcon color="#FFFFFF" size={18} />
              </View>
              <View>
                <Text style={styles.dictionaryTitle}>Dicționar LSR</Text>
                <Text style={styles.dictionarySubtitle}>1 240 semne</Text>
              </View>
            </View>
            <ChevronRightIcon color={Colors.violet} size={18} />
          </TouchableOpacity>

          <View style={styles.challengeCard}>
            <View style={styles.challengeHeader}>
              <Text style={styles.challengeTitle}>Provocarea zilei</Text>
              <View style={styles.challengeCounterPill}>
                <Text style={styles.challengeCounterText}>{completedCount}/{Math.max(displayChallenges.length, 1)}</Text>
              </View>
            </View>

            <View style={styles.challengeProgressTrack}>
              <View style={[styles.challengeProgressFill, { width: `${challengeProgress}%` } as any]} />
            </View>

            <View style={styles.challengeRow}>
              <View style={[styles.challengeIconBox, styles.challengeIconAmber]}>
                <HandIcon size={18} />
              </View>
              <Text numberOfLines={1} style={styles.challengeLabel}>{displayChallenges[0]?.title || 'Traducere live x5'}</Text>
              <View style={styles.challengeRewardPill}>
                <Text style={styles.challengeRewardText}>+{displayChallenges[0]?.xp_reward ?? 40} XP</Text>
              </View>
            </View>

            <View style={styles.challengeDivider} />

            <View style={styles.challengeRow}>
              <View style={[styles.challengeIconBox, styles.challengeIconTeal]}>
                <TextIcon color={Colors.teal} size={18} />
              </View>
              <Text numberOfLines={1} style={styles.challengeLabel}>{displayChallenges[1]?.title || 'Text în semne x3'}</Text>
              <TouchableOpacity
                style={styles.challengeCollectButton}
                activeOpacity={0.9}
                disabled={!!claimingChallengeKey}
                onPress={() => handleClaimChallenge(displayChallenges[1]?.key || 'text-x3')}>
                <Text style={styles.challengeCollectText}>
                  {claimingChallengeKey === (displayChallenges[1]?.key || 'text-x3') ? 'Se colectează' : 'Colectează'}
                </Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity activeOpacity={0.85} onPress={onOpenLevels} style={styles.challengeFooterLinkWrap}>
              <Text style={styles.challengeFooterLink}>Vezi toate</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.badgesHeader}>
            <Text style={styles.sectionTitle}>Insigne</Text>
            <TouchableOpacity activeOpacity={0.85} onPress={onOpenProfile}>
              <Text style={styles.badgesLink}>Vezi toate</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.badgesRow}>
            {badges.map(item => (
              <View key={item.key} style={styles.badgeCard}>
                {!item.done && (
                  <View style={styles.badgeLockBubble}>
                    <LockIcon color="#8B8CA6" size={12} />
                  </View>
                )}
                <View style={styles.badgeIconWrap}>{renderBadgeIcon(item.kind, item.done)}</View>
                <Text numberOfLines={2} style={styles.badgeLabel}>{item.label}</Text>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    overflow: 'hidden',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 112,
  },
  hero: {
    height: 152,
    paddingHorizontal: 16,
    paddingTop: 28,
    borderBottomLeftRadius: 34,
    borderBottomRightRadius: 34,
    overflow: 'hidden',
  },
  heroOrbLarge: {
    position: 'absolute',
    top: -32,
    left: 152,
    width: 210,
    height: 210,
    borderRadius: 105,
    backgroundColor: 'rgba(255,255,255,0.10)',
  },
  heroOrbSmall: {
    position: 'absolute',
    top: 18,
    left: 18,
    width: 92,
    height: 92,
    borderRadius: 46,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  heroTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatarWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(173,216,255,0.28)',
    borderWidth: 1.4,
    borderColor: 'rgba(255,255,255,0.44)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 21,
    fontWeight: '900',
  },
  avatarImage: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  welcomeText: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: 10,
    fontWeight: '700',
    marginBottom: 2,
  },
  nameText: {
    color: '#FFFFFF',
    fontSize: 24,
    lineHeight: 28,
    fontWeight: '900',
  },
  streakBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 18,
    backgroundColor: 'rgba(46,16,101,0.45)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.20)',
  },
  streakValue: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '900',
  },
  streakLabel: {
    color: 'rgba(255,255,255,0.82)',
    fontSize: 11,
    fontWeight: '700',
  },
  content: {
    marginTop: -24,
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  levelCard: {
    height: 92,
    backgroundColor: '#FFFFFF',
    borderRadius: 25,
    borderWidth: 1,
    borderColor: '#EEE9FC',
    paddingHorizontal: 15,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#7C3AED',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.08,
    shadowRadius: 18,
    elevation: 4,
  },
  levelBadge: {
    width: 56,
    height: 56,
    borderRadius: 20,
    backgroundColor: Colors.violet,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  levelBadgeText: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '900',
  },
  levelContent: {
    flex: 1,
  },
  levelTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 9,
    gap: 6,
  },
  levelTitle: {
    flex: 1,
    color: Colors.ink,
    fontSize: 12,
    fontWeight: '900',
  },
  levelXpText: {
    color: '#4B5563',
    fontSize: 10,
    fontWeight: '800',
  },
  progressTrack: {
    height: 8,
    borderRadius: 999,
    backgroundColor: '#ECE7FB',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: Colors.violet,
  },
  levelBottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    gap: 8,
  },
  levelHint: {
    flex: 1,
    color: '#6B7280',
    fontSize: 10,
    fontWeight: '600',
  },
  collectChip: {
    height: 34,
    borderRadius: 17,
    backgroundColor: '#E7FBF7',
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  collectChipDone: {
    backgroundColor: '#E9FFF2',
  },
  collectChipText: {
    color: Colors.teal,
    fontSize: 11,
    fontWeight: '800',
  },
  collectChipTextDone: {
    color: Colors.green,
  },
  sectionTitle: {
    color: Colors.ink,
    fontSize: 13,
    fontWeight: '900',
    marginTop: 8,
  },
  modulesRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
  moduleCard: {
    flex: 1,
    height: 132,
    borderRadius: 24,
    paddingHorizontal: 14,
    paddingTop: 16,
    paddingBottom: 14,
    overflow: 'hidden',
    justifyContent: 'space-between',
  },
  moduleCardPurple: {
    shadowColor: '#5B21B6',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.18,
    shadowRadius: 16,
    elevation: 5,
  },
  moduleCardTeal: {
    shadowColor: '#0F766E',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.16,
    shadowRadius: 16,
    elevation: 5,
  },
  moduleIconWrap: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.14)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  moduleHandGlow: {
    position: 'absolute',
    right: 18,
    top: 60,
    width: 100,
    height: 74,
    borderRadius: 30,
    backgroundColor: 'rgba(255,255,255,0.06)',
    transform: [{ rotate: '-16deg' }],
  },
  moduleTextGlowTop: {
    position: 'absolute',
    right: 18,
    top: 58,
    width: 86,
    height: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.10)',
    transform: [{ rotate: '-12deg' }],
  },
  moduleTextGlowBottom: {
    position: 'absolute',
    right: 10,
    top: 82,
    width: 98,
    height: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.08)',
    transform: [{ rotate: '-12deg' }],
  },
  moduleTitle: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '900',
  },
  moduleActionPill: {
    height: 34,
    borderRadius: 14,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  moduleActionText: {
    color: Colors.violet,
    fontSize: 11,
    fontWeight: '800',
  },
  moduleActionTextTeal: {
    color: Colors.teal,
  },
  dictionaryCard: {
    marginTop: 12,
    height: 68,
    borderRadius: 22,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#EEE9FC',
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  dictionaryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dictionaryIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: Colors.violet,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  dictionaryTitle: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '900',
  },
  dictionarySubtitle: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  challengeCard: {
    marginTop: 10,
    borderRadius: 22,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#EEE9FC',
    paddingHorizontal: 14,
    paddingTop: 14,
    paddingBottom: 8,
  },
  challengeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  challengeTitle: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '900',
  },
  challengeCounterPill: {
    minWidth: 46,
    height: 30,
    borderRadius: 15,
    backgroundColor: Colors.violetL,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  challengeCounterText: {
    color: Colors.violet,
    fontSize: 12,
    fontWeight: '800',
  },
  challengeProgressTrack: {
    marginTop: 12,
    height: 5,
    borderRadius: 999,
    backgroundColor: '#ECE7FB',
    overflow: 'hidden',
  },
  challengeProgressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: Colors.violet,
  },
  challengeRow: {
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  challengeIconBox: {
    width: 42,
    height: 42,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  challengeIconAmber: {
    backgroundColor: '#FFF3D9',
  },
  challengeIconTeal: {
    backgroundColor: '#D8F8F3',
  },
  challengeLabel: {
    flex: 1,
    color: Colors.ink,
    fontSize: 13,
    fontWeight: '700',
  },
  challengeRewardPill: {
    minWidth: 74,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.violetL,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  challengeRewardText: {
    color: Colors.violet,
    fontSize: 11,
    fontWeight: '800',
  },
  challengeDivider: {
    marginLeft: 54,
    marginTop: 10,
    height: 1,
    backgroundColor: '#EEE9FC',
  },
  challengeCollectButton: {
    minWidth: 92,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.violet,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 14,
  },
  challengeCollectText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '800',
  },
  challengeFooterLinkWrap: {
    marginTop: 8,
    alignItems: 'center',
  },
  challengeFooterLink: {
    color: Colors.violet,
    fontSize: 10,
    fontWeight: '800',
  },
  badgesHeader: {
    marginTop: 8,
    marginBottom: 6,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  badgesLink: {
    color: Colors.violet,
    fontSize: 11,
    fontWeight: '800',
  },
  badgesRow: {
    flexDirection: 'row',
    gap: 10,
  },
  badgeCard: {
    flex: 1,
    height: 82,
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#EEE9FC',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    paddingHorizontal: 8,
  },
  badgeLockBubble: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#F3F4F6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeIconWrap: {
    width: 30,
    height: 30,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  badgeLabel: {
    color: '#6B7280',
    fontSize: 9,
    fontWeight: '700',
    lineHeight: 13,
    textAlign: 'center',
  },
});

export default HomeScreen;
