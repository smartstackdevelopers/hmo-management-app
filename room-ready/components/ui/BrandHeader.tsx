import { View } from 'react-native';

import { theme } from '@/constants/theme';

/** Subtle brand accent — no gradient bar. */
export function BrandHeader() {
  return (
    <View
      style={{
        height: 3,
        backgroundColor: theme.colors.secondary,
        borderRadius: 2,
      }}
    />
  );
}
