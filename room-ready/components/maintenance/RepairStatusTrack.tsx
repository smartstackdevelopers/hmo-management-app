import { StyleSheet, Text, View } from 'react-native';

import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { REPAIR_TRACK, trackStepIndex } from '@/lib/maintenance';

export function RepairStatusTrack({ status }: { status: string }) {
  const active = trackStepIndex(status);
  const cancelled = status === 'cancelled';

  if (cancelled) {
    return (
      <View style={styles.cancelled}>
        <Text style={styles.cancelledText}>This repair was cancelled</Text>
      </View>
    );
  }

  return (
    <View style={styles.track}>
      {REPAIR_TRACK.map((step, index) => {
        const done = active > index;
        const current = active === index;
        return (
          <View key={step.key} style={styles.step}>
            <View style={styles.railRow}>
              <View
                style={[
                  styles.dot,
                  done && styles.dotDone,
                  current && styles.dotCurrent,
                ]}
              />
              {index < REPAIR_TRACK.length - 1 && (
                <View style={[styles.line, (done || current) && styles.lineActive]} />
              )}
            </View>
            <Text
              style={[
                styles.label,
                (done || current) && styles.labelActive,
                current && styles.labelCurrent,
              ]}
              numberOfLines={1}
            >
              {step.label}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  track: { flexDirection: 'row', marginTop: 4 },
  step: { flex: 1, minWidth: 0 },
  railRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  dot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: theme.colors.border,
    borderWidth: 2,
    borderColor: theme.colors.surface,
  },
  dotDone: { backgroundColor: theme.colors.secondary },
  dotCurrent: {
    backgroundColor: theme.colors.secondary,
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 3,
    borderColor: theme.colors.accentLight,
  },
  line: {
    flex: 1,
    height: 2,
    backgroundColor: theme.colors.border,
    marginHorizontal: 2,
  },
  lineActive: { backgroundColor: theme.colors.secondary },
  label: {
    fontSize: 11,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
  },
  labelActive: { color: theme.colors.textSecondary },
  labelCurrent: {
    color: theme.colors.secondaryDark,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
  },
  cancelled: {
    backgroundColor: theme.colors.errorLight,
    borderRadius: theme.radius.md,
    padding: 12,
  },
  cancelledText: {
    color: theme.colors.error,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    fontSize: 13,
  },
});
