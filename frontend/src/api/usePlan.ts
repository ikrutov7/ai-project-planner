import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteTask,
  exportExcel,
  importExcel,
  moveTask,
  patchTask,
  resetPlan,
  sendChat,
  setDependencies,
  fetchPlan,
} from './client';
import type { Plan } from '../domain/types';

export const planKey = ['plan'] as const;

export function usePlan() {
  return useQuery({
    queryKey: planKey,
    queryFn: fetchPlan,
  });
}

export function usePlanMutations() {
  const qc = useQueryClient();

  const setPlan = (plan: Plan) => {
    qc.setQueryData(planKey, plan);
  };

  const reset = useMutation({
    mutationFn: resetPlan,
    onSuccess: setPlan,
  });

  const patch = useMutation({
    mutationFn: ({ taskId, body }: { taskId: string; body: Record<string, unknown> }) =>
      patchTask(taskId, body),
    onSuccess: (data) => setPlan(data.plan),
  });

  const move = useMutation({
    mutationFn: ({ taskId, date }: { taskId: string; date: string }) => moveTask(taskId, date),
    onSuccess: (data) => setPlan(data.plan),
  });

  const deps = useMutation({
    mutationFn: ({ taskId, predecessorIds }: { taskId: string; predecessorIds: string[] }) =>
      setDependencies(taskId, predecessorIds),
    onSuccess: (data) => setPlan(data.plan),
  });

  const remove = useMutation({
    mutationFn: (taskId: string) => deleteTask(taskId),
    onSuccess: (data) => setPlan(data.plan),
  });

  const importFile = useMutation({
    mutationFn: (file: File) => importExcel(file),
    onSuccess: (data) => setPlan(data.plan),
  });

  const chat = useMutation({
    mutationFn: ({ message, conversationId }: { message: string; conversationId?: string | null }) =>
      sendChat(message, conversationId),
    onSuccess: (data) => setPlan(data.plan),
  });

  const download = async () => {
    const blob = await exportExcel();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'plan.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };

  return { setPlan, reset, patch, move, deps, remove, importFile, chat, download };
}
