"""
Shared LLM model instances for use across the application.

Only cloud-hosted models (OpenAI, Gemini) are supported on Vercel.
Ollama local models have been removed — they require a running Ollama
server which is not available in serverless / Lambda environments.
"""

# ============================================================================
# AVAILABLE MODELS (cloud-only for Vercel compatibility)
# ============================================================================

# Ollama models removed — not available on Vercel/serverless.
# All LLM instances are created dynamically in chains.get_llm() using
# user-supplied API keys (OpenAI / Gemini).

AVAILABLE_MODELS = {
    "gpt-4o-mini": "OpenAI GPT-4o Mini (requires OpenAI API key)",
    "gemini-1.5-flash": "Google Gemini 1.5 Flash (requires Gemini API key)",
}

CHAT_MODELS = AVAILABLE_MODELS
