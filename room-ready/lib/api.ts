import { API_BASE_URL } from './config';
import { getStoredToken, removeStoredToken, setStoredToken } from './tokenStorage';
import { User } from '@/types';

const TOKEN_KEY = 'roomready_token';

let authToken: string | null = null;

export async function loadToken(): Promise<string | null> {
  if (authToken) return authToken;
  authToken = await getStoredToken();
  return authToken;
}

export async function saveToken(token: string): Promise<void> {
  authToken = token;
  await setStoredToken(token);
}

export async function clearToken(): Promise<void> {
  authToken = null;
  await removeStoredToken();
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { formData?: FormData } = {}
): Promise<T> {
  const token = await loadToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const { formData, ...fetchOptions } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
    body: formData ?? fetchOptions.body,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(data.error ?? 'Request failed', response.status);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body ?? {}) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: 'POST', formData }),
};

export interface AuthResponse {
  user: User;
  token: string;
}

export interface DashboardResponse {
  stats: Record<string, number | string>;
  notifications: NotificationItem[];
  expiringDocuments: DocumentItem[];
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  read: boolean;
  createdAt: string;
  data: Record<string, string>;
  severity?: 'critical' | 'high' | 'medium' | 'info';
}

export interface PropertyItem {
  id: string;
  name: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  county?: string;
  postcode: string;
  hmoLicenceNumber?: string;
  maxOccupants: number;
  description?: string;
  emergencyContact?: string;
  houseRules?: string;
  rooms?: RoomItem[];
  documents?: DocumentItem[];
  _count?: { maintenance: number };
}

export interface RoomItem {
  id: string;
  propertyId: string;
  name: string;
  floor?: string;
  rentPcm: number;
  deposit: number;
  sizeSqm?: number;
  furnished: boolean;
  ensuite: boolean;
  status: string;
  description?: string;
  listing?: ListingItem;
  tenancies?: { id: string; tenant?: { firstName: string; lastName: string } }[];
}

export interface ListingItem {
  id: string;
  roomId: string;
  title: string;
  description?: string;
  /** JSON string or parsed string[] of image URLs */
  photos?: string | string[] | null;
  status: string;
  billsIncluded: boolean;
  availableFrom?: string;
  createdAt?: string;
  room?: RoomItem & { property?: PropertyItem };
  applications?: ApplicationItem[];
}

export interface ApplicationItem {
  id: string;
  status: string;
  message?: string;
  moveInDate?: string;
  createdAt: string;
  tenant?: { id: string; firstName: string; lastName: string; email: string; phone?: string };
  listing?: ListingItem;
}

export interface TenancyItem {
  id: string;
  startDate: string;
  endDate?: string;
  rentPcm: number;
  deposit: number;
  status: string;
  room?: RoomItem & { property?: PropertyItem };
  tenant?: { id: string; firstName: string; lastName: string; email: string; phone?: string };
}

export interface MaintenanceItem {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  photoUrls: string[];
  createdAt: string;
  updatedAt?: string;
  completedAt?: string;
  property?: { id: string; name: string; addressLine1: string; postcode: string };
  room?: { id: string; name: string };
  reporter?: { id: string; firstName: string; lastName: string };
  contractor?: { id: string; firstName: string; lastName: string; phone?: string };
  updates?: {
    id: string;
    note: string;
    photoUrls: string[];
    createdAt: string;
    author?: { firstName: string; lastName: string };
  }[];
}

export interface DocumentItem {
  id: string;
  type: string;
  name: string;
  fileUrl: string;
  expiryDate?: string;
  notes?: string;
  daysLeft?: number | null;
  riskLevel?: 'critical' | 'high' | 'medium' | 'info';
  property?: { id: string; name: string };
}

export interface ConversationItem {
  id: string;
  subject?: string;
  updatedAt: string;
  property?: { id: string; name: string };
  participants: { user: { id: string; firstName: string; lastName: string; role: string } }[];
  messages: { body: string; createdAt: string; sender?: { firstName: string } }[];
}

export interface MessageItem {
  id: string;
  body: string;
  createdAt: string;
  sender?: { id: string; firstName: string; lastName: string };
}

export interface InspectionItem {
  id: string;
  scheduledAt: string;
  completedAt?: string;
  status: string;
  notes?: string;
  findings: string[];
  property?: { id: string; name: string; addressLine1: string; postcode: string };
  inspector?: { firstName: string; lastName: string };
}

export interface AdminUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  verified: boolean;
  active: boolean;
  phone?: string;
  createdAt: string;
  _count?: { ownedProperties: number; tenancies: number };
}
