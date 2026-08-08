import type { PortfolioView } from '../lib/models';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';

export function PortfolioPage({ data }: { data: PortfolioView }) {
  const gross = data.positions.reduce((sum, row) => sum + Math.abs(Number(row.market_value)), 0);
  const pnl = data.positions.reduce((sum, row) => sum + Number(row.unrealized_pnl), 0);
  const longs = data.positions.filter((row) => row.side === 'LONG').length;
  const shorts = data.positions.filter((row) => row.side === 'SHORT').length;
  return <section><div className="page-heading"><div><span className="eyebrow">Research placeholder</span><h2>Portfolio</h2><p>{data.warning}</p></div><StatusBadge value="RESEARCH_ONLY" /></div><div className="kpi-grid"><KpiCard label="Positions" value={data.positions.length} detail={`${longs} long · ${shorts} short`} /><KpiCard label="Gross fixture value" value={`$${gross.toFixed(2)}`} /><KpiCard label="Fixture P&L" value={`${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`} /><KpiCard label="Mode" value="Synthetic" detail="No broker state" /></div><div className="table-shell"><table><thead><tr><th>Symbol</th><th>Side</th><th>Shares</th><th>Market value</th><th>Unrealized P&L</th><th>Sector</th><th>Holding</th></tr></thead><tbody>{data.positions.map((row) => <tr key={`${row.symbol}-${row.side}`}><td><strong>{row.symbol}</strong></td><td>{row.side}</td><td>{row.shares}</td><td className="mono">${Number(row.market_value).toFixed(2)}</td><td className="mono">{Number(row.unrealized_pnl) >= 0 ? '+' : ''}${Number(row.unrealized_pnl).toFixed(2)}</td><td>{row.sector}</td><td>{row.holding_sessions} sessions</td></tr>)}</tbody></table></div></section>;
}
