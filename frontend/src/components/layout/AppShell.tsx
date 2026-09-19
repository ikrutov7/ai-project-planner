import { useRef, useState, type ReactNode } from 'react';
import { StatusBadge } from '../ui/StatusBadge';
import type { BackendStatus } from '../../api/useHealth';
import styles from './AppShell.module.css';

type Props = {
  title: string;
  subtitle: string;
  backendStatus: BackendStatus;
  backendDetail: string;
  planName?: string;
  planVersion?: number;
  busy?: boolean;
  error?: string | null;
  onImport: (file: File) => void;
  onExport: () => void;
  onReset: () => void;
  gantt: ReactNode;
  chat: ReactNode;
};

export function AppShell({
  title,
  subtitle,
  backendStatus,
  backendDetail,
  planName,
  planVersion,
  busy,
  error,
  onImport,
  onExport,
  onReset,
  gantt,
  chat,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [toast, setToast] = useState<string | null>(null);

  return (
    <div className={styles.shell}>
      <div className={styles.atmosphere} aria-hidden />
      <header className={styles.header}>
        <div className={styles.brandBlock}>
          <p className={styles.brand}>PLANFORGE</p>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>
            {subtitle}
            {planName ? ` · ${planName} v${planVersion}` : ''}
          </p>
        </div>
        <div className={styles.actions}>
          <StatusBadge status={backendStatus} label={backendDetail} />
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onImport(file);
              e.target.value = '';
            }}
          />
          <button type="button" className={styles.btn} disabled={busy} onClick={() => fileRef.current?.click()}>
            Import Excel
          </button>
          <button type="button" className={styles.btn} disabled={busy} onClick={onExport}>
            Export Excel
          </button>
          <button
            type="button"
            className={`${styles.btn} ${styles.ghost}`}
            disabled={busy}
            onClick={() => {
              onReset();
              setToast('Seed plan restored');
              setTimeout(() => setToast(null), 2500);
            }}
          >
            Reset seed
          </button>
        </div>
      </header>

      {(error || toast) && (
        <div className={styles.banner} role="status">
          {error || toast}
        </div>
      )}

      <main className={styles.main}>
        <section className={styles.panel} aria-label="Gantt chart">
          {gantt}
        </section>
        <div className={styles.sidebar}>{chat}</div>
      </main>
    </div>
  );
}
