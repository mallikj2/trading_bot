export type Direction = 'LONG' | 'SHORT';

export interface LeadReason {
  code: string;
  detail: string;
  available_at: string;
  blocking: boolean;
}

export interface TradeLeadView {
  lead_id: string;
  symbol: string;
  decision_symbol: string;
  direction: Direction;
  score: string;
  state: string;
  trend_state: string;
  volatility_state: string;
  earnings_state: string;
  cost_state: string;
  borrow_state: string;
  estimated_spread_bps: string | null;
  estimated_cost_bps: string | null;
  proposed_weight: string | null;
  proposed_shares: number | null;
  decision_at: string;
  valid_until: string;
  strategy_id: string;
  strategy_version: string;
  reasons: LeadReason[];
  immutable_hash: string;
  content_hash: string;
}

export interface WatchlistView {
  lead_id: string;
  symbol: string;
  direction: Direction;
  state: string;
  score: string;
  blocking_reasons: LeadReason[];
  qualification_actions: string[];
  valid_until: string;
}

export interface OverviewView {
  generated_at: string;
  environment: string;
  runtime_state: string;
  phase: string;
  phase03_authorized: boolean;
  procurement_authorized: boolean;
  lead_counts: Record<string, number>;
  portfolio: {
    position_count: number;
    gross_market_value: string;
    net_market_value: string;
  };
  gate_summary: { total: number; blocked_or_nonpass: number };
  data_health_summary: { total: number; nonpass: number };
  fixture_notice: string;
}

export interface GateView {
  gate_id: string;
  name: string;
  status: string;
  category: string;
}

export interface DataHealthView {
  component: string;
  status: string;
  freshness: string;
  detail: string;
}

export interface PortfolioPositionView {
  symbol: string;
  side: 'LONG' | 'SHORT';
  shares: number;
  market_value: string;
  unrealized_pnl: string;
  sector: string;
  holding_sessions: number;
  source: string;
}

export interface PortfolioView {
  mode: string;
  positions: PortfolioPositionView[];
  warning: string;
}

export interface RiskView {
  runtime_state: string;
  new_risk_allowed: boolean;
  reason: string;
  position_counts: { long: number; short: number };
  hard_boundaries: string[];
}

export interface AuditView {
  occurred_at: string;
  category: string;
  entity_id: string;
  summary: string;
  provenance_hash: string;
}
