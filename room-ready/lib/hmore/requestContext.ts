import * as SecureStore from 'expo-secure-store';

const ORG_KEY = 'hmore.session.organisationId';
const ROLE_KEY = 'hmore.session.role';

export type HmoreRequestContext = {
  organisationId: string | null;
  role: string | null;
};

let current: HmoreRequestContext = { organisationId: null, role: null };

export function getRequestContext(): HmoreRequestContext {
  return current;
}

export async function loadRequestContext(): Promise<HmoreRequestContext> {
  const [organisationId, role] = await Promise.all([
    SecureStore.getItemAsync(ORG_KEY),
    SecureStore.getItemAsync(ROLE_KEY),
  ]);
  current = { organisationId, role };
  return current;
}

export async function setRequestContext(next: HmoreRequestContext): Promise<void> {
  current = {
    organisationId: next.organisationId?.trim() || null,
    role: next.role?.trim() || null,
  };
  if (current.organisationId) {
    await SecureStore.setItemAsync(ORG_KEY, current.organisationId);
  } else {
    await SecureStore.deleteItemAsync(ORG_KEY);
  }
  if (current.role) {
    await SecureStore.setItemAsync(ROLE_KEY, current.role);
  } else {
    await SecureStore.deleteItemAsync(ROLE_KEY);
  }
}

export async function clearRequestContext(): Promise<void> {
  await setRequestContext({ organisationId: null, role: null });
}
