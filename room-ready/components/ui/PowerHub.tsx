import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { ROLE_POWER_FEATURES } from '@/constants/powerFeatures';
import { theme } from '@/constants/theme';
import { UserRole } from '@/types';

interface PowerHubProps {
  role: UserRole;
}

export function PowerHub({ role }: PowerHubProps) {
  const features = ROLE_POWER_FEATURES[role] ?? [];

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>Power tools</Text>
      <Text style={styles.subtitle}>Everything your role needs in one place.</Text>
      <View style={styles.grid}>
        {features.map((feature) => (
          <Pressable
            key={feature.id}
            disabled={feature.comingSoon || !feature.route}
            onPress={() => feature.route && router.push(feature.route as never)}
            style={({ pressed }) => [styles.cell, pressed && styles.pressed]}
          >
            <Card style={[styles.tile, feature.comingSoon && styles.tileSoon]} elevated>
              <View style={styles.tileTop}>
                <View style={styles.iconWrap}>
                  <Ionicons
                    name={feature.icon as keyof typeof Ionicons.glyphMap}
                    size={17}
                    color={theme.colors.secondary}
                  />
                </View>
                {feature.badge && <Badge label={feature.badge} variant="info" format={false} />}
                {feature.comingSoon && <Badge label="Soon" variant="default" format={false} />}
              </View>
              <Text style={styles.tileTitle}>{feature.title}</Text>
              <Text style={styles.tileSub} numberOfLines={2}>{feature.subtitle}</Text>
            </Card>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  title: { ...theme.typography.h3, color: theme.colors.text },
  subtitle: { color: theme.colors.textMuted, fontSize: 13, marginTop: 2, marginBottom: theme.spacing.md },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.sm,
  },
  cell: { width: '48%', flexGrow: 1 },
  tile: { minHeight: 118, justifyContent: 'space-between' },
  tileSoon: { opacity: 0.65 },
  tileTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 },
  iconWrap: {
    width: 34,
    height: 34,
    borderRadius: theme.radius.sm,
    backgroundColor: theme.colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tileTitle: { fontWeight: '700', fontSize: 14, color: theme.colors.text },
  tileSub: { color: theme.colors.textMuted, fontSize: 12, marginTop: 4, lineHeight: 16 },
  pressed: { opacity: 0.92 },
});
