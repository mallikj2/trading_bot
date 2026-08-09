import { useEffect, useState } from 'react';
import { researchApi } from './lib/api';
import type { AuditView, DataHealthView, GateView, OverviewView, PortfolioView, RiskView, StrategyValidationView, TradeLeadView, WatchlistView, ExperimentReportingView } from './lib/models';
import { OverviewPage } from './pages/OverviewPage';
import { LeadsPage } from './pages/LeadsPage';
import { WatchlistPage } from './pages/WatchlistPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { RiskPage } from './pages/RiskPage';
import { DataHealthPage, GatesPage } from './pages/GovernancePage';
import { AuditPage } from './pages/AuditPage';
import { ValidationPage } from './pages/ValidationPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import './styles.css';

type Page = 'overview' | 'leads' | 'watchlist' | 'portfolio' | 'risk' | 'validation' | 'experiments' | 'gates' | 'health' | 'audit';

const NAV: Array<[Page, string]> = [
  ['overview','Overview'], ['leads','Trade Leads'], ['watchlist','Watchlist'], ['portfolio','Portfolio'],
  ['risk','Risk'], ['validation','Validation'], ['experiments','Experiments'], ['gates','Phase Gates'], ['health','Data Health'], ['audit','Audit Trail']
];

export default function App() {
  const [page, setPage] = useState<Page>('overview');
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<OverviewView | null>(null);
  const [leads, setLeads] = useState<TradeLeadView[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistView[]>([]);
  const [gates, setGates] = useState<GateView[]>([]);
  const [health, setHealth] = useState<DataHealthView[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioView | null>(null);
  const [risk, setRisk] = useState<RiskView | null>(null);
  const [audit, setAudit] = useState<AuditView[]>([]);
  const [validation, setValidation] = useState<StrategyValidationView | null>(null);
  const [experiments, setExperiments] = useState<ExperimentReportingView | null>(null);

  useEffect(() => {
    Promise.all([
      researchApi.overview(), researchApi.leads(), researchApi.watchlist(), researchApi.gates(),
      researchApi.dataHealth(), researchApi.portfolio(), researchApi.risk(), researchApi.audit(), researchApi.strategyValidation(), researchApi.experiments()
    ]).then(([o,l,w,g,h,p,r,a,v,e]) => { setOverview(o); setLeads(l); setWatchlist(w); setGates(g); setHealth(h); setPortfolio(p); setRisk(r); setAudit(a); setValidation(v); setExperiments(e); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to read research API'));
  }, []);

  return <div className="app-shell"><aside><div className="brand"><div className="brand-mark">QT</div><div><strong>Quant Platform</strong><span>Research Console</span></div></div><nav>{NAV.map(([key,label]) => <button key={key} className={page === key ? 'active' : ''} onClick={() => setPage(key)}>{label}</button>)}</nav><div className="side-footer"><span>PHASE 02</span><strong>READ ONLY</strong><small>No broker connectivity</small></div></aside><main><header><div><span className="system-dot" /> Local research environment</div><div className="header-meta"><span>CSMOM-LS v0.2</span><strong>Phase 03 locked</strong></div></header><div className="content">{error ? <div className="error-panel">{error}</div> : !overview ? <div className="loading">Loading deterministic research state…</div> : page === 'overview' ? <OverviewPage overview={overview} gates={gates} health={health} /> : page === 'leads' ? <LeadsPage leads={leads} /> : page === 'watchlist' ? <WatchlistPage entries={watchlist} /> : page === 'portfolio' && portfolio ? <PortfolioPage data={portfolio} /> : page === 'risk' && risk ? <RiskPage data={risk} /> : page === 'validation' && validation ? <ValidationPage data={validation} /> : page === 'experiments' && experiments ? <ExperimentsPage data={experiments} /> : page === 'gates' ? <GatesPage gates={gates} /> : page === 'health' ? <DataHealthPage health={health} /> : <AuditPage records={audit} />}</div></main></div>;
}
