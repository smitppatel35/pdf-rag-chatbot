# Frontend Features

This document outlines the core functional features implemented in the frontend of the PDF RAG Chatbot.

## 1. Authentication & Session Management
- **Automatic Login/Registration**: On initial load, the frontend transparently attempts to log in a test user, creating an account if it doesn't exist.
- **Global Auth State**: `sessionId` and `chatSessionId` are stored in a React Context (`SessionContext`), making them instantly available to the sidebar and chat components without prop-drilling.
- **Seamless Session Switching**: Clicking a session in the sidebar instantly updates the global `chatSessionId`, triggering a history fetch and re-rendering the chat window.

## 2. Multi-Document RAG Integration
- **PDF Uploads**: Users can attach documents (PDF, DOC, DOCX) up to 10MB using a hidden file input bound to a UI button.
- **Active Source Tracking**: Upon successful upload, the backend returns a `source_id`. The frontend stores this in an `activeSourceIds` array.
- **Contextual Chat**: When sending a message, the frontend includes the `activeSourceIds`. The backend uses this to perform Retrieval-Augmented Generation specifically against the uploaded documents. An empty array defaults the backend to General Chat mode.

## 3. Persistent Chat History
- **History Retrieval**: When a user switches sessions or reloads, the frontend calls `GET /chat/history/{chat_session_id}`.
- **Data Transformation**: The backend returns history as an array of objects shaped as `{ user_query: "...", ai_response: "..." }`. The `useChatSession` hook transforms this pair-based data into individual sequential message objects (`{ role: "user", content: "..." }`) expected by the UI renderer.

## 4. Multi-Model Support
- The frontend provides a dropdown to select between different backend language models (e.g., Llama 3, Gemma, GPT-4o, Claude 3.5 Sonnet).
- The selected model identifier string is passed in the JSON body of every `/chat/send` request.

## 5. Robust UI/UX Touches
- **Auto-scrolling**: The chat message container strictly binds to a `<div ref={chatAreaRef}>` and assigns `scrollTop = scrollHeight` whenever new messages are added, ensuring the latest message is always visible.
- **Sticky Layout**: A carefully constructed flexbox layout prevents the outer window from scrolling, ensuring only the chat history area is scrollable.
- **Loading States**: Includes visual feedback (`Loader2` spinners, typing indicators) for initialization, document uploading, message generation, and history loading.
