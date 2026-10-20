import type { ReactNode } from "react";
import { toPercent } from "@/lib/format";
import type { ChatResponse, ToolCall, TraceEvent, TurnTrace } from "@/lib/types";

const pretty = (value: unknown): string => JSON.stringify(value, null, 2);

function Badges({ items, tone }: { items: string[]; tone?: string }) {
  return (
    <span className="badges">
      {items.map((item, i) => (
        <span key={`${item}-${i}`} className={`badge${tone ? ` badge--${tone}` : ""}`}>
          {item}
        </span>
      ))}
    </span>
  );
}

/** Compact, step-specific summary shown under each timeline row. */
function StepDetail({ ev }: { ev: TraceEvent }): ReactNode {
  switch (ev.step) {
    case "guardrail": {
      const flags = ev.flags ?? [];
      return flags.length > 0 ? <Badges items={flags} tone="warn" /> : <span className="ok">clean</span>;
    }
    case "cache":
      return <span className={`badge badge--${ev.hit ? "good" : "muted"}`}>{ev.hit ? "hit" : "miss"}</span>;
    case "understand": {
      const confidence = toPercent(ev.confidence);
      const entities = Object.entries(ev.entities ?? {});
      return (
        <>
          <div className="tl-line">
            <span className="badge badge--accent">{ev.intent}</span>
            <span className="muted">{confidence}%</span>
          </div>
          <div
            className="conf"
            role="meter"
            aria-label="Intent confidence"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={confidence}
          >
            <span style={{ width: `${confidence}%` }} />
          </div>
          {entities.length > 0 ? (
            <div className="tl-line">
              {entities.map(([key, value]) => (
                <span key={key} className="kv">
                  <span className="muted">{key}</span> {String(value)}
                </span>
              ))}
            </div>
          ) : null}
        </>
      );
    }
    case "route":
      return (
        <span className="tl-line">
          <span className="muted">next →</span> <span className="badge badge--info">{ev.next}</span>
        </span>
      );
    case "retrieve": {
      const matches = ev.matches ?? [];
      if (matches.length === 0) return <span className="muted">no FAQ matches</span>;
      return (
        <ul className="matches">
          {matches.map((m, i) => (
            <li key={`${m.id}-${i}`}>
              <span>{m.question}</span>
              <span className="muted">{Number(m.score).toFixed(2)}</span>
            </li>
          ))}
        </ul>
      );
    }
    case "tools":
      return <Badges items={ev.names ?? []} tone="warn" />;
    case "escalate":
      return <span className="badge badge--bad">ticket {ev.ticket_id}</span>;
    case "respond":
      return (
        <span className="tl-line">
          <span className="muted">provider</span> <span className="badge">{ev.provider}</span>
        </span>
      );
    default: {
      // A step this UI doesn't know yet: show its extra fields verbatim.
      const extra = Object.entries(ev).filter(([key]) => key !== "step");
      return extra.length > 0 ? (
        <code className="muted">{extra.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(" ")}</code>
      ) : null;
    }
  }
}

function ToolBlock({ call }: { call: ToolCall }) {
  const inlineArgs = Object.entries(call.args ?? {})
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");
  return (
    <details className="tool">
      <summary>
        <span className="tool__name">{call.name}</span>
        <span className="tool__args muted">{inlineArgs}</span>
      </summary>
      <div className="tool__body">
        <div className="label">args</div>
        <pre>{pretty(call.args)}</pre>
        <div className="label">result</div>
        <pre>{pretty(call.result)}</pre>
      </div>
    </details>
  );
}

function Mini({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="mini">
      <div className="mini__label">{label}</div>
      <div className={`mini__value${tone ? ` tone-${tone}` : ""}`}>{value}</div>
    </div>
  );
}

function FinalStats({ done }: { done: ChatResponse }) {
  return (
    <div className="mini-grid">
      <Mini label="Latency" value={`${Math.round(done.latency_ms)} ms`} />
      <Mini label="Cached" value={done.cached ? "yes" : "no"} tone={done.cached ? "info" : undefined} />
      <Mini label="Escalated" value={done.escalated ? "yes" : "no"} tone={done.escalated ? "warn" : undefined} />
      <Mini label="Intent" value={`${done.intent} · ${toPercent(done.confidence)}%`} />
      {done.ticket_id ? <Mini label="Ticket" value={done.ticket_id} tone="warn" /> : null}
      {done.guardrail ? <Mini label="Guardrail" value={done.guardrail} tone="bad" /> : null}
    </div>
  );
}

export default function TracePanel({ trace }: { trace: TurnTrace | null }) {
  const status = !trace ? null : trace.streaming ? (
    <span className="badge badge--info">running</span>
  ) : trace.error ? (
    <span className="badge badge--bad">failed</span>
  ) : (
    <span className="badge badge--good">complete</span>
  );

  return (
    <section className="panel trace-panel" aria-label="Agent trace">
      <header className="panel__head">
        <h2 className="panel__title">Agent trace</h2>
        {status}
      </header>
      <div className="panel__body">
        {!trace ? (
          <p className="empty">
            Send a message to watch the agent work. Guardrails, intent, routing, retrieval and tool calls show up here
            live.
          </p>
        ) : (
          <>
            <ol className="timeline">
              {trace.steps.map((ev, i) => (
                <li key={`${i}-${ev.step}`} className="tl-row" data-step={ev.step}>
                  <span className="tl-dot" aria-hidden="true" />
                  <div className="tl-body">
                    <div className="tl-title">{ev.step}</div>
                    <div className="tl-detail">
                      <StepDetail ev={ev} />
                    </div>
                  </div>
                </li>
              ))}
              {trace.streaming ? (
                <li className="tl-row tl-row--pending">
                  <span className="tl-dot" aria-hidden="true" />
                  <div className="tl-body">
                    <div className="tl-title muted">working…</div>
                  </div>
                </li>
              ) : null}
            </ol>

            {trace.error ? <p className="trace-error">{trace.error}</p> : null}

            {trace.tools.length > 0 || !trace.streaming ? (
              <>
                <h3 className="sub">Tool calls{trace.tools.length > 0 ? ` (${trace.tools.length})` : ""}</h3>
                {trace.tools.length > 0 ? (
                  trace.tools.map((call, i) => <ToolBlock key={`${call.name}-${i}`} call={call} />)
                ) : (
                  <p className="muted">No tools were called this turn.</p>
                )}
              </>
            ) : null}

            {trace.done ? (
              <>
                <h3 className="sub">Result</h3>
                <FinalStats done={trace.done} />
              </>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
