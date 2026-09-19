import type { Plan, Task } from '../../domain/types';
import styles from './GanttChart.module.css';

type Props = {
  plan: Plan;
  selectedId: string | null;
  onSelect: (task: Task) => void;
};

const DAY_MS = 86_400_000;
const PX_PER_DAY = 28;
const ROW_H = 36;
const LABEL_W = 220;

function daysBetween(a: string, b: string): number {
  const da = new Date(a + 'T00:00:00Z').getTime();
  const db = new Date(b + 'T00:00:00Z').getTime();
  return Math.round((db - da) / DAY_MS);
}

function addDays(iso: string, n: number): string {
  const d = new Date(iso + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function assigneeName(plan: Plan, id: string | null): string {
  if (!id) return 'Unassigned';
  return plan.assignees.find((a) => a.id === id)?.name ?? id;
}

function colorFor(assigneeId: string | null): string {
  if (!assigneeId) return 'var(--bar-muted)';
  let h = 0;
  for (let i = 0; i < assigneeId.length; i++) h = (h * 31 + assigneeId.charCodeAt(i)) % 360;
  return `hsl(${h} 42% 42%)`;
}

export function GanttChart({ plan, selectedId, onSelect }: Props) {
  const tasks = [...plan.tasks].sort((a, b) => a.start_date.localeCompare(b.start_date) || a.name.localeCompare(b.name));
  if (tasks.length === 0) {
    return <div className={styles.empty}>No tasks in plan</div>;
  }

  const minStart = tasks.reduce((m, t) => (t.start_date < m ? t.start_date : m), tasks[0].start_date);
  const maxEnd = tasks.reduce((m, t) => (t.end_date > m ? t.end_date : m), tasks[0].end_date);
  const span = Math.max(daysBetween(minStart, maxEnd) + 2, 14);
  const chartW = span * PX_PER_DAY;
  const chartH = tasks.length * ROW_H + 40;

  const ticks: string[] = [];
  for (let i = 0; i <= span; i += 7) {
    ticks.push(addDays(minStart, i));
  }

  const idToIndex = new Map(tasks.map((t, i) => [t.id, i]));

  return (
    <div className={styles.wrap}>
      <div className={styles.scroll}>
        <div className={styles.grid} style={{ width: LABEL_W + chartW }}>
          <div className={styles.labelCol} style={{ width: LABEL_W }}>
            <div className={styles.headCell}>Task</div>
            {tasks.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`${styles.labelRow} ${selectedId === t.id ? styles.selected : ''}`}
                onClick={() => onSelect(t)}
              >
                <span className={styles.taskName}>{t.name}</span>
                <span className={styles.meta}>{assigneeName(plan, t.assignee_id)}</span>
              </button>
            ))}
          </div>

          <div className={styles.chartCol} style={{ width: chartW }}>
            <div className={styles.timeline} style={{ width: chartW, height: 40 }}>
              {ticks.map((d) => {
                const x = daysBetween(minStart, d) * PX_PER_DAY;
                return (
                  <div key={d} className={styles.tick} style={{ left: x }}>
                    <span>{d.slice(5)}</span>
                  </div>
                );
              })}
            </div>

            <svg
              className={styles.svg}
              width={chartW}
              height={chartH - 40}
              role="img"
              aria-label="Gantt chart"
            >
              {Array.from({ length: Math.ceil(span / 7) + 1 }, (_, i) => i * 7).map((day) => (
                <line
                  key={day}
                  x1={day * PX_PER_DAY}
                  x2={day * PX_PER_DAY}
                  y1={0}
                  y2={tasks.length * ROW_H}
                  className={styles.gridLine}
                />
              ))}

              {tasks.flatMap((t, row) =>
                t.predecessor_ids.map((pid) => {
                  const predIdx = idToIndex.get(pid);
                  if (predIdx === undefined) return null;
                  const pred = tasks[predIdx];
                  const x1 = (daysBetween(minStart, pred.end_date) + 1) * PX_PER_DAY;
                  const y1 = predIdx * ROW_H + ROW_H / 2;
                  const x2 = daysBetween(minStart, t.start_date) * PX_PER_DAY;
                  const y2 = row * ROW_H + ROW_H / 2;
                  return (
                    <path
                      key={`${pid}-${t.id}`}
                      d={`M ${x1} ${y1} C ${x1 + 12} ${y1}, ${x2 - 12} ${y2}, ${x2} ${y2}`}
                      className={styles.dep}
                      fill="none"
                    />
                  );
                }),
              )}

              {tasks.map((t, row) => {
                const x = daysBetween(minStart, t.start_date) * PX_PER_DAY;
                const w = Math.max(t.duration * PX_PER_DAY - 4, 12);
                const y = row * ROW_H + 8;
                const selected = selectedId === t.id;
                return (
                  <g key={t.id} className={styles.barGroup} onClick={() => onSelect(t)} style={{ cursor: 'pointer' }}>
                    <rect
                      x={x}
                      y={y}
                      width={w}
                      height={ROW_H - 16}
                      rx={4}
                      fill={colorFor(t.assignee_id)}
                      className={selected ? styles.barSelected : styles.bar}
                    />
                    <text x={x + 8} y={y + 14} className={styles.barText}>
                      {t.duration}d
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
