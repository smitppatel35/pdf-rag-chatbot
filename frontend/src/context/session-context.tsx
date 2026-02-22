"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { api } from "@/lib/api";

interface SessionContextType {
    sessionId: string | null;
    chatSessionId: string | null;
    refreshTrigger: number;
    setSessionId: (id: string) => void;
    setChatSessionId: (id: string | null) => void;
    triggerRefresh: () => void;
    startNewChat: () => Promise<void>;
    switchToSession: (id: string) => void;
}

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [chatSessionId, setChatSessionId] = useState<string | null>(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const triggerRefresh = useCallback(() => {
        setRefreshTrigger(n => n + 1);
    }, []);

    const startNewChat = useCallback(async () => {
        if (!sessionId) return;
        try {
            const data = await api.createChatSession(sessionId);
            setChatSessionId(data.chat_session_id);
            triggerRefresh();
        } catch (e) {
            console.error("Failed to start new chat:", e);
        }
    }, [sessionId, triggerRefresh]);

    const switchToSession = useCallback((id: string) => {
        setChatSessionId(id);
    }, []);

    return (
        <SessionContext.Provider value={{
            sessionId,
            chatSessionId,
            refreshTrigger,
            setSessionId: (id) => setSessionId(id),
            setChatSessionId,
            triggerRefresh,
            startNewChat,
            switchToSession,
        }}>
            {children}
        </SessionContext.Provider>
    );
}

export function useSession() {
    const ctx = useContext(SessionContext);
    if (!ctx) throw new Error("useSession must be used within SessionProvider");
    return ctx;
}
