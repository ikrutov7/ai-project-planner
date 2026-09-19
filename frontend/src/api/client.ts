import type { ChatResponse, Plan, Task } from '../domain/types';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      if (body.error?.message) message = body.error.message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function fetchPlan(): Promise<Plan> {
  const response = await fetch('/api/plan');
  return parseJson<Plan>(response);
}

export async function resetPlan(): Promise<Plan> {
  const response = await fetch('/api/plan/reset', { method: 'POST' });
  return parseJson<Plan>(response);
}

export async function patchTask(
  taskId: string,
  body: Record<string, unknown>,
): Promise<{ task: Task; plan: Plan }> {
  const response = await fetch(`/api/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return parseJson(response);
}

export async function moveTask(taskId: string, newStartDate: string): Promise<{ task: Task; plan: Plan }> {
  const response = await fetch(`/api/tasks/${taskId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_start_date: newStartDate }),
  });
  return parseJson(response);
}

export async function setDependencies(
  taskId: string,
  predecessorIds: string[],
): Promise<{ task: Task; plan: Plan }> {
  const response = await fetch(`/api/tasks/${taskId}/dependencies`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ predecessor_ids: predecessorIds }),
  });
  return parseJson(response);
}

export async function deleteTask(taskId: string): Promise<{ plan: Plan }> {
  const response = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
  return parseJson(response);
}

export async function importExcel(file: File): Promise<{ plan: Plan }> {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch('/api/excel/import', { method: 'POST', body: form });
  return parseJson(response);
}

export async function exportExcel(): Promise<Blob> {
  const response = await fetch('/api/excel/export');
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export async function sendChat(message: string, conversationId?: string | null): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  return parseJson(response);
}

export type HealthResponse = {
  status: string;
  database: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch('/health');
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json() as Promise<HealthResponse>;
}
