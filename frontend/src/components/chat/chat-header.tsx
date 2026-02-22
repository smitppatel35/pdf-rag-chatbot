"use client";

import { useState, useEffect } from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Settings, Save, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useSession } from "@/context/session-context";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";

const MODELS = [
    { value: "llama3", label: "Llama 3 (Local)" },
    { value: "gemma", label: "Gemma (Local)" },
    { value: "gpt-4o-mini", label: "OpenAI: GPT-4o-mini" },
    { value: "gemini-1.5-flash", label: "Google: Gemini 1.5 Flash" },
];

interface ChatHeaderProps {
    model: string;
    onModelChange: (value: string) => void;
}

export function ChatHeader({ model, onModelChange }: ChatHeaderProps) {
    const { sessionId, logout, triggerRefresh } = useSession();
    const [open, setOpen] = useState(false);
    const [openaiKey, setOpenaiKey] = useState("");
    const [geminiKey, setGeminiKey] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (open && sessionId) {
            // Load profile when sheet opens
            api.getProfile(sessionId).then((data) => {
                setOpenaiKey(data.openai_api_key || "");
                setGeminiKey(data.gemini_api_key || "");
            }).catch(console.error);
        }
    }, [open, sessionId]);

    const handleSaveKeys = async () => {
        if (!sessionId) return;
        setSaving(true);
        try {
            await api.updateProfile(sessionId, openaiKey, geminiKey);
            triggerRefresh();
            setOpen(false);
        } catch (error) {
            console.error(error);
        } finally {
            setSaving(false);
        }
    };

    return (
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b bg-background px-4 lg:h-[60px]">
            <div className="flex items-center gap-2">
                <SidebarTrigger />
                <h1 className="font-semibold text-lg">Chat</h1>
            </div>

            <div className="flex items-center gap-2">
                <Select value={model} onValueChange={onModelChange}>
                    <SelectTrigger className="w-[180px] sm:w-[220px]">
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

                <Sheet open={open} onOpenChange={setOpen}>
                    <SheetTrigger asChild>
                        <Button variant="outline" size="icon" title="API Settings">
                            <Settings className="h-4 w-4" />
                        </Button>
                    </SheetTrigger>
                    <SheetContent>
                        <SheetHeader>
                            <SheetTitle>User Settings</SheetTitle>
                            <SheetDescription>
                                Add your API keys to use cloud models. Keys are stored securely in your profile.
                            </SheetDescription>
                        </SheetHeader>

                        <div className="mt-6 space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">OpenAI API Key</label>
                                <Input
                                    type="password"
                                    placeholder="sk-..."
                                    value={openaiKey}
                                    onChange={(e) => setOpenaiKey(e.target.value)}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Gemini API Key</label>
                                <Input
                                    type="password"
                                    placeholder="AIza..."
                                    value={geminiKey}
                                    onChange={(e) => setGeminiKey(e.target.value)}
                                />
                            </div>

                            <Button className="w-full mt-4" onClick={handleSaveKeys} disabled={saving}>
                                {saving ? "Saving..." : <><Save className="mr-2 h-4 w-4" /> Save Keys</>}
                            </Button>

                            <div className="pt-6 mt-6 border-t">
                                <Button variant="destructive" className="w-full" onClick={logout}>
                                    <LogOut className="mr-2 h-4 w-4" /> Sign Out
                                </Button>
                            </div>
                        </div>
                    </SheetContent>
                </Sheet>
            </div>
        </header>
    );
}
