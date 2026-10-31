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

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardResponse>('/dashboard'),
  });
}

export function useProperties() {
  return useQuery({
    queryKey: ['properties'],
    queryFn: () => api.get<{ properties: PropertyItem[] }>('/properties'),
  });
}

export function useProperty(id: string) {
  return useQuery({
    queryKey: ['properties', id],
    queryFn: () => api.get<{ property: PropertyItem }>(`/properties/${id}`),
    enabled: !!id,
  });
}

export function useListing(id: string) {
  return useQuery({
    queryKey: ['listings', id],
    queryFn: () => api.get<{ listing: ListingItem }>(`/listings/${id}`),
    enabled: !!id,
  });
}

export function useListings(mine?: boolean) {
  return useQuery({
    queryKey: ['listings', mine],
    queryFn: () => api.get<{ listings: ListingItem[] }>(`/listings${mine ? '?mine=true' : ''}`),
  });
}

export function useApplications() {
  return useQuery({
    queryKey: ['applications'],
    queryFn: () => api.get<{ applications: ApplicationItem[] }>('/applications'),
  });
}

export function useTenancies() {
  return useQuery({
    queryKey: ['tenancies'],
    queryFn: () => api.get<{ tenancies: TenancyItem[] }>('/tenancies'),
  });
}

export function useMaintenance() {
  return useQuery({
    queryKey: ['maintenance'],
    queryFn: () => api.get<{ requests: MaintenanceItem[] }>('/maintenance'),
  });
}

export function useMaintenanceDetail(id: string) {
  return useQuery({
    queryKey: ['maintenance', id],
    queryFn: () => api.get<{ request: MaintenanceItem }>(`/maintenance/${id}`),
    enabled: !!id,
  });
}

export function useDocuments(propertyId?: string) {
  return useQuery({
    queryKey: ['documents', propertyId],
    queryFn: () =>
      api.get<{ documents: DocumentItem[] }>(
        `/documents${propertyId ? `?propertyId=${propertyId}` : ''}`
      ),
  });
}

export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.get<{ conversations: ConversationItem[] }>('/conversations'),
  });
}

export function useMessages(conversationId: string) {
  return useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => api.get<{ messages: MessageItem[] }>(`/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
    refetchInterval: 5000,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () =>
      api.get<{ notifications: DashboardResponse['notifications']; unreadCount: number }>(
        '/notifications'
      ),
  });
}

export function useInspections() {
  return useQuery({
    queryKey: ['inspections'],
    queryFn: () => api.get<{ inspections: InspectionItem[] }>('/inspections'),
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => api.get<{ users: AdminUser[] }>('/admin/users'),
  });
}

export function useAdminAnalytics() {
  return useQuery({
    queryKey: ['admin', 'analytics'],
    queryFn: () => api.get<{ analytics: Record<string, unknown> }>('/admin/analytics'),
  });
}

export function useContractors() {
  return useQuery({
    queryKey: ['contractors'],
    queryFn: () => api.get<{ contractors: AdminUser[] }>('/users/contractors'),
  });
}

export function useContacts() {
  return useQuery({
    queryKey: ['contacts'],
    queryFn: () =>
      api.get<{ contacts: { id: string; firstName: string; lastName: string; email: string; role: string }[] }>(
        '/users/contacts'
      ),
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
    mutationFn: (id: string) => api.patch(`/notifications/${id}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post('/notifications/read-all'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useRunComplianceScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ created: number }>('/notifications/compliance-scan'),
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
    mutationFn: (data: {
      participantIds: string[];
      propertyId?: string;
      subject?: string;
      initialMessage?: string;
    }) => api.post<{ conversation: ConversationItem }>('/conversations', data),
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
