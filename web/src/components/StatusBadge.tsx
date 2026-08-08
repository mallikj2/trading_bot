import { statusClass } from '../lib/selectors';

export function StatusBadge({ value }: { value: string }) {
  return <span className={`status status-${statusClass(value)}`}>{value.replaceAll('_', ' ')}</span>;
}
