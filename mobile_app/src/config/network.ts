import { NativeModules } from 'react-native';

const FALLBACK_DEV_HOST = '192.168.0.54';

const TUNNEL_HOSTS = ['loca.lt', 'ngrok.io', 'ngrok-free.app', 'serveo.net'];

function sanitizeHost(host: string | null | undefined): string | null {
  if (!host) return null;
  const trimmed = host.trim();
  if (!trimmed) return null;
  return trimmed;
}

function hostFromUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return sanitizeHost(new URL(url).hostname);
  } catch {
    return null;
  }
}

export function getBrowserHost(): string | null {
  const host = (globalThis as any)?.location?.hostname;
  return sanitizeHost(typeof host === 'string' ? host : null);
}

function getRuntimeHost(): string | null {
  const fromBrowser = getBrowserHost();
  if (fromBrowser) return fromBrowser;

  const sourceCodeUrl = (NativeModules as any)?.SourceCode?.scriptURL as string | undefined;
  const fromScript = hostFromUrl(sourceCodeUrl);
  if (fromScript) return fromScript;

  const debuggerHost = (globalThis as any)?.__REACT_DEVTOOLS_GLOBAL_HOOK__?.reactDevtoolsAgent?.host as string | undefined;
  const fromDebugger = sanitizeHost(debuggerHost);
  if (fromDebugger) return fromDebugger;

  return null;
}

export function getApiBaseUrl(): string {
  const explicitBase = (globalThis as any)?.process?.env?.EXPO_PUBLIC_API_BASE_URL as string | undefined;
  if (explicitBase && explicitBase.trim()) {
    return explicitBase.replace(/\/+$/, '');
  }

  const host = getRuntimeHost() || FALLBACK_DEV_HOST;
  
  const isTunnel = TUNNEL_HOSTS.some(t => host.endsWith(t));
  const apiHost = isTunnel ? FALLBACK_DEV_HOST : host;
  return `http://${apiHost}:5000/api`;
}
