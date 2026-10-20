"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import BarList from "@/components/BarList";
import ConversationsTable from "@/components/ConversationsTable";
import DailyChart from "@/components/DailyChart";
import StatCard from "@/components/StatCard";
import { API_URL, describeError, getAnalytics, getConversations } from "@/lib/api";
import { fmtMs, fmtNum, fmtPct } from "@/lib/format";
import type { Analytics, ConversationSummary } from "@/lib/types";

type Data = { analytics: Analytics; conversations: ConversationSummary[] };

function Skeleton() {
  return (
    <>
      <div className="stat-grid">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton" style={{ height: 92 }} />
        ))}
      </div>
      <div className="grid-2">
        <div className="skeleton" style={{ height: 220 }} />
        <div className="skeleton" style={{ height: 220 }} />
      </div>
      <div className="skeleton mt" style={{ height: 220 }} />
    </>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0); // remounts the table so stale transcripts are dropped

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [analytics, conversations] = await Promise.all([getAnalytics(), getConversations(20)]);
      setData({ analytics, conversations });
      setVersion((v) => v + 1);
    } catch (err) {
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const a = data?.analytics;
  const rows = data?.conversations ?? [];
  const isEmpty = !!a && a.total_conversations === 0 && rows.length === 0;

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="muted">Live metrics from the AgentDesk backend</p>
        </div>
        <button type="button" className="btn" onClick={() => void load()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && !data ? (
        <div className="state-card" role="alert">
          <h2>Can&apos;t load analytics</h2>
          <p>
            The AgentDesk backend didn&apos;t respond at <code>{API_URL}</code>. Make sure it&apos;s running, then try
            again.
          </p>
          <p className="muted">{error}</p>
          <button type="button" className="btn btn--primary" onClick={() => void load()} disabled={loading}>
            {loading ? "Retrying…" : "Try again"}
          </button>
        </div>
      ) : !a ? (
        <Skeleton />
      ) : (
        <>
          {error ? (
            <div className="banner banner--error" role="alert">
              Refresh failed: {error}
            </div>
          ) : null}

          {isEmpty ? (
            <div className="banner">
              No conversations yet. Start one in the <Link href="/">chat console</Link> and the numbers will appear
              here.
            </div>
          ) : null}

          <div className="stat-grid">
            <StatCard label="Conversations" value={fmtNum(a.total_conversations)} />
            <StatCard label="Messages" value={fmtNum(a.total_messages)} />
            <StatCard label="Avg latency" value={fmtMs(a.avg_latency_ms)} />
            <StatCard label="Escalation rate" value={fmtPct(a.escalation_rate)} />
            <StatCard label="Cache hit rate" value={fmtPct(a.cache_hit_rate)} />
          </div>

          <div className="grid-2">
            <section className="card">
              <h2 className="card__title">Intent mix</h2>
              <BarList items={a.intents.map((i) => ({ label: i.intent || "unknown", value: i.count }))} />
            </section>
            <section className="card">
              <h2 className="card__title">Tool usage</h2>
              <BarList items={a.tools.map((t) => ({ label: t.name, value: t.count }))} empty="No tools called yet." />
            </section>
          </div>

          <section className="card mt">
            <h2 className="card__title">Daily volume</h2>
            <DailyChart data={a.daily} />
          </section>

          <section className="card mt">
            <h2 className="card__title">Recent conversations</h2>
            {rows.length === 0 ? (
              <p className="muted">No conversations recorded yet.</p>
            ) : (
              <ConversationsTable key={version} rows={rows} />
            )}
          </section>
        </>
      )}
    </div>
  );
}
