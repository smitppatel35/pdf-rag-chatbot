"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api, ChatMessage } from "@/lib/api";
import { useSession } from "@/context/session-context";

export function useChatSession() {
    const { sessionId, chatSessionId, setSessionId, setChatSessionId, triggerRefresh, hasApiKey, isProfileLoaded } = useSession();

    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [model, setModel] = useState("llama3");
    const [activeSourceIds, setActiveSourceIds] = useState<string[]>([]);
    const [isInitializing, setIsInitializing] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const chatAreaRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (chatAreaRef.current) {
            chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
        }
    }, [messages, isGenerating]);

    const router = useRouter();

    // Redirect to login if not authenticated
    useEffect(() => {
        const storedSession = localStorage.getItem("session_id");
        if (!storedSession && !sessionId) {
            router.push("/login");
        }
    }, [sessionId, router]);

    // Initial auth + first chat session
    useEffect(() => {
        const init = async () => {
            if (!sessionId) return;

            try {
                // If there's no chat session active, create a new one
                if (!chatSessionId) {
                    const chatData = await api.createChatSession(sessionId);
                    setChatSessionId(chatData.chat_session_id);
                    triggerRefresh();

                    setMessages([{
                        role: "assistant",
                        content: "Hello! I'm ready to help. Upload a document (up to 10MB) using the paperclip icon below, or just ask a question.",
                    }]);
                }
            } catch (error) {
                console.error("Failed to initialize session:", error);
                setMessages([{ role: "assistant", content: "Error connecting to the server. Please check the backend is running on port 8000." }]);
            } finally {
                setIsInitializing(false);
            }
        };
        init();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    // Load history when switching sessions
    const loadHistory = useCallback(async (sessId: string, chatSessId: string) => {
        try {
            setIsLoadingHistory(true);
            setMessages([]);
            const data = await api.getChatHistory(chatSessId, sessId);
            const history: ChatMessage[] = [];
            (data.messages ?? []).forEach((m: { user_query: string; ai_response: string }) => {
                if (m.user_query) {
                    history.push({ role: "user", content: m.user_query });
                }
                if (m.ai_response) {
                    history.push({ role: "assistant", content: m.ai_response });
                }
            });
            setMessages(
                history.length > 0
                    ? history
                    : [{ role: "assistant", content: "Session loaded. What would you like to discuss?" }]
            );
            setActiveSourceIds([]);
        } catch (e) {
            console.error("Failed to load history:", e);
            setMessages([{ role: "assistant", content: "Could not load chat history." }]);
        } finally {
            setIsLoadingHistory(false);
        }
    }, []);

    const prevChatSessionIdRef = useRef<string | null>(null);
    useEffect(() => {
        if (!sessionId || !chatSessionId) return;
        if (chatSessionId === prevChatSessionIdRef.current) return;
        prevChatSessionIdRef.current = chatSessionId;
        if (!isInitializing) {
            loadHistory(sessionId, chatSessionId);
        }
    }, [chatSessionId, sessionId, isInitializing, loadHistory]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !sessionId || !chatSessionId) return;

        if (file.size > 10 * 1024 * 1024) {
            alert("File is larger than 10MB limit.");
            return;
        }

        try {
            setIsUploading(true);
            setMessages((prev) => [...prev, { role: "user", content: `[Attached Document: ${file.name}]` }]);

            const uploadResponse = await api.uploadPdf(file, sessionId, chatSessionId);
            if (uploadResponse?.new_source?.source_id) {
                setActiveSourceIds((prev) => [...prev, uploadResponse.new_source.source_id]);
            }

            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `I've processed **${file.name}**. What would you like to know about it?` },
            ]);
            triggerRefresh();
        } catch (err) {
            console.error("Upload error:", err);
            setMessages((prev) => prev.slice(0, -1));
            alert("Failed to upload the document. Please try again.");
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleSendMessage = async () => {
        if (!input.trim() || !sessionId || !chatSessionId || isGenerating) return;

        const userMessage = input.trim();
        setInput("");
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setIsGenerating(true);

        try {
            const response = await api.sendChat(sessionId, chatSessionId, userMessage, model, activeSourceIds);
            setMessages((prev) => [...prev, { role: "assistant", content: response.answer }]);
            triggerRefresh();
        } catch (err) {
            console.error("Chat error:", err);
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I encountered an error. Please ensure the backend is running." },
            ]);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return {
        messages,
        input,
        setInput,
        model,
        setModel,
        isInitializing,
        isUploading,
        isGenerating,
        isLoadingHistory,
        fileInputRef,
        chatAreaRef,
        handleFileUpload,
        handleSendMessage,
        handleKeyDown,
        hasApiKey,
        isProfileLoaded,
    };
}
