import { Linking, Platform, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import type { NearbyService } from '@/lib/hmore/services/helpNearMe';

function directionsUrl(lat: number, lon: number, name: string): string {
  const q = encodeURIComponent(`${name} @${lat},${lon}`);
  if (Platform.OS === 'ios') return `http://maps.apple.com/?daddr=${lat},${lon}&q=${q}`;
  if (Platform.OS === 'android') return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
  return `https://www.openstreetmap.org/directions?to=${lat}%2C${lon}`;
}

function overviewUrl(originLat: number, originLon: number, postcode: string, items: NearbyService[]): string {
  // OSM bounding view centred on the geocoded postcode; markers listed below with real coords.
  const osm = `https://www.openstreetmap.org/?mlat=${originLat}&mlon=${originLon}#map=13/${originLat}/${originLon}`;
  if (Platform.OS === 'ios') {
    return `http://maps.apple.com/?ll=${originLat},${originLon}&q=${encodeURIComponent(postcode)}`;
  }
  if (Platform.OS === 'android') {
    const pins = items
      .slice(0, 8)
      .map((item) => `${item.latitude},${item.longitude}`)
      .join('|');
    return pins
      ? `https://www.google.com/maps/dir/?api=1&origin=${originLat},${originLon}&destination=${items[0].latitude},${items[0].longitude}`
      : `https://www.google.com/maps/search/?api=1&query=${originLat},${originLon}`;
  }
  return osm;
}

/**
 * Map surface for Help Near Me using real geocoded coordinates from the API.
 * Opens the device map app (no embedded map SDK / API keys required).
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
    const url = overviewUrl(originLat, originLon, postcode, items);
    try {
      await Linking.openURL(url);
    } catch {
      await Linking.openURL(
        `https://www.openstreetmap.org/?mlat=${originLat}&mlon=${originLon}#map=13/${originLat}/${originLon}`,
      );
    }
  };

  return (
    <View style={styles.wrap}>
      <Text style={styles.lead}>
        Coordinates come from verified directory geocoding ({originLat.toFixed(5)}, {originLon.toFixed(5)} for{' '}
        {postcode}). Open the map app for pan/zoom, or use directions per service.
      </Text>
      <Text style={styles.meta}>{items.length} nearby service{items.length === 1 ? '' : 's'} with coordinates</Text>
      <Button title="Open map for searched postcode" onPress={openOverview} accessibilityLabel="Open map" />
      <View style={styles.list}>
        {items.map((item) => (
          <View key={item.id} style={styles.item}>
            <Text style={styles.name}>
              {item.name} · {item.distance_km} km
            </Text>
            <Text style={styles.meta}>
              {Number(item.latitude).toFixed(5)}, {Number(item.longitude).toFixed(5)}
            </Text>
            <View style={styles.row}>
              <Button title="Details" variant="secondary" onPress={() => onSelect(item.id)} />
              <Button
                title="Directions"
                variant="secondary"
                onPress={() =>
                  void Linking.openURL(directionsUrl(Number(item.latitude), Number(item.longitude), item.name))
                }
              />
            </View>
          </View>
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
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted },
  list: { gap: 10 },
  item: {
    gap: 6,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    borderRadius: theme.radius.md,
    padding: theme.spacing.sm,
    backgroundColor: theme.colors.surface,
  },
  name: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  row: { flexDirection: 'row', gap: 8 },
});
