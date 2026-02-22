"use client";

import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from "react";
import { api } from "@/lib/api";

interface SessionContextType {
    sessionId: string | null;
    chatSessionId: string | null;
    refreshTrigger: number;
    setSessionId: (id: string | null) => void;
    setChatSessionId: (id: string | null) => void;
    triggerRefresh: () => void;
    startNewChat: () => Promise<void>;
    switchToSession: (id: string) => void;
    logout: () => Promise<void>;
    hasApiKey: boolean;
    isProfileLoaded: boolean;
}

const SessionContext = createContext<SessionContextType | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
    const [sessionId, setSessionIdState] = useState<string | null>(null);
    const [chatSessionId, setChatSessionId] = useState<string | null>(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [hasApiKey, setHasApiKey] = useState<boolean>(false);
    const [isProfileLoaded, setIsProfileLoaded] = useState<boolean>(false);

    const triggerRefresh = useCallback(() => {
        setRefreshTrigger(n => n + 1);
    }, []);

    const setSessionId = useCallback((id: string | null) => {
        if (id) {
            localStorage.setItem("session_id", id);
        } else {
            localStorage.removeItem("session_id");
            setChatSessionId(null);
        }
        setSessionIdState(id);
    }, []);

    useEffect(() => {
        const stored = localStorage.getItem("session_id");
        if (stored && !sessionId) {
            setSessionIdState(stored);
        }
    }, [sessionId]);

    useEffect(() => {
        if (sessionId) {
            api.getProfile(sessionId)
                .then(profile => {
                    setHasApiKey(!!(profile.openai_api_key || profile.gemini_api_key));
                    setIsProfileLoaded(true);
                })
                .catch(err => {
                    console.error("Failed to fetch profile in SessionProvider", err);
                    setIsProfileLoaded(true);
                });
        } else {
            setHasApiKey(false);
            setIsProfileLoaded(false);
        }
    }, [sessionId, refreshTrigger]);

    const logout = useCallback(async () => {
        if (sessionId) {
            try {
                await api.logout(sessionId);
            } catch (e) {
                console.error("Logout failed", e);
            }
            setSessionId(null);
            // hard reload to reset state
            window.location.href = "/login";
        }
    }, [sessionId, setSessionId]);

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
            setSessionId,
            setChatSessionId,
            triggerRefresh,
            startNewChat,
            switchToSession,
            logout,
            hasApiKey,
            isProfileLoaded,
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
