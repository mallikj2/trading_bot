import { useMemo, useState } from 'react';
import type { Direction, TradeLeadView } from '../lib/models';
import { filterDirection, rankLeads } from '../lib/selectors';
import { StatusBadge } from '../components/StatusBadge';

export function LeadsPage({ leads }: { leads: TradeLeadView[] }) {
  const [direction, setDirection] = useState<Direction | 'ALL'>('ALL');
  const rows = useMemo(() => filterDirection(rankLeads(leads), direction), [leads, direction]);
  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Signals</span><h2>Trade leads</h2><p>Deterministic Phase 02 research artifacts. No execution controls are present.</p></div></div>
      <div className="segmented">{(['ALL','LONG','SHORT'] as const).map((value) => <button className={direction === value ? 'active' : ''} key={value} onClick={() => setDirection(value)}>{value}</button>)}</div>
      <div className="table-shell"><table><thead><tr><th>Symbol</th><th>Side</th><th>Score</th><th>Trend</th><th>Spread</th><th>Cost</th><th>Status</th><th>Reason</th></tr></thead><tbody>{rows.map((lead) => <tr key={lead.lead_id}><td><strong>{lead.symbol}</strong><small>{lead.strategy_id} v{lead.strategy_version}</small></td><td>{lead.direction}</td><td className="mono">{lead.score}</td><td>{lead.trend_state.replaceAll('_',' ')}</td><td>{lead.estimated_spread_bps ?? '—'} bps</td><td>{lead.estimated_cost_bps ?? '—'} bps</td><td><StatusBadge value={lead.state} /></td><td>{lead.reasons[0]?.detail ?? 'All current research checks passed.'}</td></tr>)}</tbody></table></div>
    </section>
  );
}
