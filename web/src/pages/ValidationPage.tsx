import type { StrategyValidationView } from '../lib/models';

export function ValidationPage({ data }: { data: StrategyValidationView }) {
  return <section>
    <div className="page-heading"><div><span className="eyebrow">PF05</span><h1>Strategy Validation</h1><p>Future-leakage and recursive-stability controls for the frozen research strategy.</p></div><span className={`status ${data.status === 'PASS' ? 'good' : 'bad'}`}>{data.status}</span></div>
    <div className="metric-grid">
      <article className="metric-card"><span>Lookahead</span><strong>{data.lookahead.status}</strong><small>{data.lookahead.difference_count} differences</small></article>
      <article className="metric-card"><span>Recursive</span><strong>{data.recursive.status}</strong><small>{data.recursive.difference_count} differences</small></article>
      <article className="metric-card"><span>Warm-ups</span><strong>{data.recursive.warmup_sessions.join(' / ')}</strong><small>sessions</small></article>
      <article className="metric-card"><span>Phase 03</span><strong>{data.live_acceptance_backtest_validated ? 'VALIDATED' : 'LOCKED'}</strong><small>PF05 does not authorize backtesting</small></article>
    </div>
    <div className="panel"><h2>Contamination controls</h2><table><thead><tr><th>Control</th><th>Expected result</th></tr></thead><tbody>{Object.entries(data.contaminated_controls).map(([key,value]) => <tr key={key}><td>{key.replaceAll('_',' ')}</td><td><span className="status good">{value}</span></td></tr>)}</tbody></table></div>
    <div className="notice">{data.notice}</div>
  </section>;
}
