import { useState, useEffect } from 'react';
import {
    FileText,
    Plus,
    Edit2,
    Trash2,
    AlertCircle,
    X,
    Save,
    Tag
} from 'lucide-react';

interface Prompt {
    id: number;
    name: string;
    template: string;
    category: string;
    priority: number;
    tags: string[];
    description: string;
    use_case: string;
    is_active: boolean;
    updated_at: string;
    created_by: string;
}

export function PromptsManagement() {
    const [prompts, setPrompts] = useState<Prompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

    // Carregar prompts
    useEffect(() => {
        fetchPrompts();
    }, []);

    // Fechar modal com ESC
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && editingPrompt) {
                setEditingPrompt(null);
                setIsCreating(false);
            }
        };

        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [editingPrompt]);

    const fetchPrompts = async () => {
        try {
            setLoading(true);
            const response = await fetch('http://localhost:5000/api/prompts');
            const data = await response.json();
            setPrompts(data.prompts || []);
        } catch (err) {
            setError('Erro ao carregar prompts');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = async (promptId: number) => {
        try {
            // Buscar dados completos do prompt (incluindo template)
            const response = await fetch(`http://localhost:5000/api/prompts/${promptId}`);
            const promptData = await response.json();

            setEditingPrompt(promptData);
            setIsCreating(false);
        } catch (err) {
            alert('Erro ao carregar dados do prompt');
            console.error(err);
        }
    };

    const handleDelete = async (id: number) => {
        try {
            // Verificar se pode deletar
            const checkRes = await fetch(`http://localhost:5000/api/prompts/${id}/can-delete`);
            const checkData = await checkRes.json();

            if (!checkData.can_delete) {
                alert(checkData.reason);
                return;
            }

            // Deletar
            const res = await fetch(`http://localhost:5000/api/prompts/${id}`, {
                method: 'DELETE'
            });

            if (!res.ok) {
                const errorData = await res.json();
                alert(errorData.error);
                return;
            }

            setDeleteConfirm(null);
            fetchPrompts();
        } catch (err) {
            alert('Erro ao deletar prompt');
            console.error(err);
        }
    };

    const handleSave = async () => {
        if (!editingPrompt) return;

        try {
            const isNew = editingPrompt.id === 0;
            const url = isNew
                ? 'http://localhost:5000/api/prompts'
                : `http://localhost:5000/api/prompts/${editingPrompt.id}`;

            const method = isNew ? 'POST' : 'PUT';

            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: editingPrompt.name,
                    template: editingPrompt.template,
                    category: editingPrompt.category,
                    description: editingPrompt.description,
                    priority: editingPrompt.priority,
                    tags: editingPrompt.tags,
                    use_case: editingPrompt.use_case,
                    is_active: editingPrompt.is_active
                })
            });

            if (!res.ok) {
                const errorData = await res.json();
                alert(errorData.error);
                return;
            }

            setEditingPrompt(null);
            setIsCreating(false);
            fetchPrompts();
        } catch (err) {
            alert('Erro ao salvar prompt');
            console.error(err);
        }
    };

    const openCreateModal = () => {
        setEditingPrompt({
            id: 0,
            name: '',
            template: '',
            category: 'rag_main',
            priority: 100,
            tags: [],
            description: '',
            use_case: '',
            is_active: true,
            updated_at: '',
            created_by: 'user'
        });
        setIsCreating(true);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center gap-2 text-red-400 bg-red-400/10 p-4 rounded-lg">
                <AlertCircle size={20} />
                {error}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-semibold text-text-primary">Gerenciamento de Prompts</h2>
                    <p className="text-sm text-text-secondary mt-1">
                        Total: {prompts.length} prompts
                    </p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/90 transition-colors"
                >
                    <Plus size={18} />
                    Novo Prompt
                </button>
            </div>

            {/* Prompts Table */}
            <div className="bg-surface border border-border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-chat border-b border-border">
                            <tr>
                                <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Nome
                                </th>
                                <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Categoria
                                </th>
                                <th className="text-center px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Prioridade
                                </th>
                                <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Tags
                                </th>
                                <th className="text-left px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Descrição
                                </th>
                                <th className="text-center px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="text-right px-4 py-3 text-xs font-medium text-text-secondary uppercase tracking-wider">
                                    Ações
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {prompts.map((prompt) => (
                                <>
                                    <tr
                                        key={prompt.id}
                                        className="hover:bg-chat/50 transition-colors"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <FileText size={14} className="text-accent-primary shrink-0" />
                                                <span className="text-sm font-medium text-text-primary truncate max-w-[200px]">
                                                    {prompt.name}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="inline-flex px-2 py-1 bg-accent-primary/10 text-accent-primary text-xs rounded-full">
                                                {prompt.category}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className="text-sm text-text-primary font-mono">
                                                {prompt.priority}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex flex-wrap gap-1">
                                                {prompt.tags && prompt.tags.length > 0 ? (
                                                    prompt.tags.slice(0, 2).map((tag, idx) => (
                                                        <span
                                                            key={idx}
                                                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-surface border border-border text-xs text-text-secondary rounded"
                                                        >
                                                            <Tag size={10} />
                                                            {tag}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="text-xs text-text-secondary">—</span>
                                                )}
                                                {prompt.tags && prompt.tags.length > 2 && (
                                                    <span className="text-xs text-text-secondary">
                                                        +{prompt.tags.length - 2}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="text-sm text-text-secondary truncate max-w-[300px] block">
                                                {prompt.description || '—'}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            {prompt.is_active ? (
                                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/10 text-green-500 text-xs rounded-full">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                                                    Ativo
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-500/10 text-yellow-500 text-xs rounded-full">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
                                                    Inativo
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleEdit(prompt.id)}
                                                    className="p-1.5 hover:bg-accent-primary/10 text-text-secondary hover:text-accent-primary rounded transition-colors"
                                                    title="Editar"
                                                >
                                                    <Edit2 size={14} />
                                                </button>
                                                <button
                                                    onClick={() => setDeleteConfirm(prompt.id)}
                                                    className="p-1.5 hover:bg-red-500/10 text-text-secondary hover:text-red-500 rounded transition-colors"
                                                    title="Deletar"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    {/* Delete Confirmation Row */}
                                    {deleteConfirm === prompt.id && (
                                        <tr className="bg-red-500/5">
                                            <td colSpan={7} className="px-4 py-3">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm text-text-secondary">
                                                        Tem certeza que deseja deletar este prompt?
                                                    </span>
                                                    <div className="flex gap-2">
                                                        <button
                                                            onClick={() => handleDelete(prompt.id)}
                                                            className="px-3 py-1.5 bg-red-500 text-white text-sm rounded hover:bg-red-600 transition-colors"
                                                        >
                                                            Confirmar
                                                        </button>
                                                        <button
                                                            onClick={() => setDeleteConfirm(null)}
                                                            className="px-3 py-1.5 bg-surface text-text-secondary text-sm rounded hover:bg-surface/80 transition-colors border border-border"
                                                        >
                                                            Cancelar
                                                        </button>
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Empty State */}
                {prompts.length === 0 && (
                    <div className="text-center py-12">
                        <FileText size={48} className="mx-auto text-text-secondary opacity-50 mb-3" />
                        <p className="text-text-secondary">Nenhum prompt encontrado</p>
                    </div>
                )}
            </div>

            {/* Editor Modal */}
            {editingPrompt && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-card border border-border rounded-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto">
                        <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-text-primary">
                                {isCreating ? 'Novo Prompt' : 'Editar Prompt'}
                            </h3>
                            <button
                                onClick={() => {
                                    setEditingPrompt(null);
                                    setIsCreating(false);
                                }}
                                className="p-2 hover:bg-surface rounded-lg transition-colors"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="p-4 space-y-4">
                            {/* Name */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-1">
                                    Nome *
                                </label>
                                <input
                                    type="text"
                                    value={editingPrompt.name}
                                    onChange={(e) => setEditingPrompt({ ...editingPrompt, name: e.target.value })}
                                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                    placeholder="ex: my_custom_prompt"
                                    disabled={!isCreating}
                                />
                            </div>

                            {/* Category & Priority */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-text-primary mb-1">
                                        Categoria *
                                    </label>
                                    <select
                                        value={editingPrompt.category}
                                        onChange={(e) => setEditingPrompt({ ...editingPrompt, category: e.target.value })}
                                        className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                        disabled={!isCreating}
                                    >
                                        <option value="rag_main">RAG Main</option>
                                        <option value="hyde">HyDE</option>
                                        <option value="query_expansion">Query Expansion</option>
                                        <option value="instruction">Instruction</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-text-primary mb-1">
                                        Prioridade
                                    </label>
                                    <input
                                        type="number"
                                        value={editingPrompt.priority}
                                        onChange={(e) => setEditingPrompt({ ...editingPrompt, priority: parseInt(e.target.value) })}
                                        className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                    />
                                </div>
                            </div>

                            {/* Description */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-1">
                                    Descrição
                                </label>
                                <input
                                    type="text"
                                    value={editingPrompt.description}
                                    onChange={(e) => setEditingPrompt({ ...editingPrompt, description: e.target.value })}
                                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                />
                            </div>

                            {/* Template */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-1">
                                    Template *
                                </label>
                                <textarea
                                    value={editingPrompt.template}
                                    onChange={(e) => setEditingPrompt({ ...editingPrompt, template: e.target.value })}
                                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary font-mono text-sm"
                                    rows={10}
                                    placeholder="Escreva seu template aqui..."
                                />
                            </div>

                            {/* Tags */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-1">
                                    Tags (separadas por vírgula)
                                </label>
                                <input
                                    type="text"
                                    value={editingPrompt.tags.join(', ')}
                                    onChange={(e) => setEditingPrompt({
                                        ...editingPrompt,
                                        tags: e.target.value.split(',').map(t => t.trim()).filter(t => t)
                                    })}
                                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                    placeholder="ex: quick, technical, default"
                                />
                            </div>

                            {/* Use Case */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-1">
                                    Caso de Uso
                                </label>
                                <textarea
                                    value={editingPrompt.use_case}
                                    onChange={(e) => setEditingPrompt({ ...editingPrompt, use_case: e.target.value })}
                                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                    rows={2}
                                    placeholder="Quando usar este prompt..."
                                />
                            </div>

                            {/* Is Active */}
                            {!isCreating && (
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={editingPrompt.is_active}
                                        onChange={(e) => setEditingPrompt({ ...editingPrompt, is_active: e.target.checked })}
                                        className="w-4 h-4 rounded border-border bg-surface text-accent-primary focus:ring-accent-primary focus:ring-offset-0"
                                    />
                                    <span className="text-sm text-text-primary">Prompt ativo</span>
                                </label>
                            )}

                            {/* Actions */}
                            <div className="flex gap-2 pt-4 border-t border-border">
                                <button
                                    onClick={handleSave}
                                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white rounded-lg hover:bg-accent-primary/90 transition-colors"
                                >
                                    <Save size={16} />
                                    Salvar
                                </button>
                                <button
                                    onClick={() => {
                                        setEditingPrompt(null);
                                        setIsCreating(false);
                                    }}
                                    className="px-4 py-2 bg-surface text-text-secondary rounded-lg hover:bg-surface/80 transition-colors"
                                >
                                    Cancelar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
