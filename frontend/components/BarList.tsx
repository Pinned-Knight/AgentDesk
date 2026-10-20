type Item = { label: string; value: number };

/** Horizontal CSS bar chart: one labelled row per item, widths relative to the max. */
export default function BarList({ items, empty = "No data yet." }: { items: Item[]; empty?: string }) {
  if (items.length === 0) return <p className="muted">{empty}</p>;

  const sorted = [...items].sort((a, b) => b.value - a.value);
  const max = Math.max(sorted[0].value, 1);
  const total = sorted.reduce((sum, i) => sum + i.value, 0) || 1;

  return (
    <ul className="barlist">
      {sorted.map((item) => (
        <li key={item.label}>
          <div className="barlist__head">
            <span className="barlist__label" title={item.label}>
              {item.label}
            </span>
            <span className="barlist__value">
              {item.value.toLocaleString()} <span className="muted">· {Math.round((item.value / total) * 100)}%</span>
            </span>
          </div>
          <div className="barlist__track">
            <div className="barlist__fill" style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
