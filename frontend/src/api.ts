export const API_URL = "http://localhost:5000/api";

export async function fetchSessions() {
    const res = await fetch(`${API_URL}/chat/sessions`);
    if (!res.ok) throw new Error("Failed to fetch sessions");
    return res.json();
}

export async function fetchCollections() {
    const res = await fetch(`${API_URL}/collections`);
    if (!res.ok) throw new Error("Failed to fetch collections");
    return res.json();
}

export async function createSession() {
    const res = await fetch(`${API_URL}/chat/new`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create session");
    return res.json();
}

export async function deleteSession(sessionId: string) {
    const res = await fetch(`${API_URL}/chat/sessions/${sessionId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete session");
    return res.json();
}

export async function fetchHistory(sessionId: string) {
    const res = await fetch(`${API_URL}/chat/sessions/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
}

export async function streamChat(
    question: string,
    sessionId: string | null,
    collectionId: string | null,
    onToken: (token: string) => void,
    debug: boolean = false,
    temperature?: number,
    includeExplanation: boolean = true,
    responseStyle: string = "detailed"
) {
    const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            question,
            session_id: sessionId,
            collection: collectionId || undefined,
            debug: debug,
            temperature: temperature,
            include_explanation: includeExplanation,
            response_style: responseStyle
        })
    });

    if (!res.ok) throw new Error("Failed to send message");
    const data = await res.json();

    // Typewriter effect - simular streaming no cliente
    const fullText = data.answer;
    const words = fullText.split(' ');

    for (let i = 0; i < words.length; i++) {
        const partialText = words.slice(0, i + 1).join(' ');
        onToken(partialText);
        // Delay proporcional ao tamanho da palavra para efeito mais natural
        await new Promise(r => setTimeout(r, Math.min(30, 10 + words[i].length * 2)));
    }

    // Garantir que todo o texto foi enviado
    onToken(fullText);

    return data;
}

export async function submitFeedback(sessionId: string, messageIndex: number, rating: number, comment?: string) {
    const res = await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sessionId,
            message_index: messageIndex,
            rating,
            comment
        })
    });
    if (!res.ok) throw new Error("Failed to submit feedback");
    return res.json();
}
