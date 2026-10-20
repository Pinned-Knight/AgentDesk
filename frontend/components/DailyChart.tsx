type Point = { date: string; count: number };

const W = 600;
const H = 160;
const PAD = 4;

/** Small inline-SVG bar chart. Stretches to its container; labels live in HTML so they stay crisp. */
export default function DailyChart({ data }: { data: Point[] }) {
  if (data.length === 0) return <p className="muted">No activity yet.</p>;

  const max = Math.max(...data.map((d) => d.count), 1);
  const slot = W / data.length;
  const barWidth = Math.min(slot * 0.68, 44);
  const inner = H - PAD * 2;

  return (
    <div className="daily">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Daily volume bar chart">
        {[0, 0.5, 1].map((f) => (
          <line key={f} className="daily__grid" x1={0} x2={W} y1={H - PAD - f * inner} y2={H - PAD - f * inner} />
        ))}
        {data.map((d, i) => {
          const h = d.count > 0 ? Math.max((d.count / max) * inner, 2) : 0;
          return (
            <rect
              key={d.date}
              className="daily__bar"
              x={i * slot + (slot - barWidth) / 2}
              y={H - PAD - h}
              width={barWidth}
              height={h}
            >
              <title>{`${d.date}: ${d.count.toLocaleString()}`}</title>
            </rect>
          );
        })}
      </svg>
      <div className="daily__axis">
        <span>{data[0].date}</span>
        <span>peak {max.toLocaleString()}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
