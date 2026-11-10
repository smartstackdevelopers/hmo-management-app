import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCommunicationPreferences, patchCommunicationPreferences } from '@/lib/hmore/services/communications';

export function PushPreferenceToggle() {
  const client = useQueryClient();
  const prefs = useQuery({ queryKey: ['hmore', 'communication-preferences'], queryFn: getCommunicationPreferences });
  const save = useMutation({
    mutationFn: (allowPush: boolean) => patchCommunicationPreferences({ allow_push: allowPush }),
    onSuccess: (updated) => {
      client.setQueryData(['hmore', 'communication-preferences'], updated);
    },
  });
  const allowPush = prefs.data?.allow_push !== false;
  const label = prefs.isLoading ? 'Loading push preference' : allowPush ? 'Push notifications on' : 'Push notifications off';

  return (
    <Card style={styles.card}>
      <Pressable
        accessibilityRole="switch"
        accessibilityLabel="Allow push notifications"
        accessibilityState={{ checked: allowPush, disabled: prefs.isLoading || save.isPending }}
        disabled={prefs.isLoading || save.isPending || prefs.isError}
        onPress={() => save.mutate(!allowPush)}
        style={styles.row}
      >
        <View style={styles.copy}>
          <Text style={styles.title}>Push notifications</Text>
          <Text style={styles.detail}>
            The inbox still holds the message. A push only says a notification is waiting. It does not include case or medical details. A
            real device needs an EAS build and Expo credentials.
          </Text>
        </View>
        <Text style={styles.state}>{label}</Text>
      </Pressable>
      {prefs.isError ? <Text style={styles.error}>{hmoreErrorMessage(prefs.error, 'Could not load push preference.')}</Text> : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1 },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  detail: { fontFamily: FONT_MEDIUM, fontSize: 13, lineHeight: 18, color: theme.colors.textSecondary, marginTop: 4 },
  state: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 13 },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.error, marginTop: 8 },
});
