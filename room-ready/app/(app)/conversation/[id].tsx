import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useLayoutEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { InitialsTile, titleCase } from '@/components/dashboard/mobileChrome';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useConversations, useMessages, useSendMessage } from '@/hooks/useApi';

function dayLabel(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const today = new Date();
  if (date.toDateString() === today.toDateString()) return 'Today';
  return formatUKDate(iso);
}

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const navigation = useNavigation();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const { data: convData } = useConversations();
  const { data, isLoading, error, refetch, isRefetching } = useMessages(id);
  const send = useSendMessage();
  const [text, setText] = useState('');
  const [sendError, setSendError] = useState('');
  const listRef = useRef<FlatList>(null);

  const conversation = convData?.conversations?.find((item) => item.id === id);
  const other = conversation?.participants.find((participant) => participant.user && participant.user.id !== user?.id)?.user
    ?? conversation?.participants.find((participant) => participant.user)?.user;
  const person = other ? `${other.firstName} ${other.lastName}`.trim() : '';
  const headerTitle = person || conversation?.subject || conversation?.property?.name || 'Conversation';
  const roleLabel = other?.role ? titleCase(other.role) : '';

  useLayoutEffect(() => {
    navigation.setOptions({
      headerTitle: () => (
        <View style={styles.header}>
          <InitialsTile name={person || headerTitle} size={32} />
          <View style={styles.headerCopy}>
            <Text style={styles.headerTitle} numberOfLines={1}>{headerTitle}</Text>
            {roleLabel ? <Text style={styles.headerRole} numberOfLines={1}>{roleLabel}</Text> : null}
          </View>
        </View>
      ),
    });
  }, [navigation, headerTitle, person, roleLabel]);

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load conversation" onRetry={refetch} />;

  const messages = data?.messages ?? [];

  async function handleSend() {
    if (!text.trim()) return;
    setSendError('');
    try {
      await send.mutateAsync({ conversationId: id, body: text.trim() });
      setText('');
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : 'Failed to send message');
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 88 : 0}
    >
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={[styles.list, messages.length === 0 && styles.listEmpty]}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
        ListEmptyComponent={
          <EmptyState title="Start the conversation" message="Send a message to get things moving." icon="chatbubble-outline" />
        }
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
        renderItem={({ item, index }) => {
          const isMe = item.sender?.id === user?.id;
          const time = new Date(item.createdAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
          const day = dayLabel(item.createdAt);
          const previous = index > 0 ? dayLabel(messages[index - 1].createdAt) : '';
          return (
            <View>
              {day && day !== previous ? <Text style={styles.day}>{day}</Text> : null}
              <View style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleOther]}>
                {!isMe && item.sender?.firstName && !(item.sender.firstName === 'User' && !item.sender.lastName) ? (
                  <Text style={styles.sender}>{item.sender.firstName}</Text>
                ) : null}
                <Text style={[styles.body, isMe && styles.bodyMe]}>{item.body}</Text>
                <Text style={[styles.time, isMe && styles.timeMe]}>{time}</Text>
              </View>
            </View>
          );
        }}
      />
      <View style={[styles.composer, { paddingBottom: Math.max(insets.bottom, theme.spacing.md) }]}>
        {sendError ? <Text style={styles.error}>{sendError}</Text> : null}
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="Write a message..."
            placeholderTextColor={theme.colors.textMuted}
            multiline
            accessibilityLabel="Write a message"
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Send"
            onPress={handleSend}
            disabled={!text.trim() || send.isPending}
            style={[styles.send, (!text.trim() || send.isPending) && styles.sendOff]}
          >
            {send.isPending ? (
              <ActivityIndicator color={theme.colors.textInverse} size="small" />
            ) : (
              <Ionicons name="send" size={18} color={theme.colors.textInverse} />
            )}
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, maxWidth: 240 },
  headerCopy: { flexShrink: 1 },
  headerTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  headerRole: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary },
  list: { padding: theme.spacing.md, paddingBottom: theme.spacing.sm, flexGrow: 1 },
  listEmpty: { flex: 1, justifyContent: 'center' },
  day: { textAlign: 'center', color: theme.colors.textMuted, fontFamily: FONT_SEMIBOLD, fontSize: 12, marginBottom: 10 },
  bubble: { maxWidth: '82%', padding: 14, borderRadius: theme.radius.lg, marginBottom: 10 },
  bubbleMe: { alignSelf: 'flex-end', backgroundColor: theme.colors.secondaryDark, borderBottomRightRadius: 6 },
  bubbleOther: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    borderBottomLeftRadius: 4,
  },
  sender: { fontSize: 12, fontFamily: FONT_SEMIBOLD, color: theme.colors.secondary, marginBottom: 4 },
  body: { color: theme.colors.text, lineHeight: 22, fontSize: 15, fontFamily: FONT_MEDIUM },
  bodyMe: { color: theme.colors.textInverse },
  time: { fontSize: 11, color: theme.colors.textMuted, marginTop: 6, alignSelf: 'flex-end' },
  timeMe: { color: 'rgba(255,255,255,0.72)' },
  composer: {
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderLight,
    backgroundColor: theme.colors.surface,
    paddingHorizontal: theme.spacing.md,
    paddingTop: theme.spacing.sm,
  },
  inputRow: { flexDirection: 'row', gap: 10, alignItems: 'flex-end' },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.full,
    paddingHorizontal: 16,
    paddingVertical: 12,
    maxHeight: 100,
    color: theme.colors.text,
    fontSize: 15,
    fontFamily: FONT_MEDIUM,
    backgroundColor: theme.colors.surfaceSecondary,
  },
  send: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: theme.colors.secondaryDark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendOff: { opacity: 0.45 },
  error: { color: theme.colors.error, fontSize: 13, marginBottom: 8, fontFamily: FONT_MEDIUM },
});
