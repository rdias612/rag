import { useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatArea } from "./components/ChatArea";
import { UploadModal } from "./components/UploadModal";
import { Toast } from "./components/Toast";
import { useToast } from "./hooks/useToast";
import type { Message, Session } from "./types";
import { fetchSessions, streamChat, createSession, deleteSession, fetchHistory, fetchCollections } from "./api";

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
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
        currentText = token; // Token contains full text from typewriter effect
        setMessages(prev => {
          const newMessages = [...prev];
          // Check if the assistant message at the expected index already exists and is an assistant message
          if (newMessages[assistantMsgIndex] && newMessages[assistantMsgIndex].role === 'assistant') {
            newMessages[assistantMsgIndex] = {
              ...newMessages[assistantMsgIndex],
              content: currentText
            };
          } else {
            // If not, add a new assistant message at the end
            newMessages.push({
              role: 'assistant',
              content: currentText,
              timestamp: Date.now()
            });
          }
          return newMessages;
        });
      });

      // Update with final message including sources
      setMessages(prev => {
        const newMessages = [...prev];
        // Ensure the message at assistantMsgIndex is the one we're updating
        if (newMessages[assistantMsgIndex] && newMessages[assistantMsgIndex].role === 'assistant') {
          newMessages[assistantMsgIndex] = {
            role: 'assistant',
            content: res.answer,
            timestamp: Date.now(),
            sources: res.sources
          };
        } else {
          // Fallback in case the index was off or message wasn't found (e.g., if streaming was very fast)
          newMessages.push({
            role: 'assistant',
            content: res.answer,
            timestamp: Date.now(),
            sources: res.sources
          });
        }
        return newMessages;
      });

      // Update session ID if it was new
      if (!currentSessionId && res.session_id) {
        setCurrentSessionId(res.session_id);
        loadSessions(); // Refresh list to show new session
      }

    } catch (error) {
      console.error("Chat error", error);

      let errorMessage = "Desculpe, encontrei um erro. Tente novamente.";

      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        errorMessage = "Não foi possível conectar ao servidor. Verifique sua conexão.";
      } else if (error instanceof Error && error.message.includes('timeout')) {
        errorMessage = "A requisição demorou muito. Tente novamente.";
      } else if (error instanceof Error && error.message.includes('401')) {
        errorMessage = "Sessão expirada. Por favor, recarregue a página.";
      }

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

  return (
    <div className="flex w-full h-full bg-transparent">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />
      <ChatArea
        messages={messages}
        isLoading={isLoading}
        onSend={handleSendMessage}
        onOpenUpload={() => setIsUploadOpen(true)}
        collections={collections}
        selectedCollection={selectedCollection}
        onSelectCollection={setSelectedCollection}
      />
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
    </div>
  );
}

export default App;
