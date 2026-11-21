import { StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function ActivityRow({
  name,
  title,
  meta,
  chip,
  chipTone = 'gray',
  onPress,
  highContrast = false,
}: {
  name: string;
  title: string;
  meta?: string;
  chip?: string;
  chipTone?: Tone;
  onPress?: () => void;
  highContrast?: boolean;
}) {
  return (
    <Card
      onPress={onPress}
      accessibilityLabel={chip ? `${title}. ${chip}` : title}
      style={[styles.card, highContrast && styles.contrast]}
    >
      <View style={styles.row}>
        <InitialsTile name={name || title} size={40} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
          {meta ? (
            <Text style={styles.meta} numberOfLines={2}>
              {meta}
            </Text>
          ) : null}
        </View>
        {chip ? <Chip label={chip} tone={chipTone} /> : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm },
  contrast: { borderWidth: 2, borderColor: '#000000' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 44 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
});
