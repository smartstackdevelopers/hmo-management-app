import { Tabs } from 'expo-router';
import { Platform, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { TabIcon } from '@/components/ui/TabIcon';
import { LEGACY_TENANT_TABS, ROLE_TABS, TAB_SCREEN_TITLES, TabConfig } from '@/constants/navigation';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';

const ALL_SCREENS = [
  'index', 'find', 'properties', 'compliance', 'tenancy', 'maintenance', 'support', 'inspections',
  'schedule', 'messages', 'users', 'listings', 'settings', 'more',
] as const;

export default function TabLayout() {
  const { user, hmore } = useAuth();
  const insets = useSafeAreaInsets();
  const role = user?.role;
  const visibleTabs = role === 'tenant' && !hmore ? LEGACY_TENANT_TABS : role ? ROLE_TABS[role] : [];
  const visibleNames = new Set(visibleTabs.map((t) => t.name));
  const tabBarHeight = theme.layout.tabBarBase + insets.bottom;

  function getTabConfig(name: string): TabConfig | undefined {
    return visibleTabs.find((t) => t.name === name);
  }

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.background },
        headerTintColor: theme.colors.text,
        headerTitleStyle: { fontWeight: '700', fontSize: 17, letterSpacing: -0.2 },
        headerShadowVisible: false,
        sceneStyle: { backgroundColor: theme.colors.background, flex: 1 },
        tabBarActiveTintColor: theme.colors.tabBarActive,
        tabBarInactiveTintColor: theme.colors.tabBarInactive,
        tabBarStyle: {
          backgroundColor: theme.colors.tabBar,
          borderTopColor: theme.colors.tabBarBorder,
          borderTopWidth: 1,
          height: tabBarHeight,
          paddingBottom: insets.bottom > 0 ? insets.bottom : 8,
          paddingTop: 8,
          ...(Platform.OS !== 'web' ? theme.shadows.sm : {}),
        },
        tabBarLabelStyle: styles.tabLabel,
      }}
    >
      {ALL_SCREENS.map((name) => {
        const tab = getTabConfig(name);
        const isVisible = visibleNames.has(name);

        return (
          <Tabs.Screen
            key={name}
            name={name}
            options={{
              title: tab?.title ?? TAB_SCREEN_TITLES[name] ?? name,
              href: isVisible ? undefined : null,
              headerShown: name !== 'index' && name !== 'more',
              tabBarIcon: tab
                ? ({ color, focused }) => (
                    <TabIcon
                      name={tab.icon}
                      focusedName={tab.iconFocused}
                      focused={focused}
                      color={color as string}
                    />
                  )
                : undefined,
            }}
          />
        );
      })}
    </Tabs>
  );
}

const styles = StyleSheet.create({
  tabLabel: { fontSize: 11, fontWeight: '600', letterSpacing: -0.1 },
});
