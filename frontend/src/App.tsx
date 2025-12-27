import { useState, useEffect } from "react";
import { Settings, Menu, Bug, Sun, Moon } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ChatArea } from "./components/ChatArea";
import { UploadModal } from "./components/UploadModal";
import { AdminDashboard } from "./components/AdminDashboard";
import { Toast } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import { useTheme } from "./components/ThemeContext";
import type { Message, Session } from "./types";
import { fetchSessions, streamChat, createSession, deleteSession, fetchHistory, fetchCollections, submitFeedback } from "./api";

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAdminOpen, setIsAdminOpen] = useState(false);
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [debugMode, setDebugMode] = useState(false);
  const [temperature, setTemperature] = useState<number | undefined>(undefined);
  const { theme, toggleTheme } = useTheme();
  const { toast, showToast, hideToast } = useToast();

  // Load initial sessions
  useEffect(() => {
    loadSessions();
    loadCollections();
  }, []);

  async function loadSessions() {
    try {
      const data = await fetchSessions();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error("Failed to load sessions", error);
      showToast("Não foi possível carregar as sessões. Verifique sua conexão.", "error");
    }
  }

  async function handleSelectSession(sessionId: string) {
    setCurrentSessionId(sessionId);
    setIsSidebarOpen(false); // close on mobile
    setIsLoading(true);
    try {
      const history = await fetchHistory(sessionId);
      if (history && history.messages) {
        setMessages(history.messages);
      }
    } catch (error) {
      console.error("Failed to load history", error);
      showToast("Erro ao carregar histórico da sessão.", "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function loadCollections() {
    try {
      const data = await fetchCollections();
      setCollections(data.collections || []);
    } catch (error) {
      console.error("Failed to load collections", error);
      showToast("Não foi possível carregar as coleções.", "error");
    }
  }

  async function handleNewChat() {
    try {
      const newSession = await createSession();
      setCurrentSessionId(newSession.session_id);
      setMessages([]);
      setIsSidebarOpen(false);
      loadSessions();
    } catch (error) {
      console.error("Failed to create session", error);
      showToast("Não foi possível criar nova sessão.", "error");
    }
  }

  async function handleSendMessage(content: string) {
    // Optimistic UI update
    const userMsg: Message = { role: 'user', content, timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // Create placeholder for assistant message
    const assistantMsgIndex = messages.length + 1;

    try {
      let currentText = "";

      const res = await streamChat(content, currentSessionId, selectedCollection, (token) => {
        currentText = token;
        setMessages(prev => {
          const newMessages = [...prev];
          if (newMessages[assistantMsgIndex] && newMessages[assistantMsgIndex].role === 'assistant') {
            newMessages[assistantMsgIndex] = {
              ...newMessages[assistantMsgIndex],
              content: currentText
            };
          } else {
            newMessages.push({
              role: 'assistant',
              content: currentText,
              timestamp: Date.now()
            });
          }
          return newMessages;
        });
      }, debugMode, temperature);

      // Update with final message including sources
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[assistantMsgIndex] && newMessages[assistantMsgIndex].role === 'assistant') {
          newMessages[assistantMsgIndex] = {
            role: 'assistant',
            content: res.answer,
            timestamp: Date.now(),
            sources: res.sources,
            debugInfo: res._debug
          };
        } else {
          newMessages.push({
            role: 'assistant',
            content: res.answer,
            timestamp: Date.now(),
            sources: res.sources,
            debugInfo: res._debug
          });
        }
        return newMessages;
      });

      if (!currentSessionId && res.session_id) {
        setCurrentSessionId(res.session_id);
        loadSessions();
      }

    } catch (error) {
      console.error("Chat error", error);
      let errorMessage = "Desculpe, encontrei um erro. Tente novamente.";
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        errorMessage = "Não foi possível conectar ao servidor. Verifique sua conexão.";
      }
      // ... more error handling if needed ...

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage
      }]);
      showToast(errorMessage, "error");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteSession(e: React.MouseEvent, sessionId: string) {
    e.stopPropagation();
    if (!confirm("Tem certeza que deseja excluir este chat?")) return;

    try {
      await deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
      showToast("Chat excluído com sucesso.", "success");
    } catch (error) {
      console.error("Failed to delete", error);
      showToast("Erro ao excluir chat.", "error");
    }
  }

  async function handleFeedback(messageIndex: number, rating: number) {
    if (!currentSessionId) return;

    try {
      await submitFeedback(currentSessionId, messageIndex, rating);

      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[messageIndex]) {
          newMessages[messageIndex] = {
            ...newMessages[messageIndex],
            feedback: rating === 1 ? 'good' : 'bad'
          };
        }
        return newMessages;
      });

      showToast("Feedback registrado. Obrigado!", "success");
    } catch (error) {
      console.error("Feedback error", error);
      showToast("Erro ao registrar feedback.", "error");
    }
  }

  return (
    <div className={`flex h-screen bg-chat text-text-primary font-sans overflow-hidden selection:bg-accent-primary/20 ${theme}`}>

      {/* Sidebar - Fixed on desktop, Drawer on mobile */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        temperature={temperature}
        setTemperature={setTemperature}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full relative w-full md:pl-0 transition-all duration-300">

        {/* Header */}
        <header className="h-16 border-b border-border bg-chat/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2 text-text-secondary hover:text-text-primary"
            >
              <Menu size={20} />
            </button>
            <div className="md:hidden flex items-center gap-2">
              <span className="font-semibold text-sm text-text-primary">RAG Assistant</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <select
              className="bg-card text-xs font-medium text-text-primary px-3 py-1.5 rounded-lg border border-border focus:border-accent-primary focus:outline-none hover:bg-surface transition-colors cursor-pointer"
              value={selectedCollection || ""}
              onChange={(e) => setSelectedCollection(e.target.value || null)}
            >
              <option value="">Todas as coleções</option>
              {collections.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="w-9 h-9 flex items-center justify-center rounded-lg bg-surface border border-border text-text-secondary hover:text-text-primary transition-colors"
              title={theme === 'dark' ? "Mudar para tema claro" : "Mudar para tema escuro"}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            {/* Debug Toggle */}
            <button
              onClick={() => setDebugMode(!debugMode)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border transition-all ${debugMode
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                : 'bg-surface text-text-secondary border-border hover:border-text-secondary'
                }`}
              title={debugMode ? "Debug ativado" : "Debug desativado"}
            >
              <Bug size={14} />
              <span className="hidden sm:inline">{debugMode ? 'ON' : 'OFF'}</span>
            </button>

            <button
              onClick={() => setIsAdminOpen(true)}
              className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-surface text-text-secondary hover:text-text-primary transition-colors"
              title="Painel de Administração"
            >
              <Settings size={18} />
            </button>
          </div>
        </header>

        {/* Scrollable Chat Area */}
        <div className="flex-1 overflow-hidden relative">
          <ChatArea
            messages={messages}
            isLoading={isLoading}
            onSend={handleSendMessage}
            onOpenUpload={() => setIsUploadOpen(true)}
            onFeedback={handleFeedback}
          />
        </div>

      </main>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
      />
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />

      {/* Admin Dashboard Overlay */}
      {isAdminOpen && (
        <AdminDashboard onClose={() => setIsAdminOpen(false)} />
      )}
    </div>
  );
}

export default App;
