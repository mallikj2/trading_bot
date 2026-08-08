import type { WatchlistView } from '../lib/models';
import { watchlistHeadline } from '../lib/selectors';
import { StatusBadge } from '../components/StatusBadge';

export function WatchlistPage({ entries }: { entries: WatchlistView[] }) {
  return <section><div className="page-heading"><div><span className="eyebrow">Near-misses & blocks</span><h2>Watchlist</h2><p>Why a candidate is not currently actionable and what a future decision would need to change.</p></div></div><div className="card-grid">{entries.map((entry) => <article className="watch-card" key={entry.lead_id}><div className="watch-top"><div><strong>{entry.symbol}</strong><span>{entry.direction} · score {entry.score}</span></div><StatusBadge value={entry.state} /></div><p>{watchlistHeadline(entry)}</p><div className="action-box"><span className="eyebrow">Next qualifying condition</span>{entry.qualification_actions.map((action) => <span key={action}>{action}</span>)}</div></article>)}</div></section>;
}
