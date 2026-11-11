import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';

export default function EmploymentHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 24 * fontScale }]}>{t('employment.title')}</Text>
      <Text style={styles.lead}>{t('employment.lead')}</Text>
      <View style={styles.stack}>
        <Button title={t('employment.skills')} onPress={() => router.push('/(app)/employment-skills')} />
        <Button title={t('employment.cvs')} variant="secondary" onPress={() => router.push('/(app)/employment-cvs')} />
        <Button
          title={t('employment.applications')}
          variant="secondary"
          onPress={() => router.push('/(app)/employment-applications')}
        />
        <Button
          title={t('employment.interview')}
          variant="secondary"
          onPress={() => router.push('/(app)/employment-interview')}
        />
        <Button
          title={t('employment.roadmap')}
          variant="secondary"
          onPress={() => router.push('/(app)/employment-roadmap')}
        />
        <Button
          title={t('jobMatching.title')}
          variant="secondary"
          onPress={() => router.push('/(app)/job-matching')}
        />
        <Button
          title={t('communityHub.title')}
          variant="secondary"
          onPress={() => router.push('/(app)/community-hub')}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: theme.spacing.lg },
  stack: { gap: 10 },
});
