import * as React from 'react';




const Svg = 'svg' as any;
const Path = 'path' as any;
const Circle = 'circle' as any;

interface IconProps {
  color?: string;
  size?: number;
}

export const HomeIcon: React.FC<IconProps> = ({ color = '#fff', size = 24 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H5a1 1 0 01-1-1V9.5z" fill={color} />
    <Path d="M9 21V12h6v9" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
  </Svg>
);

export const CameraIcon: React.FC<IconProps> = ({ color = '#fff', size = 24 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path
      d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"
      stroke={color}
      strokeWidth="2"
      fill="none"
    />
    <Circle cx="12" cy="13" r="4" stroke={color} strokeWidth="2" />
  </Svg>
);

export const TextIcon: React.FC<IconProps> = ({ color = '#fff', size = 24 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 6h16M4 10h16M4 14h10M4 18h8" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
  </Svg>
);

export const BookIcon: React.FC<IconProps> = ({ color = '#fff', size = 24 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke={color} strokeWidth="2" fill="none" />
    <Path
      d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"
      stroke={color}
      strokeWidth="2"
      fill="none"
    />
  </Svg>
);

export const ClockIcon: React.FC<IconProps> = ({ color = '#fff', size = 24 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2" />
    <Path d="M12 7v5l3 3" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const StarIcon: React.FC<IconProps> = ({ color = '#F97316', size = 20 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Path
      d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"
      fill={color}
    />
  </Svg>
);

export const HandIcon: React.FC<IconProps> = ({ size = 32 }) => (
  <Svg width={size} height={size} viewBox="0 0 64 64">
    <Path
      d="M32 8c-2 0-3.5 1.5-3.5 3.5V32c0 2 1.5 3.5 3.5 3.5s3.5-1.5 3.5-3.5V11.5C35.5 9.5 34 8 32 8z"
      fill="#7C3AED"
    />
    <Path
      d="M23 14c-2 0-3.5 1.5-3.5 3.5v14c0 2 1.5 3.5 3.5 3.5s3.5-1.5 3.5-3.5v-14C26.5 15.5 25 14 23 14z"
      fill="#8B5CF6"
    />
    <Path
      d="M14 20c-2 0-3.5 1.5-3.5 3.5v10c0 2 1.5 3.5 3.5 3.5s3.5-1.5 3.5-3.5v-10C17.5 21.5 16 20 14 20z"
      fill="#A78BFA"
    />
    <Path
      d="M41 16c-2 0-3.5 1.5-3.5 3.5V34c0 2 1.5 3.5 3.5 3.5s3.5-1.5 3.5-3.5V19.5C44.5 17.5 43 16 41 16z"
      fill="#8B5CF6"
    />
    <Path
      d="M49.5 26c-2 0-3.5 1.5-3.5 3.5v6a14 14 0 01-14 14H30a14 14 0 01-14-14v-2.5h-2.5l-3 3C9 37 8 39 8 41a6 6 0 006 6h.5A20 20 0 0032 56h.5A20 20 0 0053 36.5v-7C53 27.5 51.5 26 49.5 26z"
      fill="#7C3AED"
    />
  </Svg>
);

export const ArrowLeftIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path
      d="M19 12H5M5 12l7 7M5 12l7-7"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </Svg>
);

export const PlayIcon: React.FC<IconProps> = ({ color = '#fff', size = 20 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Path d="M5 3l14 9L5 21V3z" fill={color} />
  </Svg>
);

export const FireIcon: React.FC<{ size?: number }> = ({ size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24">
    <Path
      d="M12 22c-4.4 0-8-3.6-8-8 0-2.5 1-4.8 2.8-6.4.4-.4 1-.1 1 .5 0 1.2.4 2.3 1.1 3.2.2.3.6.2.7-.1.5-1.5.7-3.1.5-4.7-.1-.5.4-.9.8-.7C14.3 7.4 16 10.6 16 14c0 1.5-.5 2.9-1.3 4 .1-.4.2-.8.2-1.2 0-1.5-.8-2.8-2-3.5-.4-.2-.8.1-.8.5-.1 1.7-1 3.2-2.4 4.1.2-.5.3-1 .3-1.4 0-1.2-.6-2.3-1.5-3-.3-.2-.7 0-.7.3C7.6 15.4 7 17.3 7 18c0 2.8 2.2 5 5 5h.3c2.5-.3 4.7-2.3 4.7-5C17 16.2 14.8 22 12 22z"
      fill="#F97316"
    />
  </Svg>
);

export const SearchIcon: React.FC<IconProps> = ({ color = '#9CA3AF', size = 20 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="11" cy="11" r="8" stroke={color} strokeWidth="2.2" />
    <Path d="M21 21l-4.35-4.35" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
  </Svg>
);

export const FlipIcon: React.FC<IconProps> = ({ color = '#fff', size = 20 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path
      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      stroke={color}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </Svg>
);

export const CheckIcon: React.FC<IconProps> = ({ color = '#22C55E', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M20 6L9 17l-5-5" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const UserIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="8" r="4" stroke={color} strokeWidth="2" />
    <Path d="M4 20c0-3.3 3.6-6 8-6s8 2.7 8 6" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const BellIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <Path d="M13.73 21a2 2 0 01-3.46 0" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const VolumeIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M11 5L6 9H2v6h4l5 4V5z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <Path d="M15.54 8.46a5 5 0 010 7.07" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const GlobeIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="12" r="10" stroke={color} strokeWidth="2" />
    <Path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke={color} strokeWidth="2" />
  </Svg>
);

export const GaugeIcon: React.FC<IconProps> = ({ color = '#0D9488', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M12 2a10 10 0 100 20A10 10 0 0012 2z" stroke={color} strokeWidth="2" />
    <Path d="M12 12l-3.5-3.5" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    <Circle cx="12" cy="12" r="1.5" fill={color} />
    <Path d="M7 16h10" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
  </Svg>
);

export const PhoneVibrateIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M15 4h1a2 2 0 012 2v12a2 2 0 01-2 2h-1M9 4H8a2 2 0 00-2 2v12a2 2 0 002 2h1" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <Path d="M9 4h6v16H9z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M5 8.5a7 7 0 000 7M19 8.5a7 7 0 010 7" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const InfoIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="12" r="10" stroke={color} strokeWidth="2" />
    <Path d="M12 16v-4M12 8h.01" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const ShieldIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M12 2L3 7v5c0 5.25 3.75 10.15 9 11.35C17.25 22.15 21 17.25 21 12V7L12 2z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M9 12l2 2 4-4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const FileTextIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const LogoutIcon: React.FC<IconProps> = ({ color = '#DC2626', size = 22 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    <Path d="M16 17l5-5-5-5M21 12H9" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const ChevronRightIcon: React.FC<IconProps> = ({ color = '#9CA3AF', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M9 18l6-6-6-6" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const TrashIcon: React.FC<IconProps> = ({ color = '#DC2626', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 7h16" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <Path d="M9 3h6l1 2H8l1-2z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M7 7l1 12a2 2 0 002 2h4a2 2 0 002-2l1-12" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M10 11v5M14 11v5" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const SettingsIcon: React.FC<IconProps> = ({ color = '#FFFFFF', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M12 8.5A3.5 3.5 0 1112 15.5 3.5 3.5 0 0112 8.5z" stroke={color} strokeWidth="2" />
    <Path
      d="M19.4 15a1 1 0 00.2 1.1l.1.1a2 2 0 01-2.8 2.8l-.1-.1a1 1 0 00-1.1-.2 1 1 0 00-.6.9V21a2 2 0 01-4 0v-.2a1 1 0 00-.6-.9 1 1 0 00-1.1.2l-.1.1a2 2 0 01-2.8-2.8l.1-.1a1 1 0 00.2-1.1 1 1 0 00-.9-.6H3a2 2 0 010-4h.2a1 1 0 00.9-.6 1 1 0 00-.2-1.1l-.1-.1a2 2 0 012.8-2.8l.1.1a1 1 0 001.1.2 1 1 0 00.6-.9V3a2 2 0 014 0v.2a1 1 0 00.6.9 1 1 0 001.1-.2l.1-.1a2 2 0 012.8 2.8l-.1.1a1 1 0 00-.2 1.1 1 1 0 00.9.6H21a2 2 0 010 4h-.2a1 1 0 00-.9.6z"
      stroke={color}
      strokeWidth="1.8"
      strokeLinejoin="round"
    />
  </Svg>
);

export const LockIcon: React.FC<IconProps> = ({ color = '#64748B', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M7 10V8a5 5 0 0110 0v2" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <Path d="M6 10h12v10a2 2 0 01-2 2H8a2 2 0 01-2-2V10z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Circle cx="12" cy="15" r="1.5" fill={color} />
  </Svg>
);

export const BoltIcon: React.FC<IconProps> = ({ color = '#A855F7', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M13 2L5 13h5l-1 9 8-11h-5l1-9z" fill={color} />
  </Svg>
);

export const TargetIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="12" r="8" stroke={color} strokeWidth="2" />
    <Circle cx="12" cy="12" r="4" stroke={color} strokeWidth="2" />
    <Circle cx="12" cy="12" r="1.6" fill={color} />
  </Svg>
);

export const CrownIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 18l2-10 6 5 6-5 2 10H4z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M8 18h8" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <Circle cx="6" cy="8" r="1.2" fill={color} />
    <Circle cx="12" cy="6" r="1.2" fill={color} />
    <Circle cx="18" cy="8" r="1.2" fill={color} />
  </Svg>
);

export const GemIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M7 4h10l4 5-9 11L3 9l4-5z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M7 4l5 16 5-16M3 9h18" stroke={color} strokeWidth="1.8" strokeLinejoin="round" />
  </Svg>
);

export const MedalIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M8 3h3l1 4H9L8 3zM13 3h3l-1 4h-3l1-4z" fill={color} opacity="0.85" />
    <Circle cx="12" cy="14" r="5" stroke={color} strokeWidth="2" />
    <Path d="M12 11.5l.9 1.8 2 .3-1.4 1.4.3 2-1.8-.9-1.8.9.3-2-1.4-1.4 2-.3.9-1.8z" fill={color} />
  </Svg>
);

export const PenIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 20l4.5-1 9-9a2.1 2.1 0 10-3-3l-9 9L4 20z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M13.5 6.5l4 4" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const CalendarIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 011 1v13a2 2 0 01-2 2H6a2 2 0 01-2-2V6a1 1 0 011-1z" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const CoinIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Circle cx="12" cy="12" r="8" stroke={color} strokeWidth="2" />
    <Path d="M9.5 9.5c.4-.8 1.2-1.3 2.5-1.3 1.7 0 2.8.8 2.8 2 0 1.2-.8 1.8-2.2 2.2-1.3.4-1.8.7-1.8 1.7V15M12 16.5h.01" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const MountainIcon: React.FC<IconProps> = ({ color = '#22C55E', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M3 19l6-10 3 5 3-4 6 9H3z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M14 10l1-2 2 3" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const SeedIcon: React.FC<IconProps> = ({ color = '#22C55E', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M12 20v-7" stroke={color} strokeWidth="2" strokeLinecap="round" />
    <Path d="M12 13c0-4.5 3.5-6 6-6 0 3.5-1.5 7-6 7zM12 13c0-4.5-3.5-6-6-6 0 3.5 1.5 7 6 7z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
  </Svg>
);

export const BookBadgeIcon: React.FC<IconProps> = ({ color = '#7C3AED', size = 18 }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <Path d="M4 6.5A2.5 2.5 0 016.5 4H20v15H6.5A2.5 2.5 0 014 16.5v-10z" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    <Path d="M8 7h8M8 11h8" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const BadgeIcon: React.FC<{ badgeKey?: string; color?: string; size?: number }> = ({
  badgeKey,
  color = '#7C3AED',
  size = 22,
}) => {
  switch (badgeKey) {
    case 'first_translation':
    case 'challenge_complete_20':
      return <MedalIcon color={color} size={size} />;
    case 'translations_10':
    case 'text_sign_first':
      return <PenIcon color={color} size={size} />;
    case 'translations_50':
      return <BookBadgeIcon color={color} size={size} />;
    case 'translations_100':
      return <StarIcon color={color} size={size} />;
    case 'translations_500':
    case 'xp_5000':
      return <GemIcon color={color} size={size} />;
    case 'streak_3':
    case 'streak_7':
    case 'streak_14':
    case 'streak_30':
      return <FireIcon size={size} />;
    case 'level_5':
    case 'level_10':
      return <CrownIcon color={color} size={size} />;
    case 'daily_claims_7':
      return <CalendarIcon color={color} size={size} />;
    case 'camera_first':
      return <CameraIcon color={color} size={size} />;
    case 'challenge_complete_5':
      return <TargetIcon color={color} size={size} />;
    case 'xp_1000':
      return <CoinIcon color={color} size={size} />;
    default:
      return <MedalIcon color={color} size={size} />;
  }
};
