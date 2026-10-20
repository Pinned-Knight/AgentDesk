type MicProps = {
  supported: boolean;
  listening: boolean;
  disabled?: boolean;
  onToggle: () => void;
};

/** 🎤 toggle for browser speech recognition. */
export function MicButton({ supported, listening, disabled, onToggle }: MicProps) {
  const title = !supported
    ? "Voice input not supported in this browser"
    : listening
      ? "Stop listening"
      : "Speak your message";

  return (
    <span title={title} className="tip">
      <button
        type="button"
        className={`icon-btn${listening ? " is-listening" : ""}`}
        onClick={onToggle}
        disabled={!supported || disabled}
        aria-pressed={listening}
        aria-label={title}
        title={title}
      >
        🎤
      </button>
    </span>
  );
}

type SpeakProps = {
  supported: boolean;
  enabled: boolean;
  onChange: (value: boolean) => void;
};

/** "🔊 Speak replies" switch (state persisted by the caller). */
export function SpeakToggle({ supported, enabled, onChange }: SpeakProps) {
  const title = supported ? "Read each finished reply aloud" : "Speech output not supported in this browser";
  return (
    <label className={`toggle${supported ? "" : " is-disabled"}`} title={title}>
      <input
        type="checkbox"
        checked={enabled && supported}
        disabled={!supported}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="toggle__track" aria-hidden="true" />
      <span>🔊 Speak replies</span>
    </label>
  );
}
