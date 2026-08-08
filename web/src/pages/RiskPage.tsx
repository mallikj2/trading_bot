import type { RiskView } from '../lib/models';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';

function permission(value: boolean) { return value ? 'Allowed' : 'Blocked'; }

export function RiskPage({ data }: { data: RiskView }) {
  return <section>
    <div className="page-heading">
      <div>
        <span className="eyebrow">Runtime safety</span>
        <h2>Risk & Protections</h2>
        <p>PF04 separates operational safety from strategy alpha. Protections can restrict runtime permissions but cannot rewrite frozen CSMOM-LS-v0.2 signals.</p>
      </div>
      <StatusBadge value={data.runtime_state} />
    </div>
    <div className="kpi-grid">
      <KpiCard label="Runtime state" value={data.runtime_state} detail={data.runtime_recovery_required ? 'Recovery approval required' : 'No pending recovery'} />
      <KpiCard label="Simulated new risk" value={permission(data.runtime_permissions.simulate_increase_exposure)} detail="Runtime safety only" />
      <KpiCard label="Risk reduction" value={permission(data.runtime_permissions.reduce_exposure)} />
      <KpiCard label="Live broker mutation" value="Blocked" detail="Phase 02 hard boundary" />
    </div>
    <div className="two-col">
      <div className="panel">
        <div className="panel-title"><span className="eyebrow">Protection engine</span><h3>Current evaluations</h3></div>
        {data.protections.map((row) => <div className="governance-row" key={row.protection_id}>
          <div><strong>{row.protection_id.replaceAll('_',' ')}</strong><span>{row.detail}</span></div>
          <div><StatusBadge value={row.required_state} /><small>{row.scope}</small></div>
        </div>)}
      </div>
      <div className="panel">
        <div className="panel-title"><span className="eyebrow">Governance</span><h3>Hard boundaries</h3></div>
        <div className="list-row"><div><strong>Order authority</strong><span>{data.reason.replaceAll('_',' ')}</span></div><StatusBadge value="BLOCKED" /></div>
        <div className="list-row"><div><strong>Long / short fixture positions</strong><span>{data.position_counts.long} long · {data.position_counts.short} short</span></div><StatusBadge value="SYNTHETIC" /></div>
        {data.hard_boundaries.map((boundary) => <div className="boundary-row" key={boundary}><span className="boundary-dot" /><strong>{boundary.replaceAll('_',' ')}</strong></div>)}
      </div>
    </div>
  </section>;
}
