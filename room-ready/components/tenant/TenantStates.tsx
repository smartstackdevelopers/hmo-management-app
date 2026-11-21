import { router } from 'expo-router';

import { ErrorState, OfflineState } from '@/components/ui/States';
import { useI18n } from '@/hooks/useI18n';

export function TenantOffline() {
  const { t } = useI18n();
  return (
    <OfflineState
      title={t('states.offlineTitle')}
      message={t('states.offlineBody')}
      actionLabel={t('states.viewDrafts')}
      onAction={() => router.push('/(app)/offline-drafts')}
    />
  );
}

export function TenantLoadError({
  title,
  onRetry,
  showContact = true,
}: {
  title: string;
  onRetry: () => void;
  showContact?: boolean;
}) {
  const { t } = useI18n();
  return (
    <ErrorState
      title={title}
      message={t('states.draftsSafe')}
      actionLabel={t('states.tryAgain')}
      onRetry={onRetry}
      secondaryLabel={showContact ? t('states.contactSupport') : undefined}
      onSecondary={showContact ? () => router.push('/(app)/(tabs)/support') : undefined}
    />
  );
}
