import { HMORE_API_BASE_URL } from '@/lib/hmore/config';

export { resolveDevHost } from '@/lib/network';

/** File URLs for HMore API–served assets (not legacy port 3001). */
export function getFileUrl(path: string): string {
  if (path.startsWith('http')) return path;
  const origin = HMORE_API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${origin}${normalized}`;
}