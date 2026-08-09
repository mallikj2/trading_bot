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
  procurement_ready_for_manual_approval: boolean;
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

export interface ProtectionDecisionView {
  protection_id: string;
  scope: string;
  evaluated_at: string;
  required_state: string;
  reason_code: string;
  detail: string;
  observation_hash: string | null;
  active: boolean;
}

export interface RiskView {
  runtime_state: string;
  new_risk_allowed: boolean;
  reason: string;
  runtime_blocks_new_risk: boolean;
  runtime_recovery_required: boolean;
  runtime_permissions: {
    simulate_increase_exposure: boolean;
    reduce_exposure: boolean;
    cancel_open_orders: boolean;
    mutate_broker: boolean;
  };
  protections: ProtectionDecisionView[];
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


export interface StrategyValidationView {
  mode: string;
  strategy_id: string;
  status: string;
  lookahead: { status: string; difference_count: number; method: string };
  recursive: { status: string; difference_count: number; warmup_sessions: number[] };
  contaminated_controls: Record<string, string>;
  live_acceptance_backtest_validated: boolean;
  notice: string;
}

export interface ExperimentDefinitionView {
  definition_id: string;
  name: string;
  strategy_id: string;
  strategy_version: string;
  scenario: string;
  purpose: string;
  code_commit: string;
  dataset_manifest_hash: string;
  universe_manifest_hash: string;
  parameter_manifest_hash: string;
  cost_model_version: string;
  acceptance_start: string;
  acceptance_end: string;
  random_seed: number;
}

export interface ExperimentAttributionView {
  long_contribution_bps: string;
  short_contribution_bps: string;
  gross_return_bps: string;
  cost_components_bps: Record<string, string>;
  total_cost_bps: string;
  net_return_bps: string;
}

export interface ExperimentRunView {
  run_id: string;
  result_hash: string;
  definition_id: string;
  evidence_class: string;
  started_at: string;
  completed_at: string;
  source_runtime_hash: string;
  metrics: Record<string, string>;
  attribution: ExperimentAttributionView;
  artifact_hashes: Record<string, string>;
}

export interface ExperimentComparisonRowView {
  run_id: string;
  evidence_class: string;
  net_return_bps: string;
  delta_net_return_bps: string;
  max_drawdown_bps: string;
  delta_max_drawdown_bps: string;
  sharpe: string;
  delta_sharpe: string;
  turnover_bps: string;
  delta_turnover_bps: string;
  total_cost_bps: string;
  delta_total_cost_bps: string;
}

export interface ExperimentReportingView {
  mode: string;
  status: string;
  strategy_profitability_validated: boolean;
  phase03_acceptance_backtest: boolean;
  notice: string;
  experiments: Array<{ definition: ExperimentDefinitionView; run: ExperimentRunView; label: string }>;
  comparison: {
    baseline_run_id: string;
    rows: ExperimentComparisonRowView[];
    comparison_hash: string;
  };
}

export interface AlertIncidentAlertView {
  alert_id: string;
  fingerprint: string;
  incident_id: string;
  rule_id: string;
  component: string;
  entity_id: string;
  condition_key: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  status: 'OPEN' | 'RESOLVED';
  title: string;
  detail: string;
  evidence_hash: string;
  first_seen_at: string;
  last_seen_at: string;
  occurrence_count: number;
}

export interface IncidentView {
  incident_id: string;
  incident_key: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  opened_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  acknowledgement_note: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution: string | null;
  alerts: AlertIncidentAlertView[];
}

export interface IncidentReportingView {
  mode: string;
  status: string;
  summary: {
    active_incident_count: number;
    open_incident_count: number;
    acknowledged_incident_count: number;
    resolved_incident_count: number;
    active_by_severity: Record<string, number>;
    total_alert_count: number;
    journal_head_hash: string;
  };
  incidents: IncidentView[];
  delivery_channels: string[];
  paid_notification_dependency: boolean;
  live_notification_delivery_enabled: boolean;
  notice: string;
}


export interface RecoveryFindingView {
  code: string; severity: 'INFO' | 'WARNING' | 'CRITICAL'; entity_id: string; detail: string;
  disposition: 'AUTO_REPAIRED' | 'OBSERVED' | 'UNRESOLVED'; detected_at: string; evidence_hash: string; unresolved: boolean;
}

export interface RecoveryScenarioView {
  name: string; result: string; runtime_state: string; findings: RecoveryFindingView[]; report_hash: string;
}

export interface RecoveryReportingView {
  mode: string; status: string; real_broker_used: boolean; duplicate_risk_created: boolean;
  scenarios: RecoveryScenarioView[];
  acceptance: { crash_recovered_without_resubmit: boolean; unexplained_divergence_halts: boolean; incident_audit_generated: boolean; phase03_authorized: boolean; procurement_authorized: boolean };
  notice: string; fixture_hash: string;
}
