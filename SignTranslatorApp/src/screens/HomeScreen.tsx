import React from 'react';
import {
  Platform,
  ScrollView,
  StatusBar,
  StyleProp,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ViewStyle,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import LinearGradient from 'react-native-linear-gradient';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const Palette = {
  ink: '#1E1540',
  sub: '#6B7280',
  bg: '#F7F5FF',
  card: '#FFFFFF',
  rule: '#EDE9FE',
  violet: '#7C3AED',
  violetDark: '#5B21B6',
  violetLight: '#EDE9FE',
  violetMid: '#A78BFA',
  teal: '#0D9488',
  tealDark: '#0F766E',
  tealLight: '#CCFBF1',
  orange: '#F97316',
  orangeLight: '#FFF0E5',
  green: '#22C55E',
  greenLight: '#DCFCE7',
  muted: '#9CA3AF',
  mutedBg: '#F3F4F6',
};

const profile = {
  fullName: 'Emma Bernard',
  streak: 7,
  level: 3,
  levelName: 'Pre-Intermediar',
  xp: 540,
  currentLevelXp: 400,
  nextLevelXp: 700,
};

const challenges = [
  {title: 'Exerseaza 5 semne noi', progress: 3, target: 5, xp: 20, done: false, icon: 'hand-clap'},
  {title: 'Trimite o traducere live', progress: 1, target: 1, xp: 15, done: true, icon: 'check-bold'},
  {title: 'Foloseste modul Text -> Semn', progress: 1, target: 2, xp: 15, done: false, icon: 'text-box-outline'},
];

const badges = [
  {emoji: '⭐', label: 'Primul semn', locked: false},
  {emoji: '🔥', label: '7 zile', locked: false},
  {emoji: '📚', label: 'Vocabular', locked: true},
  {emoji: '🏆', label: 'Expert', locked: true},
];

type GradientSurfaceProps = {
  colors: [string, string];
  style?: StyleProp<ViewStyle>;
  children: React.ReactNode;
};

const GradientSurface = ({colors, style, children}: GradientSurfaceProps) => {
  if (Platform.OS === 'web') {
    return (
      <View
        style={[
          style,
          {
            backgroundColor: colors[0],
            backgroundImage: `linear-gradient(160deg, ${colors[0]} 0%, ${colors[1]} 100%)`,
          } as ViewStyle,
        ]}>
        {children}
      </View>
    );
  }

  return (
    <LinearGradient colors={colors} start={{x: 0, y: 0}} end={{x: 1, y: 1}} style={style}>
      {children}
    </LinearGradient>
  );
};

const HomeScreen = () => {
  const navigation = useNavigation<any>();
  const firstName = profile.fullName.split(' ')[0];
  const initials = profile.fullName
    .split(' ')
    .map(part => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  const xpInLevel = profile.xp - profile.currentLevelXp;
  const xpSpan = profile.nextLevelXp - profile.currentLevelXp;
  const progress = Math.min(1, Math.max(0, xpInLevel / xpSpan));

  return (
    <View style={styles.screen}>
      <StatusBar barStyle="light-content" backgroundColor={Palette.violet} />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.contentContainer}
        showsVerticalScrollIndicator={false}
        bounces={false}>
        <GradientSurface colors={[Palette.violet, Palette.violetDark]} style={styles.hero}>
          <View style={styles.heroRow}>
            <TouchableOpacity
              activeOpacity={0.85}
              onPress={() => navigation.navigate('Account')}
              style={styles.avatarButton}>
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>{initials}</Text>
              </View>
            </TouchableOpacity>

            <View style={styles.heroTextBlock}>
              <Text style={styles.heroLabel}>Buna ziua,</Text>
              <View style={styles.heroNameRow}>
                <Text style={styles.heroName}>{firstName}</Text>
                <Icon name="hand-wave-outline" size={20} color="#FFFFFF" />
              </View>
            </View>

            <View style={styles.streakBadge}>
              <Icon name="fire" size={18} color={Palette.orange} />
              <Text style={styles.streakValue}>{profile.streak}</Text>
              <Text style={styles.streakText}>zile</Text>
            </View>
          </View>

          <View style={styles.xpBox}>
            <View style={styles.xpHeader}>
              <Text style={styles.xpLevel}>
                Nivel {profile.level} - {profile.levelName}
              </Text>
              <Text style={styles.xpValue}>
                {xpInLevel} / {xpSpan} XP
              </Text>
            </View>
            <View style={styles.xpTrack}>
              <View style={[styles.xpFill, {width: `${progress * 100}%`}]} />
            </View>
          </View>
        </GradientSurface>

        <View style={styles.modesSection}>
          <GradientSurface colors={[Palette.violet, Palette.violetDark]} style={styles.modeCard}>
            <TouchableOpacity
              activeOpacity={0.9}
              style={styles.modePressable}
              onPress={() => navigation.navigate('Conversation')}>
              <View style={styles.modeIconWrap}>
                <Icon name="camera-outline" size={28} color="#FFFFFF" />
              </View>
              <Text style={styles.modeTitle}>Semnez</Text>
              <Text style={styles.modeDescription}>
                Semnele tale sunt traduse{'\n'}in text in timp real
              </Text>
              <View style={styles.modeChip}>
                <Text style={styles.modeChipText}>Semn -&gt; Text</Text>
              </View>
            </TouchableOpacity>
          </GradientSurface>

          <GradientSurface colors={[Palette.teal, Palette.tealDark]} style={styles.modeCard}>
            <TouchableOpacity activeOpacity={0.9} style={styles.modePressable}>
              <View style={styles.modeIconWrap}>
                <Icon name="text-box-outline" size={28} color="#FFFFFF" />
              </View>
              <Text style={styles.modeTitle}>Traduc</Text>
              <Text style={styles.modeDescription}>
                Scrie un text, avatarul il{'\n'}semneaza pentru tine
              </Text>
              <View style={styles.modeChip}>
                <Text style={styles.modeChipText}>Text -&gt; Semn</Text>
              </View>
            </TouchableOpacity>
          </GradientSurface>
        </View>

        <TouchableOpacity activeOpacity={0.85} style={styles.dictionaryCard}>
          <View style={styles.dictionaryLeft}>
            <View style={styles.dictionaryIcon}>
              <Icon name="book-open-page-variant-outline" size={22} color={Palette.violet} />
            </View>
            <View>
              <Text style={styles.dictionaryTitle}>Dictionar LSR</Text>
              <Text style={styles.dictionarySubtitle}>1 240 de semne - cauta orice</Text>
            </View>
          </View>
          <Icon name="chevron-right" size={24} color={Palette.sub} />
        </TouchableOpacity>

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Provocarea Zilei</Text>
            <View style={styles.rewardBadge}>
              <Text style={styles.rewardText}>+50 XP total</Text>
            </View>
          </View>

          {challenges.map(item => (
            <View
              key={item.title}
              style={[styles.challengeCard, item.done && styles.challengeCardDone]}>
              <View style={[styles.challengeIcon, item.done && styles.challengeIconDone]}>
                <Icon
                  name={item.done ? 'check-bold' : item.icon}
                  size={18}
                  color={item.done ? '#FFFFFF' : Palette.violet}
                />
              </View>

              <View style={styles.challengeContent}>
                <Text style={[styles.challengeTitle, item.done && styles.challengeTitleDone]}>
                  {item.title}
                </Text>
                <Text style={styles.challengeProgress}>
                  {item.progress}/{item.target} completate
                </Text>
              </View>

              <View style={[styles.challengeReward, item.done && styles.challengeRewardDone]}>
                <Text style={[styles.challengeRewardText, item.done && styles.challengeRewardTextDone]}>
                  {item.done ? 'Gata!' : `+${item.xp} XP`}
                </Text>
              </View>
            </View>
          ))}
        </View>

        <View style={[styles.section, styles.badgesSection]}>
          <Text style={styles.sectionTitle}>Insigne</Text>
          <View style={styles.badgesRow}>
            {badges.map(item => (
              <View key={item.label} style={[styles.badgeCard, item.locked && styles.badgeCardLocked]}>
                <View style={[styles.badgeCircle, item.locked && styles.badgeCircleLocked]}>
                  <Text style={styles.badgeEmoji}>{item.emoji}</Text>
                </View>
                <Text style={[styles.badgeLabel, item.locked && styles.badgeLabelLocked]}>{item.label}</Text>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: Palette.bg,
  },
  container: {
    flex: 1,
    backgroundColor: Palette.bg,
  },
  contentContainer: {
    paddingBottom: 96,
  },
  hero: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 28,
    borderBottomLeftRadius: 32,
    borderBottomRightRadius: 32,
    overflow: 'hidden',
  },
  heroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 18,
  },
  avatarButton: {
    marginRight: 12,
  },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.22)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
  },
  heroTextBlock: {
    flex: 1,
  },
  heroLabel: {
    color: 'rgba(255,255,255,0.72)',
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 2,
  },
  heroNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  heroName: {
    color: '#FFFFFF',
    fontSize: 26,
    fontWeight: '900',
    lineHeight: 30,
  },
  streakBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.18)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 4,
  },
  streakValue: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
  },
  streakText: {
    color: 'rgba(255,255,255,0.76)',
    fontSize: 12,
    fontWeight: '700',
  },
  xpBox: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 20,
    padding: 14,
  },
  xpHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  xpLevel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
  xpValue: {
    color: 'rgba(255,255,255,0.82)',
    fontSize: 12,
    fontWeight: '700',
  },
  xpTrack: {
    height: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.25)',
    overflow: 'hidden',
  },
  xpFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: Palette.violetMid,
  },
  modesSection: {
    flexDirection: 'row',
    gap: 14,
    paddingHorizontal: 24,
    marginTop: 20,
  },
  modeCard: {
    flex: 1,
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#000000',
    shadowOffset: {width: 0, height: 6},
    shadowOpacity: 0.14,
    shadowRadius: 14,
    elevation: 5,
  },
  modePressable: {
    minHeight: 204,
    padding: 18,
  },
  modeIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  modeTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 6,
  },
  modeDescription: {
    color: 'rgba(255,255,255,0.78)',
    fontSize: 12,
    lineHeight: 18,
    fontWeight: '700',
    marginBottom: 14,
  },
  modeChip: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255,255,255,0.22)',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  modeChipText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '800',
  },
  dictionaryCard: {
    marginHorizontal: 24,
    marginTop: 16,
    backgroundColor: Palette.card,
    borderRadius: 24,
    padding: 16,
    borderWidth: 1.5,
    borderColor: Palette.rule,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  dictionaryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  dictionaryIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: Palette.violetLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dictionaryTitle: {
    color: Palette.ink,
    fontSize: 15,
    fontWeight: '800',
  },
  dictionarySubtitle: {
    color: Palette.sub,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 2,
  },
  section: {
    marginTop: 24,
    paddingHorizontal: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  sectionTitle: {
    color: Palette.ink,
    fontSize: 15,
    fontWeight: '800',
  },
  rewardBadge: {
    backgroundColor: Palette.orangeLight,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  rewardText: {
    color: Palette.orange,
    fontSize: 11,
    fontWeight: '800',
  },
  challengeCard: {
    backgroundColor: Palette.card,
    borderWidth: 1.5,
    borderColor: Palette.rule,
    borderRadius: 16,
    padding: 13,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  challengeCardDone: {
    backgroundColor: Palette.greenLight,
    borderColor: Palette.green,
  },
  challengeIcon: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: Palette.violetLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  challengeIconDone: {
    backgroundColor: Palette.green,
  },
  challengeContent: {
    flex: 1,
    marginLeft: 10,
  },
  challengeTitle: {
    color: Palette.ink,
    fontSize: 14,
    fontWeight: '700',
  },
  challengeTitleDone: {
    color: Palette.sub,
    textDecorationLine: 'line-through',
  },
  challengeProgress: {
    color: Palette.sub,
    fontSize: 11,
    fontWeight: '700',
    marginTop: 2,
  },
  challengeReward: {
    backgroundColor: Palette.violetLight,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  challengeRewardDone: {
    backgroundColor: Palette.greenLight,
  },
  challengeRewardText: {
    color: Palette.violet,
    fontSize: 11,
    fontWeight: '800',
  },
  challengeRewardTextDone: {
    color: Palette.green,
  },
  badgesSection: {
    marginBottom: 12,
  },
  badgesRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
  },
  badgeCard: {
    flex: 1,
    backgroundColor: Palette.card,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: Palette.rule,
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 6,
  },
  badgeCardLocked: {
    backgroundColor: Palette.mutedBg,
    borderColor: '#E5E7EB',
  },
  badgeCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Palette.violetLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  badgeCircleLocked: {
    backgroundColor: '#E5E7EB',
  },
  badgeEmoji: {
    fontSize: 22,
  },
  badgeLabel: {
    color: Palette.sub,
    fontSize: 10,
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 13,
  },
  badgeLabelLocked: {
    color: Palette.muted,
  },
});

export default HomeScreen;
