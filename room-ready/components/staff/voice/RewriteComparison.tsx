import { StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function RewriteComparison({
  original,
  rewritten,
  onChangeRewritten,
  onAccept,
  onReject,
  onReport,
  canReport,
  reporting,
}: {
  original: string;
  rewritten: string;
  onChangeRewritten: (value: string) => void;
  onAccept: () => void;
  onReject: () => void;
  onReport: () => void;
  canReport: boolean;
  reporting?: boolean;
}) {
  return (
    <Card>
      <Text style={styles.heading}>Original</Text>
      <Text style={styles.body}>{original}</Text>
      <Text style={styles.heading}>Rewritten</Text>
      <Text style={styles.notice}>AI-generated draft. Review it before saving. Nothing is saved yet.</Text>
      <Input
        label="Edit rewritten"
        value={rewritten}
        onChangeText={onChangeRewritten}
        multiline
      />
      <Button title="Accept rewrite" onPress={onAccept} fullWidth />
      <Button title="Reject" variant="outline" onPress={onReject} fullWidth />
      {canReport ? (
        <Button title="Report incorrect" variant="ghost" onPress={onReport} loading={reporting} fullWidth />
      ) : (
        <Text style={styles.notice}>This rewrite has no activity id, so incorrect-answer feedback cannot be sent.</Text>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  heading: {
    fontFamily: FONT_SEMIBOLD,
    fontSize: 16,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  body: {
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
    lineHeight: 22,
  },
  notice: {
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.sm,
    lineHeight: 20,
  },
});
