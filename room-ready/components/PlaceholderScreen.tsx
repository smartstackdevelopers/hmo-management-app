import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';

interface PlaceholderScreenProps {
  title: string;
  description: string;
  features: string[];
}

export function PlaceholderScreen({ title, description, features }: PlaceholderScreenProps) {
  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>🚧</Text>
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>

      <Text style={styles.comingSoon}>Coming in next release</Text>

      <View style={styles.featureList}>
        {features.map((feature) => (
          <View key={feature} style={styles.featureRow}>
            <View style={styles.bullet} />
            <Text style={styles.featureText}>{feature}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: theme.spacing.lg,
    alignItems: 'center',
  },
  iconContainer: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: theme.colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.lg,
    marginTop: theme.spacing.md,
  },
  icon: { fontSize: 32 },
  title: {
    ...theme.typography.h2,
    color: theme.colors.text,
    textAlign: 'center',
  },
  description: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  comingSoon: {
    ...theme.typography.label,
    color: theme.colors.secondary,
    backgroundColor: theme.colors.infoLight,
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: theme.radius.full,
    overflow: 'hidden',
    marginBottom: theme.spacing.lg,
  },
  featureList: {
    alignSelf: 'stretch',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
  },
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.colors.secondary,
    marginTop: 7,
  },
  featureText: {
    flex: 1,
    fontSize: 14,
    color: theme.colors.textSecondary,
    lineHeight: 20,
  },
});
