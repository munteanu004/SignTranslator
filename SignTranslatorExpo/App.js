import React, { useState, useRef, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { WebView } from 'react-native-webview';
import Constants from 'expo-constants';
import { useCameraPermissions } from 'expo-camera';
import NativeCameraScreen from './NativeCameraScreen';

const WEBPACK_PORT = 3000;
const LOCALTUNNEL_URL = 'https://signtranslator.loca.lt';

function getWebpackUrl() {
  // Daca localtunnel ruleaza, foloseste HTTPS (permite camera in WebView pe telefon)
  if (LOCALTUNNEL_URL) return LOCALTUNNEL_URL;
  try {
    const hostUri =
      Constants.expoConfig?.hostUri ||
      Constants.manifest2?.extra?.expoGo?.debuggerHost ||
      Constants.manifest?.debuggerHost ||
      '';
    const ip = hostUri.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      return `http://${ip}:${WEBPACK_PORT}`;
    }
  } catch {}
  return `http://localhost:${WEBPACK_PORT}`;
}

export default function App() {
  const [url] = useState(getWebpackUrl);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [key, setKey] = useState(0);
  const [showNativeCamera, setShowNativeCamera] = useState(false);
  const webviewRef = useRef(null);

  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  // Request camera permission on mount
  useEffect(() => {
    if (cameraPermission && !cameraPermission.granted) {
      requestCameraPermission();
    }
  }, [cameraPermission]);

  // Handle messages from WebView (e.g. navigation to Live tab)
  const handleWebViewMessage = (event) => {
    try {
      const msg = JSON.parse(event.nativeEvent.data);
      if (msg.type === 'SHOW_NATIVE_CAMERA') {
        setShowNativeCamera(true);
      } else if (msg.type === 'HIDE_NATIVE_CAMERA') {
        setShowNativeCamera(false);
      }
    } catch {}
  };

  const handleCameraClose = () => {
    setShowNativeCamera(false);
    // Tell WebView we came back
    webviewRef.current?.injectJavaScript(
      `window.dispatchEvent(new CustomEvent('nativeCameraClosed')); true;`
    );
  };

  if (Platform.OS === 'web') {
    const IFrame = 'iframe';
    return (
      <View style={styles.container}>
        <IFrame
          src={url}
          allow="camera; microphone; autoplay"
          referrerPolicy="strict-origin-when-cross-origin"
          style={{ flex: 1, border: 'none', width: '100%' }}
        />
      </View>
    );
  }

  const reload = () => { setError(''); setLoading(true); setKey(k => k + 1); };

  return (
    <View style={styles.container}>
      {/* Top bar */}
      <View style={styles.topBar}>
        <Text style={styles.topBarText} numberOfLines={1}>{url}</Text>
        <TouchableOpacity onPress={reload}>
          <Text style={styles.reloadBtn}>↺</Text>
        </TouchableOpacity>
      </View>

      {/* WebView cu permisiuni camera */}
      <WebView
        key={key}
        ref={webviewRef}
        source={{ uri: url, headers: { 'bypass-tunnel-reminder': 'true' } }}
        style={styles.webview}
        onLoadStart={() => { setLoading(true); setError(''); }}
        onLoadEnd={() => setLoading(false)}
        onError={e => {
          setLoading(false);
          setError(e.nativeEvent.description || 'Nu se poate conecta la server.');
        }}
        onMessage={handleWebViewMessage}
        injectedJavaScriptBeforeContentLoaded={`window.__EXPO_NATIVE_CONTAINER__ = true; true;`}
        injectedJavaScript={`window.__EXPO_NATIVE_CONTAINER__ = true; true;`}
        // Permisiuni media
        mediaPlaybackRequiresUserAction={false}
        allowsInlineMediaPlayback
        allowsProtectedMedia
        onPermissionRequest={e => e.request.grant(e.request.resources)}
        javaScriptEnabled
        domStorageEnabled
        allowFileAccess
        allowFileAccessFromFileURLs
        allowUniversalAccessFromFileURLs
        mixedContentMode="always"
        originWhitelist={['*']}
        mediaCapturePermissionGrantType="grant"
      />

      {/* Native camera overlay — shown when web app requests it */}
      {showNativeCamera && (
        <View style={StyleSheet.absoluteFill}>
          <NativeCameraScreen
            onClose={handleCameraClose}
            onResult={result => {
              webviewRef.current?.injectJavaScript(
                `window.dispatchEvent(new CustomEvent('nativeCameraResult', {detail: ${JSON.stringify(result)}})); true;`
              );
            }}
          />
        </View>
      )}

      {/* Loading overlay */}
      {loading && !error && (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#7C3AED" />
          <Text style={styles.overlayTitle}>Se conectează...</Text>
          <Text style={styles.overlayUrl}>{url}</Text>
        </View>
      )}

      {/* Error screen */}
      {!!error && (
        <View style={styles.overlay}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={styles.errorTitle}>Nu s-a putut conecta</Text>
          <Text style={styles.errorMsg}>{error}</Text>
          <Text style={styles.errorHint}>
            Asigură-te că serverul webpack rulează:{'\n'}
            <Text style={styles.errorCmd}>cd mobile_app{'\n'}npm run web</Text>
          </Text>
          <Text style={styles.errorHint2}>
            Server așteptat la:{'\n'}
            <Text style={styles.errorUrl}>{url}</Text>
          </Text>
          <TouchableOpacity style={styles.retryBtn} onPress={reload}>
            <Text style={styles.retryText}>Încearcă din nou</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#080412',
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111827',
    paddingTop: Constants.statusBarHeight || 44,
    paddingBottom: 6,
    paddingHorizontal: 14,
    gap: 8,
  },
  topBarText: {
    flex: 1,
    color: '#6B7280',
    fontSize: 11,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  reloadBtn: {
    color: '#7C3AED',
    fontSize: 20,
    fontWeight: '700',
    paddingHorizontal: 4,
  },
  webview: {
    flex: 1,
    backgroundColor: '#080412',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#080412',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
    gap: 12,
  },
  overlayTitle: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
    marginTop: 12,
  },
  overlayUrl: {
    color: '#6B7280',
    fontSize: 12,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  errorIcon: { fontSize: 40 },
  errorTitle: { color: '#FFFFFF', fontSize: 18, fontWeight: '800' },
  errorMsg: { color: '#F87171', fontSize: 13, textAlign: 'center' },
  errorHint: {
    color: '#9CA3AF',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 20,
    marginTop: 8,
  },
  errorCmd: {
    color: '#A78BFA',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  errorHint2: {
    color: '#9CA3AF',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 20,
  },
  errorUrl: {
    color: '#60A5FA',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  retryBtn: {
    marginTop: 8,
    backgroundColor: '#7C3AED',
    borderRadius: 14,
    paddingHorizontal: 28,
    paddingVertical: 13,
  },
  retryText: { color: '#FFFFFF', fontSize: 14, fontWeight: '800' },
});
