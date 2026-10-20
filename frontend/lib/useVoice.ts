"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  describeSpeechError,
  getRecognitionCtor,
  stopSpeaking,
  synthesisSupported,
  type SpeechRecognitionLike,
} from "./speech";

const SPEAK_KEY = "agentdesk.speak";

type RecognitionHandlers = {
  /** Called with the live partial transcript. */
  onInterim: (text: string) => void;
  /** Called once with the final transcript. */
  onFinal: (text: string) => void;
};

/** Push-to-toggle speech input. Feature-detected after mount (SSR-safe). */
export function useSpeechRecognition(handlers: RecognitionHandlers) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const recRef = useRef<SpeechRecognitionLike | null>(null);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  });

  useEffect(() => {
    setSupported(getRecognitionCtor() !== null);
    return () => {
      clearTimeout(noticeTimer.current);
      recRef.current?.abort();
    };
  }, []);

  const flash = useCallback((message: string) => {
    setNotice(message);
    clearTimeout(noticeTimer.current);
    noticeTimer.current = setTimeout(() => setNotice(null), 5000);
  }, []);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor || recRef.current) return;
    stopSpeaking(); // don't transcribe our own voice

    const rec = new Ctor();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    let delivered = false;

    rec.onresult = (event) => {
      let text = "";
      let isFinal = false;
      for (let i = 0; i < event.results.length; i++) {
        text += event.results[i][0].transcript;
        isFinal = event.results[i].isFinal;
      }
      text = text.trim();
      if (!text) return;
      if (!isFinal) {
        handlersRef.current.onInterim(text);
      } else if (!delivered) {
        delivered = true;
        handlersRef.current.onFinal(text);
      }
    };
    rec.onerror = (event) => {
      const message = describeSpeechError(event.error);
      if (message) flash(message);
    };
    rec.onend = () => {
      recRef.current = null;
      setListening(false);
    };

    try {
      rec.start();
      recRef.current = rec;
      setListening(true);
      setNotice(null);
    } catch {
      flash("Could not start voice input.");
    }
  }, [flash]);

  const toggle = useCallback(() => {
    if (recRef.current) recRef.current.stop(); // flushes any pending final result
    else start();
  }, [start]);

  const abort = useCallback(() => recRef.current?.abort(), []);

  return { supported, listening, notice, toggle, abort };
}

/** "Speak replies" preference, persisted in localStorage. */
export function useSpeakPreference() {
  const [enabled, setEnabledState] = useState(false);
  const [supported, setSupported] = useState(false);

  useEffect(() => {
    setSupported(synthesisSupported());
    try {
      setEnabledState(localStorage.getItem(SPEAK_KEY) === "1");
    } catch {
      // storage unavailable - stays off
    }
  }, []);

  const setEnabled = useCallback((value: boolean) => {
    setEnabledState(value);
    try {
      localStorage.setItem(SPEAK_KEY, value ? "1" : "0");
    } catch {
      // not persisted, still applies for this page view
    }
    if (!value) stopSpeaking();
  }, []);

  return { enabled, supported, setEnabled };
}
