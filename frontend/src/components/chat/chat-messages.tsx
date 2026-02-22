"use client";

import { RefObject } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Loader2, Bot, User } from "lucide-react";
import { ChatMessage } from "@/lib/api";

interface ChatMessagesProps {
    messages: ChatMessage[];
    isGenerating: boolean;
    isLoadingHistory: boolean;
    chatAreaRef: RefObject<HTMLDivElement | null>;
}

function TypingIndicator() {
    return (
        <div className="flex items-start gap-4">
            <Avatar className="w-8 h-8 rounded-full border bg-primary text-primary-foreground min-w-8 min-h-8">
                <AvatarFallback><Bot className="w-4 h-4" /></AvatarFallback>
            </Avatar>
            <div className="flex flex-col gap-2">
                <div className="font-medium text-xs text-muted-foreground">Assistant</div>
                <div className="text-sm rounded-2xl px-4 py-2.5 flex items-center h-[42px]">
                    <span className="flex gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce" />
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:-.3s]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:-.5s]" />
                    </span>
                </div>
            </div>
        </div>
    );
}

function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === "user";
    return (
        <div className={`flex items-start gap-4 ${isUser ? "justify-end" : ""}`}>
            {!isUser && (
                <Avatar className="w-8 h-8 rounded-full border bg-primary text-primary-foreground min-w-8 min-h-8">
                    <AvatarFallback><Bot className="w-4 h-4" /></AvatarFallback>
                </Avatar>
            )}
            <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
                <div className="font-medium text-xs text-muted-foreground">
                    {isUser ? "You" : "Assistant"}
                </div>
                <div
                    className={`text-sm prose prose-sm dark:prose-invert rounded-2xl px-4 py-2.5 ${isUser ? "bg-muted/60 border" : ""
                        }`}
                >
                    <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                </div>
            </div>
            {isUser && (
                <Avatar className="w-8 h-8 rounded-full border min-w-8 min-h-8">
                    <AvatarFallback><User className="w-4 h-4" /></AvatarFallback>
                </Avatar>
            )}
        </div>
    );
}

export function ChatMessages({
    messages,
    isGenerating,
    isLoadingHistory,
    chatAreaRef,
}: ChatMessagesProps) {
    return (
        <div
            ref={chatAreaRef}
            className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6 lg:p-8"
        >
            <div className="mx-auto flex max-w-3xl flex-col gap-6 pb-12">
                {isLoadingHistory ? (
                    <div className="flex justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : (
                    messages.map((message, i) => (
                        <MessageBubble key={i} message={message} />
                    ))
                )}
                {isGenerating && <TypingIndicator />}
            </div>
        </div>
    );
}
