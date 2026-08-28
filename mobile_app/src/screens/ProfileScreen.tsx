import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
} from 'react-native';
import { Colors } from '../theme';
import ApiService, { GamificationStatus, UserProfile } from '../services/ApiService';
import { ArrowLeftIcon, BadgeIcon, FireIcon, SettingsIcon, StarIcon } from '../components/Icons';

interface ProfileScreenProps {
  user: UserProfile;
  signHistoryCount: number;
  textHistoryCount: number;
  gamification: GamificationStatus | null;
  onOpenSettings: () => void;
  onBack: () => void;
  onEditProfile?: () => void;
}

const ProfileScreen: React.FC<ProfileScreenProps> = ({
  user,
  signHistoryCount,
  textHistoryCount,
  gamification,
  onOpenSettings,
  onBack,
  onEditProfile,
}) => {
  const streak = gamification?.streak ?? 0;
  const xp = gamification?.xp ?? 0;
  const level = gamification?.level ?? 1;
  const currentLevelXp = gamification?.current_level_xp ?? 0;
  const nextLevelXp = gamification?.next_level_xp ?? 100;
  const xpInLevel = Math.max(0, xp - currentLevelXp);
  const xpSpan = Math.max(1, nextLevelXp - currentLevelXp);

  const initials = user.name
    .split(' ')
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const progressPct = Math.min(100, (xpInLevel / xpSpan) * 100);

  const stats = [
    { label: 'Traduceri Live', value: signHistoryCount, color: Colors.violet, bg: Colors.violetL },
    { label: 'Text -> Semn', value: textHistoryCount, color: Colors.teal, bg: Colors.tealL },
    { label: 'Total XP', value: xp, color: Colors.amber, bg: Colors.amberL },
    { label: 'Zile streak', value: streak, color: Colors.green, bg: Colors.greenL },
  ];
  const maxStatValue = Math.max(1, ...stats.map(item => item.value));

  const badges = (gamification?.achievements ?? []).slice(0, 6).map(item => ({
    key: item.key,
    label: item.title,
    done: item.earned,
  }));

  return (
    <View style={styles.container}>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={[styles.header, { background: 'linear-gradient(145deg,#2E1065,#1E0A47)' } as any]}>
          <View style={styles.headerGlow} />

          <View style={styles.headerTop}>
            <TouchableOpacity onPress={onBack} style={styles.headerButton} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>

            <Text style={styles.headerTitle}>Profilul meu</Text>

            <TouchableOpacity onPress={onOpenSettings} style={styles.headerButton} activeOpacity={0.85}>
              <SettingsIcon color="rgba(255,255,255,0.72)" size={18} />
            </TouchableOpacity>
          </View>

          <View style={styles.profileRow}>
            <TouchableOpacity activeOpacity={0.85} onPress={onEditProfile} style={styles.avatarTouchable}>
              {user.avatar_url ? (
                <Image
                  source={{ uri: ApiService.getAvatarUrl(user.avatar_url) }}
                  style={styles.avatarImage}
                />
              ) : (
                <View style={[styles.avatar, { background: 'linear-gradient(135deg,#7C3AED,#0D9488)' } as any]}>
                  <Text style={styles.avatarText}>{initials}</Text>
                </View>
              )}
            </TouchableOpacity>

            <View>
              <Text style={styles.name}>{user.name}</Text>
              <Text style={styles.email}>{user.email}</Text>

              <View style={styles.profilePills}>
                <View style={styles.profilePill}><View style={styles.profilePillIconWrap}><StarIcon color="#FFFFFF" size={12} /></View><Text style={styles.profilePillText}>Nivel {level}</Text></View>
                <View style={[styles.profilePill, styles.profilePillWarm]}><View style={styles.profilePillIconWrap}><FireIcon size={12} /></View><Text style={[styles.profilePillText, styles.profilePillWarmText]}>{streak} zile</Text></View>
              </View>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionCaption}>Statistici</Text>
          <View style={styles.statsGrid}>
            {stats.map(item => (
              <View key={item.label} style={styles.statCard}>
                <Text style={[styles.statValue, { color: item.color }]}>{item.value}</Text>
                <Text style={styles.statLabel}>{item.label}</Text>
                <View style={[styles.statBarTrack, { backgroundColor: item.bg }]}>
                  <View
                    style={[
                      styles.statBarFill,
                      {
                        backgroundColor: item.color,
                        width: `${Math.max(8, (item.value / maxStatValue) * 100)}%`,
                      },
                    ]} />
                </View>
              </View>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.progressCard}>
            <View style={styles.progressTop}>
              <Text style={styles.progressTitle}>Progres nivel {level} → {level + 1}</Text>
              <Text style={styles.progressCount}>{xpInLevel} / {xpSpan} XP</Text>
            </View>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${progressPct}%` } as any]} />
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.badgesTitle}>Insigne</Text>
          <View style={styles.badgesGrid}>
            {badges.length === 0 ? (
              <View style={styles.badgeCard}>
                <Text style={styles.badgeLabel}>Insignele se incarca...</Text>
              </View>
            ) : badges.map(item => (
              <View key={item.key} style={[styles.badgeCard, !item.done && styles.badgeCardLocked]}>
                <View style={styles.badgeIconWrap}><BadgeIcon badgeKey={item.key} size={24} color={item.done ? Colors.violet : '#B8B4C9'} /></View>
                <Text style={styles.badgeLabel}>{item.label}</Text>
                {item.done && <Text style={styles.badgeEarned}>Obtinut</Text>}
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
  },
  scroll: {
    flex: 1,
  },
  content: {
    paddingBottom: 112,
  },
  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 32,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
    position: 'relative',
    overflow: 'hidden',
  },
  headerGlow: {
    position: 'absolute',
    top: -40,
    right: -40,
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: 'rgba(124,58,237,0.15)',
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 24,
  },
  headerButton: {
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
    flex: 1,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  avatarTouchable: {
    position: 'relative',
  },
  avatarImage: {
    width: 72,
    height: 72,
    borderRadius: 24,
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.25)',
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.15)',
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
    elevation: 4,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 26,
    fontWeight: '900',
  },
  name: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '900',
  },
  email: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 3,
  },
  profilePills: {
    flexDirection: 'row',
    gap: 6,
    marginTop: 6,
  },
  profilePill: {
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  profilePillWarm: {
    backgroundColor: 'rgba(249,115,22,0.2)',
  },
  profilePillIconWrap: {
    marginRight: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  profilePillText: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 10,
    fontWeight: '700',
  },
  profilePillWarmText: {
    color: '#FB923C',
  },
  section: {
    paddingHorizontal: 16,
    paddingTop: 18,
  },
  sectionCaption: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1.2,
    marginBottom: 13,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  statCard: {
    width: '48%',
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },
  statValue: {
    fontSize: 28,
    fontWeight: '900',
    lineHeight: 30,
  },
  statLabel: {
    color: Colors.sub,
    fontSize: 11,
    fontWeight: '600',
    marginTop: 5,
  },
  statBarTrack: {
    height: 3,
    borderRadius: 99,
    marginTop: 8,
    overflow: 'hidden',
  },
  statBarFill: {
    height: '100%',
    borderRadius: 99,
  },
  progressCard: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },
  progressTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  progressTitle: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '800',
  },
  progressCount: {
    color: Colors.sub,
    fontSize: 12,
    fontWeight: '600',
  },
  progressTrack: {
    height: 10,
    borderRadius: 99,
    backgroundColor: Colors.violetL,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 99,
    backgroundColor: Colors.violet,
  },
  badgesTitle: {
    color: Colors.ink,
    fontSize: 15,
    fontWeight: '800',
    marginBottom: 13,
  },
  badgesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  badgeCard: {
    width: '31%',
    backgroundColor: Colors.card,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 8,
  },
  badgeCardLocked: {
    backgroundColor: '#F3F4F6',
    borderColor: '#E5E7EB',
    opacity: 0.4,
  },
  badgeIconWrap: {
    width: 28,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeLabel: {
    color: Colors.sub,
    fontSize: 10,
    fontWeight: '700',
    marginTop: 6,
    textAlign: 'center',
  },
  badgeEarned: {
    color: Colors.green,
    fontSize: 9,
    fontWeight: '600',
    marginTop: 2,
  },
});

export default ProfileScreen;

