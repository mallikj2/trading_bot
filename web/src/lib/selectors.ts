import type { Direction, TradeLeadView, WatchlistView } from './models.js';

export function numericScore(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function rankLeads(leads: TradeLeadView[]): TradeLeadView[] {
  return [...leads].sort((a, b) => {
    const magnitude = Math.abs(numericScore(b.score)) - Math.abs(numericScore(a.score));
    return magnitude !== 0 ? magnitude : a.symbol.localeCompare(b.symbol);
  });
}

export function filterDirection<T extends { direction: Direction }>(rows: T[], direction: Direction | 'ALL'): T[] {
  return direction === 'ALL' ? rows : rows.filter((row) => row.direction === direction);
}

export function watchlistHeadline(entry: WatchlistView): string {
  const blocker = entry.blocking_reasons[0];
  return blocker ? blocker.detail : 'Await the next deterministic strategy decision cycle.';
}

export function statusClass(status: string): 'good' | 'warn' | 'bad' | 'neutral' {
  if (['PASS', 'OK', 'QUALIFIED'].includes(status)) return 'good';
  if (['IN_PROGRESS', 'WATCHLIST', 'RESEARCH_ONLY'].includes(status)) return 'warn';
  if (['BLOCKED', 'FAILED', 'HALTED'].includes(status)) return 'bad';
  return 'neutral';
}
