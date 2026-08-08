import type { DataHealthView, GateView, OverviewView } from '../lib/models';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';

export function OverviewPage({ overview, gates, health }: { overview: OverviewView; gates: GateView[]; health: DataHealthView[] }) {
  return (
    <section>
      <div className="page-heading">
        <div><span className="eyebrow">Command center</span><h2>Research overview</h2></div>
        <StatusBadge value={overview.runtime_state} />
      </div>
      <div className="fixture-banner">{overview.fixture_notice}</div>
      <div className="kpi-grid">
        <KpiCard label="Visible leads" value={Object.values(overview.lead_counts).reduce((a, b) => a + b, 0)} detail="fixture-backed" />
        <KpiCard label="Research positions" value={overview.portfolio.position_count} detail={`Gross $${overview.portfolio.gross_market_value}`} />
        <KpiCard label="Non-pass gates" value={overview.gate_summary.blocked_or_nonpass} detail={`${overview.gate_summary.total} shown`} />
        <KpiCard label="Data health" value={overview.data_health_summary.nonpass === 0 ? 'PASS' : `${overview.data_health_summary.nonpass} attention`} />
      </div>
      <div className="two-col">
        <div className="panel"><div className="panel-title"><h3>Phase gates</h3></div>{gates.map((gate) => <div className="list-row" key={gate.gate_id}><div><strong>{gate.gate_id}</strong><span>{gate.name}</span></div><StatusBadge value={gate.status} /></div>)}</div>
        <div className="panel"><div className="panel-title"><h3>Data health</h3></div>{health.map((item) => <div className="list-row" key={item.component}><div><strong>{item.component}</strong><span>{item.detail}</span></div><StatusBadge value={item.status} /></div>)}</div>
      </div>
    </section>
  );
}
