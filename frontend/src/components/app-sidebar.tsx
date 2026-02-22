"use client";

import { useEffect, useState, useCallback } from "react";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { api, ChatSession } from "@/lib/api";
import { useSession } from "@/context/session-context";
import { MessageSquare, Plus, Trash2, Loader2 } from "lucide-react";

export function AppSidebar() {
    const { sessionId, chatSessionId, switchToSession, startNewChat, refreshTrigger } = useSession();
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const fetchSessions = useCallback(async () => {
        if (!sessionId) return;
        try {
            setIsLoading(true);
            const data = await api.getAllSessions(sessionId);
            setSessions(data.sessions ?? []);
        } catch (e) {
            console.error("Failed to load sessions:", e);
        } finally {
            setIsLoading(false);
        }
    }, [sessionId]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions, refreshTrigger]);

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        if (!sessionId) return;
        try {
            await api.deleteChatSession(id, sessionId);
            setSessions(prev => prev.filter(s => s.chat_session_id !== id));
            if (chatSessionId === id) startNewChat();
        } catch (err) {
            console.error("Failed to delete session:", err);
        }
    };

    return (
        <Sidebar>
            <SidebarContent>
                <div className="p-3 pt-4">
                    <Button
                        variant="outline"
                        className="w-full justify-start gap-2 text-sm"
                        onClick={startNewChat}
                    >
                        <Plus className="h-4 w-4" />
                        New Chat
                    </Button>
                </div>

                <SidebarGroup>
                    <SidebarGroupLabel className="flex items-center gap-1">
                        Recent Chats
                        {isLoading && <Loader2 className="h-3 w-3 animate-spin ml-1" />}
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {sessions.length === 0 && !isLoading && (
                                <p className="text-xs text-muted-foreground px-3 py-2">No sessions yet</p>
                            )}
                            {sessions.map((session) => (
                                <SidebarMenuItem key={session.chat_session_id}>
                                    <SidebarMenuButton
                                        asChild
                                        isActive={session.chat_session_id === chatSessionId}
                                    >
                                        <button
                                            className="flex w-full items-center gap-2 group"
                                            onClick={() => switchToSession(session.chat_session_id)}
                                        >
                                            <MessageSquare className="h-4 w-4 shrink-0" />
                                            <span className="flex-1 truncate text-left text-sm">
                                                {session.title ?? "Untitled Chat"}
                                            </span>
                                            <span
                                                role="button"
                                                className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:text-destructive rounded"
                                                onClick={(e) => handleDelete(e, session.chat_session_id)}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </span>
                                        </button>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </Sidebar>
    );
}
