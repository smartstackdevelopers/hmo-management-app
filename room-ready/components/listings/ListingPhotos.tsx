import React, { useState } from 'react';
import {
  Dimensions,
  Image,
  ImageStyle,
  NativeScrollEvent,
  NativeSyntheticEvent,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { theme } from '@/constants/theme';
import { parseListingPhotos } from '@/lib/listingPhotos';

interface ListingPhotoGalleryProps {
  photos?: string | string[] | null;
  height?: number;
  listingId?: string;
}

export function ListingPhotoGallery({ photos, height = 220, listingId }: ListingPhotoGalleryProps) {
  const urls = parseListingPhotos(photos, listingId);
  const width = Math.min(Dimensions.get('window').width, theme.layout.phoneMaxWidth) - theme.spacing.md * 2;
  const [index, setIndex] = useState(0);

  function onScroll(e: NativeSyntheticEvent<NativeScrollEvent>) {
    const next = Math.round(e.nativeEvent.contentOffset.x / Math.max(width, 1));
    if (next !== index) setIndex(next);
  }

  return (
    <View style={[styles.wrap, { height }]}>
      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={onScroll}
        scrollEventThrottle={16}
        style={{ width }}
      >
        {urls.map((uri) => (
          <Image
            key={uri}
            source={{ uri }}
            style={{ width, height, backgroundColor: theme.colors.surfaceMuted }}
            resizeMode="cover"
            accessibilityLabel="Room photo"
          />
        ))}
      </ScrollView>
      {urls.length > 1 && (
        <View style={styles.dots}>
          {urls.map((uri, i) => (
            <View key={uri} style={[styles.dot, i === index && styles.dotActive]} />
          ))}
        </View>
      )}
      <View style={styles.count}>
        <Text style={styles.countText}>
          {index + 1}/{urls.length}
        </Text>
      </View>
    </View>
  );
}

export function ListingThumb({
  photos,
  listingId,
  style,
}: {
  photos?: string | string[] | null;
  listingId?: string;
  style?: StyleProp<ImageStyle>;
}) {
  const urls = parseListingPhotos(photos, listingId);
  return (
    <Image
      source={{ uri: urls[0] }}
      style={[styles.thumb, style]}
      resizeMode="cover"
      accessibilityLabel="Room photo"
    />
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
    borderRadius: theme.radius.lg,
    overflow: 'hidden',
    backgroundColor: theme.colors.surfaceMuted,
    marginBottom: theme.spacing.md,
    position: 'relative',
  },
  dots: {
    position: 'absolute',
    bottom: 10,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 5,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255,255,255,0.45)',
  },
  dotActive: { backgroundColor: '#fff', width: 16 },
  count: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(11,18,32,0.55)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
  },
  countText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  thumb: {
    width: '100%',
    height: 160,
    backgroundColor: theme.colors.surfaceMuted,
  },
});
