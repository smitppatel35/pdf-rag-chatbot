"use client";

import { Loader2 } from "lucide-react";
import { ChatHeader } from "@/components/chat/chat-header";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import { useChatSession } from "@/hooks/use-chat-session";

export default function Home() {
  const {
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
  } = useChatSession();

  if (isInitializing) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Connecting to server...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col bg-background">
      <ChatHeader model={model} onModelChange={setModel} />

      <ChatMessages
        messages={messages}
        isGenerating={isGenerating}
        isLoadingHistory={isLoadingHistory}
        chatAreaRef={chatAreaRef}
      />

      <ChatInput
        input={input}
        onInputChange={setInput}
        onSend={handleSendMessage}
        onKeyDown={handleKeyDown}
        onFileChange={handleFileUpload}
        fileInputRef={fileInputRef}
        isGenerating={isGenerating}
        isUploading={isUploading}
        isLoadingHistory={isLoadingHistory}
      />
    </div>
  );
}
