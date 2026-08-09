import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';
import type { IncidentReportingView } from '../lib/models';

function stamp(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

export function IncidentsPage({ data }: { data: IncidentReportingView }) {
  return <>
    <div className="page-heading">
      <div><span className="eyebrow">Operational observability</span><h2>Alerts & Incident Center</h2><p>Deterministic journal-backed alert deduplication, severity escalation, acknowledgement and resolution. Phase 02 uses the local console only; no paid notification delivery is required.</p></div>
      <StatusBadge value={data.status} />
    </div>
    <div className="fixture-banner">{data.notice}</div>
    <section className="kpi-grid">
      <KpiCard label="Active incidents" value={data.summary.active_incident_count} detail={`${data.summary.open_incident_count} open · ${data.summary.acknowledged_incident_count} acknowledged`} />
      <KpiCard label="Critical" value={data.summary.active_by_severity.CRITICAL ?? 0} detail="Active synthetic incidents" />
      <KpiCard label="Alert records" value={data.summary.total_alert_count} detail="Deduplicated alert identities" />
      <KpiCard label="Paid notification" value={data.paid_notification_dependency ? 'Required' : 'Not required'} detail={data.live_notification_delivery_enabled ? 'Delivery enabled' : 'Local console only'} />
    </section>
    <div className="incident-grid">
      {data.incidents.map((incident) => <section className="panel incident-card" key={incident.incident_id}>
        <div className="incident-head"><div><span className="eyebrow">{incident.incident_key}</span><h3>{incident.alerts[0]?.title ?? 'Incident'}</h3></div><div className="incident-badges"><StatusBadge value={incident.severity} /><StatusBadge value={incident.status} /></div></div>
        <div className="incident-meta"><span>Opened {stamp(incident.opened_at)}</span><code>{incident.incident_id.slice(0, 14)}…</code></div>
        {incident.alerts.map((alert) => <div className="incident-alert" key={alert.alert_id}><div><strong>{alert.rule_id.replaceAll('_',' ')}</strong><span>{alert.detail}</span></div><div><StatusBadge value={alert.severity} /><small>{alert.occurrence_count} occurrence{alert.occurrence_count === 1 ? '' : 's'}</small></div></div>)}
        {incident.status === 'ACKNOWLEDGED' ? <div className="incident-note"><span className="eyebrow">Acknowledged</span><strong>{incident.acknowledged_by}</strong><p>{incident.acknowledgement_note}</p></div> : null}
        {incident.status === 'RESOLVED' ? <div className="incident-note"><span className="eyebrow">Resolution</span><strong>{incident.resolved_by}</strong><p>{incident.resolution}</p></div> : null}
      </section>)}
    </div>
    <section className="panel" style={{marginTop:16}}><span className="eyebrow">Delivery boundary</span><h3>Local incident visibility only</h3><div className="boundary-row"><span className="boundary-dot"/><span>Channels: {data.delivery_channels.join(', ')}</span></div><div className="boundary-row"><span className="boundary-dot"/><span>No external notification credentials are stored or required in PF09.</span></div><div className="boundary-row"><span className="boundary-dot"/><span>Journal head: <code>{data.summary.journal_head_hash.slice(0,18)}…</code></span></div></section>
  </>;
}
