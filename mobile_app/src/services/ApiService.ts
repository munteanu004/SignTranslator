import axios, { AxiosRequestConfig } from 'axios';
import { getApiBaseUrl } from '../config/network';

const API_BASE_URL = getApiBaseUrl();

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface UserProfile {
  id: number;
  name: string;
  email: string;
  phone?: string;
  avatar_url?: string;
  xp: number;
  streak: number;
  level: number;
  created_at: string | null;
}

export interface HistoryEntry {
  id: number;
  type: 'sign-to-text' | 'text-to-sign';
  input_text: string;
  output_text: string;
  words: string[];
  confidence: number | null;
  timestamp: string;
}

export interface RecognitionResponse {
  success: boolean;
  prediction: string;
  prediction_ro?: string;
  confidence: number;
  top5: { label: string; confidence: number }[];
}

export interface AslRecognitionResponse {
  success: boolean;
  gloss_en: string;
  gloss_ro?: string;
  confidence: number;
  top5: { label: string; confidence: number }[];
  setup_required?: boolean;
}

export interface VideoResponse {
  success: boolean;
  message: string;
  video_url: string;
  video_id: string;
  word_count?: number;
  duration?: number;
}

export interface SignAnimationFrame {
  word: string;
  points: [number, number, number][];
}

export interface SignAnimationResponse {
  success: boolean;
  text: string;
  fps: number;
  frame_count: number;
  signs: { word: string; english: string; method: string; source: string }[];
  frames: SignAnimationFrame[];
}

export interface SignAvatarFrame {
  word: string;
  image: string;
}

export interface SignAvatarFramesResponse {
  success: boolean;
  text: string;
  fps: number;
  frame_count: number;
  signs: { word: string; english: string; method: string; source: string }[];
  frames: SignAvatarFrame[];
}

export interface UserSettings {
  language: string;
  avatar_speed: string;
  skill_level: string;
  notifications: boolean;
  sounds: boolean;
  haptic: boolean;
}

export interface DictionaryCategory {
  name: string;
  count: number;
}

export interface DictionaryEntry {
  id: string;
  word: string;
  english: string;
  category: string;
  level: string;
  xp: number;
  source: string;
  has_animation: boolean;
  lookup: string;
  lookup_type: 'english' | 'romanian';
}

export interface DictionaryResponse {
  entries: DictionaryEntry[];
  total: number;
  catalog_total: number;
  categories: DictionaryCategory[];
}

export interface GamificationStatus {
  xp: number;
  level: number;
  streak: number;
  current_level_xp: number;
  next_level_xp: number;
  daily_claim: {
    can_claim: boolean;
    claim_day: number;
    next_reward_xp: number;
    total_claims: number;
    rewards_calendar: number[];
  };
  challenges: ChallengeData[];
  achievements: AchievementData[];
}

export interface ChallengeData {
  key: string;
  title: string;
  desc: string;
  target: number;
  progress: number;
  completed: boolean;
  xp_claimed: boolean;
  xp_reward: number;
}

export interface AchievementData {
  key: string;
  icon: string;
  title: string;
  desc: string;
  xp_reward: number;
  earned: boolean;
}

export interface ClaimResponse {
  success: boolean;
  xp_earned: number;
  day_in_cycle: number;
  total_xp: number;
  level: number;
  streak: number;
  new_achievements: { key: string; title: string; icon: string; xp_reward: number }[];
}

export interface ProgressResponse {
  success: boolean;
  xp_earned: number;
  base_xp: number;
  streak_bonus: number;
  total_xp: number;
  level: number;
  streak: number;
  new_achievements: { key: string; title: string; icon: string; xp_reward: number }[];
}

export interface ChallengeClaimResponse {
  success: boolean;
  key: string;
  xp_earned: number;
  total_xp: number;
  level: number;
  streak: number;
  new_achievements: { key: string; title: string; icon: string; xp_reward: number }[];
}

class ApiService {
  private token: string | null = null;

  constructor() {
    try {
      this.token = localStorage.getItem('lsr_token');
    } catch {}
  }

  setToken(token: string | null) {
    this.token = token;
    try {
      if (token) localStorage.setItem('lsr_token', token);
      else localStorage.removeItem('lsr_token');
    } catch {}
  }

  getToken(): string | null {
    return this.token;
  }

  private authHeaders(): Record<string, string> {
    if (this.token) {
      return { Authorization: `Bearer ${this.token}` };
    }
    return {};
  }

  private config(timeout = 10000): AxiosRequestConfig {
    return { timeout, headers: this.authHeaders() };
  }

  

  async register(name: string, email: string, password: string): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(
      `${API_BASE_URL}/auth/register`,
      { name, email, password },
      { timeout: 10000 },
    );
    return res.data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(
      `${API_BASE_URL}/auth/login`,
      { email, password },
      { timeout: 10000 },
    );
    return res.data;
  }

  async loginWithGoogle(credential: string): Promise<AuthResponse> {
    const res = await axios.post<AuthResponse>(
      `${API_BASE_URL}/auth/google`,
      { credential },
      { timeout: 10000 },
    );
    return res.data;
  }

  async getMe(): Promise<{ user: UserProfile }> {
    const res = await axios.get<{ user: UserProfile }>(
      `${API_BASE_URL}/auth/me`,
      this.config(),
    );
    return res.data;
  }

  async updateProfile(data: {
    name?: string;
    email?: string;
    phone?: string;
    skill_level?: string;
    current_password?: string;
    new_password?: string;
  }): Promise<{ user: UserProfile }> {
    const res = await axios.put<{ user: UserProfile }>(
      `${API_BASE_URL}/auth/profile`,
      data,
      this.config(),
    );
    return res.data;
  }

  async uploadAvatar(dataUrl: string): Promise<{ avatar_url: string }> {
    const res = await axios.post<{ avatar_url: string }>(
      `${API_BASE_URL}/auth/avatar`,
      { data_url: dataUrl },
      this.config(20000),
    );
    return res.data;
  }

  getAvatarUrl(path: string): string {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    return `${API_BASE_URL.replace('/api', '')}${path}`;
  }

  

  async getHistory(type?: string): Promise<HistoryEntry[]> {
    const params = type ? `?type=${type}` : '';
    const res = await axios.get<{ history: HistoryEntry[] }>(
      `${API_BASE_URL}/history${params}`,
      this.config(),
    );
    return res.data.history;
  }

  async saveHistory(entry: {
    type: string;
    input_text?: string;
    output_text?: string;
    words?: string[];
    confidence?: number;
  }): Promise<HistoryEntry> {
    const res = await axios.post<{ entry: HistoryEntry }>(
      `${API_BASE_URL}/history`,
      entry,
      this.config(),
    );
    return res.data.entry;
  }

  async deleteHistory(id: number): Promise<void> {
    await axios.delete(`${API_BASE_URL}/history/${id}`, this.config());
  }

  async clearHistory(): Promise<void> {
    await axios.delete(`${API_BASE_URL}/history`, this.config());
  }

  

  async getDictionary(params?: {
    q?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<DictionaryResponse> {
    const searchParams = new URLSearchParams();
    if (params?.q) searchParams.set('q', params.q);
    if (params?.category) searchParams.set('category', params.category);
    if (typeof params?.limit === 'number') searchParams.set('limit', String(params.limit));
    if (typeof params?.offset === 'number') searchParams.set('offset', String(params.offset));

    const query = searchParams.toString();
    const res = await axios.get<DictionaryResponse>(
      `${API_BASE_URL}/dictionary${query ? `?${query}` : ''}`,
      this.config(),
    );
    return res.data;
  }

  

  async getSettings(): Promise<UserSettings> {
    const res = await axios.get<{ settings: UserSettings }>(
      `${API_BASE_URL}/settings`,
      this.config(),
    );
    return res.data.settings;
  }

  async updateSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
    const res = await axios.put<{ settings: UserSettings }>(
      `${API_BASE_URL}/settings`,
      settings,
      this.config(),
    );
    return res.data.settings;
  }

  

  async getGamificationStatus(): Promise<GamificationStatus> {
    const res = await axios.get<GamificationStatus>(
      `${API_BASE_URL}/gamification/status`,
      this.config(),
    );
    return res.data;
  }

  async getGamificationChallenges(): Promise<ChallengeData[]> {
    const res = await axios.get<{ challenges: ChallengeData[] }>(
      `${API_BASE_URL}/gamification/challenges`,
      this.config(),
    );
    return res.data.challenges;
  }

  async getGamificationAchievements(): Promise<AchievementData[]> {
    const res = await axios.get<{ achievements: AchievementData[] }>(
      `${API_BASE_URL}/gamification/achievements`,
      this.config(),
    );
    return res.data.achievements;
  }

  async claimDailyReward(): Promise<ClaimResponse> {
    const res = await axios.post<ClaimResponse>(
      `${API_BASE_URL}/gamification/claim`,
      {},
      this.config(),
    );
    return res.data;
  }

  async reportProgress(type: string): Promise<ProgressResponse> {
    const res = await axios.post<ProgressResponse>(
      `${API_BASE_URL}/gamification/progress`,
      { type },
      this.config(),
    );
    return res.data;
  }

  async claimChallenge(challengeKey: string): Promise<ChallengeClaimResponse> {
    const res = await axios.post<ChallengeClaimResponse>(
      `${API_BASE_URL}/gamification/challenge-claim`,
      { key: challengeKey },
      this.config(),
    );
    return res.data;
  }

  

  async recognizeSign(keypoints: number[][][]): Promise<RecognitionResponse> {
    const res = await axios.post<RecognitionResponse>(
      `${API_BASE_URL}/recognize-sign`,
      { keypoints },
      this.config(15000),
    );
    return res.data;
  }

  async recognizeAsl(keypoints: number[][][]): Promise<AslRecognitionResponse> {
    const res = await axios.post<AslRecognitionResponse>(
      `${API_BASE_URL}/recognize-asl`,
      { keypoints },
      this.config(15000),
    );
    return res.data;
  }

  async getAslStatus(): Promise<{ ready: boolean; message: string }> {
    const res = await axios.get<{ ready: boolean; message: string }>(
      `${API_BASE_URL}/recognize-asl/status`,
      this.config(5000),
    );
    return res.data;
  }

  async recognizeRules(keypoints: number[][][]): Promise<{
    success: boolean;
    sign_ro?: string;
    sign_en?: string;
    confidence?: number;
    votes?: number;
    total_frames?: number;
    method?: string;
    reason?: string;
  }> {
    const res = await axios.post(
      `${API_BASE_URL}/recognize-rules`,
      { keypoints },
      this.config(8000),
    );
    return res.data;
  }

  async getRulesSigns(): Promise<{
    signs: { ro: string; en: string; emoji: string; description: string }[];
    count: number;
  }> {
    const res = await axios.get(`${API_BASE_URL}/recognize-rules/signs`, this.config(5000));
    return res.data;
  }

  async recognizeFocused(keypoints: number[][][]): Promise<{
    success: boolean;
    word?: string;
    word_ro?: string;
    confidence?: number;
    reason?: string;
    method?: string;
  }> {
    const res = await axios.post(
      `${API_BASE_URL}/recognize-focused`,
      { keypoints },
      this.config(15000),
    );
    return res.data;
  }

  async getFocusedWords(): Promise<{
    words: { en: string; ro: string; emoji: string; description: string }[];
  }> {
    const res = await axios.get(`${API_BASE_URL}/recognize-focused/words`, this.config(5000));
    return res.data;
  }

  async recordFocusedTemplate(word: string, keypoints: number[][][]): Promise<{ success: boolean; template_count?: number }> {
    const res = await axios.post(
      `${API_BASE_URL}/recognize-focused/record`,
      { word, keypoints },
      this.config(10000),
    );
    return res.data;
  }

  async getFocusedTemplates(): Promise<{ calibrated: Record<string, number>; words: string[] }> {
    const res = await axios.get(`${API_BASE_URL}/recognize-focused/templates`, this.config(5000));
    return res.data;
  }

  

  async getSignAnimation(text: string): Promise<SignAnimationResponse> {
    const res = await axios.post<SignAnimationResponse>(
      `${API_BASE_URL}/sign-animation`,
      { text },
      this.config(30000),
    );
    return res.data;
  }

  async getSignAvatarFrames(text: string, lookup?: string, lookupLabel?: string): Promise<SignAvatarFramesResponse> {
    const res = await axios.post<SignAvatarFramesResponse>(
      `${API_BASE_URL}/sign-animation-frames`,
      { text, lookup, label: lookupLabel || text },
      this.config(180000),
    );
    return res.data;
  }

  async generate3DVideo(text: string): Promise<VideoResponse> {
    const res = await axios.post<VideoResponse>(
      `${API_BASE_URL}/generate-3d-video`,
      { text },
      this.config(180000),
    );
    return res.data;
  }

  async generateRomanianVideo(text: string): Promise<VideoResponse> {
    const res = await axios.post<VideoResponse>(
      `${API_BASE_URL}/generate-romanian-video`,
      { text },
      this.config(180000),
    );
    return res.data;
  }

  

  async healthCheck() {
    const res = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
    return res.data;
  }
}

export default new ApiService();
