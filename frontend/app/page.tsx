"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChatWindow from "@/components/ChatWindow";
import TracePanel from "@/components/TracePanel";
import { speak, stopSpeaking } from "@/lib/speech";
import { useChat } from "@/lib/useChat";
import { useSpeakPreference, useSpeechRecognition } from "@/lib/useVoice";

export default function ChatPage() {
  const tts = useSpeakPreference();
  const speakRef = useRef(false);
  useEffect(() => {
    speakRef.current = tts.enabled;
  }, [tts.enabled]);

  const chat = useChat((reply) => {
    if (speakRef.current) speak(reply);
  });
  const { send, newChat } = chat;
  const [input, setInput] = useState("");

  const submit = useCallback(
    (text: string) => {
      if (send(text)) setInput("");
    },
    [send],
  );

  const voice = useSpeechRecognition({
    onInterim: setInput,
    // Auto-send the final transcript; keep it in the box if a turn is still running.
    onFinal: (text) => setInput(send(text) ? "" : text),
  });
  const { abort: abortVoice } = voice;

  const handleNewChat = useCallback(() => {
    abortVoice();
    stopSpeaking();
    setInput("");
    newChat();
  }, [abortVoice, newChat]);

  return (
    <div className="console">
      <ChatWindow
        sessionId={chat.sessionId}
        messages={chat.messages}
        busy={chat.busy}
        input={input}
        onInput={setInput}
        onSend={submit}
        onNewChat={handleNewChat}
        mic={{ supported: voice.supported, listening: voice.listening, notice: voice.notice, onToggle: voice.toggle }}
        speak={{ supported: tts.supported, enabled: tts.enabled, onChange: tts.setEnabled }}
      />
      <TracePanel trace={chat.trace} />
    </div>
  );
}
