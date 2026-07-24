import type { View } from "../types";
import type { Message } from "../App";
import Sidebar from "./Sidebar";
import ChatView from "./Chat/ChatView";
import DashboardView from "./Dashboard/DashboardView";
import PlanView from "./Plan/PlanView";
import ProgressView from "./Progress/ProgressView";
import NutritionView from "./Nutrition/NutritionView";
import ProfileView from "./Profile/ProfileView";
import TutorialOverlay from "./Tutorial/TutorialOverlay";

interface Props {
  currentView: View;
  onViewChange: (v: View) => void;
  onWorkoutLogged: (message: string) => void;
  onProfileSaved: () => void;
  sidebarRefreshKey: number;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  tutorialStep: number | null;
  tutorialHighlightTab: View | undefined;
  onTutorialNext: () => void;
  onTutorialSkip: () => void;
}

function MainContent({
  view, onWorkoutLogged, onProfileSaved, messages, setMessages,
}: {
  view: View;
  onWorkoutLogged: (msg: string) => void;
  onProfileSaved: () => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}) {
  return (
    <div className="h-full relative">
      {/* ChatView bleibt immer gemountet, wird nur versteckt */}
      <div className={view === "chat" ? "h-full" : "hidden"}>
        <ChatView messages={messages} setMessages={setMessages} />
      </div>
      {view === "dashboard" && <DashboardView />}
      {view === "plan" && <PlanView onWorkoutLogged={onWorkoutLogged} />}
      {view === "progress" && <ProgressView />}
      {view === "nutrition" && <NutritionView />}
      {view === "profile" && <ProfileView onSaved={onProfileSaved} />}
    </div>
  );
}

export default function Layout({
  currentView, onViewChange, onWorkoutLogged, onProfileSaved, sidebarRefreshKey,
  messages, setMessages, tutorialStep, tutorialHighlightTab, onTutorialNext, onTutorialSkip,
}: Props) {
  return (
    <div className="flex h-full">
      <Sidebar
        current={currentView}
        onChange={onViewChange}
        refreshKey={sidebarRefreshKey}
        tutorialHighlightTab={tutorialHighlightTab}
      />
      <main className="flex-1 min-w-0 overflow-hidden">
        <MainContent
          view={currentView}
          onWorkoutLogged={onWorkoutLogged}
          onProfileSaved={onProfileSaved}
          messages={messages}
          setMessages={setMessages}
        />
      </main>
      {tutorialStep !== null && (
        <TutorialOverlay
          step={tutorialStep}
          onNext={onTutorialNext}
          onSkip={onTutorialSkip}
        />
      )}
    </div>
  );
}
