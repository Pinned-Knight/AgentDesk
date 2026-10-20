type Props = { label: string; value: string; hint?: string };

export default function StatCard({ label, value, hint }: Props) {
  return (
    <div className="card stat">
      <div className="stat__label">{label}</div>
      <div className="stat__value">{value}</div>
      {hint ? <div className="stat__hint">{hint}</div> : null}
    </div>
  );
}
