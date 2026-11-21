import { secureDeleteItem, secureGetItem, secureSetItem } from '@/lib/secureStorage';

const TOKEN_KEY = 'roomready_token';

export async function getStoredToken(): Promise<string | null> {
  return secureGetItem(TOKEN_KEY);
}

export async function setStoredToken(token: string): Promise<void> {
  await secureSetItem(TOKEN_KEY, token);
}

export async function removeStoredToken(): Promise<void> {
  await secureDeleteItem(TOKEN_KEY);
}
