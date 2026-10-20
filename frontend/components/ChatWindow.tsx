"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatMessage, ChatResponse } from "@/lib/types";
import { MicButton, SpeakToggle } from "./VoiceControls";

const SUGGESTIONS = [
  "Where is my order ORD-1002?",
  "I want to return ORD-1001",
  "What is your refund policy?",
  "How long does shipping take?",
  "I'd like to speak to a human",
];

type Props = {
  sessionId: string | null;
  messages: ChatMessage[];
  busy: boolean;
  input: string;
  onInput: (value: string) => void;
  onSend: (text: string) => void;
  onNewChat: () => void;
  mic: { supported: boolean; listening: boolean; notice: string | null; onToggle: () => void };
  speak: { supported: boolean; enabled: boolean; onChange: (value: boolean) => void };
};

function MetaLine({ meta }: { meta: ChatResponse }) {
  return (
    <div className="meta">
      <span className="badge badge--accent">{meta.intent}</span>
      <span className="meta__item">{Math.round(meta.latency_ms)} ms</span>
      {meta.cached ? <span className="badge badge--info">cached</span> : null}
      {meta.escalated ? (
        <span className="badge badge--warn">escalated{meta.ticket_id ? ` · ${meta.ticket_id}` : ""}</span>
      ) : null}
      {meta.guardrail ? <span className="badge badge--bad">{meta.guardrail}</span> : null}
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="bubble bubble--user">{message.content}</div>
      </div>
    );
  }
  if (message.role === "error") {
    return (
      <div className="msg msg--assistant">
        <div className="bubble bubble--error" role="alert">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="msg msg--assistant">
      <div className="bubble bubble--assistant">
        {message.content}
        {message.streaming && !message.content ? (
          <span className="typing" role="status" aria-label="Assistant is typing">
            <i />
            <i />
            <i />
          </span>
        ) : null}
        {message.streaming && message.content ? <span className="caret" aria-hidden="true" /> : null}
      </div>
      {message.meta ? <MetaLine meta={message.meta} /> : null}
    </div>
  );
}

export default function ChatWindow({ sessionId, messages, busy, input, onInput, onSend, onNewChat, mic, speak }: Props) {
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const stickRef = useRef(true); // follow new content unless the user scrolled up
  const wasBusy = useRef(false);

  useEffect(() => {
    const el = listRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Grow the textarea with its content (capped at ~6 lines).
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // Hand focus back to the box when a reply finishes.
  useEffect(() => {
    if (wasBusy.current && !busy) inputRef.current?.focus();
    wasBusy.current = busy;
  }, [busy]);

  const canSend = !busy && !!sessionId && input.trim().length > 0;

  const send = (text: string) => {
    stickRef.current = true;
    onSend(text);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (canSend) send(input);
    }
  };

  const onScroll = () => {
    const el = listRef.current;
    if (el) stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  return (
    <section className="panel chat-panel" aria-label="Conversation">
      <header className="panel__head">
        <h2 className="panel__title">Conversation</h2>
        {sessionId ? (
          <span className="session-tag" title={`Session ${sessionId}`}>
            {sessionId.slice(0, 8)}
          </span>
        ) : null}
        <button type="button" className="btn btn--sm push" onClick={onNewChat}>
          New chat
        </button>
      </header>

      <div className="chat-list" ref={listRef} onScroll={onScroll} role="log" aria-label="Messages">
        {messages.length === 0 ? (
          <div className="empty-hero">
            <h3 className="empty-hero__title">How can I help today?</h3>
            <p className="muted">Ask about an order, a return, shipping or refunds - or try one of these:</p>
            <div className="chips">
              {SUGGESTIONS.map((text) => (
                <button key={text} type="button" className="chip" disabled={busy || !sessionId} onClick={() => send(text)}>
                  {text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => <Bubble key={m.id} message={m} />)
        )}
      </div>

      <div className="composer">
        <div className="composer__row">
          <textarea
            ref={inputRef}
            value={input}
            rows={1}
            placeholder={mic.listening ? "Listening…" : "Message AgentDesk…"}
            aria-label="Message"
            disabled={busy || !sessionId}
            onChange={(e) => onInput(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <MicButton supported={mic.supported} listening={mic.listening} disabled={busy || !sessionId} onToggle={mic.onToggle} />
          <button type="button" className="btn btn--primary send-btn" disabled={!canSend} onClick={() => send(input)}>
            Send
          </button>
        </div>
        <div className="composer__foot">
          <SpeakToggle supported={speak.supported} enabled={speak.enabled} onChange={speak.onChange} />
          <span className="hint" aria-live="polite">
            {mic.listening ? "Listening… speak now" : (mic.notice ?? "Enter to send · Shift+Enter for a new line")}
          </span>
        </div>
      </div>
    </section>
  );
}
