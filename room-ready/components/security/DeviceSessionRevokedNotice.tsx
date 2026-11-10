import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import {
  setDeviceSessionRevokedMessage,
  subscribeDeviceSessionRevokedMessage,
} from '@/lib/hmore/security/deviceSessionRevoke';

export function DeviceSessionRevokedNotice() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => subscribeDeviceSessionRevokedMessage(setMessage), []);

  if (!message) return null;

  return (
    <View style={styles.banner}>
      <Text style={styles.title}>Device signed out</Text>
      <Text style={styles.body}>{message}</Text>
      <Pressable accessibilityRole="button" onPress={() => setDeviceSessionRevokedMessage(null)}>
        <Text style={styles.dismiss}>Dismiss</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: theme.colors.warningLight,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.warning,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  title: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginBottom: 4 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 18 },
  dismiss: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, marginTop: 8 },
});
