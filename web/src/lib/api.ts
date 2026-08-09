import type { AuditView, DataHealthView, GateView, OverviewView, PortfolioView, RiskView, StrategyValidationView, TradeLeadView, WatchlistView, ExperimentReportingView, IncidentReportingView } from './models';

const API = '/api/v1';

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) throw new Error(`Read failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const researchApi = {
  overview: () => readJson<OverviewView>('/overview'),
  leads: () => readJson<TradeLeadView[]>('/leads'),
  watchlist: () => readJson<WatchlistView[]>('/watchlist'),
  portfolio: () => readJson<PortfolioView>('/portfolio'),
  risk: () => readJson<RiskView>('/risk'),
  gates: () => readJson<GateView[]>('/gates'),
  dataHealth: () => readJson<DataHealthView[]>('/data-health'),
  audit: () => readJson<AuditView[]>('/audit'),
  strategyValidation: () => readJson<StrategyValidationView>('/strategy-validation'),
  experiments: () => readJson<ExperimentReportingView>('/experiments'),
  incidents: () => readJson<IncidentReportingView>('/incidents')
};
