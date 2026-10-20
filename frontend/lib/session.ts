const KEY = "agentdesk.session";
const VALID = /^[A-Za-z0-9_-]{8,64}$/; // the backend's session id rule

export function newSessionId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  // randomUUID needs a secure context; plain-http hosts fall back to random hex.
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function saveSessionId(id: string): void {
  try {
    localStorage.setItem(KEY, id);
  } catch {
    // storage unavailable (private mode, blocked) - the id just won't persist
  }
}

export function loadSessionId(): string {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored && VALID.test(stored)) return stored;
  } catch {
    // fall through to a fresh id
  }
  const id = newSessionId();
  saveSessionId(id);
  return id;
}
