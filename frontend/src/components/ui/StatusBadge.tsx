import type { BackendStatus } from '../../api/useHealth';
import styles from './StatusBadge.module.css';

type StatusBadgeProps = {
  status: BackendStatus;
  label: string;
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[status]}`} title={label}>
      {label}
    </span>
  );
}
