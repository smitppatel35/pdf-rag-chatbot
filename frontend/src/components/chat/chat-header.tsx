"use client";

import { SidebarTrigger } from "@/components/ui/sidebar";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

const MODELS = [
    { value: "llama3", label: "Llama 3" },
    { value: "gemma", label: "Gemma" },
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
];

interface ChatHeaderProps {
    model: string;
    onModelChange: (value: string) => void;
}

export function ChatHeader({ model, onModelChange }: ChatHeaderProps) {
    return (
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b bg-background px-4 lg:h-[60px]">
            <div className="flex items-center gap-2">
                <SidebarTrigger />
                <h1 className="font-semibold text-lg">New Chat</h1>
            </div>
            <Select value={model} onValueChange={onModelChange}>
                <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select Model" />
                </SelectTrigger>
                <SelectContent>
                    {MODELS.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                            {m.label}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
        </header>
    );
}
