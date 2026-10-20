"use client";

import { Fragment, useCallback, useState } from "react";
import { describeError, getConversation } from "@/lib/api";
import { fmtDate, shortId } from "@/lib/format";
import type { ConversationMessage, ConversationSummary } from "@/lib/types";

type Transcript =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; messages: ConversationMessage[] };

function TranscriptView({ state }: { state: Transcript | undefined }) {
  if (!state || state.status === "loading") return <p className="muted transcript">Loading transcript…</p>;
  if (state.status === "error") return <p className="transcript trace-error">Could not load transcript: {state.message}</p>;
  if (state.messages.length === 0) return <p className="muted transcript">This conversation has no messages.</p>;

  return (
    <div className="transcript">
      {state.messages.map((m, i) => (
        <div key={i} className={`t-msg t-msg--${m.role}`}>
          <div className="t-head">
            <strong>{m.role === "user" ? "Customer" : "Agent"}</strong>
            {m.intent ? <span className="badge badge--accent">{m.intent}</span> : null}
            {m.escalated ? <span className="badge badge--warn">escalated</span> : null}
            {m.latency_ms != null ? <span className="muted">{Math.round(m.latency_ms)} ms</span> : null}
            <span className="muted push">{fmtDate(m.created_at)}</span>
          </div>
          <div className="t-body">{m.content}</div>
          {(m.tools ?? []).length > 0 ? (
            <div className="t-tools">
              {m.tools.map((t, j) => (
                <span key={`${t.name}-${j}`} className="badge badge--warn">
                  {t.name}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/** Recent conversations; clicking a row expands its transcript underneath. */
export default function ConversationsTable({ rows }: { rows: ConversationSummary[] }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [transcripts, setTranscripts] = useState<Record<string, Transcript>>({});

  const load = useCallback((id: string) => {
    setTranscripts((t) => ({ ...t, [id]: { status: "loading" } }));
    getConversation(id)
      .then((c) => setTranscripts((t) => ({ ...t, [id]: { status: "ready", messages: c.messages } })))
      .catch((err: unknown) => setTranscripts((t) => ({ ...t, [id]: { status: "error", message: describeError(err) } })));
  }, []);

  const toggle = (id: string) => {
    const willOpen = !open[id];
    setOpen((o) => ({ ...o, [id]: willOpen }));
    if (willOpen && transcripts[id]?.status !== "ready") load(id);
  };

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Session</th>
            <th scope="col">Turns</th>
            <th scope="col">Last intent</th>
            <th scope="col">Escalated</th>
            <th scope="col">Last activity</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isOpen = !!open[r.session_id];
            return (
              <Fragment key={r.session_id}>
                <tr className={`row${isOpen ? " is-open" : ""}`} onClick={() => toggle(r.session_id)}>
                  <td>
                    <button type="button" className="row-btn mono" aria-expanded={isOpen} title={r.session_id}>
                      <span className="chev" aria-hidden="true">
                        {isOpen ? "▾" : "▸"}
                      </span>
                      {shortId(r.session_id)}
                    </button>
                  </td>
                  <td>{r.turns}</td>
                  <td>
                    {r.last_intent ? <span className="badge badge--accent">{r.last_intent}</span> : <span className="muted">—</span>}
                  </td>
                  <td>{r.escalated ? <span className="badge badge--warn">escalated</span> : <span className="muted">no</span>}</td>
                  <td className="nowrap">{fmtDate(r.last_message_at)}</td>
                </tr>
                {isOpen ? (
                  <tr className="expander">
                    <td colSpan={5}>
                      <TranscriptView state={transcripts[r.session_id]} />
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
