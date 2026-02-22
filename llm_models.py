"""
Shared LLM model instances for use across the application.

Centralised here to avoid circular imports between ai_engine.py and chains.py,
since both previously defined the same OllamaLLM instances independently.
"""

from langchain_ollama import OllamaLLM

# ============================================================================
# OLLAMA LOCAL MODEL INSTANCES
# ============================================================================

llama3_llm = OllamaLLM(model="llama3", temperature=0.1)
gemma_llm = OllamaLLM(model="gemma3", temperature=0.1)
phi3_llm = OllamaLLM(model="phi3", temperature=0.1)

# Available models mapping
AVAILABLE_MODELS = {
    "llama3": llama3_llm,
    "gemma": gemma_llm,
    "phi3": phi3_llm,
}

# Chat-only models (phi3 reserved for podcast/mindmap generation)
CHAT_MODELS = {
    "llama3": llama3_llm,
    "gemma": gemma_llm,
}
