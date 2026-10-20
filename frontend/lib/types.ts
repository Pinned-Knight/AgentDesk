// Shared types mirroring the AgentDesk backend contract.

export type ToolCall = {
  name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  intent: string;
  confidence: number; // 0..1
  tools: ToolCall[];
  escalated: boolean;
  ticket_id: string | null;
  latency_ms: number;
  cached: boolean;
  guardrail: string | null; // e.g. "pii_masked" | "prompt_injection" | null
};

export type Health = {
  status: string;
  mode: "demo" | "live";
  llm_provider: string;
  mongo: string;
  redis: string;
};

/** One `trace` SSE event: a step of the agent graph plus step-specific extras. */
export type TraceEvent =
  | { step: "guardrail"; flags: string[] }
  | { step: "cache"; hit: boolean }
  | { step: "understand"; intent: string; confidence: number; entities: { order_id?: string } }
  | { step: "route"; next: "run_tools" | "retrieve" | "escalate" | "respond" }
  | { step: "retrieve"; matches: { id: string; question: string; score: number }[] }
  | { step: "tools"; names: string[] }
  | { step: "escalate"; ticket_id: string }
  | { step: "respond"; provider: string };

export type ConversationSummary = {
  session_id: string;
  started_at: string;
  last_message_at: string;
  turns: number;
  last_intent: string | null;
  escalated: boolean;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  intent: string | null;
  tools: ToolCall[];
  escalated: boolean;
  latency_ms: number | null;
  created_at: string;
};

export type ConversationDetail = {
  session_id: string;
  messages: ConversationMessage[];
};

export type Analytics = {
  total_conversations: number;
  total_messages: number;
  escalation_rate: number; // 0..1
  avg_latency_ms: number;
  cache_hit_rate: number; // 0..1
  intents: { intent: string; count: number }[];
  tools: { name: string; count: number }[];
  daily: { date: string; count: number }[]; // date = YYYY-MM-DD
};

// ---- UI state (not part of the API) ----

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  streaming?: boolean;
  meta?: ChatResponse; // set once the `done` event arrives
};

/** Live view of the most recent turn, rendered by the trace panel. */
export type TurnTrace = {
  steps: TraceEvent[];
  tools: ToolCall[];
  done: ChatResponse | null;
  streaming: boolean;
  error: string | null;
};
