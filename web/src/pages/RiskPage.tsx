import type { RiskView } from '../lib/models';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';

export function RiskPage({ data }: { data: RiskView }) {
  return <section><div className="page-heading"><div><span className="eyebrow">Safety boundary</span><h2>Risk</h2><p>PF02 exposes runtime constraints only; strategy protections and state transitions arrive in PF04.</p></div><StatusBadge value={data.runtime_state} /></div><div className="kpi-grid"><KpiCard label="New risk" value={data.new_risk_allowed ? 'Allowed' : 'Blocked'} detail={data.reason} /><KpiCard label="Long positions" value={data.position_counts.long} /><KpiCard label="Short positions" value={data.position_counts.short} /><KpiCard label="Broker" value="Disconnected" detail="By design" /></div><div className="panel"><div className="panel-title"><h3>Hard boundaries</h3></div>{data.hard_boundaries.map((boundary) => <div className="boundary-row" key={boundary}><span className="boundary-dot" /><strong>{boundary.replaceAll('_',' ')}</strong></div>)}</div></section>;
}
