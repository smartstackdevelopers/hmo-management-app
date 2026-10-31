import { useLocalSearchParams, useNavigation } from 'expo-router';
import { useLayoutEffect, useRef, useState } from 'react';
import { FlatList, KeyboardAvoidingView, Platform, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useAIAssistMessage, useConversations, useMessages, useSendMessage } from '@/hooks/useApi';

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const navigation = useNavigation();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const { data: convData } = useConversations();
  const { data, isLoading, error, refetch, isRefetching } = useMessages(id);
  const send = useSendMessage();
  const aiAssist = useAIAssistMessage();
  const [text, setText] = useState('');
  const [sendError, setSendError] = useState('');
  const listRef = useRef<FlatList>(null);

  const conversation = convData?.conversations?.find((c) => c.id === id);
  const other = conversation?.participants.find((p) => p.user?.id !== user?.id)?.user;
  const headerTitle =
    conversation?.subject ??
    conversation?.property?.name ??
    (other ? `${other.firstName} ${other.lastName}` : 'Conversation');

  useLayoutEffect(() => {
    navigation.setOptions({ title: headerTitle });
  }, [navigation, headerTitle]);

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

  async function handleAIAssist(mode: 'rewrite_professional' | 'summarize') {
    if (!text.trim()) return;
    try {
      const result = await aiAssist.mutateAsync({ mode, text });
      setText(result.output);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : 'AI assist failed');
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
        contentContainerStyle={[
          styles.list,
          messages.length === 0 && styles.listEmpty,
        ]}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />
        }
        ListEmptyComponent={
          <EmptyState
            title="Start the conversation"
            message="Send a message to get things moving."
            icon="chatbubble-outline"
          />
        }
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
        renderItem={({ item }) => {
          const isMe = item.sender?.id === user?.id;
          const time = new Date(item.createdAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
          return (
            <View style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleOther]}>
              {!isMe && <Text style={styles.sender}>{item.sender?.firstName}</Text>}
              <Text style={[styles.body, isMe && styles.bodyMe]}>{item.body}</Text>
              <Text style={[styles.time, isMe && styles.timeMe]}>{time}</Text>
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
            placeholder="Type a message..."
            placeholderTextColor={theme.colors.textMuted}
            multiline
          />
          <Button title="Send" onPress={handleSend} loading={send.isPending} size="sm" />
        </View>
        <View style={styles.aiRow}>
          <Button
            title="AI Rewrite"
            variant="outline"
            size="sm"
            onPress={() => handleAIAssist('rewrite_professional')}
            loading={aiAssist.isPending}
          />
          <Button
            title="AI Summarize"
            variant="outline"
            size="sm"
            onPress={() => handleAIAssist('summarize')}
            loading={aiAssist.isPending}
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  list: { padding: theme.spacing.md, paddingBottom: theme.spacing.sm, flexGrow: 1 },
  listEmpty: { flex: 1, justifyContent: 'center' },
  bubble: { maxWidth: '82%', padding: 14, borderRadius: theme.radius.lg, marginBottom: 10 },
  bubbleMe: { alignSelf: 'flex-end', backgroundColor: theme.colors.secondary, borderBottomRightRadius: 4 },
  bubbleOther: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    borderBottomLeftRadius: 4,
  },
  sender: { fontSize: 12, fontWeight: '700', color: theme.colors.secondary, marginBottom: 4 },
  body: { color: theme.colors.text, lineHeight: 22, fontSize: 15 },
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
  aiRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    maxHeight: 100,
    color: theme.colors.text,
    fontSize: 15,
    backgroundColor: theme.colors.surfaceSecondary,
  },
  error: { color: theme.colors.error, fontSize: 13, marginBottom: 8 },
});
