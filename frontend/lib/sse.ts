// Minimal Server-Sent Events parser. EventSource cannot POST, so we read a
// fetch() body stream and feed decoded text through these helpers.

export type SSEMessage = { event: string; data: string };

function parseBlock(block: string): SSEMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line === "" || line.startsWith(":")) continue; // blank line or comment/keep-alive
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length > 0 ? { event, data: data.join("\n") } : null;
}

/**
 * Pure: extract every complete message (terminated by a blank line) from
 * `buffer` and return it with the unconsumed remainder. Feed the remainder
 * back in, prefixed to the next chunk. Handles \n, \r\n and \r line endings,
 * including a \r\n pair split across two chunks.
 */
export function parseSSEBuffer(buffer: string): { messages: SSEMessage[]; rest: string } {
  let text = buffer;
  let carry = "";
  if (text.endsWith("\r")) {
    // Might be the first half of "\r\n"; hold it back until we know.
    carry = "\r";
    text = text.slice(0, -1);
  }
  text = text.replace(/\r\n?/g, "\n");

  const messages: SSEMessage[] = [];
  let rest = text;
  for (let end = rest.indexOf("\n\n"); end !== -1; end = rest.indexOf("\n\n")) {
    const message = parseBlock(rest.slice(0, end));
    if (message) messages.push(message);
    rest = rest.slice(end + 2);
  }
  return { messages, rest: rest + carry };
}

/** Async-iterate SSE messages from a fetch() response body. */
export async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      const parsed = parseSSEBuffer(buffer + decoder.decode(value, { stream: true }));
      buffer = parsed.rest;
      yield* parsed.messages;
    }
    // Stream ended: flush a final message that lacked its trailing blank line.
    yield* parseSSEBuffer(buffer + decoder.decode() + "\n\n").messages;
  } finally {
    reader.cancel().catch(() => undefined);
  }
}
