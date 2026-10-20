"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { describeError, isAbortError, streamChat } from "./api";
import { loadSessionId, newSessionId, saveSessionId } from "./session";
import type { ChatMessage, TurnTrace } from "./types";

let seq = 0;
const nextId = () => `m${++seq}`;

/** Chat state + streaming turn runner. `onReply` fires with each finished reply. */
export function useChat(onReply?: (reply: string) => void) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TurnTrace | null>(null);
  const [busy, setBusy] = useState(false);

  const sessionRef = useRef<string | null>(null);
  const busyRef = useRef(false);
  // Bumped on every new turn and on "New chat" so callbacks of an abandoned stream are ignored.
  const turnRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const onReplyRef = useRef(onReply);

  useEffect(() => {
    onReplyRef.current = onReply;
  });

  useEffect(() => {
    const id = loadSessionId();
    sessionRef.current = id;
    setSessionId(id);
    return () => abortRef.current?.abort();
  }, []);

  const run = useCallback(async (session: string, text: string) => {
    const turn = ++turnRef.current;
    const controller = new AbortController();
    abortRef.current = controller;
    const live = () => turnRef.current === turn;
    const assistantId = nextId();
    let settled = false; // a `done` or `error` has been handled

    const patchAssistant = (fn: (m: ChatMessage) => ChatMessage) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)));

    const fail = (message: string) => {
      settled = true;
      setMessages((prev) => [
        // Drop an empty placeholder; keep partial text but stop its cursor.
        ...prev.flatMap((m) => (m.id !== assistantId ? [m] : m.content ? [{ ...m, streaming: false }] : [])),
        { id: nextId(), role: "error" as const, content: message },
      ]);
      setTrace((t) => (t ? { ...t, streaming: false, error: message } : t));
    };

    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: "user", content: text },
      { id: assistantId, role: "assistant", content: "", streaming: true },
    ]);
    setTrace({ steps: [], tools: [], done: null, streaming: true, error: null });

    try {
      await streamChat(
        session,
        text,
        {
          onTrace: (event) => {
            if (live()) setTrace((t) => (t ? { ...t, steps: [...t.steps, event] } : t));
          },
          onTool: (call) => {
            if (live()) setTrace((t) => (t ? { ...t, tools: [...t.tools, call] } : t));
          },
          onToken: (chunk) => {
            if (live()) patchAssistant((m) => ({ ...m, content: m.content + chunk }));
          },
          onDone: (response) => {
            if (!live()) return;
            settled = true;
            // `reply` is authoritative (covers cached / non-token paths).
            patchAssistant((m) => ({ ...m, content: response.reply || m.content, streaming: false, meta: response }));
            setTrace((t) => (t ? { ...t, done: response, streaming: false } : t));
            onReplyRef.current?.(response.reply);
          },
          onError: (detail) => {
            if (live()) fail(detail);
          },
        },
        controller.signal,
      );
      if (live() && !settled) fail("The connection closed before the reply finished.");
    } catch (err) {
      if (live() && !isAbortError(err)) fail(describeError(err));
    } finally {
      if (live()) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  }, []);

  /** Start a turn. Returns false (and does nothing) if empty or a turn is already running. */
  const send = useCallback(
    (raw: string): boolean => {
      const text = raw.trim();
      const session = sessionRef.current;
      if (!text || !session || busyRef.current) return false;
      busyRef.current = true;
      setBusy(true);
      void run(session, text);
      return true;
    },
    [run],
  );

  const newChat = useCallback(() => {
    turnRef.current++; // orphan any in-flight stream
    abortRef.current?.abort();
    busyRef.current = false;
    setBusy(false);
    const id = newSessionId();
    saveSessionId(id);
    sessionRef.current = id;
    setSessionId(id);
    setMessages([]);
    setTrace(null);
  }, []);

  return { sessionId, messages, trace, busy, send, newChat };
}
