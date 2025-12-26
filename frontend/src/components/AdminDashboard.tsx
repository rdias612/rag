import { useState } from 'react';
import {
    X,
    Activity,
    HardDrive,
    MessageSquare,
    ArrowLeft
} from 'lucide-react';
import { SystemOverview } from './admin/SystemOverview';
import { DocumentsPanel } from './admin/DocumentsPanel';
import { SessionsPanel } from './admin/SessionsPanel';

type TabId = 'overview' | 'documents' | 'sessions';

interface Tab {
    id: TabId;
    label: string;
    icon: typeof Activity;
}

const TABS: Tab[] = [
    { id: 'overview', label: 'Visão Geral', icon: Activity },
    { id: 'documents', label: 'Documentos', icon: HardDrive },
    { id: 'sessions', label: 'Sessões', icon: MessageSquare },
];

interface AdminDashboardProps {
    onClose: () => void;
}

export function AdminDashboard({ onClose }: AdminDashboardProps) {
    const [activeTab, setActiveTab] = useState<TabId>('overview');

    const renderContent = () => {
        switch (activeTab) {
            case 'overview':
                return <SystemOverview />;
            case 'documents':
                return <DocumentsPanel />;
            case 'sessions':
                return <SessionsPanel />;
            default:
                return <SystemOverview />;
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-[#09090b] flex flex-col animate-fade-in">
            {/* Header */}
            <header className="h-16 border-b border-white/5 bg-[#09090b] flex items-center justify-between px-4 md:px-6 shrink-0">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onClose}
                        className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft size={20} />
                        <span className="text-sm">Voltar ao Chat</span>
                    </button>
                </div>
                <h1 className="text-lg font-semibold text-white">
                    Painel de Administração
                </h1>
                <button
                    onClick={onClose}
                    className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                >
                    <X size={18} />
                </button>
            </header>

            {/* Main content area with tabs */}
            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar Tabs (Desktop) */}
                <nav className="hidden md:flex w-56 border-r border-white/5 flex-col p-4 shrink-0">
                    <div className="space-y-1">
                        {TABS.map((tab) => {
                            const Icon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id
                                            ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                            : 'text-zinc-400 hover:text-white hover:bg-white/5'
                                        }`}
                                >
                                    <Icon size={18} />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </div>
                </nav>

                {/* Mobile Tab Bar */}
                <div className="md:hidden fixed bottom-0 left-0 right-0 border-t border-white/5 bg-[#09090b] flex z-50">
                    {TABS.map((tab) => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex-1 flex flex-col items-center gap-1 py-3 text-xs transition-colors ${activeTab === tab.id
                                        ? 'text-indigo-400'
                                        : 'text-zinc-500'
                                    }`}
                            >
                                <Icon size={20} />
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                {/* Content Area */}
                <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
                    {renderContent()}
                </main>
            </div>
        </div>
    );
}
