import { AppRegistry } from 'react-native';
import App from './App';

const appName = 'SignTranslatorApp';
const rootTag = document.getElementById('root');

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function showBootError(title, details) {
  if (!rootTag) return;
  rootTag.innerHTML = `
    <div style="
      height:100%;
      box-sizing:border-box;
      padding:20px;
      background:#111827;
      color:#f9fafb;
      font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
      overflow:auto;
    ">
      <h2 style="margin:0 0 10px 0;font-size:18px;">${escapeHtml(title)}</h2>
      <pre style="white-space:pre-wrap;line-height:1.45;color:#fca5a5;margin:0;">${escapeHtml(details || 'Unknown error')}</pre>
    </div>
  `;
}

window.addEventListener('error', event => {
  const message = event?.error?.stack || event?.message || 'Unknown runtime error';
  showBootError('SignTranslator web runtime error', message);
});

window.addEventListener('unhandledrejection', event => {
  const reason = event?.reason?.stack || event?.reason || 'Unhandled promise rejection';
  showBootError('SignTranslator web promise error', reason);
});

AppRegistry.registerComponent(appName, () => App);

try {
  AppRegistry.runApplication(appName, { rootTag });
} catch (error) {
  showBootError('SignTranslator web boot failed', error?.stack || String(error));
}

setTimeout(() => {
  if (rootTag && rootTag.childElementCount === 0) {
    showBootError(
      'SignTranslator web did not mount',
      'App root is empty after startup. Check browser console and dev server logs.'
    );
  }
}, 4000);

console.log('React Native Web app loaded.');
