import { listingCoverPhoto } from '@/lib/listingPhotos';

/** Cover images for seeded Birmingham HMOs (aligned with listing photo sets). */
export const PROPERTY_COVERS: Record<string, string> = {
  'seed-property-1': listingCoverPhoto(null, 'seed-listing-1'),
  'seed-property-2': listingCoverPhoto(null, 'seed-listing-3'),
  'seed-property-3': listingCoverPhoto(null, 'seed-listing-6'),
  'seed-property-4': listingCoverPhoto(null, 'seed-listing-9'),
};

export function propertyCoverUrl(propertyId: string): string {
  return PROPERTY_COVERS[propertyId] ?? listingCoverPhoto(null, propertyId);
}
