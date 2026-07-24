import { useRef } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const val = ref.current?.value.trim();
    if (!val || disabled) return;
    ref.current!.value = "";
    ref.current!.style.height = "auto";
    onSend(val);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function onInput() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  return (
    <div className="flex items-end gap-2 p-4 border-t border-border bg-bg-elevated">
      <textarea
        ref={ref}
        rows={1}
        placeholder="Nachricht eingeben…"
        disabled={disabled}
        onKeyDown={onKeyDown}
        onInput={onInput}
        className="flex-1 resize-none bg-bg-surface border border-border rounded-[10px] px-4 py-2.5 text-sm text-text placeholder-text-subtle focus:outline-none focus:border-accent disabled:opacity-50 leading-relaxed"
        style={{ maxHeight: 120 }}
      />
      <button
        onClick={submit}
        disabled={disabled}
        className="shrink-0 w-10 h-10 flex items-center justify-center bg-accent hover:bg-accent-hover disabled:opacity-50 rounded-[10px] transition-colors"
      >
        <Send size={16} className="text-white" />
      </button>
    </div>
  );
}
