import { useState, useCallback, useEffect } from "react";
import type { View } from "./types";
import Layout from "./components/Layout";
import Toast from "./components/Toast";
import SetupModal from "./components/Profile/SetupModal";
import { api } from "./api/backend";
import { sendChatMessage } from "./api/rasa";
import { TUTORIAL_STEPS } from "./components/Tutorial/TutorialOverlay";

const TUTORIAL_KEY = "fitcoach_tutorial_done";

export interface QuickReply {
  title: string;
  payload: string;
}

interface Message {
  id: number;
  role: "user" | "bot";
  text: string;
  timestamp: Date;
  buttons?: QuickReply[];
}

interface ToastState {
  id: number;
  message: string;
}

let msgId = 0;
export function newMsg(role: "user" | "bot", text: string, buttons?: QuickReply[]): Message {
  return { id: ++msgId, role, text, timestamp: new Date(), buttons };
}

export type { Message };

export default function App() {
  const [currentView, setCurrentView] = useState<View>("chat");
  const [toast, setToast] = useState<ToastState | null>(null);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [tutorialStep, setTutorialStep] = useState<number | null>(null);

  const bumpSidebar = useCallback(() => setSidebarRefreshKey((k) => k + 1), []);

  const showToast = useCallback((message: string) => {
    setToast({ id: Date.now(), message });
    setSidebarRefreshKey((k) => k + 1);
  }, []);

  function startTutorialIfNeeded() {
    if (!localStorage.getItem(TUTORIAL_KEY)) {
      setTimeout(() => setTutorialStep(0), 600);
    }
  }

  async function triggerRasaGreet() {
    try {
      const responses = await sendChatMessage("/greet");
      if (responses.length > 0) {
        setMessages(
          responses
            .filter((r) => r.text)
            .map((r) => newMsg("bot", r.text!, r.buttons))
        );
      }
    } catch {
      setMessages([newMsg("bot", "Hi! Ich bin dein FitCoach. Wie kann ich dir helfen?")]);
    }
  }

  useEffect(() => {
    const handler = async () => {
      setCurrentView("chat");
      setMessages((prev) => [...prev, newMsg("user", "Ich habe gerade trainiert")]);
      try {
        const responses = await sendChatMessage("Ich habe gerade trainiert");
        const botMsgs = responses.filter((r) => r.text).map((r) => newMsg("bot", r.text!, r.buttons));
        if (botMsgs.length > 0) {
          setMessages((prev) => [...prev, ...botMsgs]);
          const activityKeywords = ["eingetragen", "Punkte erhalten", "neuen Streak", "Workout geloggt"];
          if (botMsgs.some((m) => activityKeywords.some((kw) => m.text?.includes(kw)))) {
            window.dispatchEvent(new CustomEvent("activity_logged"));
          }
        }
      } catch {}
    };
    window.addEventListener("workout_completed", handler);
    return () => window.removeEventListener("workout_completed", handler);
  }, []);

  useEffect(() => {
    api.getProfile()
      .then((p) => {
        setProfileLoaded(true);

        // Frisches Profil → Tutorial-Flag zurücksetzen damit Intro neu startet
        if (!p.onboarded) {
          localStorage.removeItem(TUTORIAL_KEY);
        }

        if (!p.name) {
          setShowSetupModal(true);
          return;
        }

        triggerRasaGreet();
        startTutorialIfNeeded();
      })
      .catch(() => {
        setProfileLoaded(true);
        setMessages([newMsg("bot", "Hi! Ich bin dein FitCoach. Wie kann ich dir helfen?")]);
      });
  }, []);

  function handleSetupComplete(name: string) {
    setShowSetupModal(false);
    bumpSidebar();
    const greeting = name
      ? `Super, schön dich kennenzulernen, ${name}! 👋`
      : "Super, willkommen bei FitCoach!";
    setMessages([
      newMsg("bot", greeting, [
        { title: "🚀 Trainingsplan erstellen", payload: "/start_onboarding" },
      ]),
    ]);
    startTutorialIfNeeded();
  }

  function handleTutorialNext() {
    if (tutorialStep === null) return;
    const next = tutorialStep + 1;
    if (next >= TUTORIAL_STEPS.length) {
      localStorage.setItem(TUTORIAL_KEY, "1");
      setTutorialStep(null);
      setCurrentView("chat");
    } else {
      setTutorialStep(next);
      const tab = TUTORIAL_STEPS[next].highlightTab;
      if (tab) setCurrentView(tab);
    }
  }

  function handleTutorialSkip() {
    localStorage.setItem(TUTORIAL_KEY, "1");
    setTutorialStep(null);
  }

  const tutorialHighlightTab =
    tutorialStep !== null ? TUTORIAL_STEPS[tutorialStep]?.highlightTab : undefined;

  return (
    <>
      {profileLoaded && showSetupModal && (
        <SetupModal onComplete={handleSetupComplete} />
      )}
      <Layout
        currentView={currentView}
        onViewChange={setCurrentView}
        onWorkoutLogged={showToast}
        onProfileSaved={bumpSidebar}
        sidebarRefreshKey={sidebarRefreshKey}
        messages={messages}
        setMessages={setMessages}
        tutorialStep={tutorialStep}
        tutorialHighlightTab={tutorialHighlightTab}
        onTutorialNext={handleTutorialNext}
        onTutorialSkip={handleTutorialSkip}
      />
      {toast && (
        <Toast key={toast.id} message={toast.message} onDone={() => setToast(null)} />
      )}
    </>
  );
}
