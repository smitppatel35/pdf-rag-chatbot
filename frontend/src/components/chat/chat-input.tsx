"use client";

import { RefObject } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Paperclip, Send, Loader2 } from "lucide-react";

interface ChatInputProps {
    input: string;
    onInputChange: (value: string) => void;
    onSend: () => void;
    onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
    onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    fileInputRef: RefObject<HTMLInputElement | null>;
    isGenerating: boolean;
    isUploading: boolean;
    isLoadingHistory: boolean;
}

export function ChatInput({
    input,
    onInputChange,
    onSend,
    onKeyDown,
    onFileChange,
    fileInputRef,
    isGenerating,
    isUploading,
    isLoadingHistory,
}: ChatInputProps) {
    const isDisabled = isGenerating || isUploading || isLoadingHistory;

    return (
        <div className="p-4 bg-background w-full max-w-4xl mx-auto shrink-0">
            <div className="flex flex-col rounded-2xl border bg-background shadow-sm overflow-hidden transition-shadow focus-within:shadow-md">
                <Textarea
                    value={input}
                    onChange={(e) => onInputChange(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={isDisabled}
                    placeholder={isUploading ? "Uploading document..." : "Ask a question about your documents..."}
                    className="min-h-[80px] max-h-[200px] w-full resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:outline-none px-4 pt-4 pb-2 shadow-none text-sm"
                    rows={2}
                />
                <div className="flex items-center justify-between px-3 py-2 border-t bg-muted/20">
                    <div className="flex items-center gap-2">
                        <input
                            type="file"
                            id="file-upload"
                            ref={fileInputRef}
                            className="hidden"
                            accept=".pdf,.doc,.docx"
                            onChange={onFileChange}
                            disabled={isDisabled}
                        />
                        <label htmlFor="file-upload">
                            <div
                                className={`flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors px-2 py-1.5 rounded-lg hover:bg-muted text-xs font-medium ${isDisabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                                    }`}
                            >
                                {isUploading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Paperclip className="h-4 w-4" />
                                )}
                                Attach document
                            </div>
                        </label>
                        <span className="text-xs text-muted-foreground hidden sm:inline-block">
                            · Max 10MB
                        </span>
                    </div>
                    <Button
                        size="icon"
                        className="h-8 w-8 rounded-xl shrink-0 bg-foreground text-background hover:bg-foreground/90 disabled:opacity-40 transition-opacity"
                        onClick={onSend}
                        disabled={!input.trim() || isDisabled}
                    >
                        <Send className="h-4 w-4" />
                        <span className="sr-only">Send message</span>
                    </Button>
                </div>
            </div>
            <p className="text-center text-xs text-muted-foreground mt-2">
                AI can make mistakes. Verify important information.
            </p>
        </div>
    );
}
