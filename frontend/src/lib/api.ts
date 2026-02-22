// src/lib/api.ts
// Client-side API wrapper for interacting with the Python backend

export interface ChatMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatResponse {
    answer: string;
    turn_id: string;
    sources: string[];
    timestamp: string;
}

export interface ChatSession {
    chat_session_id: string;
    title?: string;
    created_at?: string;
    updated_at?: string;
}

// Redirect to login on 401 — clears stale session from localStorage
const handleUnauthorized = () => {
    localStorage.removeItem("session_id");
    window.location.href = "/login";
};

// Ensure error handling is robust
const handleResponse = async (response: Response) => {
    if (response.status === 401) {
        handleUnauthorized();
        // Return a never-resolving promise so the calling code doesn't proceed
        return new Promise(() => { }) as Promise<never>;
    }
    if (!response.ok) {
        let errorMsg = response.statusText;
        try {
            const errorData = await response.json();
            if (errorData.detail) {
                errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
            }
        } catch (e) {
            console.error(e);
        }
        throw new Error(`API Error (${response.status}): ${errorMsg}`);
    }
    return response.json();
};

export const api = {
    // --- AUTH OPERATIONS ---
    async login(email: string, password: string) {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        return handleResponse(res);
    },

    async register(email: string, username: string, password: string) {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username, password, confirm_password: password })
        });
        return handleResponse(res);
    },

    async logout(sessionId: string) {
        const res = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        return handleResponse(res);
    },

    async getProfile(sessionId: string) {
        const res = await fetch(`/api/auth/profile?session_id=${encodeURIComponent(sessionId)}`);
        return handleResponse(res);
    },

    async updateProfile(sessionId: string, openaiApiKey?: string, geminiApiKey?: string) {
        const res = await fetch('/api/auth/profile', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                openai_api_key: openaiApiKey,
                gemini_api_key: geminiApiKey
            })
        });
        return handleResponse(res);
    },

    // --- PDF / SESSION OPERATIONS ---
    async createChatSession(sessionId: string) {
        const params = new URLSearchParams();
        params.append('session_id', sessionId);

        const res = await fetch('/api/pdf/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params.toString()
        });
        return handleResponse(res);
    },

    async getAllSessions(sessionId: string, limit = 50): Promise<{ sessions: ChatSession[] }> {
        const res = await fetch(`/api/pdf/sessions?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
        return handleResponse(res);
    },

    async getChatSession(chatSessionId: string, sessionId: string) {
        const res = await fetch(`/api/pdf/session/${chatSessionId}?session_id=${encodeURIComponent(sessionId)}`);
        return handleResponse(res);
    },

    async deleteChatSession(chatSessionId: string, sessionId: string) {
        const res = await fetch(`/api/pdf/session/${chatSessionId}?session_id=${encodeURIComponent(sessionId)}`, {
            method: 'DELETE'
        });
        return handleResponse(res);
    },

    async renameSession(chatSessionId: string, sessionId: string, newTitle: string) {
        const res = await fetch(
            `/api/pdf/session/${chatSessionId}/rename?session_id=${encodeURIComponent(sessionId)}&new_title=${encodeURIComponent(newTitle)}`,
            { method: 'PATCH' }
        );
        return handleResponse(res);
    },

    async uploadPdf(file: File, sessionId: string, chatSessionId: string) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', sessionId);
        formData.append('chat_session_id', chatSessionId);

        const res = await fetch('/api/pdf/upload', {
            method: 'POST',
            body: formData
        });
        return handleResponse(res);
    },

    // --- CHAT OPERATIONS ---
    async getModels() {
        const res = await fetch('/api/chat/models');
        return handleResponse(res);
    },

    async getChatHistory(chatSessionId: string, sessionId: string, limit = 50) {
        const res = await fetch(
            `/api/chat/history/${chatSessionId}?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`
        );
        return handleResponse(res);
    },

    async sendChat(sessionId: string, chatSessionId: string, userInput: string, model: string = "llama3", activeSourceIds: string[] = []) {
        const res = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                chat_session_id: chatSessionId,
                user_input: userInput,
                model: model,
                active_source_ids: activeSourceIds
            })
        });
        return handleResponse(res);
    }
};
