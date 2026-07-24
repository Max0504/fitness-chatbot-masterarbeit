import type { Message } from "../../App";

interface Props {
  message: Message;
  onButtonClick: (title: string, payload: string) => void;
}

function renderMarkdown(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((part, j) =>
      part.startsWith("**") && part.endsWith("**")
        ? <strong key={j} className="font-semibold">{part.slice(2, -2)}</strong>
        : part
    );
    return <span key={i}>{rendered}{i < lines.length - 1 && <br />}</span>;
  });
}

function formatTime(d: Date) {
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

export default function MessageBubble({ message, onButtonClick }: Props) {
  const { role, text, timestamp, buttons } = message;
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[78%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1.5`}>
        {/* Bubble */}
        <div
          className={`px-4 py-2.5 rounded-[10px] text-sm leading-relaxed ${
            isUser
              ? "bg-accent text-white rounded-br-sm"
              : "bg-bg-surface text-text rounded-bl-sm border border-border-subtle"
          }`}
        >
          {renderMarkdown(text)}
        </div>

        {/* Quick-reply buttons (bot only) */}
        {!isUser && buttons && buttons.length > 0 && (
          <div className="flex flex-wrap gap-2 pl-1">
            {buttons.map((btn) => (
              <button
                key={btn.payload}
                onClick={() => onButtonClick(btn.title, btn.payload)}
                className="px-3 py-1.5 text-xs font-medium rounded-full border border-accent text-accent
                  hover:bg-accent hover:text-white transition-colors"
              >
                {btn.title}
              </button>
            ))}
          </div>
        )}

        <span className="text-[11px] text-text-subtle px-1">
          {formatTime(timestamp)}
        </span>
      </div>
    </div>
  );
}
