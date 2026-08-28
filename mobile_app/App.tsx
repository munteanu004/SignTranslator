import * as React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';

import ApiService, { GamificationStatus, HistoryEntry as ApiHistoryEntry, UserProfile } from './src/services/ApiService';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import CameraScreen from './src/screens/CameraScreen';
import TextSignScreen from './src/screens/TextSignScreen';
import DictionaryScreen from './src/screens/DictionaryScreen';
import HistoryScreen, { HistoryEntry as ScreenHistoryEntry } from './src/screens/HistoryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import EditProfileScreen from './src/screens/EditProfileScreen';
import LevelsScreen from './src/screens/LevelsScreen';
import LearnScreen from './src/screens/LearnScreen';
import { HomeIcon, CameraIcon, TextIcon, BookIcon, ClockIcon } from './src/components/Icons';

const Colors = {
  ink: '#1E1540',
  violet: '#7C3AED',
  violetL: '#EDE9FE',
  bg: '#F7F5FF',
  rule: '#EDE9FE',
};

type Screen =
  | 'Home'
  | 'Camera'
  | 'TextSign'
  | 'Dictionary'
  | 'History'
  | 'Profile'
  | 'Settings'
  | 'EditProfile'
  | 'Levels'
  | 'Learn';

type TabItem = {
  key: Screen;
  label: string;
  Icon: React.FC<{ color: string; size: number }>;
};

type TextSignLaunch = {
  text: string;
  lookup?: string;
  lookupType?: 'english' | 'romanian';
  token: number;
};

const TAB_ITEMS: TabItem[] = [
  { key: 'Home', label: 'Acasă', Icon: HomeIcon },
  { key: 'Camera', label: 'Live', Icon: CameraIcon },
  { key: 'TextSign', label: 'Text–Semn', Icon: TextIcon },
  { key: 'Dictionary', label: 'Dicționar', Icon: BookIcon },
  { key: 'History', label: 'Istoric', Icon: ClockIcon },
];

const App = (): React.JSX.Element => {
  const [user, setUser] = React.useState<UserProfile | null>(null);
  const [screen, setScreen] = React.useState<Screen>('Home');
  const [history, setHistory] = React.useState<ApiHistoryEntry[]>([]);
  const [gamification, setGamification] = React.useState<GamificationStatus | null>(null);
  const [checkingAuth, setCheckingAuth] = React.useState(true);
  const [replayEntry, setReplayEntry] = React.useState<ScreenHistoryEntry | null>(null);
  const [replayToken, setReplayToken] = React.useState(0);
  const [textSignLaunch, setTextSignLaunch] = React.useState<TextSignLaunch | null>(null);
  const [avatarSpeed, setAvatarSpeed] = React.useState(1.0);
  const [editProfileReturnTo, setEditProfileReturnTo] = React.useState<Screen>('Settings');

  const SPEED_MAP: Record<string, number> = { lent: 0.5, normal: 1.0, rapid: 1.75 };

  const loadSettings = async () => {
    try {
      const s = await ApiService.getSettings();
      setAvatarSpeed(SPEED_MAP[s.avatar_speed] ?? 1.0);
    } catch {}
  };

  const loadGamification = async () => {
    try {
      const status = await ApiService.getGamificationStatus();
      setGamification(status);
      setUser(prev => (prev ? { ...prev, xp: status.xp, streak: status.streak, level: status.level } : prev));
    } catch {}
  };

  React.useEffect(() => {
    const checkToken = async () => {
      if (ApiService.getToken()) {
        try {
          const res = await ApiService.getMe();
          setUser(res.user);
          loadHistory();
          loadGamification();
          loadSettings();
        } catch {
          ApiService.setToken(null);
        }
      }
      setCheckingAuth(false);
    };
    checkToken();
  }, []);

  const loadHistory = async () => {
    try {
      const h = await ApiService.getHistory();
      setHistory(h);
    } catch {}
  };

  const handleLogin = (u: UserProfile) => {
    setUser(u);
    loadHistory();
    loadGamification();
    loadSettings();
  };

  const handleLogout = () => {
    setUser(null);
    setHistory([]);
    setGamification(null);
    ApiService.setToken(null);
    setScreen('Home');
  };

  const addHistory = async (entry: any) => {
    try {
      await ApiService.saveHistory({
        type: entry.type,
        input_text: entry.text || entry.input_text || '',
        output_text: entry.prediction || entry.output_text || '',
        words: entry.words || [],
        confidence: entry.confidence,
      });
      loadHistory();
    } catch {}
  };

  const reportSessionProgress = async (type: 'sign-to-text' | 'text-to-sign') => {
    try {
      await ApiService.reportProgress(type);
    } catch {}
    loadGamification();
  };

  const claimDailyReward = async () => {
    try {
      await ApiService.claimDailyReward();
    } finally {
      await loadGamification();
    }
  };

  const claimChallengeReward = async (challengeKey: string) => {
    try {
      await ApiService.claimChallenge(challengeKey);
    } finally {
      await loadGamification();
    }
  };

  const deleteHistory = async (id: string | number) => {
    try {
      await ApiService.deleteHistory(Number(id));
      setHistory(prev => prev.filter(h => h.id !== Number(id)));
    } catch {}
  };

  const clearHistory = async () => {
    try {
      await ApiService.clearHistory();
      setHistory([]);
    } catch {}
  };

  const handleReplay = (entry: ScreenHistoryEntry) => {
    setReplayEntry(entry);
    setReplayToken(prev => prev + 1);
    setScreen(entry.type === 'sign-to-text' ? 'Camera' : 'TextSign');
  };

  if (checkingAuth) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.violet} />
      </View>
    );
  }

  if (!user) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  const historyForScreen = history.map(h => ({
    id: String(h.id),
    type: h.type as 'sign-to-text' | 'text-to-sign',
    words: h.words,
    text: h.input_text || h.output_text,
    outputText: h.output_text,
    confidence: h.confidence,
    timestamp: h.timestamp,
  }));
  const signHistoryCount = history.filter(h => h.type === 'sign-to-text').length;
  const textHistoryCount = history.filter(h => h.type === 'text-to-sign').length;

  const renderScreen = () => {
    switch (screen) {
      case 'Home':
        return (
          <HomeScreen
            user={user}
            gamification={gamification}
            onNavigate={(s: string) => setScreen(s as Screen)}
            onOpenProfile={() => setScreen('Profile')}
            onOpenLevels={() => setScreen('Levels')}
            onClaimDaily={claimDailyReward}
            onClaimChallenge={claimChallengeReward}
          />
        );
      case 'Camera':
        return (
          <CameraScreen
            onBack={() => setScreen('Home')}
            onSaveHistory={addHistory}
            onCompleteSession={reportSessionProgress}
            replayEntry={replayEntry?.type === 'sign-to-text' ? replayEntry : null}
            replayToken={replayToken}
            onReplayHandled={() => setReplayEntry(null)}
          />
        );
      case 'TextSign':
        return (
          <TextSignScreen
            onBack={() => setScreen('Home')}
            onSaveHistory={addHistory}
            onCompleteSession={reportSessionProgress}
            replayEntry={replayEntry?.type === 'text-to-sign' ? replayEntry : null}
            replayToken={replayToken}
            onReplayHandled={() => setReplayEntry(null)}
            initialText={textSignLaunch?.text || ''}
            exactLookup={textSignLaunch?.lookup}
            exactLookupType={textSignLaunch?.lookupType}
            initialPlaybackToken={textSignLaunch?.token || 0}
            onInitialPlaybackHandled={() => setTextSignLaunch(null)}
            initialSpeed={avatarSpeed}
          />
        );
      case 'Dictionary':
        return (
          <DictionaryScreen
            onBack={() => setScreen('Home')}
            onPracticeSign={entry => {
              setTextSignLaunch({
                text: entry.word,
                lookup: entry.lookup,
                lookupType: entry.lookup_type,
                token: Date.now(),
              });
              setScreen('TextSign');
            }}
          />
        );
      case 'History':
        return (
          <HistoryScreen
            history={historyForScreen}
            onDelete={deleteHistory}
            onClearAll={clearHistory}
            onReplay={handleReplay as any}
            onBack={() => setScreen('Home')}
          />
        );
      case 'Profile':
        return (
          <ProfileScreen
            user={user}
            signHistoryCount={signHistoryCount}
            textHistoryCount={textHistoryCount}
            gamification={gamification}
            onOpenSettings={() => setScreen('Settings')}
            onBack={() => setScreen('Home')}
            onEditProfile={() => {
              setEditProfileReturnTo('Profile');
              setScreen('EditProfile');
            }}
          />
        );
      case 'Settings':
        return (
          <SettingsScreen
            onBack={() => setScreen('Profile')}
            onLogout={handleLogout}
            onAvatarSpeedChange={setAvatarSpeed}
            onEditProfile={() => {
              setEditProfileReturnTo('Settings');
              setScreen('EditProfile');
            }}
          />
        );
      case 'EditProfile':
        return (
          <EditProfileScreen
            user={user}
            onBack={() => setScreen(editProfileReturnTo)}
            onSave={updated => {
              setUser(updated);
              setScreen(editProfileReturnTo);
            }}
          />
        );
      case 'Levels':
        return <LevelsScreen gamification={gamification} onBack={() => setScreen('Home')} />;
      case 'Learn':
        return <LearnScreen onBack={() => setScreen('Home')} />;
      default:
        return null;
    }
  };

  const showTabBar = !['Levels', 'Settings', 'Profile', 'EditProfile', 'Learn'].includes(screen);

  return (
    <View style={styles.container}>
      <View style={styles.screenArea}>{renderScreen()}</View>

      {showTabBar && (
        <View style={[styles.tabBar, { backdropFilter: 'blur(20px)' } as any]}>
          {TAB_ITEMS.map(tab => {
            const isActive = screen === tab.key;
            const iconColor = isActive ? Colors.violet : '#9CA3AF';
            return (
              <TouchableOpacity key={tab.key} style={styles.tabItem} onPress={() => setScreen(tab.key)}>
                <View style={[styles.tabIconWrap, isActive && styles.tabIconWrapActive]}>
                  <tab.Icon color={iconColor} size={20} />
                </View>
                <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>{tab.label}</Text>
                {tab.key === 'History' && history.length > 0 && !isActive && (
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{history.length > 99 ? '99+' : history.length}</Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    overflow: 'hidden',
  },
  screenArea: {
    flex: 1,
    overflow: 'hidden',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.bg,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.97)',
    paddingBottom: 14,
    paddingTop: 6,
    marginHorizontal: 12,
    marginBottom: 12,
    borderRadius: 24,
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
    shadowColor: '#1E1540',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 12,
    zIndex: 50,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    position: 'relative',
    paddingHorizontal: 2,
  },
  tabIconWrap: {
    width: 42,
    height: 30,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  tabIconWrapActive: {
    backgroundColor: Colors.violetL,
  },
  tabLabel: {
    fontSize: 9,
    color: '#94A3B8',
    marginTop: 2,
    fontWeight: '600',
  },
  tabLabelActive: {
    color: Colors.violet,
    fontWeight: '800',
  },
  badge: {
    position: 'absolute',
    top: 2,
    right: 2,
    backgroundColor: '#DC2626',
    borderRadius: 99,
    minWidth: 16,
    height: 16,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 3,
  },
  badgeText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: '800',
  },
});

export default App;
