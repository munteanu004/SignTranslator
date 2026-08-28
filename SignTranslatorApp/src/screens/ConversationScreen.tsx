import React, {useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const ConversationScreen = () => {
  const [selectedLanguage, setSelectedLanguage] = useState('ASL (Eng)');

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton}>
          <Icon name="arrow-left" size={24} color="#45C8C2" />
        </TouchableOpacity>
      </View>

      {/* User Video Display */}
      <View style={styles.userVideoContainer}>
        <View style={styles.videoPlaceholder}>
          <Text style={styles.videoText}>USER SIGN INPUT</Text>
        </View>
      </View>

      {/* Translated Text */}
      <View style={styles.translationBox}>
        <Text style={styles.translationText}>Hola, cómo estás?</Text>
      </View>

      {/* Avatar Display */}
      <View style={styles.avatarContainer}>
        <View style={styles.avatarPlaceholder}>
          <Text style={styles.avatarText}>AVATAR</Text>
        </View>
      </View>

      {/* Language Selector Buttons */}
      <View style={styles.languageButtons}>
        <TouchableOpacity
          style={[
            styles.langButton,
            selectedLanguage === 'ASL (Eng)' && styles.langButtonActive,
          ]}
          onPress={() => setSelectedLanguage('ASL (Eng)')}>
          <Icon name="hand-wave" size={20} color="#FFFFFF" />
          <Text style={styles.langButtonText}>ASL (Eng)</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.langButton,
            selectedLanguage === 'Auto' && styles.langButtonActive,
          ]}
          onPress={() => setSelectedLanguage('Auto')}>
          <Icon name="auto-fix" size={20} color="#FFFFFF" />
          <Text style={styles.langButtonText}>Auto</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.langButton,
            selectedLanguage === 'Română' && styles.langButtonActive,
          ]}
          onPress={() => setSelectedLanguage('Română')}>
          <Icon name="microphone" size={20} color="#FFFFFF" />
          <Text style={styles.langButtonText}>Spanish</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 10,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userVideoContainer: {
    height: 200,
    marginHorizontal: 20,
    marginBottom: 15,
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: '#F5F5F5',
  },
  videoPlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  videoText: {
    fontSize: 18,
    color: '#CCCCCC',
    fontWeight: '600',
  },
  translationBox: {
    backgroundColor: '#F5F5F5',
    marginHorizontal: 20,
    padding: 20,
    borderRadius: 20,
    marginBottom: 15,
  },
  translationText: {
    fontSize: 18,
    color: '#111111',
    textAlign: 'center',
  },
  avatarContainer: {
    flex: 1,
    marginHorizontal: 20,
    marginBottom: 15,
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: '#F5F5F5',
  },
  avatarPlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 24,
    color: '#CCCCCC',
    fontWeight: '600',
  },
  languageButtons: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingBottom: 100,
    gap: 12,
  },
  langButton: {
    flex: 1,
    backgroundColor: '#45C8C2',
    paddingVertical: 14,
    borderRadius: 30,
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  langButtonActive: {
    backgroundColor: '#3AB8B2',
  },
  langButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '500',
  },
});

export default ConversationScreen;
