import { useCallback, useEffect, useState } from 'react';

import { ListingItem } from '@/lib/api';
import {
  FavoriteListing,
  SavedSearch,
  getFavorites,
  getSavedSearches,
  removeSavedSearch,
  saveSearch,
  toggleFavorite,
} from '@/lib/tenantPreferences';

export function useTenantPreferences() {
  const [favorites, setFavorites] = useState<FavoriteListing[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const [f, s] = await Promise.all([getFavorites(), getSavedSearches()]);
    setFavorites(f);
    setSavedSearches(s);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = useCallback(async (listing: ListingItem) => {
    const next = await toggleFavorite(listing);
    setFavorites(next);
    return next;
  }, []);

  const addSavedSearch = useCallback(
    async (search: Omit<SavedSearch, 'id' | 'createdAt'>) => {
      const next = await saveSearch(search);
      setSavedSearches(next);
      return next;
    },
    []
  );

  const deleteSavedSearch = useCallback(async (id: string) => {
    const next = await removeSavedSearch(id);
    setSavedSearches(next);
    return next;
  }, []);

  const isFavorited = useCallback(
    (listingId: string) => favorites.some((f) => f.listingId === listingId),
    [favorites]
  );

  return {
    favorites,
    savedSearches,
    loading,
    refresh,
    toggle,
    addSavedSearch,
    deleteSavedSearch,
    isFavorited,
  };
}
