export function KpiCard({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <article className="kpi-card">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}
