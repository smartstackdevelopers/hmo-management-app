import Svg, { Path, Rect } from 'react-native-svg';

import { theme } from '@/constants/theme';

interface LogoMarkProps {
  size?: number;
}

/** Vector app mark — teal house with white stroke and check. */
export function LogoMark({ size = 44 }: LogoMarkProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 48 48">
      <Rect width={48} height={48} rx={14} fill={theme.colors.secondary} />
      <Path
        d="M24 11 L36 20.5 V33 H29.5 V25 H18.5 V33 H12 V20.5 Z"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth={2.2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <Path
        d="M30.5 17.5 V13.5 H33.5 V19.5"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <Path
        d="M19 25.5 L22.8 29.5 L31.5 19.5"
        fill="none"
        stroke="#CCFBF1"
        strokeWidth={2.6}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </Svg>
  );
}
