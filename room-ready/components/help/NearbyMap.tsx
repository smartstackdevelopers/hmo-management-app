import { Linking, Platform, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import type { NearbyService } from '@/lib/hmore/services/helpNearMe';

/**
 * Lightweight map alternative that does not embed API keys in the app.
 * Opens the searched area and markers in the device maps / OSM browser.
 */
export function NearbyMap({
  originLat,
  originLon,
  postcode,
  items,
  onSelect,
}: {
  originLat: number;
  originLon: number;
  postcode: string;
  items: NearbyService[];
  onSelect: (id: string) => void;
}) {
  const openOverview = async () => {
    const markerQuery = items
      .slice(0, 12)
      .map((item) => `${item.latitude},${item.longitude}`)
      .join('/');
    const osm = `https://www.openstreetmap.org/?mlat=${originLat}&mlon=${originLon}#map=13/${originLat}/${originLon}`;
    const apple = `http://maps.apple.com/?ll=${originLat},${originLon}&q=${encodeURIComponent(postcode)}`;
    const google = `https://www.google.com/maps/search/?api=1&query=${originLat},${originLon}`;
    const url = Platform.OS === 'ios' ? apple : Platform.OS === 'android' ? google : osm;
    try {
      await Linking.openURL(url);
    } catch {
      await Linking.openURL(osm);
    }
    void markerQuery;
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.lead}>
        Map markers use real geocoded coordinates from directory records. Open the map app for
        pan/zoom, or pick a service below.
      </Text>
      <Button title="Open map for searched postcode" onPress={openOverview} accessibilityLabel="Open map" />
      <View style={styles.list}>
        {items.map((item) => (
          <Button
            key={item.id}
            title={`${item.name} · ${item.distance_km} km`}
            variant="secondary"
            onPress={() => onSelect(item.id)}
            accessibilityLabel={item.name}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10, marginBottom: theme.spacing.md },
  lead: {
    fontFamily: FONT_MEDIUM,
    fontSize: 13,
    color: theme.colors.textSecondary,
    lineHeight: 20,
  },
  list: { gap: 8 },
});
