import type { AuditView } from '../lib/models';

export function AuditPage({ records }: { records: AuditView[] }) {
  return <section><div className="page-heading"><div><span className="eyebrow">Provenance</span><h2>Audit trail</h2><p>Every visible lead links back to an immutable research content hash.</p></div></div><div className="timeline">{records.map((row) => <article className="timeline-row" key={`${row.occurred_at}-${row.entity_id}`}><span className="timeline-dot" /><div><span className="eyebrow">{new Date(row.occurred_at).toLocaleString()} · {row.category}</span><strong>{row.summary}</strong><code>{row.provenance_hash.slice(0,20)}…</code></div></article>)}</div></section>;
}
