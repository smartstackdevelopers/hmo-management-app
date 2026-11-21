import { FlatList, FlatListProps, RefreshControl, StyleSheet, View, ViewStyle } from 'react-native';

import { useTabClearance } from '@/hooks/useLayout';
import { theme } from '@/constants/theme';

interface ListScreenProps<T> extends Omit<FlatListProps<T>, 'refreshControl'> {
  refreshing?: boolean;
  onRefresh?: () => void;
  fabClearance?: number;
  containerStyle?: ViewStyle;
  /** Horizontal page padding. Defaults to on. */
  padded?: boolean;
}

export function ListScreen<T>({
  refreshing,
  onRefresh,
  fabClearance = 0,
  containerStyle,
  contentContainerStyle,
  padded = true,
  ...props
}: ListScreenProps<T>) {
  const bottomPad = useTabClearance(fabClearance);

  return (
    <View style={[styles.container, containerStyle]}>
      <FlatList
        showsVerticalScrollIndicator={false}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={!!refreshing}
              onRefresh={onRefresh}
              tintColor={theme.colors.secondary}
              colors={[theme.colors.secondaryDark]}
              progressBackgroundColor={theme.colors.surface}
            />
          ) : undefined
        }
        contentContainerStyle={[
          padded ? styles.content : styles.contentBare,
          contentContainerStyle,
          { paddingBottom: bottomPad },
        ]}
        {...props}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, flexGrow: 1 },
  contentBare: { flexGrow: 1 },
});
