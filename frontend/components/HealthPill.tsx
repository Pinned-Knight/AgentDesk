"use client";

import { useEffect, useState } from "react";
import { API_URL, getHealth } from "@/lib/api";
import type { Health } from "@/lib/types";

type State = { kind: "loading" } | { kind: "offline" } | { kind: "ok"; health: Health };

/** "in-memory (mongomock)" -> "mongomock"; plain names pass through. */
const short = (s: string): string => /\(([^)]+)\)/.exec(s)?.[1] ?? s;

export default function HealthPill() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      getHealth()
        .then((health) => {
          if (!cancelled) setState({ kind: "ok", health });
        })
        .catch(() => {
          if (!cancelled) setState({ kind: "offline" });
        });
    };
    poll();
    const timer = setInterval(poll, 15_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <span className="pill" title={`Checking ${API_URL}`} role="status">
        <span className="pill__dot" aria-hidden="true">●</span>
        <span>connecting…</span>
      </span>
    );
  }

  if (state.kind === "offline") {
    return (
      <span className="pill pill--bad" title={`Backend unreachable at ${API_URL}`} role="status">
        <span className="pill__dot" aria-hidden="true">●</span>
        <span>offline</span>
      </span>
    );
  }

  const h = state.health;
  const tone = h.status !== "ok" ? "warn" : h.mode === "live" ? "good" : "info";
  return (
    <span
      className={`pill pill--${tone}`}
      title={`status: ${h.status} · LLM: ${h.llm_provider} · mongo: ${h.mongo} · redis: ${h.redis}`}
      role="status"
    >
      <span className="pill__dot" aria-hidden="true">●</span>
      <span>{h.mode}</span>
      <span className="pill__detail">
        {" · "}
        {short(h.mongo)}
        {" · "}
        {short(h.redis)}
      </span>
    </span>
  );
}
