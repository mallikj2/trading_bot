import type { RecoveryReportingView } from '../lib/models';

export function RecoveryPage({ data }: { data: RecoveryReportingView }) {
  return <section><div className="page-heading"><div><span className="eyebrow">PF10</span><h1>Recovery & Reconciliation</h1><p>Crash and broker-divergence fixtures. Synthetic broker evidence only.</p></div><span className="status-badge pass">{data.status}</span></div>
    <div className="notice-panel"><strong>No real broker used.</strong> {data.notice}</div>
    <div className="card-grid">{data.scenarios.map(s => <article className="card" key={s.name}><div className="card-title"><strong>{s.name}</strong><span className={`status-badge ${s.result === 'RECOVERED' ? 'pass' : 'blocked'}`}>{s.result}</span></div><p>Runtime: <strong>{s.runtime_state}</strong></p><ul>{s.findings.map(f => <li key={`${f.code}-${f.evidence_hash}`}>{f.code}: {f.disposition}</li>)}</ul><small>{s.report_hash.slice(0, 18)}…</small></article>)}</div>
    <div className="panel"><h2>Acceptance evidence</h2><table><tbody>{Object.entries(data.acceptance).map(([k,v]) => <tr key={k}><td>{k.replaceAll('_',' ')}</td><td><strong>{String(v)}</strong></td></tr>)}</tbody></table></div>
  </section>;
}
