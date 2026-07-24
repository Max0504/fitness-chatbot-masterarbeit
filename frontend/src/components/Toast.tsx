import { useEffect, useState } from "react";
import { CheckCircle } from "lucide-react";

interface Props {
  message: string;
  onDone: () => void;
}

export default function Toast({ message, onDone }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // trigger enter animation on next frame
    const t1 = setTimeout(() => setVisible(true), 10);
    const t2 = setTimeout(() => setVisible(false), 2800);
    const t3 = setTimeout(onDone, 3200);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5
        bg-bg-surface border border-accent/40 shadow-lg rounded-[10px] px-5 py-3
        transition-all duration-300
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"}`}
    >
      <CheckCircle size={16} className="text-accent shrink-0" />
      <span className="text-sm text-text">{message}</span>
    </div>
  );
}
