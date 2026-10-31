import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

import { ListingItem } from '@/lib/api';

const FAVORITES_KEY = '@roomready_favorites';
const SAVED_SEARCHES_KEY = '@roomready_saved_searches';

export interface SavedSearch {
  id: string;
  label: string;
  query: string;
  filter: string;
  sort: string;
  createdAt: string;
}

export interface FavoriteListing {
  listingId: string;
  title: string;
  city?: string;
  rentPcm: number;
  savedAt: string;
}

async function readJson<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw =
      Platform.OS === 'web'
        ? localStorage.getItem(key)
        : await AsyncStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function writeJson<T>(key: string, value: T): Promise<void> {
  const raw = JSON.stringify(value);
  if (Platform.OS === 'web') {
    localStorage.setItem(key, raw);
    return;
  }
  await AsyncStorage.setItem(key, raw);
}

export async function getFavorites(): Promise<FavoriteListing[]> {
  return readJson<FavoriteListing[]>(FAVORITES_KEY, []);
}

export async function toggleFavorite(listing: ListingItem): Promise<FavoriteListing[]> {
  const current = await getFavorites();
  const exists = current.find((f) => f.listingId === listing.id);
  const next = exists
    ? current.filter((f) => f.listingId !== listing.id)
    : [
        {
          listingId: listing.id,
          title: listing.title,
          city: listing.room?.property?.city,
          rentPcm: listing.room?.rentPcm ?? 0,
          savedAt: new Date().toISOString(),
        },
        ...current,
      ];
  await writeJson(FAVORITES_KEY, next);
  return next;
}

export async function isFavorite(listingId: string): Promise<boolean> {
  const favorites = await getFavorites();
  return favorites.some((f) => f.listingId === listingId);
}

export async function getSavedSearches(): Promise<SavedSearch[]> {
  return readJson<SavedSearch[]>(SAVED_SEARCHES_KEY, []);
}

export async function saveSearch(search: Omit<SavedSearch, 'id' | 'createdAt'>): Promise<SavedSearch[]> {
  const current = await getSavedSearches();
  const duplicate = current.find(
    (s) => s.query === search.query && s.filter === search.filter && s.sort === search.sort
  );
  if (duplicate) return current;

  const entry: SavedSearch = {
    ...search,
    id: `search-${Date.now()}`,
    createdAt: new Date().toISOString(),
  };
  const next = [entry, ...current].slice(0, 10);
  await writeJson(SAVED_SEARCHES_KEY, next);
  return next;
}

export async function removeSavedSearch(id: string): Promise<SavedSearch[]> {
  const next = (await getSavedSearches()).filter((s) => s.id !== id);
  await writeJson(SAVED_SEARCHES_KEY, next);
  return next;
}
