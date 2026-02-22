# Application Screens & Layout

The frontend currently consists of a primary single-page chat interface `src/app/page.tsx`, functioning as a dashboard.

## Main Layout (`RootLayout`)
The application is wrapped in two primary providers:
1. `SessionProvider`: Manages global `sessionId` and `chatSessionId` state.
2. `SidebarProvider`: Manages the state (open/closed) of the collapsible sidebar.

The layout structure enforces a strict `h-screen overflow-hidden` constraint, ensuring the outer shell of the application never scrolls, and delegating specific scrolling behavior to the internal chat area.

## The Chat Interface

The main chat interface is composed of a sidebar and a main content column. The main column orchestrates three distinct components:

### 1. App Sidebar (`app-sidebar.tsx`)
A collapsible navigation drawer that functions as a **Live Session Navigator**.
- Displays a list of all historical chat sessions fetched from the backend.
- Provides a "New Chat" button to initialize fresh sessions.
- Allows users to select existing sessions to load chat history.
- Includes a per-session delete button (visible on hover).

### 2. Chat Header (`chat-header.tsx`)
Fixed at the top of the main area.
- Contains the Sidebar Trigger (hamburger menu).
- Displays the current session title (defaults to "New Chat").
- Contains a model selection dropdown (Llama 3, Gemma, GPT-4o, Claude 3.5 Sonnet).

### 3. Chat Messages (`chat-messages.tsx`)
The primary scrollable viewport.
- Uses `flex-1 min-h-0 overflow-y-auto` to strictly contain scrolling within this specific div.
- Renders `MessageBubble` components for both the User and Assistant.
- Displays an animated `TypingIndicator` when the model is generating a response.
- Auto-scrolls to the bottom automatically when new messages arrive.

### 4. Chat Input (`chat-input.tsx`)
Fixed at the bottom of the main area.
- A styled, borderless `<Textarea>` that auto-expands up to a maximum height.
- A toolbar containing:
  - A hidden file input triggered by a "Attach document" button.
  - A Send button.
- Clean design utilizing `shadow-sm` and `focus-within:shadow-md` without harsh focus rings.

## Responsive Design
The layout is fully responsive. On mobile devices, the sidebar is hidden by default and accessible via the hamburger menu in the `ChatHeader`.
