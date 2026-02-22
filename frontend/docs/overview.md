# Frontend Overview

The frontend of the PDF RAG Chatbot is a modern web application built with [Next.js](https://nextjs.org/) (App Router), [React](https://react.dev/), [Tailwind CSS](https://tailwindcss.com/), and [shadcn/ui](https://ui.shadcn.com/).

## Architecture & Structure

The application has been heavily refactored from a single monolithic page into a focused, modular, production-ready structure. The core philosophy separates state management (hooks), UI components, and API execution.

### Key Directories
- `src/app/` - Next.js routing. Contains the root `layout.tsx` and the main `page.tsx` (which acts as a thin orchestrator).
- `src/components/` - Reusable UI components.
  - `chat/` - Focused components for the chat interface (`chat-header.tsx`, `chat-messages.tsx`, `chat-input.tsx`).
- `src/hooks/` - Custom React hooks. `use-chat-session.ts` houses all complex state logic (message handling, uploading, history, auto-scrolling).
- `src/context/` - React Context providers. `session-context.tsx` provides shared authentication and active session state globally without prop drilling.
- `src/lib/` - Utilities and API client (`api.ts`).

## Tech Stack
- **Framework**: Next.js 15 (React 19)
- **Styling**: Tailwind CSS
- **Component Library**: shadcn/ui
- **Icons**: lucide-react

## Further Documentation
- **[Screens & Layout Documentation](./screens.md)**: Details on the UI layout, sidebar, and component composition.
- **[Features Documentation](./features.md)**: Details on the core capabilities, including PDF upload, session management, and multi-model chat.
