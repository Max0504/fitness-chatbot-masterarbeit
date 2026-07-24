import { useEffect, useRef, useState } from "react";
import { sendChatMessage } from "../../api/rasa";
import type { Message } from "../../App";
import { newMsg } from "../../App";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";

interface Props {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

export default function ChatView({ messages, setMessages }: Props) {
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendToRasa(payload: string): Promise<void> {
    setLoading(true);
    try {
      const responses = await sendChatMessage(payload);
      const botMsgs = responses
        .filter((r) => r.text)
        .map((r) => newMsg("bot", r.text!, r.buttons));

      if (botMsgs.length === 0) {
        const retry = await sendChatMessage("/nlu_fallback");
        const retryMsgs = retry.filter((r) => r.text).map((r) => newMsg("bot", r.text!, r.buttons));
        setMessages((prev) => [
          ...prev,
          ...(retryMsgs.length > 0
            ? retryMsgs
            : [newMsg("bot", "Kannst du das etwas anders formulieren? Ich bin für dich da.")]),
        ]);
        return;
      }

      setMessages((prev) => [...prev, ...botMsgs]);

      const activityKeywords = ["eingetragen", "Punkte erhalten", "neuen Streak", "Workout geloggt"];
      const hasActivity = botMsgs.some((m) =>
        activityKeywords.some((kw) => m.text?.includes(kw))
      );
      if (hasActivity) window.dispatchEvent(new CustomEvent("activity_logged"));
    } catch {
      setMessages((prev) => [
        ...prev,
        newMsg("bot", "Verbindungsfehler — läuft der Rasa-Server?"),
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(text: string) {
    setMessages((prev) => [...prev, newMsg("user", text)]);
    await sendToRasa(text);
  }

  async function handleButtonClick(messageId: number, title: string, payload: string) {
    // Buttons vom auslösenden Message entfernen (einmalige Nutzung)
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, buttons: undefined } : m))
    );
    // Titel als User-Nachricht anzeigen
    setMessages((prev) => [...prev, newMsg("user", title)]);
    await sendToRasa(payload);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border bg-bg-elevated">
        <h1 className="font-semibold text-text">Chat</h1>
        <p className="text-xs text-text-subtle mt-0.5">Dein persönlicher Fitness-Coach</p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            onButtonClick={(title, payload) => handleButtonClick(m.id, title, payload)}
          />
        ))}

        {loading && (
          <div className="flex justify-start mb-3">
            <div className="bg-bg-surface border border-border-subtle rounded-[10px] rounded-bl-sm px-4 py-3 flex gap-1.5 items-center">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-text-subtle animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
