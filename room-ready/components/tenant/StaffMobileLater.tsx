import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function StaffMobileLater() {
  return (
    <Screen>
      <Text style={styles.title}>Tenant app</Text>
      <Card>
        <Text style={styles.body}>
          This release is the tenant mobile app. Housing, repairs, support, documents and the assistant
          are available on a tenant account. The staff mobile app is a later phase.
        </Text>
      </Card>
      <View style={styles.actions}>
        <Button title="Account" variant="outline" onPress={() => router.push('/(app)/(tabs)/more')} fullWidth />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    fontFamily: FONT_BOLD,
    fontSize: 28,
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    letterSpacing: -0.4,
  },
  body: { fontFamily: FONT_MEDIUM, fontSize: 15, lineHeight: 22, color: theme.colors.textSecondary },
  actions: { marginTop: theme.spacing.md },
});
