import { FlatList, FlatListProps, RefreshControl, StyleSheet, View, ViewStyle } from 'react-native';

import { useTabClearance } from '@/hooks/useLayout';
import { theme } from '@/constants/theme';

interface ListScreenProps<T> extends Omit<FlatListProps<T>, 'refreshControl'> {
  refreshing?: boolean;
  onRefresh?: () => void;
  fabClearance?: number;
  containerStyle?: ViewStyle;
}

export function ListScreen<T>({
  refreshing,
  onRefresh,
  fabClearance = 0,
  containerStyle,
  contentContainerStyle,
  ...props
}: ListScreenProps<T>) {
  const bottomPad = useTabClearance(fabClearance);

  return (
    <View style={[styles.container, containerStyle]}>
      <FlatList
        showsVerticalScrollIndicator={false}
        refreshControl={
          onRefresh ? (
            <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={theme.colors.secondary} />
          ) : undefined
        }
        contentContainerStyle={[
          styles.content,
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
});
