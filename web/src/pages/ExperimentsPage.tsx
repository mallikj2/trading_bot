import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';
import type { ExperimentReportingView } from '../lib/models';

function bps(value: string): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return '—';
  return `${parsed > 0 ? '+' : ''}${parsed.toFixed(0)} bps`;
}

export function ExperimentsPage({ data }: { data: ExperimentReportingView }) {
  const baseline = data.experiments.find((row) => row.run.run_id === data.comparison.baseline_run_id) ?? data.experiments[0];
  return <>
    <div className="page-heading"><div><span className="eyebrow">Research lineage</span><h2>Experiments & Attribution</h2><p>Immutable synthetic experiment records, provenance, scenario comparison, and cost/long-short attribution. These are reporting fixtures, not Phase 03 performance evidence.</p></div><StatusBadge value={data.status} /></div>
    <div className="fixture-banner">{data.notice}</div>
    <section className="kpi-grid">
      <KpiCard label="Registered runs" value={data.experiments.length} detail="Immutable PF08 fixtures" />
      <KpiCard label="Acceptance evidence" value={data.phase03_acceptance_backtest ? 'YES' : 'NO'} detail="Phase 03 remains locked" />
      <KpiCard label="Profitability validated" value={data.strategy_profitability_validated ? 'YES' : 'NO'} detail="PF08 cannot make this claim" />
      <KpiCard label="Baseline net" value={baseline ? bps(baseline.run.metrics.net_return_bps) : '—'} detail="Synthetic illustration only" />
    </section>
    <section className="table-shell"><table><thead><tr><th>Scenario</th><th>Evidence</th><th>Net</th><th>Drawdown</th><th>Sharpe</th><th>Costs</th><th>Lineage</th></tr></thead><tbody>{data.experiments.map(({definition,run,label}) => <tr key={run.run_id}><td><strong>{definition.scenario.replaceAll('_',' ')}</strong><small>{definition.strategy_id} v{definition.strategy_version}</small></td><td><StatusBadge value={run.evidence_class} /><small>{label}</small></td><td className="mono">{bps(run.metrics.net_return_bps)}</td><td className="mono">{bps(run.metrics.max_drawdown_bps)}</td><td className="mono">{run.metrics.sharpe}</td><td className="mono">{bps(run.attribution.total_cost_bps)}</td><td><small className="mono">run {run.run_id.slice(0,10)}…</small><small className="mono">result {run.result_hash.slice(0,10)}…</small></td></tr>)}</tbody></table></section>
    {baseline ? <div className="two-col" style={{marginTop:16}}><section className="panel"><span className="eyebrow">Baseline attribution</span><h3>{baseline.definition.scenario.replaceAll('_',' ')}</h3><div className="governance-row"><div><strong>Long contribution</strong><span>Research-side contribution</span></div><div className="mono">{bps(baseline.run.attribution.long_contribution_bps)}</div></div><div className="governance-row"><div><strong>Short contribution</strong><span>Research-side contribution</span></div><div className="mono">{bps(baseline.run.attribution.short_contribution_bps)}</div></div>{Object.entries(baseline.run.attribution.cost_components_bps).map(([name,value]) => <div className="governance-row" key={name}><div><strong>{name.replaceAll('_',' ')}</strong><span>Cost drag</span></div><div className="mono">{bps(value)}</div></div>)}</section><section className="panel"><span className="eyebrow">Comparison policy</span><h3>No automatic winner</h3><p style={{color:'#8fa6b4',lineHeight:1.6}}>PF08 records scenario deltas but does not optimize parameters, select a winner, or claim alpha. Phase 03 will define the acceptance comparison set under preregistered rules.</p><div className="boundary-row"><span className="boundary-dot"/><span>Comparison hash: <code>{data.comparison.comparison_hash.slice(0,18)}…</code></span></div><div className="boundary-row"><span className="boundary-dot"/><span>Baseline run: <code>{data.comparison.baseline_run_id.slice(0,18)}…</code></span></div></section></div> : null}
  </>;
}
