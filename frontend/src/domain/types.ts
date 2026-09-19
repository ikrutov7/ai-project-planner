export type TaskStatus = 'pending' | 'in_progress' | 'done' | 'blocked';

export type Assignee = {
  id: string;
  name: string;
  created_at: string;
};

export type Task = {
  id: string;
  plan_id: string;
  name: string;
  description: string;
  assignee_id: string | null;
  start_date: string;
  duration: number;
  end_date: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  predecessor_ids: string[];
};

export type Plan = {
  id: string;
  name: string;
  project_start: string;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  tasks: Task[];
  assignees: Assignee[];
};

export type ChatResponse = {
  conversation_id: string;
  message: { role: string; content: string };
  plan: Plan;
  changes: Array<Record<string, unknown>>;
  tool_trace: Array<Record<string, unknown>>;
  mode: string;
};

export type ApiError = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};
