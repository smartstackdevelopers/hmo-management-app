import { useQuery } from '@tanstack/react-query';

import { HmoreApiError } from '@/lib/hmore/client';
import { readConnectivity } from '@/lib/hmore/offline/network';

export async function orNull<T>(task: () => Promise<T>): Promise<T | null> {
  try {
    return await task();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}

export function useConnectivity() {
  return useQuery({
    queryKey: ['hmore', 'connectivity'],
    queryFn: () => readConnectivity(),
    staleTime: 20_000,
  });
}
