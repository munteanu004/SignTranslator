import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Colors } from '../theme';
import ApiService from '../services/ApiService';
import {
  ArrowLeftIcon,
  UserIcon,
  BellIcon,
  VolumeIcon,
  GaugeIcon,
  PhoneVibrateIcon,
  InfoIcon,
  ShieldIcon,
  FileTextIcon,
  LogoutIcon,
  CheckIcon,
} from '../components/Icons';

interface SettingsScreenProps {
  onBack: () => void;
  onLogout: () => void;
  onAvatarSpeedChange?: (speed: number) => void;
  onEditProfile?: () => void;
}

const SPEED_MAP: Record<string, number> = { lent: 0.5, normal: 1.0, rapid: 1.75 };

const Toggle = ({ value, onChange }: { value: boolean; onChange: (next: boolean) => void }) => (
  <TouchableOpacity activeOpacity={0.85} onPress={() => onChange(!value)} style={[styles.toggle, value && styles.toggleActive]}>
    <View style={[styles.toggleKnob, value && styles.toggleKnobActive]} />
  </TouchableOpacity>
);

const SettingsScreen: React.FC<SettingsScreenProps> = ({ onBack, onLogout, onAvatarSpeedChange, onEditProfile }) => {
  const [notifications, setNotifications] = React.useState(true);
  const [sounds, setSounds] = React.useState(true);
  const [avatarSpeed, setAvatarSpeed] = React.useState<'lent' | 'normal' | 'rapid'>('normal');
  const [haptic, setHaptic] = React.useState(true);
  const [savedVisible, setSavedVisible] = React.useState(false);
  const savedOpacity = React.useRef(new Animated.Value(0)).current;
  const saveTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    ApiService.getSettings().then(s => {
      setAvatarSpeed((s.avatar_speed || 'normal') as 'lent' | 'normal' | 'rapid');
      setNotifications(s.notifications ?? true);
      setSounds(s.sounds ?? true);
      setHaptic(s.haptic ?? true);
    }).catch(() => {});
  }, []);

  const showSavedToast = () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    Animated.sequence([
      Animated.timing(savedOpacity, { toValue: 1, duration: 180, useNativeDriver: true }),
      Animated.delay(1400),
      Animated.timing(savedOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start();
    saveTimer.current = setTimeout(() => setSavedVisible(false), 2000);
    setSavedVisible(true);
  };

  const save = (patch: Record<string, any>) => {
    ApiService.updateSettings(patch).then(() => showSavedToast()).catch(() => {});
  };

  const handleAvatarSpeed = (value: 'lent' | 'normal' | 'rapid') => {
    setAvatarSpeed(value);
    save({ avatar_speed: value });
    onAvatarSpeedChange?.(SPEED_MAP[value]);
  };

  return (
    <View style={styles.container}>
      {}
      {savedVisible && (
        <Animated.View style={[styles.savedToast, { opacity: savedOpacity }]}>
          <CheckIcon color="#22C55E" size={14} />
          <Text style={styles.savedToastText}>Salvat</Text>
        </Animated.View>
      )}

      <ScrollView style={styles.scroll} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {}
        <View style={[styles.header, { background: 'linear-gradient(145deg,#1E1540,#111827)' } as any]}>
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={onBack} style={styles.backButton} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>
            <View>
              <Text style={styles.headerTitle}>Setări</Text>
              <Text style={styles.headerSub}>Personalizează experiența</Text>
            </View>
          </View>
        </View>

        {}
        <SectionLabel>Cont</SectionLabel>
        <View style={styles.card}>
          <SettingsRow
            Icon={<UserIcon color={Colors.violet} size={18} />}
            iconBg={Colors.violetL}
            label="Profilul meu"
            sub="Editează datele contului"
            right={
              <TouchableOpacity activeOpacity={0.85} onPress={onEditProfile} style={styles.chip}>
                <Text style={styles.chipText}>Editează</Text>
              </TouchableOpacity>
            }
            border={false}
          />
        </View>

        {}
        <SectionLabel>Viteză avatar</SectionLabel>
        <View style={styles.card}>
          <View style={styles.speedRow}>
            <View style={styles.speedIconWrap}>
              <GaugeIcon color={Colors.teal} size={18} />
            </View>
            <View style={styles.speedTextCol}>
              <Text style={styles.rowLabel}>Viteză animație</Text>
              <Text style={styles.rowSub}>Controlează ritmul avatarului 3D</Text>
            </View>
          </View>
          <View style={styles.speedButtons}>
            {([
              { key: 'lent', label: 'Lent', sub: '0.5×' },
              { key: 'normal', label: 'Normal', sub: '1.0×' },
              { key: 'rapid', label: 'Rapid', sub: '1.75×' },
            ] as const).map(item => (
              <TouchableOpacity
                key={item.key}
                activeOpacity={0.85}
                onPress={() => handleAvatarSpeed(item.key)}
                style={[styles.speedBtn, avatarSpeed === item.key && styles.speedBtnActive]}>
                <Text style={[styles.speedBtnLabel, avatarSpeed === item.key && styles.speedBtnLabelActive]}>
                  {item.label}
                </Text>
                <Text style={[styles.speedBtnSub, avatarSpeed === item.key && styles.speedBtnSubActive]}>
                  {item.sub}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {}
        <SectionLabel>Notificări</SectionLabel>
        <View style={styles.card}>
          <SettingsRow
            Icon={<BellIcon color={Colors.violet} size={18} />}
            iconBg={Colors.violetL}
            label="Notificări push"
            sub="Mementouri și actualizări zilnice"
            right={<Toggle value={notifications} onChange={v => { setNotifications(v); save({ notifications: v }); }} />}
          />
          <SettingsRow
            Icon={<VolumeIcon color={Colors.violet} size={18} />}
            iconBg={Colors.violetL}
            label="Sunete"
            sub="Feedback audio la interacțiuni"
            right={<Toggle value={sounds} onChange={v => { setSounds(v); save({ sounds: v }); }} />}
          />
          <SettingsRow
            Icon={<PhoneVibrateIcon color={Colors.violet} size={18} />}
            iconBg={Colors.violetL}
            label="Vibrații"
            sub="Feedback haptic pe mobil"
            right={<Toggle value={haptic} onChange={v => { setHaptic(v); save({ haptic: v }); }} />}
            border={false}
          />
        </View>

        {}
        <SectionLabel>Despre</SectionLabel>
        <View style={styles.card}>
          <SettingsRow
            Icon={<InfoIcon color="#3B82F6" size={18} />}
            iconBg="#EFF6FF"
            label="Versiune aplicație"
            sub="LSR SignTranslator 1.0.0"
          />
          <SettingsRow
            Icon={<FileTextIcon color="#3B82F6" size={18} />}
            iconBg="#EFF6FF"
            label="Termeni și condiții"
            sub="Documentație legală"
          />
          <SettingsRow
            Icon={<ShieldIcon color="#3B82F6" size={18} />}
            iconBg="#EFF6FF"
            label="Politica de confidențialitate"
            sub="Date și securitate"
            border={false}
          />
        </View>

        {}
        <View style={styles.logoutWrap}>
          <TouchableOpacity activeOpacity={0.88} onPress={onLogout} style={styles.logoutButton}>
            <LogoutIcon color="#DC2626" size={18} />
            <Text style={styles.logoutText}>Deconectare</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
};

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <Text style={styles.sectionLabel}>{children}</Text>
);

const SettingsRow = ({
  Icon,
  iconBg,
  label,
  sub,
  right,
  border = true,
}: {
  Icon: React.ReactNode;
  iconBg: string;
  label: string;
  sub?: string;
  right?: React.ReactNode;
  border?: boolean;
}) => (
  <View style={[styles.row, !border && styles.rowNoBorder]}>
    <View style={[styles.rowIconBox, { backgroundColor: iconBg }]}>{Icon}</View>
    <View style={styles.rowTextWrap}>
      <Text style={styles.rowLabel}>{label}</Text>
      {sub ? <Text style={styles.rowSub}>{sub}</Text> : null}
    </View>
    {right}
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  scroll: { flex: 1 },
  content: { paddingBottom: 32 },

  savedToast: {
    position: 'absolute',
    top: 60,
    alignSelf: 'center',
    zIndex: 999,
    backgroundColor: '#F0FDF4',
    borderRadius: 99,
    borderWidth: 1,
    borderColor: '#BBF7D0',
    paddingHorizontal: 16,
    paddingVertical: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 6,
  },
  savedToastText: {
    color: '#16A34A',
    fontSize: 13,
    fontWeight: '700',
  },

  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 26,
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
    color: 'rgba(255,255,255,0.4)',
    fontSize: 11,
    fontWeight: '600',
    marginTop: 1,
  },

  sectionLabel: {
    color: Colors.sub,
    fontSize: 10,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 1.4,
    marginTop: 20,
    marginBottom: 8,
    marginHorizontal: 20,
  },

  card: {
    marginHorizontal: 16,
    backgroundColor: Colors.card,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: Colors.rule,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 10,
    elevation: 1,
  },

  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
  rowNoBorder: { borderBottomWidth: 0 },
  rowIconBox: {
    width: 36,
    height: 36,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  rowTextWrap: { flex: 1, minWidth: 0 },
  rowLabel: { color: Colors.ink, fontSize: 14, fontWeight: '700' },
  rowSub: { color: Colors.sub, fontSize: 11, fontWeight: '600', marginTop: 2 },

  chip: {
    backgroundColor: Colors.violetL,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chipText: { color: Colors.violet, fontSize: 11, fontWeight: '700' },

  
  speedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 12,
  },
  speedIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 11,
    backgroundColor: Colors.tealL,
    justifyContent: 'center',
    alignItems: 'center',
  },
  speedTextCol: { flex: 1 },
  speedButtons: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingBottom: 14,
  },
  speedBtn: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 14,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: 'transparent',
  },
  speedBtnActive: {
    backgroundColor: Colors.teal,
    borderColor: Colors.teal,
    shadowColor: Colors.teal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 2,
  },
  speedBtnLabel: { color: Colors.sub, fontSize: 13, fontWeight: '800' },
  speedBtnLabelActive: { color: '#FFFFFF' },
  speedBtnSub: { color: '#9CA3AF', fontSize: 10, fontWeight: '600', marginTop: 2 },
  speedBtnSubActive: { color: 'rgba(255,255,255,0.75)' },

  
  toggle: {
    width: 48,
    height: 28,
    borderRadius: 99,
    backgroundColor: '#D1D5DB',
    position: 'relative',
    flexShrink: 0,
  },
  toggleActive: { backgroundColor: Colors.violet },
  toggleKnob: {
    position: 'absolute',
    top: 3,
    left: 3,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 2,
  },
  toggleKnobActive: { left: 22 },

  
  logoutWrap: { paddingHorizontal: 16, paddingTop: 24 },
  logoutButton: {
    backgroundColor: '#FEF2F2',
    borderRadius: 18,
    borderWidth: 1.5,
    borderColor: '#FECACA',
    paddingVertical: 16,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
    gap: 10,
  },
  logoutText: { color: '#DC2626', fontSize: 14, fontWeight: '700' },
});

export default SettingsScreen;
