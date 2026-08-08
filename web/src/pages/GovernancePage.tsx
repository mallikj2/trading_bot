import type { DataHealthView, GateView } from '../lib/models';
import { StatusBadge } from '../components/StatusBadge';

export function GatesPage({ gates }: { gates: GateView[] }) {
  return <section><div className="page-heading"><div><span className="eyebrow">Governance</span><h2>Phase gates</h2><p>Visible evidence boundaries. Non-pass mandatory gates continue to block later-phase authorization.</p></div></div><div className="panel">{gates.map((gate) => <div className="governance-row" key={gate.gate_id}><div><strong>{gate.gate_id}</strong><span>{gate.name}</span></div><div><small>{gate.category}</small><StatusBadge value={gate.status} /></div></div>)}</div></section>;
}

export function DataHealthPage({ health }: { health: DataHealthView[] }) {
  return <section><div className="page-heading"><div><span className="eyebrow">Operations</span><h2>Data health</h2><p>Read-only readiness of fixture, provider, and broker boundaries.</p></div></div><div className="card-grid">{health.map((row) => <article className="watch-card" key={row.component}><div className="watch-top"><div><strong>{row.component}</strong><span>{row.freshness}</span></div><StatusBadge value={row.status} /></div><p>{row.detail}</p></article>)}</div></section>;
}
