import { Link, Stack } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export default function NotFoundScreen() {
  const insets = useSafeAreaInsets();

  return (
    <>
      <Stack.Screen options={{ title: 'Not found', headerShown: false }} />
      <View style={[styles.container, { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 }]}>
        <View style={styles.icon}>
          <Ionicons name="map-outline" size={32} color={theme.colors.secondaryDark} />
        </View>
        <Text style={styles.title} accessibilityRole="header">This screen doesn't exist</Text>
        <Text style={styles.message}>The link may be out of date. You can return to HMore.</Text>
        <Link href="/" asChild>
          <Button title="Go to home" size="lg" fullWidth style={styles.action} />
        </Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: theme.spacing.lg,
    backgroundColor: theme.colors.background,
  },
  icon: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
  },
  title: {
    fontSize: 22,
    lineHeight: 28,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  message: {
    marginTop: 8,
    fontSize: 15,
    lineHeight: 22,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    maxWidth: 300,
  },
  action: { marginTop: theme.spacing.xl, maxWidth: 360 },
});
