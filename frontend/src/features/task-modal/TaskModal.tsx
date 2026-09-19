import { useMemo, useState, type FormEvent } from 'react';
import type { Plan, Task } from '../../domain/types';
import styles from './TaskModal.module.css';

type Props = {
  plan: Plan;
  task: Task;
  onClose: () => void;
  onSave: (body: Record<string, unknown>) => Promise<void>;
  onDeps: (predecessorIds: string[]) => Promise<void>;
  onDelete: () => Promise<void>;
};

export function TaskModal({ plan, task, onClose, onSave, onDeps, onDelete }: Props) {
  const [name, setName] = useState(task.name);
  const [description, setDescription] = useState(task.description);
  const [duration, setDuration] = useState(task.duration);
  const [assigneeId, setAssigneeId] = useState(task.assignee_id ?? '');
  const [startDate, setStartDate] = useState(task.start_date);
  const [preds, setPreds] = useState<string[]>(task.predecessor_ids);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const others = useMemo(() => plan.tasks.filter((t) => t.id !== task.id), [plan.tasks, task.id]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSave({
        name,
        description,
        duration_days: duration,
        start_date: startDate,
        clear_assignee: !assigneeId,
        assignee: assigneeId
          ? plan.assignees.find((a) => a.id === assigneeId)?.name ?? assigneeId
          : null,
      });
      await onDeps(preds);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Delete «${task.name}»?`)) return;
    setBusy(true);
    try {
      await onDelete();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
      setBusy(false);
    }
  };

  return (
    <div className={styles.backdrop} role="presentation" onClick={onClose}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="task-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>{task.id}</p>
            <h2 id="task-modal-title">Task details</h2>
          </div>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <form className={styles.form} onSubmit={submit}>
          <label>
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </label>
          <div className={styles.row}>
            <label>
              Start
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </label>
            <label>
              Duration (days)
              <input
                type="number"
                min={1}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </label>
          </div>
          <label>
            Assignee
            <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
              <option value="">Unassigned</option>
              {plan.assignees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend>Predecessors (FS)</legend>
            <div className={styles.preds}>
              {others.map((t) => {
                const checked = preds.includes(t.id);
                return (
                  <label key={t.id} className={styles.check}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setPreds((prev) =>
                          checked ? prev.filter((id) => id !== t.id) : [...prev, t.id],
                        )
                      }
                    />
                    {t.name}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div className={styles.meta}>
            <span>
              Scheduled {task.start_date} → {task.end_date}
            </span>
            <span>Status: {task.status}</span>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.actions}>
            <button type="button" className={styles.danger} onClick={remove} disabled={busy}>
              Delete
            </button>
            <div className={styles.spacer} />
            <button type="button" className={styles.ghost} onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button type="submit" disabled={busy}>
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
