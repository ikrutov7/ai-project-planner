import { useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '../components/layout/AppShell';
import { useHealth } from '../api/useHealth';
import { usePlan, usePlanMutations } from '../api/usePlan';
import { GanttChart } from '../features/gantt/GanttChart';
import { ChatPanel, type UiMessage } from '../features/chat/ChatPanel';
import { TaskModal } from '../features/task-modal/TaskModal';
import type { Task } from '../domain/types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, refetchOnWindowFocus: false },
  },
});

function PlannerApp() {
  const health = useHealth();
  const planQuery = usePlan();
  const mutations = usePlanMutations();
  const [selected, setSelected] = useState<Task | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content:
        'План загружен. Можно править через чат: перенос, зависимости, исполнители, новые задачи. Без API-ключа работает demo-агент.',
    },
  ]);
  const [uiError, setUiError] = useState<string | null>(null);
  const [agentMode, setAgentMode] = useState('demo');

  const busy =
    planQuery.isLoading ||
    mutations.chat.isPending ||
    mutations.importFile.isPending ||
    mutations.reset.isPending;

  const modeHint = useMemo(() => {
    if (agentMode === 'llm') return 'LLM agent via MCP tools';
    if (agentMode === 'demo') return 'Demo agent (heuristic MCP tools)';
    return 'Agent mode unknown';
  }, [agentMode]);

  const onSend = async (text: string) => {
    setUiError(null);
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: 'user', content: text }]);
    try {
      const result = await mutations.chat.mutateAsync({ message: text, conversationId });
      setConversationId(result.conversation_id);
      setAgentMode(result.mode);
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', content: result.message.content },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Chat failed';
      setUiError(msg);
      setMessages((prev) => [...prev, { id: `e-${Date.now()}`, role: 'assistant', content: msg }]);
    }
  };

  return (
    <>
      <AppShell
        title="AI-native Gantt planner"
        subtitle="Seed plan · Excel · natural-language edits"
        backendStatus={health.status}
        backendDetail={health.detail}
        planName={planQuery.data?.name}
        planVersion={planQuery.data?.version}
        busy={busy}
        error={uiError || (planQuery.error instanceof Error ? planQuery.error.message : null)}
        onImport={async (file) => {
          setUiError(null);
          try {
            await mutations.importFile.mutateAsync(file);
          } catch (err) {
            setUiError(err instanceof Error ? err.message : 'Import failed');
          }
        }}
        onExport={async () => {
          try {
            await mutations.download();
          } catch (err) {
            setUiError(err instanceof Error ? err.message : 'Export failed');
          }
        }}
        onReset={async () => {
          setUiError(null);
          await mutations.reset.mutateAsync();
        }}
        gantt={
          planQuery.data ? (
            <GanttChart
              plan={planQuery.data}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
          ) : (
            <div style={{ padding: 32, color: 'var(--muted)' }}>
              {planQuery.isLoading ? 'Loading plan…' : 'No plan'}
            </div>
          )
        }
        chat={
          <ChatPanel messages={messages} busy={mutations.chat.isPending} modeHint={modeHint} onSend={onSend} />
        }
      />

      {selected && planQuery.data && (
        <TaskModal
          key={selected.id + planQuery.data.version}
          plan={planQuery.data}
          task={planQuery.data.tasks.find((t) => t.id === selected.id) ?? selected}
          onClose={() => setSelected(null)}
          onSave={async (body) => {
            await mutations.patch.mutateAsync({ taskId: selected.id, body });
          }}
          onDeps={async (predecessorIds) => {
            await mutations.deps.mutateAsync({ taskId: selected.id, predecessorIds });
          }}
          onDelete={async () => {
            await mutations.remove.mutateAsync(selected.id);
          }}
        />
      )}
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <PlannerApp />
    </QueryClientProvider>
  );
}
