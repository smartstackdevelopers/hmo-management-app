import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { compactGBP, StatTiles } from '@/components/dashboard/mobileChrome';
import { HeroCard } from '@/components/ui/HeroCard';
import { QuickActions } from '@/components/ui/QuickActions';
import { Section } from '@/components/ui/Section';
import { theme } from '@/constants/theme';
import { PropertyItem } from '@/lib/api';

interface PortfolioHomeCardProps {
  properties: PropertyItem[];
  portfolioScore: number | null;
  openRepairs: number;
  expiringDocs: number;
  role?: string;
}

export function PortfolioHomeCard({
  properties,
  openRepairs,
  expiringDocs,
  role,
}: PortfolioHomeCardProps) {
  if (properties.length === 0) {
    return (
      <HeroCard
        kicker="Occupancy"
        title="Add your first property"
        subtitle="Rooms, certificates and repairs show up here once a property is added."
        icon="home-outline"
        ctaLabel="Add property"
        onCta={() => router.push('/(app)/property/new')}
      />
    );
  }

  const occupied = properties.reduce(
    (sum, property) => sum + (property.rooms?.filter((room) => room.status === 'occupied').length ?? 0),
    0
  );
  const rooms = properties.reduce((sum, property) => sum + (property.rooms?.length ?? 0), 0);
  const vacant = Math.max(rooms - occupied, 0);
  const percent = rooms > 0 ? Math.round((occupied / rooms) * 100) : 0;
  const listings = properties.reduce(
    (sum, property) => sum + (property.rooms?.filter((room) => room.listing).length ?? 0),
    0
  );
  const rent = properties.reduce(
    (sum, property) =>
      sum +
      (property.rooms?.filter((room) => room.status === 'occupied').reduce((roomSum, room) => roomSum + (room.rentPcm || 0), 0) ?? 0),
    0
  );
  const subtitle = [
    `${vacant} room${vacant === 1 ? '' : 's'} vacant`,
    listings > 0 ? `${listings} listing${listings === 1 ? '' : 's'} live` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <View style={styles.wrap}>
      <HeroCard
        kicker="Occupancy"
        value={rooms > 0 ? `${percent}% · ${occupied} of ${rooms}` : `${properties.length}`}
        subtitle={subtitle}
        ctaLabel={vacant > 0 ? 'View vacancies' : 'View properties'}
        onCta={() => router.push('/(app)/(tabs)/properties')}
      />
      <StatTiles
        items={[
          { value: String(openRepairs), label: 'Open repairs' },
          { value: String(expiringDocs), label: 'Certs due' },
          { value: rent > 0 ? compactGBP(rent) : '—', label: 'Rent this month' },
        ]}
      />
      <Section title="Quick actions">
        <QuickActions
          actions={[
            {
              key: 'add',
              label: role === 'property_manager' ? 'Properties' : 'Add property',
              icon: role === 'property_manager' ? 'business-outline' : 'add',
              tone: 'blue',
              onPress: () => router.push(role === 'property_manager' ? '/(app)/(tabs)/properties' : '/(app)/property/new'),
            },
            { key: 'repair', label: 'Log repair', icon: 'construct-outline', tone: 'indigo', onPress: () => router.push('/(app)/maintenance/new') },
            {
              key: 'inspect',
              label: role === 'property_manager' ? 'Inspection' : 'Checks',
              icon: 'clipboard-outline',
              tone: 'amber',
              onPress: () => router.push(role === 'property_manager' ? '/(app)/(tabs)/inspections' : '/(app)/(tabs)/compliance'),
            },
            { key: 'listing', label: 'Listing', icon: 'list-outline', tone: 'green', onPress: () => router.push('/(app)/(tabs)/listings') },
          ]}
        />
      </Section>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.sm },
});
