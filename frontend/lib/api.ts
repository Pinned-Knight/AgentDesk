import { readSSE } from "./sse";
import type {
  Analytics,
  ChatResponse,
  ConversationDetail,
  ConversationSummary,
  Health,
  ToolCall,
  TraceEvent,
} from "./types";

// Inlined at build time; trailing slashes are stripped so paths join cleanly.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

/** Non-2xx response (or transport failure when status is 0). */
export class ApiError extends Error {
  readonly status: number;
  readonly retryAfter?: number;

  constructor(message: string, status: number, retryAfter?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail = res.statusText || `HTTP ${res.status}`;
  let retryAfter: number | undefined;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object") {
      const b = body as { detail?: unknown; retry_after?: unknown };
      if (typeof b.detail === "string") {
        detail = b.detail;
      } else if (Array.isArray(b.detail)) {
        // FastAPI 422 validation errors: [{ loc, msg, type }, ...]
        detail = b.detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join("; ");
      }
      if (typeof b.retry_after === "number") retryAfter = b.retry_after;
    }
  } catch {
    // Body was not JSON; keep the status text.
  }
  if (retryAfter === undefined) {
    const header = Number(res.headers.get("Retry-After"));
    if (Number.isFinite(header) && header > 0) retryAfter = header;
  }
  return new ApiError(detail, res.status, retryAfter);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

/** AbortSignal that fires after `ms` (AbortSignal.timeout isn't in every browser). */
function timeoutSignal(ms: number): AbortSignal {
  if (typeof AbortSignal.timeout === "function") return AbortSignal.timeout(ms);
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

export const getHealth = () => request<Health>("/api/health", { signal: timeoutSignal(6000) });

export const getAnalytics = () => request<Analytics>("/api/analytics");

export const getConversations = (limit = 20) =>
  request<ConversationSummary[]>(`/api/conversations?limit=${limit}`);

export const getConversation = (sessionId: string) =>
  request<ConversationDetail>(`/api/conversations/${encodeURIComponent(sessionId)}`);

const jsonPost = (sessionId: string, message: string, extra?: RequestInit): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ session_id: sessionId, message }),
  ...extra,
});

/** Non-streaming chat turn. */
export const sendChat = (sessionId: string, message: string) =>
  request<ChatResponse>("/api/chat", jsonPost(sessionId, message));

export type StreamHandlers = {
  onTrace?: (event: TraceEvent) => void;
  onTool?: (call: ToolCall) => void;
  onToken?: (text: string) => void;
  onDone?: (response: ChatResponse) => void;
  onError?: (detail: string) => void;
};

/**
 * Streaming chat turn over POST + SSE. Resolves when the stream closes;
 * rejects with ApiError for HTTP failures (e.g. 429) or the fetch error otherwise.
 */
export async function streamChat(
  sessionId: string,
  message: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `${API_URL}/api/chat/stream`,
    jsonPost(sessionId, message, {
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      cache: "no-store",
      signal,
    }),
  );
  if (!res.ok) throw await toApiError(res);
  if (!res.body) throw new ApiError("This browser cannot stream responses.", 0);

  for await (const { event, data } of readSSE(res.body)) {
    let payload: unknown;
    try {
      payload = JSON.parse(data);
    } catch {
      continue; // ignore malformed frames
    }
    switch (event) {
      case "trace":
        handlers.onTrace?.(payload as TraceEvent);
        break;
      case "tool":
        handlers.onTool?.(payload as ToolCall);
        break;
      case "token":
        handlers.onToken?.(String((payload as { text?: unknown }).text ?? ""));
        break;
      case "done":
        handlers.onDone?.(payload as ChatResponse);
        break;
      case "error":
        handlers.onError?.(String((payload as { detail?: unknown }).detail ?? "Unknown error"));
        break;
    }
  }
}

/** Human-readable message for any error thrown by the client above. */
export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return err.retryAfter !== undefined
        ? `Slow down — retry in ${Math.ceil(err.retryAfter)} s`
        : "Slow down — too many requests, try again shortly";
    }
    return err.status ? `Request failed (HTTP ${err.status}): ${err.message}` : err.message;
  }
  if (err instanceof TypeError) return `Can't reach the backend at ${API_URL}. Is it running?`;
  return err instanceof Error ? err.message : String(err);
}

export const isAbortError = (err: unknown): boolean => err instanceof DOMException && err.name === "AbortError";
