import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Animated,
  ActivityIndicator,
  Image,
} from 'react-native';
import { Colors } from '../theme';
import ApiService, { UserProfile } from '../services/ApiService';
import {
  ArrowLeftIcon,
  UserIcon,
  CheckIcon,
  ChevronRightIcon,
} from '../components/Icons';

const Svg = 'svg' as any;
const Path = 'path' as any;
const Circle = 'circle' as any;

const MailIcon = ({ color = '#6B7280', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
    <Path d="M22 6l-10 7L2 6" />
  </Svg>
);

const PhoneIcon = ({ color = '#6B7280', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.18 2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" />
  </Svg>
);

const LockIcon = ({ color = '#6B7280', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M19 11H5a2 2 0 00-2 2v7a2 2 0 002 2h14a2 2 0 002-2v-7a2 2 0 00-2-2z" />
    <Path d="M7 11V7a5 5 0 0110 0v4" />
  </Svg>
);

const CameraSmallIcon = ({ color = '#FFFFFF', size = 16 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <Path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" />
    <Circle cx="12" cy="13" r="4" />
  </Svg>
);

interface EditProfileScreenProps {
  user: UserProfile;
  onBack: () => void;
  onSave: (updated: UserProfile) => void;
}

type SkillLevel = 'incepator' | 'intermediar' | 'avansat';

const SKILL_LABELS: Record<SkillLevel, string> = {
  incepator: 'Începător',
  intermediar: 'Intermediar',
  avansat: 'Avansat',
};

const EditProfileScreen: React.FC<EditProfileScreenProps> = ({ user, onBack, onSave }) => {
  const [name, setName] = React.useState(user.name || '');
  const [email, setEmail] = React.useState(user.email || '');
  const [phone, setPhone] = React.useState(user.phone || '');
  const [skillLevel, setSkillLevel] = React.useState<SkillLevel>('incepator');
  const [showPasswordSection, setShowPasswordSection] = React.useState(false);
  const [currentPassword, setCurrentPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const [toastVisible, setToastVisible] = React.useState(false);
  const toastOpacity = React.useRef(new Animated.Value(0)).current;
  const toastTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  
  const [avatarPreview, setAvatarPreview] = React.useState<string>('');
  const [pendingAvatarDataUrl, setPendingAvatarDataUrl] = React.useState<string>('');
  const fileInputRef = React.useRef<any>(null);

  const currentAvatarUrl = user.avatar_url ? ApiService.getAvatarUrl(user.avatar_url) : '';

  React.useEffect(() => {
    ApiService.getSettings().then(s => {
      if (s.skill_level && s.skill_level in SKILL_LABELS) {
        setSkillLevel(s.skill_level as SkillLevel);
      }
    }).catch(() => {});
  }, []);

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: any) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Selectează un fișier imagine (JPG, PNG, etc.)');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Imaginea este prea mare. Maxim 5 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev: any) => {
      const dataUrl = ev.target?.result as string;
      setAvatarPreview(dataUrl);
      setPendingAvatarDataUrl(dataUrl);
      setError('');
    };
    reader.readAsDataURL(file);
    
    e.target.value = '';
  };

  const showToast = () => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    Animated.sequence([
      Animated.timing(toastOpacity, { toValue: 1, duration: 180, useNativeDriver: true }),
      Animated.delay(1400),
      Animated.timing(toastOpacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start();
    setToastVisible(true);
    toastTimer.current = setTimeout(() => setToastVisible(false), 2000);
  };

  const handleSave = async () => {
    setError('');
    if (!name.trim()) { setError('Numele este obligatoriu.'); return; }
    if (!email.trim()) { setError('Email-ul este obligatoriu.'); return; }
    if (showPasswordSection) {
      if (!currentPassword) { setError('Introdu parola curentă.'); return; }
      if (newPassword.length < 4) { setError('Parola nouă trebuie să aibă minim 4 caractere.'); return; }
      if (newPassword !== confirmPassword) { setError('Parolele nu coincid.'); return; }
    }

    setSaving(true);
    try {
      
      let newAvatarUrl = user.avatar_url || '';
      if (pendingAvatarDataUrl) {
        const res = await ApiService.uploadAvatar(pendingAvatarDataUrl);
        newAvatarUrl = res.avatar_url;
        setPendingAvatarDataUrl('');
      }

      const payload: Parameters<typeof ApiService.updateProfile>[0] = {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        skill_level: skillLevel,
      };
      if (showPasswordSection && newPassword) {
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }
      const profileRes = await ApiService.updateProfile(payload);
      const updatedUser = { ...profileRes.user, avatar_url: newAvatarUrl };
      onSave(updatedUser);
      showToast();

      if (showPasswordSection) {
        setShowPasswordSection(false);
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || 'A apărut o eroare. Încearcă din nou.';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const displayAvatar = avatarPreview || currentAvatarUrl;
  const avatarInitials = name.trim().split(' ').slice(0, 2).map(w => w[0] || '').join('').toUpperCase() || 'U';

  return (
    <View style={styles.container}>
      {}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' } as any}
        onChange={handleFileChange}
      />

      {}
      {toastVisible && (
        <Animated.View style={[styles.toast, { opacity: toastOpacity }]}>
          <CheckIcon color="#22C55E" size={14} />
          <Text style={styles.toastText}>Profilul a fost actualizat</Text>
        </Animated.View>
      )}

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled">

        {}
        <View style={[styles.header, { background: 'linear-gradient(145deg,#1E1540,#111827)' } as any]}>
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={onBack} style={styles.backBtn} activeOpacity={0.85}>
              <ArrowLeftIcon color="#FFFFFF" size={18} />
            </TouchableOpacity>
            <View>
              <Text style={styles.headerTitle}>Editează profil</Text>
              <Text style={styles.headerSub}>Actualizează datele tale</Text>
            </View>
          </View>

          {}
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={openFilePicker}
            style={styles.avatarWrap}>
            {displayAvatar ? (
              <Image
                source={{ uri: displayAvatar }}
                style={styles.avatarImage}
                resizeMode="cover"
              />
            ) : (
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarInitials}>{avatarInitials}</Text>
              </View>
            )}
            <View style={styles.cameraBtn}>
              <CameraSmallIcon color="#FFFFFF" size={14} />
            </View>
          </TouchableOpacity>
          <TouchableOpacity onPress={openFilePicker} activeOpacity={0.75}>
            <Text style={styles.changePhotoText}>
              {pendingAvatarDataUrl ? 'Poza selectată ✓' : 'Schimbă poza'}
            </Text>
          </TouchableOpacity>
        </View>

        {}
        <SectionLabel>Informații personale</SectionLabel>
        <View style={styles.card}>
          <InputRow
            icon={<UserIcon color={Colors.violet} size={18} />}
            iconBg={Colors.violetL}
            label="Nume complet"
            value={name}
            onChange={setName}
            placeholder="Numele tău"
            border
          />
          <InputRow
            icon={<MailIcon color={Colors.blue} size={18} />}
            iconBg={Colors.blueL}
            label="Email"
            value={email}
            onChange={setEmail}
            placeholder="adresa@email.com"
            keyboardType="email-address"
            autoCapitalize="none"
            border
          />
          <InputRow
            icon={<PhoneIcon color={Colors.teal} size={18} />}
            iconBg={Colors.tealL}
            label="Telefon"
            value={phone}
            onChange={setPhone}
            placeholder="+40 700 000 000"
            keyboardType="phone-pad"
            border={false}
          />
        </View>

        {}
        <SectionLabel>Preferințe</SectionLabel>
        <View style={styles.card}>
          <View style={styles.skillHeader}>
            <View style={[styles.iconBox, { backgroundColor: Colors.orangeL }]}>
              <LockIcon color={Colors.orange} size={18} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>Nivel</Text>
              <Text style={styles.rowSub}>Nivelul tău de cunoaștere LSR</Text>
            </View>
          </View>
          <View style={styles.skillButtons}>
            {(['incepator', 'intermediar', 'avansat'] as SkillLevel[]).map(key => (
              <TouchableOpacity
                key={key}
                activeOpacity={0.85}
                onPress={() => setSkillLevel(key)}
                style={[styles.skillBtn, skillLevel === key && styles.skillBtnActive]}>
                <Text style={[styles.skillBtnText, skillLevel === key && styles.skillBtnTextActive]}>
                  {SKILL_LABELS[key]}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {}
        <SectionLabel>Securitate</SectionLabel>
        <View style={styles.card}>
          <TouchableOpacity
            activeOpacity={0.85}
            onPress={() => { setShowPasswordSection(v => !v); setError(''); }}
            style={[styles.row, { borderBottomWidth: showPasswordSection ? 1 : 0 }]}>
            <View style={[styles.iconBox, { backgroundColor: '#FEF3C7' }]}>
              <LockIcon color="#D97706" size={18} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowLabel}>Schimbă parola</Text>
              <Text style={styles.rowSub}>Actualizează parola contului</Text>
            </View>
            <View style={[styles.chevronWrap, showPasswordSection && styles.chevronWrapOpen]}>
              <ChevronRightIcon color={Colors.sub} size={16} />
            </View>
          </TouchableOpacity>

          {showPasswordSection && (
            <View style={styles.passwordSection}>
              <PasswordInput
                label="Parola curentă"
                value={currentPassword}
                onChange={setCurrentPassword}
                placeholder="••••••••"
                border
              />
              <PasswordInput
                label="Parola nouă"
                value={newPassword}
                onChange={setNewPassword}
                placeholder="Minim 4 caractere"
                border
              />
              <PasswordInput
                label="Confirmă parola nouă"
                value={confirmPassword}
                onChange={setConfirmPassword}
                placeholder="Repetă parola nouă"
                border={false}
              />
            </View>
          )}
        </View>

        {}
        {!!error && (
          <View style={styles.errorBox}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {}
      <View style={styles.actionBar}>
        <TouchableOpacity activeOpacity={0.85} onPress={onBack} style={styles.cancelBtn}>
          <Text style={styles.cancelText}>Anulează</Text>
        </TouchableOpacity>
        <TouchableOpacity
          activeOpacity={0.85}
          onPress={handleSave}
          style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
          disabled={saving}>
          {saving
            ? <ActivityIndicator color="#FFFFFF" size="small" />
            : <Text style={styles.saveText}>Salvează</Text>}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <Text style={styles.sectionLabel}>{children}</Text>
);

const InputRow = ({
  icon, iconBg, label, value, onChange, placeholder, keyboardType, autoCapitalize, border,
}: {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  keyboardType?: any;
  autoCapitalize?: any;
  border: boolean;
}) => (
  <View style={[styles.row, !border && { borderBottomWidth: 0 }]}>
    <View style={[styles.iconBox, { backgroundColor: iconBg }]}>{icon}</View>
    <View style={{ flex: 1 }}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor="#9CA3AF"
        keyboardType={keyboardType || 'default'}
        autoCapitalize={autoCapitalize || 'words'}
      />
    </View>
  </View>
);

const PasswordInput = ({
  label, value, onChange, placeholder, border,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  border: boolean;
}) => (
  <View style={[styles.passwordRow, !border && { borderBottomWidth: 0 }]}>
    <Text style={styles.inputLabel}>{label}</Text>
    <TextInput
      style={styles.input}
      value={value}
      onChangeText={onChange}
      placeholder={placeholder}
      placeholderTextColor="#9CA3AF"
      secureTextEntry
      autoCapitalize="none"
    />
  </View>
);

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  scroll: { flex: 1 },
  content: { paddingBottom: 24 },

  toast: {
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
  toastText: { color: '#16A34A', fontSize: 13, fontWeight: '700' },

  header: {
    paddingTop: 46,
    paddingHorizontal: 18,
    paddingBottom: 28,
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
    alignItems: 'center',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 24,
    alignSelf: 'stretch',
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: { color: '#FFFFFF', fontSize: 17, fontWeight: '800' },
  headerSub: { color: 'rgba(255,255,255,0.4)', fontSize: 11, fontWeight: '600', marginTop: 1 },

  avatarWrap: { position: 'relative', marginBottom: 8 },
  avatarImage: {
    width: 84,
    height: 84,
    borderRadius: 42,
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  avatarCircle: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: Colors.violet,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255,255,255,0.25)',
  },
  avatarInitials: { color: '#FFFFFF', fontSize: 30, fontWeight: '800' },
  cameraBtn: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.violet,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2.5,
    borderColor: '#FFFFFF',
  },
  changePhotoText: {
    color: 'rgba(255,255,255,0.65)',
    fontSize: 12,
    fontWeight: '600',
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
  iconBox: {
    width: 36,
    height: 36,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  rowLabel: { color: Colors.ink, fontSize: 14, fontWeight: '700' },
  rowSub: { color: Colors.sub, fontSize: 11, fontWeight: '600', marginTop: 2 },

  inputLabel: {
    color: Colors.sub,
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 2,
  },
  input: {
    color: Colors.ink,
    fontSize: 14,
    fontWeight: '600',
    paddingVertical: 2,
    outlineStyle: 'none',
  } as any,

  skillHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
  skillButtons: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  skillBtn: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 14,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: 'transparent',
  },
  skillBtnActive: {
    backgroundColor: Colors.violet,
    borderColor: Colors.violet,
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 2,
  },
  skillBtnText: { color: Colors.sub, fontSize: 12, fontWeight: '700' },
  skillBtnTextActive: { color: '#FFFFFF' },

  chevronWrap: { padding: 4 },
  chevronWrapOpen: { transform: [{ rotate: '90deg' }] },

  passwordSection: {
    paddingHorizontal: 16,
    paddingBottom: 4,
  },
  passwordRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },

  errorBox: {
    marginHorizontal: 16,
    marginTop: 12,
    backgroundColor: '#FEF2F2',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#FECACA',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  errorText: { color: '#DC2626', fontSize: 13, fontWeight: '600' },

  actionBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 28,
    backgroundColor: 'rgba(247,245,255,0.97)',
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
    shadowColor: '#1E1540',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 8,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: '#F3F4F6',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: Colors.rule,
  },
  cancelText: { color: Colors.sub, fontSize: 14, fontWeight: '700' },
  saveBtn: {
    flex: 2,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: Colors.violet,
    alignItems: 'center',
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 14,
    elevation: 4,
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveText: { color: '#FFFFFF', fontSize: 14, fontWeight: '800' },
});

export default EditProfileScreen;
