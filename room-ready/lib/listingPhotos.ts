/** Demo / fallback room photos (Unsplash). */

const ROOM_SETS: string[][] = [
  [
    'https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=1200&q=80',
    'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=1200&q=80',
    'https://images.unsplash.com/photo-1560184897-ae75f418493e?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=1200&q=80',
    'https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=1200&q=80',
    'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=1200&q=80',
    'https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=1200&q=80',
    'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200&q=80',
    'https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=1200&q=80',
    'https://images.unsplash.com/photo-1484154218962-a197022b5858?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1200&q=80',
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200&q=80',
    'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1200&q=80',
    'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdbc?w=1200&q=80',
    'https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1554995207-c18c203602cb?w=1200&q=80',
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1200&q=80',
    'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&q=80',
    'https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=1200&q=80',
    'https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1600121848594-d8644e57abab?w=1200&q=80',
    'https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=1200&q=80',
    'https://images.unsplash.com/photo-1600573472591-ee6981cf4214?w=1200&q=80',
  ],
  [
    'https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1200&q=80',
    'https://images.unsplash.com/photo-1618220179428-22790b461013?w=1200&q=80',
    'https://images.unsplash.com/photo-1616137466211-f939a420be44?w=1200&q=80',
  ],
];

/** Curated photo sets for seed listing IDs. */
export const DEMO_LISTING_PHOTOS: Record<string, string[]> = {
  'seed-listing-1': ROOM_SETS[0],
  'seed-listing-2': ROOM_SETS[1],
  'seed-listing-3': ROOM_SETS[2],
  'seed-listing-4': ROOM_SETS[3],
  'seed-listing-5': ROOM_SETS[4],
  'seed-listing-6': ROOM_SETS[5],
  'seed-listing-7': ROOM_SETS[6],
  'seed-listing-8': ROOM_SETS[7],
  'seed-listing-9': ROOM_SETS[8],
  'seed-listing-10': ROOM_SETS[9],
};

function hashId(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return h;
}

export function parseListingPhotos(
  photos?: string | string[] | null,
  listingId?: string
): string[] {
  if (Array.isArray(photos) && photos.length > 0) return photos;
  if (typeof photos === 'string' && photos.trim()) {
    try {
      const parsed = JSON.parse(photos) as unknown;
      if (Array.isArray(parsed) && parsed.every((p) => typeof p === 'string') && parsed.length > 0) {
        return parsed;
      }
    } catch {
      // fall through
    }
  }
  if (listingId && DEMO_LISTING_PHOTOS[listingId]) return DEMO_LISTING_PHOTOS[listingId];
  if (listingId) return ROOM_SETS[hashId(listingId) % ROOM_SETS.length];
  return ROOM_SETS[0];
}

export function listingCoverPhoto(photos?: string | string[] | null, listingId?: string): string {
  return parseListingPhotos(photos, listingId)[0];
}
