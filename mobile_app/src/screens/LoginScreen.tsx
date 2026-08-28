import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { Colors } from '../theme';
import ApiService from '../services/ApiService';



const GOOGLE_CLIENT_ID = '93868467081-i3v8l2urr4t0vneqk6oeotbbf3u1ejpd.apps.googleusercontent.com';

const GoogleDiv = 'div' as any;

interface LoginScreenProps {
  onLogin: (user: { name: string; email: string }) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin }) => {
  const [mode, setMode] = React.useState<'login' | 'register'>('login');
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [name, setName] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const googleBtnRef = React.useRef<any>(null);
  const callbackRef = React.useRef<(r: any) => void>(() => {});

  
  callbackRef.current = async (response: any) => {
    const credential = response?.credential;
    if (!credential) return;
    setLoading(true);
    setError('');
    try {
      const result = await ApiService.loginWithGoogle(credential);
      ApiService.setToken(result.token);
      onLogin(result.user);
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Eroare la autentificarea Google.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;
    const tryInit = () => {
      const win = window as any;
      if (!win.google?.accounts?.id) return false;
      if (!googleBtnRef.current) return false;
      win.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (r: any) => callbackRef.current(r),
      });
      win.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'filled_black',
        size: 'large',
        width: 340,
        text: 'continue_with',
        locale: 'ro',
      });
      return true;
    };
    if (!tryInit()) {
      const interval = setInterval(() => { if (tryInit()) clearInterval(interval); }, 500);
      return () => clearInterval(interval);
    }
  }, []);

  const handleSubmit = async () => {
    if (mode === 'register' && !name.trim()) {
      setError('Introduceți numele complet.');
      return;
    }
    if (!email.includes('@')) {
      setError('Adresă email invalidă.');
      return;
    }
    if (password.length < 6) {
      setError('Parola trebuie să aibă minimum 6 caractere.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const result = mode === 'login'
        ? await ApiService.login(email.trim(), password)
        : await ApiService.register(name.trim(), email.trim(), password);
      ApiService.setToken(result.token);
      onLogin(result.user);
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Eroare la conectare. Verifică serverul.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.glowLeft} />
      <View style={styles.glowRight} />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <View style={[styles.logoBox, { background: 'linear-gradient(135deg,#7C3AED,#0D9488)' } as any]}>
            <Text style={styles.logoText}>LSR</Text>
          </View>
          <Text style={styles.wordmark}>SignTranslator</Text>
          <View style={styles.wordmarkLine} />
          <Text style={styles.subtitle}>Învață limbajul semnelor române{'\n'}Learn Romanian Sign Language</Text>
        </View>

        <View style={styles.toggleRow}>
          {[
            { id: 'login' as const, label: 'Autentificare' },
            { id: 'register' as const, label: 'Cont nou' },
          ].map(item => (
            <TouchableOpacity
              key={item.id}
              activeOpacity={0.85}
              onPress={() => {
                setMode(item.id);
                setError('');
              }}
              style={[styles.toggleButton, mode === item.id && styles.toggleButtonActive]}>
              <Text style={[styles.toggleButtonText, mode === item.id && styles.toggleButtonTextActive]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.form}>
          {mode === 'register' && (
            <View>
              <Text style={styles.label}>Nume complet</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                placeholder="Maria Popescu"
                placeholderTextColor="rgba(255,255,255,0.35)"
                style={styles.input}
              />
            </View>
          )}

          <View>
            <Text style={styles.label}>Email</Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder="maria@email.ro"
              placeholderTextColor="rgba(255,255,255,0.35)"
              keyboardType="email-address"
              autoCapitalize="none"
              style={styles.input}
            />
          </View>

          <View>
            <Text style={styles.label}>Parolă</Text>
            <TextInput
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor="rgba(255,255,255,0.35)"
              secureTextEntry
              style={styles.input}
            />
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {mode === 'login' && <Text style={styles.forgotText}>Ai uitat parola?</Text>}

          <TouchableOpacity activeOpacity={0.88} onPress={handleSubmit} style={styles.submitButton}>
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.submitButtonText}>{mode === 'login' ? 'Intră în cont →' : 'Creează cont →'}</Text>
            )}
          </TouchableOpacity>

          <View style={styles.dividerRow}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>sau</Text>
            <View style={styles.dividerLine} />
          </View>

          {GOOGLE_CLIENT_ID ? (
            <GoogleDiv
              ref={(el: any) => { googleBtnRef.current = el; }}
              style={{ width: '100%', minHeight: 46, display: 'flex', justifyContent: 'center' }}
            />
          ) : (
            <View style={[styles.googleButton, { opacity: 0.5 }]}>
              <Text style={styles.googleIcon}>G</Text>
              <Text style={styles.googleText}>Continuă cu Google</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F0A1E',
    overflow: 'hidden',
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 112,
  },
  glowLeft: {
    position: 'absolute',
    top: -80,
    left: -60,
    width: 260,
    height: 260,
    borderRadius: 130,
    backgroundColor: 'rgba(124,58,237,0.18)',
  },
  glowRight: {
    position: 'absolute',
    top: 120,
    right: -80,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(13,148,136,0.12)',
  },
  hero: {
    paddingTop: 50,
    paddingHorizontal: 28,
    paddingBottom: 28,
    alignItems: 'center',
  },
  logoBox: {
    width: 80,
    height: 80,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 18,
  },
  logoText: {
    color: '#FFFFFF',
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 2,
  },
  wordmark: {
    color: '#A78BFA',
    fontSize: 30,
    fontWeight: '900',
    letterSpacing: -1,
  },
  wordmarkLine: {
    width: 60,
    height: 2,
    borderRadius: 99,
    backgroundColor: Colors.teal,
    opacity: 0.6,
    marginTop: 3,
  },
  subtitle: {
    color: 'rgba(255,255,255,0.45)',
    fontSize: 13,
    fontWeight: '600',
    marginTop: 6,
    lineHeight: 20,
    textAlign: 'center',
  },
  toggleRow: {
    marginHorizontal: 24,
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 16,
    padding: 4,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  toggleButton: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: 'center',
  },
  toggleButtonActive: {
    backgroundColor: 'rgba(124,58,237,0.7)',
  },
  toggleButtonText: {
    color: 'rgba(255,255,255,0.4)',
    fontSize: 13,
    fontWeight: '800',
  },
  toggleButtonTextActive: {
    color: '#FFFFFF',
  },
  form: {
    paddingHorizontal: 24,
    paddingTop: 22,
    gap: 12,
  },
  label: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  input: {
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 13,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  errorBox: {
    backgroundColor: 'rgba(220,38,38,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(220,38,38,0.3)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  errorText: {
    color: '#FCA5A5',
    fontSize: 12,
    fontWeight: '600',
  },
  forgotText: {
    color: 'rgba(124,58,237,0.8)',
    fontSize: 12,
    fontWeight: '700',
    textAlign: 'right',
  },
  submitButton: {
    backgroundColor: Colors.violet,
    borderRadius: 16,
    paddingVertical: 15,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 4,
    shadowColor: Colors.violet,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 24,
    elevation: 4,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
  dividerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginVertical: 4,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  dividerText: {
    color: 'rgba(255,255,255,0.25)',
    fontSize: 11,
    fontWeight: '600',
  },
  googleButton: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.1)',
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  googleIcon: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '800',
  },
  googleText: {
    color: 'rgba(255,255,255,0.75)',
    fontSize: 14,
    fontWeight: '700',
  },
});

export default LoginScreen;
