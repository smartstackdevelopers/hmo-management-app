import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  api,
  ApplicationItem,
  ConversationItem,
  DashboardResponse,
  DocumentItem,
  InspectionItem,
  ListingItem,
  MaintenanceItem,
  MessageItem,
  PropertyItem,
  TenancyItem,
  AdminUser,
} from '@/lib/api';
import { HmoreApiError, hmoreFetch } from '@/lib/hmore/client';
import { isAuth0MobileConfigured } from '@/lib/hmoreAuth0';
import { isDemoAuthEnabled } from '@/lib/hmoreDemoAuth';
import { isNativeAuthEnabled } from '@/lib/hmoreNativeAuth';
import { listInbox } from '@/lib/hmore/services/communications';
import { listProperties, mapHmoreProperty } from '@/lib/hmore/services/properties';
import { listOwnTenants } from '@/lib/hmore/services/tenants';
import type { InboxMessage } from '@/lib/hmore/types';

function useHmoreDataMode(): boolean {
  return isDemoAuthEnabled() || isNativeAuthEnabled() || isAuth0MobileConfigured();
}

function isSoftEmptyHmoreError(error: unknown): boolean {
  return (
    error instanceof HmoreApiError &&
    (error.status === 403 || error.status === 404 || error.status === 400)
  );
}

function mapInboxToConversations(items: InboxMessage[]): ConversationItem[] {
  return items.map((item) => ({
    id: item.conversation_id || item.message_id,
    subject: item.subject,
    updatedAt: item.created_at,
    participants: [],
    messages: [
      {
        body: item.body_preview,
        createdAt: item.created_at,
        sender: { firstName: 'Inbox' },
      },
    ],
  }));
}

export function useDashboard() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['dashboard', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        // Legacy Room Ready dashboard is not used with native HMore auth.
        return {
          stats: {},
          notifications: [],
          expiringDocuments: [],
        } satisfies DashboardResponse;
      }
      return api.get<DashboardResponse>('/dashboard');
    },
  });
}

export function useProperties() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['properties', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const page = await listProperties();
          return { properties: (page.items ?? []).map(mapHmoreProperty) };
        } catch (error) {
          // Tenants and roles without properties.read should see an empty list, not a crash screen.
          if (isSoftEmptyHmoreError(error)) {
            return { properties: [] as PropertyItem[] };
          }
          throw error;
        }
      }
      return api.get<{ properties: PropertyItem[] }>('/properties');
    },
  });
}

export function useProperty(id: string) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['properties', id, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        const row = await hmoreFetch<import('@/lib/hmore/services/properties').HmoreProperty>(
          `/properties/${id}`,
          { method: 'GET' },
        );
        return { property: mapHmoreProperty(row) };
      }
      return api.get<{ property: PropertyItem }>(`/properties/${id}`);
    },
    enabled: !!id,
  });
}

export function useListing(id: string) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['listings', id, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { listing: null as unknown as ListingItem };
      }
      return api.get<{ listing: ListingItem }>(`/listings/${id}`);
    },
    enabled: !!id && !hmoreMode,
  });
}

export function useListings(mine?: boolean) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['listings', mine, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { listings: [] as ListingItem[] };
      }
      return api.get<{ listings: ListingItem[] }>(`/listings${mine ? '?mine=true' : ''}`);
    },
  });
}

export function useApplications() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['applications', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { applications: [] as ApplicationItem[] };
      }
      return api.get<{ applications: ApplicationItem[] }>('/applications');
    },
  });
}

export function useTenancies() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['tenancies', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        // Tenancy list for native HMore is loaded via tenant housing / staff APIs elsewhere.
        return { tenancies: [] as TenancyItem[] };
      }
      return api.get<{ tenancies: TenancyItem[] }>('/tenancies');
    },
  });
}

export function useMaintenance() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['maintenance', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const { listMaintenance } = await import('@/lib/hmore/services/maintenance');
          const page = await listMaintenance({ page: 1, page_size: 50 });
          return {
            requests: (page.items ?? []).map((item) => ({
              id: String(item.id),
              title: item.title || 'Repair',
              description: item.description || '',
              category: item.category_code || 'general',
              priority: item.priority || 'medium',
              status: item.status || 'open',
              photoUrls: [],
              createdAt: item.created_at || new Date().toISOString(),
            })) as MaintenanceItem[],
          };
        } catch (error) {
          if (isSoftEmptyHmoreError(error)) {
            return { requests: [] as MaintenanceItem[] };
          }
          throw error;
        }
      }
      return api.get<{ requests: MaintenanceItem[] }>('/maintenance');
    },
  });
}

export function useMaintenanceDetail(id: string) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['maintenance', id, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        const { getMaintenance } = await import('@/lib/hmore/services/maintenance');
        const item = await getMaintenance(id);
        return {
          request: {
            id: String(item.id),
            title: item.title || 'Repair',
            description: item.description || '',
            category: item.category_code || 'general',
            priority: item.priority || 'medium',
            status: item.status || 'open',
            photoUrls: [],
            createdAt: item.created_at || item.reported_at || new Date().toISOString(),
          } as MaintenanceItem,
        };
      }
      return api.get<{ request: MaintenanceItem }>(`/maintenance/${id}`);
    },
    enabled: !!id,
  });
}

export function useDocuments(propertyId?: string) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['documents', propertyId, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { documents: [] as DocumentItem[] };
      }
      return api.get<{ documents: DocumentItem[] }>(
        `/documents${propertyId ? `?propertyId=${propertyId}` : ''}`,
      );
    },
  });
}

export function useConversations() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['conversations', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const page = await listInbox();
          return { conversations: mapInboxToConversations(page.items ?? []) };
        } catch (error) {
          if (isSoftEmptyHmoreError(error)) {
            return { conversations: [] as ConversationItem[] };
          }
          throw error;
        }
      }
      return api.get<{ conversations: ConversationItem[] }>('/conversations');
    },
  });
}

export function useMessages(conversationId: string) {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['messages', conversationId, hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const rows = await hmoreFetch<
            { id: string; body: string; created_at: string; sender_user_id?: string | null }[]
          >(`/communications/conversations/${conversationId}/messages`, { method: 'GET' });
          return {
            messages: (rows ?? []).map((row) => ({
              id: String(row.id),
              body: row.body,
              createdAt: row.created_at,
              sender: row.sender_user_id
                ? { id: String(row.sender_user_id), firstName: 'User', lastName: '' }
                : undefined,
            })) as MessageItem[],
          };
        } catch (error) {
          if (isSoftEmptyHmoreError(error)) {
            return { messages: [] as MessageItem[] };
          }
          throw error;
        }
      }
      return api.get<{ messages: MessageItem[] }>(`/conversations/${conversationId}/messages`);
    },
    enabled: !!conversationId,
    refetchInterval: hmoreMode ? false : 5000,
  });
}

export function useNotifications() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['notifications', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const page = await listInbox();
          const notifications = (page.items ?? []).map((item) => ({
            id: item.message_id,
            type: 'message',
            title: item.subject || 'Message',
            body: item.body_preview,
            read: Boolean(item.read_at),
            createdAt: item.created_at,
            data: {},
          }));
          return {
            notifications,
            unreadCount: notifications.filter((n) => !n.read).length,
          };
        } catch (error) {
          if (isSoftEmptyHmoreError(error)) {
            return { notifications: [], unreadCount: 0 };
          }
          throw error;
        }
      }
      return api.get<{ notifications: DashboardResponse['notifications']; unreadCount: number }>(
        '/notifications',
      );
    },
  });
}

export function useInspections() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['inspections', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { inspections: [] as InspectionItem[] };
      }
      return api.get<{ inspections: InspectionItem[] }>('/inspections');
    },
  });
}

export function useAdminUsers() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['admin', 'users', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { users: [] as AdminUser[] };
      }
      return api.get<{ users: AdminUser[] }>('/admin/users');
    },
  });
}

export function useAdminAnalytics() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['admin', 'analytics', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { analytics: {} as Record<string, unknown> };
      }
      return api.get<{ analytics: Record<string, unknown> }>('/admin/analytics');
    },
  });
}

export function useContractors() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['contractors', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        return { contractors: [] as AdminUser[] };
      }
      return api.get<{ contractors: AdminUser[] }>('/users/contractors');
    },
  });
}

export function useContacts() {
  const hmoreMode = useHmoreDataMode();
  return useQuery({
    queryKey: ['contacts', hmoreMode ? 'hmore' : 'legacy'],
    queryFn: async () => {
      if (hmoreMode) {
        try {
          const page = await listOwnTenants();
          const contacts = (page.items ?? [])
            .filter((row) => row.user_id)
            .map((row) => {
              const name = (row.preferred_name || row.full_name || row.email || 'Tenant').trim();
              const parts = name.split(/\s+/).filter(Boolean);
              return {
                id: String(row.user_id),
                firstName: parts[0] || 'Tenant',
                lastName: parts.slice(1).join(' '),
                email: row.email || '',
                role: 'tenant',
              };
            });
          return { contacts };
        } catch (error) {
          // Landlord without tenants.read (or empty org) → empty contacts, not an error screen.
          if (isSoftEmptyHmoreError(error)) {
            return { contacts: [] as { id: string; firstName: string; lastName: string; email: string; role: string }[] };
          }
          throw error;
        }
      }
      return api.get<{ contacts: { id: string; firstName: string; lastName: string; email: string; role: string }[] }>(
        '/users/contacts',
      );
    },
  });
}

export function useInvalidate() {
  const queryClient = useQueryClient();
  return (keys: string[]) => keys.forEach((k) => queryClient.invalidateQueries({ queryKey: [k] }));
}

export function useCreateProperty() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: Partial<PropertyItem>) => api.post('/properties', data),
    onSuccess: () => invalidate(['properties', 'dashboard']),
  });
}

export function useCreateMaintenance() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/maintenance', data),
    onSuccess: () => invalidate(['maintenance', 'dashboard']),
  });
}

export function useUpdateMaintenance() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/maintenance/${id}`, data),
    onSuccess: () => invalidate(['maintenance', 'dashboard']),
  });
}

export function useApplyListing() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: { listingId: string; message?: string }) => api.post('/applications', data),
    onSuccess: () => invalidate(['applications', 'listings']),
  });
}

export function useReviewApplication() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'approved' | 'rejected' }) =>
      api.patch(`/applications/${id}`, { status }),
    onSuccess: () => invalidate(['applications', 'tenancies', 'properties', 'listings']),
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conversationId, body }: { conversationId: string; body: string }) =>
      api.post(`/conversations/${conversationId}/messages`, { body }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['messages', vars.conversationId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useVerifyUser() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, verified }: { id: string; verified: boolean }) =>
      api.patch(`/admin/users/${id}`, { verified }),
    onSuccess: () => invalidate(['admin']),
  });
}

export function useUpdateProperty() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/properties/${id}`, data),
    onSuccess: () => invalidate(['properties', 'dashboard']),
  });
}

export function useDeleteProperty() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/properties/${id}`),
    onSuccess: () => invalidate(['properties', 'dashboard']),
  });
}

export function useCreateRoom() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ propertyId, ...data }: { propertyId: string } & Record<string, unknown>) =>
      api.post(`/properties/${propertyId}/rooms`, data),
    onSuccess: () => invalidate(['properties']),
  });
}

export function useUpdateRoom() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ roomId, ...data }: { roomId: string } & Record<string, unknown>) =>
      api.patch(`/properties/rooms/${roomId}`, data),
    onSuccess: () => invalidate(['properties']),
  });
}

export function useDeleteRoom() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (roomId: string) => api.delete(`/properties/rooms/${roomId}`),
    onSuccess: () => invalidate(['properties']),
  });
}

export function useCreateListing() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/listings', data),
    onSuccess: () => invalidate(['listings', 'properties', 'dashboard']),
  });
}

export function useUpdateListing() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/listings/${id}`, data),
    onSuccess: () => invalidate(['listings', 'properties']),
  });
}

export function useUploadDocument() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (formData: FormData) => api.upload<{ document: DocumentItem }>('/documents', formData),
    onSuccess: () => invalidate(['documents', 'properties', 'dashboard']),
  });
}

export function useDeleteDocument() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => invalidate(['documents', 'properties', 'dashboard']),
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      if (useHmoreDataMode()) {
        try {
          await hmoreFetch(`/communications/messages/${id}/read`, {
            method: 'PATCH',
            body: { read: true },
          });
        } catch {
          // Soft-ignore when inbox message ids are not available yet.
        }
        return;
      }
      return api.patch(`/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (useHmoreDataMode()) {
        return { status: 'ok' };
      }
      return api.post('/notifications/read-all');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useRunComplianceScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (useHmoreDataMode()) {
        return { created: 0 };
      }
      return api.post<{ created: number }>('/notifications/compliance-scan');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useAIAssistMessage() {
  return useMutation({
    mutationFn: (data: { mode: 'rewrite_professional' | 'summarize'; text: string }) =>
      api.post<{ output: string }>('/conversations/ai-assist', data),
  });
}

export function useEvidencePack() {
  return useMutation({
    mutationFn: (propertyId: string) =>
      api.get<{ evidencePack: Record<string, unknown> }>(`/documents/evidence-pack?propertyId=${propertyId}`),
  });
}

export function useCreateConversation() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (data: {
      participantIds: string[];
      propertyId?: string;
      subject?: string;
      initialMessage?: string;
    }) => {
      if (useHmoreDataMode()) {
        const recipient = data.participantIds[0];
        if (!recipient) {
          throw new Error('Select a recipient');
        }
        if (!data.initialMessage?.trim()) {
          throw new Error('Enter a message');
        }
        const result = await hmoreFetch<{
          conversation_id?: string;
          id?: string;
          message_id?: string;
        }>('/communications/messages', {
          method: 'POST',
          body: {
            recipient_user_id: recipient,
            subject: data.subject || null,
            body: data.initialMessage,
            conversation_property_id: data.propertyId || null,
          },
        });
        const conversationId = String(result.conversation_id || result.id || result.message_id || '');
        return {
          conversation: {
            id: conversationId,
            subject: data.subject,
            updatedAt: new Date().toISOString(),
            participants: [],
            messages: [{ body: data.initialMessage, createdAt: new Date().toISOString() }],
          } satisfies ConversationItem,
        };
      }
      return api.post<{ conversation: ConversationItem }>('/conversations', data);
    },
    onSuccess: () => invalidate(['conversations']),
  });
}

export function useCreateInspection() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (data: { propertyId: string; scheduledAt: string; notes?: string }) =>
      api.post('/inspections', data),
    onSuccess: () => invalidate(['inspections', 'dashboard']),
  });
}

export function useUpdateInspection() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/inspections/${id}`, data),
    onSuccess: () => invalidate(['inspections', 'dashboard']),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { currentPassword: string; newPassword: string }) =>
      api.patch('/auth/password', data),
  });
}
