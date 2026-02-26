import { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { streamChat, SSEEvent } from '../../lib/sse';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  streaming?: boolean;
}

const THEME = {
  bg: '#0a0e14',
  surface: '#141920',
  border: '#1e2530',
  green: '#33ff33',
  greenDim: '#1a8c1a',
  amber: '#ffb833',
  text: '#c5cdd8',
  muted: '#6b7a8d',
};

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: 'RigSherpa online. Ask me anything about your FZJ80 Land Cruiser.',
    },
  ]);
  const [input, setInput] = useState('');
  const [generating, setGenerating] = useState(false);
  const listRef = useRef<FlatList>(null);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || generating) return;

    setInput('');
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    const assistantId = (Date.now() + 1).toString();
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setGenerating(true);

    try {
      await streamChat(text, null, (event: SSEEvent) => {
        if (event.type === 'token') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + (event.token || '') } : m,
            ),
          );
        } else if (event.type === 'sources') {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, sources: event.sources } : m)),
          );
        } else if (event.type === 'done') {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)),
          );
        }
      });
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `Error: ${err.message}`, streaming: false }
            : m,
        ),
      );
    }

    setGenerating(false);
  }, [input, generating]);

  const renderMessage = ({ item }: { item: Message }) => (
    <View style={[styles.message, item.role === 'user' && styles.userMessage]}>
      <Text style={[styles.roleTag, item.role === 'user' ? styles.userTag : styles.assistantTag]}>
        {item.role === 'user' ? '>' : '<'}
      </Text>
      <View style={styles.messageContent}>
        <Text style={styles.messageText}>
          {item.content}
          {item.streaming && <Text style={styles.cursor}>_</Text>}
        </Text>
        {item.sources && item.sources.length > 0 && (
          <View style={styles.sources}>
            {item.sources.map((s: any, i: number) => (
              <View key={i} style={styles.sourceBadge}>
                <Text style={styles.sourceText}>
                  [{s.index}] {s.source.toUpperCase()}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <FlatList
        ref={listRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        style={styles.list}
        onContentSizeChange={() => listRef.current?.scrollToEnd()}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder={generating ? 'Generating...' : 'Ask about your FZJ80...'}
          placeholderTextColor={THEME.muted}
          editable={!generating}
          returnKeyType="send"
          onSubmitEditing={sendMessage}
        />
        <Pressable
          style={[styles.sendBtn, (!input.trim() || generating) && styles.sendBtnDisabled]}
          onPress={sendMessage}
          disabled={!input.trim() || generating}
        >
          <Text style={styles.sendBtnText}>{generating ? '...' : '>'}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: THEME.bg },
  list: { flex: 1, padding: 12 },
  message: { flexDirection: 'row', marginBottom: 12, gap: 8 },
  userMessage: {},
  roleTag: { fontSize: 14, fontWeight: '700', fontFamily: 'monospace', marginTop: 2 },
  userTag: { color: THEME.amber },
  assistantTag: { color: THEME.green },
  messageContent: { flex: 1 },
  messageText: { color: THEME.text, fontFamily: 'monospace', fontSize: 13, lineHeight: 20 },
  cursor: { color: THEME.green },
  sources: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 6 },
  sourceBadge: {
    backgroundColor: THEME.surface,
    borderColor: THEME.border,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  sourceText: { color: THEME.greenDim, fontFamily: 'monospace', fontSize: 10 },
  inputRow: {
    flexDirection: 'row',
    padding: 8,
    backgroundColor: THEME.surface,
    borderTopWidth: 1,
    borderTopColor: THEME.border,
    gap: 8,
  },
  input: {
    flex: 1,
    backgroundColor: THEME.bg,
    color: THEME.text,
    fontFamily: 'monospace',
    fontSize: 13,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: THEME.border,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  sendBtn: {
    backgroundColor: 'rgba(51,255,51,0.08)',
    borderColor: THEME.greenDim,
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 16,
    justifyContent: 'center',
  },
  sendBtnDisabled: { opacity: 0.4 },
  sendBtnText: { color: THEME.green, fontWeight: '700', fontFamily: 'monospace' },
});
