"""
Chains module for LangChain Expression Language (LCEL) implementations.

This module provides LCEL-based chains for chat and RAG operations,
replacing the old async generator approach with composable chains.

Phase 4 additions: Callback integration for observability and monitoring.
"""

import logging
from typing import Dict, List, Optional, Any
from operator import itemgetter

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
# LLM instances are shared from llm_models to avoid circular imports
from llm_models import AVAILABLE_MODELS, CHAT_MODELS

from prompts import (
    CHAT_PROMPT_TEMPLATE,
    RAG_PROMPT_TEMPLATE,
    MULTI_PDF_RAG_PROMPT_TEMPLATE,
    HISTORY_LENGTH
)
from vectorstore_manager import get_vectorstore_manager
from memory_manager import get_windowed_messages
from callbacks import create_callback_manager, LoggingCallbackHandler, PerformanceCallbackHandler
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================================
# LLM INSTANCES (imported from ai_engine to avoid duplication)
# ============================================================================

# Model mapping (cloud-only; Ollama removed for Vercel compatibility)
AVAILABLE_MODELS = AVAILABLE_MODELS
CHAT_MODELS = CHAT_MODELS


def get_llm(model_name: str = "gpt-4o-mini", api_keys: dict = None):
    """Get LLM instance by name. Only cloud models are supported on Vercel."""
    if model_name == "gpt-4o-mini":
        from langchain_openai import ChatOpenAI
        key = api_keys.get("openai") if api_keys else None
        if not key:
            raise ValueError("OpenAI API key missing. Please add it in settings.")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=key)
    elif model_name == "gemini-1.5-flash":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_keys.get("gemini") if api_keys else None
        if not key:
            raise ValueError("Gemini API key missing. Please add it in settings.")
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1, google_api_key=key)
    raise ValueError(
        f"Unknown or unsupported model: '{model_name}'. "
        f"Supported models: gpt-4o-mini, gemini-1.5-flash"
    )


# ============================================================================
# HELPER FUNCTIONS FOR CHAINS
# ============================================================================

def format_chat_history(messages: List) -> List:
    """
    Convert message list to LangChain message format.
    
    Args:
        messages: List of messages (ChatMessage objects or dicts)
        
    Returns:
        List of HumanMessage/AIMessage objects
    """
    formatted = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user':
                formatted.append(HumanMessage(content=content))
            elif role == 'assistant':
                formatted.append(AIMessage(content=content))
        else:
            # Already a ChatMessage object
            formatted.append(msg)
    return formatted


def format_docs(docs: List) -> str:
    """
    Format retrieved documents into context string.
    
    Args:
        docs: List of Document objects
        
    Returns:
        Formatted context string
    """
    return "\n\n--\n\n".join([doc.page_content for doc in docs])


def get_session_history(session_id: str, k: int = HISTORY_LENGTH) -> List:
    """
    Retrieve windowed chat history for a session.
    
    Args:
        session_id: Chat session ID
        k: Number of message pairs to retrieve
        
    Returns:
        List of ChatMessage objects
    """
    messages = get_windowed_messages(session_id, k=k)
    return messages


# ============================================================================
# BASIC CHAT CHAIN (No RAG)
# ============================================================================

def create_chat_chain(
    model_name: str = "llama3",
    api_keys: dict = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a basic chat chain using LCEL.
    
    Chain structure: prompt | llm | output_parser
    
    Args:
        model_name: Name of the model to use (llama3, gemma)
        api_keys: Dictionary of API keys for remote models
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable chain
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    # LCEL chain: prompt template | llm | output parser
    chain = CHAT_PROMPT_TEMPLATE | llm | output_parser
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created chat chain with model: {model_name}, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


def create_chat_chain_with_history(
    model_name: str = "llama3",
    api_keys: dict = None,
    session_id: Optional[str] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a chat chain with conversation history.
    
    Args:
        model_name: Name of the model to use
        api_keys: Dictionary of API keys for remote models
        session_id: Session ID for history retrieval
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable chain with history integration
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    # Create chain with history loading
    def load_history(inputs: Dict) -> Dict:
        """Load chat history for the session."""
        sid = inputs.get('session_id', session_id)
        if sid:
            history = get_session_history(sid)
            inputs['chat_history'] = history
        else:
            inputs['chat_history'] = []
        return inputs
    
    # LCEL chain with history
    chain = (
        RunnableLambda(load_history)
        | CHAT_PROMPT_TEMPLATE
        | llm
        | output_parser
    )
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created chat chain with history for session: {session_id}, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


# ============================================================================
# RAG CHAIN (Single PDF)
# ============================================================================

def create_rag_chain(
    source_id: str,
    model_name: str = "llama3",
    api_keys: dict = None,
    k: int = 3,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a RAG chain using LCEL with MongoDB Atlas Vector Search retriever.
    
    Chain structure: retriever → format_context → prompt | llm | output_parser
    
    Args:
        source_id: MongoDB source identifier for filtering
        model_name: Name of the model to use
        api_keys: Dictionary of API keys for remote models
        k: Number of documents to retrieve
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable RAG chain
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    # Get retriever from vectorstore manager (pass OpenAI key for embeddings)
    openai_key = api_keys.get("openai") if api_keys else None
    vectorstore_mgr = get_vectorstore_manager(openai_api_key=openai_key)
    retriever = vectorstore_mgr.as_retriever(
        source_id=source_id,
        search_kwargs={'k': k}
    )
    
    # LCEL chain: retriever | format | prompt | llm | parse
    chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "input": RunnablePassthrough(),
            "chat_history": lambda x: []  # No history for simple RAG
        }
        | RAG_PROMPT_TEMPLATE
        | llm
        | output_parser
    )
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created RAG chain for source: {source_id}, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


def create_rag_chain_with_history(
    source_id: str,
    session_id: str,
    model_name: str = "llama3",
    api_keys: dict = None,
    k: int = 3,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a RAG chain with conversation history.
    
    Args:
        source_id: MongoDB source identifier
        session_id: Session ID for history retrieval
        model_name: Name of the model to use
        api_keys: Dictionary of API keys for remote models
        k: Number of documents to retrieve
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable RAG chain with history
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    # Get retriever (pass OpenAI key for embeddings)
    openai_key = api_keys.get("openai") if api_keys else None
    vectorstore_mgr = get_vectorstore_manager(openai_api_key=openai_key)
    retriever = vectorstore_mgr.as_retriever(
        source_id=source_id,
        search_kwargs={'k': k}
    )
    
    # LCEL chain with history
    chain = (
        {
            "context": itemgetter("input") | retriever | RunnableLambda(format_docs),
            "input": itemgetter("input"),
            "chat_history": lambda x: get_session_history(session_id)
        }
        | RAG_PROMPT_TEMPLATE
        | llm
        | output_parser
    )
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created RAG chain with history for source: {source_id}, session: {session_id}, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


# ============================================================================
# MULTI-PDF RAG CHAIN
# ============================================================================

def create_multi_pdf_rag_chain(
    source_ids: List[str],
    model_name: str = "llama3",
    api_keys: dict = None,
    k: int = 2,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a multi-PDF RAG chain using LCEL.
    
    Retrieves context using independent source_id filters and combines them.
    
    Args:
        source_ids: List of MongoDB source identifiers
        model_name: Name of the model to use
        api_keys: Dictionary of API keys for remote models
        k: Number of documents to retrieve per source
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable multi-PDF RAG chain
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    openai_key = api_keys.get("openai") if api_keys else None
    vectorstore_mgr = get_vectorstore_manager(openai_api_key=openai_key)
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    def retrieve_from_multiple(query: str) -> str:
        """Retrieve and combine context from multiple sources."""
        all_contexts = []
        
        for s_id in source_ids:
            try:
                retriever = vectorstore_mgr.as_retriever(
                    source_id=s_id,
                    search_kwargs={'k': k}
                )
                docs = retriever.invoke(query)
                if docs:
                    context = format_docs(docs)
                    # Add source identifier
                    all_contexts.append(f"Context from {s_id}:\n{context}")
            except Exception as e:
                logger.warning(f"Failed to retrieve from source {s_id}: {e}")
                continue
        
        return "\n\n--\n\n".join(all_contexts) if all_contexts else "No context found."
    
    # LCEL chain for multi-PDF
    chain = (
        {
            "context": RunnableLambda(retrieve_from_multiple),
            "input": RunnablePassthrough(),
            "chat_history": lambda x: []
        }
        | MULTI_PDF_RAG_PROMPT_TEMPLATE
        | llm
        | output_parser
    )
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created multi-PDF RAG chain for {len(source_ids)} sources, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


def create_multi_pdf_rag_chain_with_history(
    source_ids: List[str],
    session_id: str,
    model_name: str = "llama3",
    api_keys: dict = None,
    k: int = 2,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Create a multi-PDF RAG chain with conversation history.
    
    Args:
        source_ids: List of MongoDB source identifiers
        session_id: Session ID for history retrieval
        model_name: Name of the model to use
        api_keys: Dictionary of API keys for remote models
        k: Number of documents to retrieve per source
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Runnable multi-PDF RAG chain with history
    """
    llm = get_llm(model_name, api_keys)
    output_parser = StrOutputParser()
    openai_key = api_keys.get("openai") if api_keys else None
    vectorstore_mgr = get_vectorstore_manager(openai_api_key=openai_key)
    
    # Create default callbacks if observability enabled
    if enable_observability and callbacks is None:
        callbacks = create_callback_manager(
            enable_logging=True,
            enable_performance=True,
            enable_debug=False
        )
    
    def retrieve_from_multiple(inputs: Dict) -> str:
        """Retrieve and combine context from multiple sources."""
        query = inputs.get("input", "")
        all_contexts = []
        
        for s_id in source_ids:
            try:
                retriever = vectorstore_mgr.as_retriever(
                    source_id=s_id,
                    search_kwargs={'k': k}
                )
                docs = retriever.invoke(query)
                if docs:
                    context = format_docs(docs)
                    all_contexts.append(f"Context from {s_id}:\n{context}")
            except Exception as e:
                logger.warning(f"Failed to retrieve from {s_id}: {e}")
                continue
        
        return "\n\n--\n\n".join(all_contexts) if all_contexts else "No context found."
    
    # LCEL chain with history
    chain = (
        {
            "context": RunnableLambda(retrieve_from_multiple),
            "input": itemgetter("input"),
            "chat_history": lambda x: get_session_history(session_id)
        }
        | MULTI_PDF_RAG_PROMPT_TEMPLATE
        | llm
        | output_parser
    )
    
    # Attach callbacks if provided
    if callbacks:
        chain = chain.with_config(callbacks=callbacks)
    
    logger.info(f"Created multi-PDF RAG chain with history for {len(collection_names)} collections, session: {session_id}, callbacks: {len(callbacks) if callbacks else 0}")
    return chain


# ============================================================================
# CHAIN FACTORY
# ============================================================================

def get_chain(
    chain_type: str,
    model_name: str = "llama3",
    source_id: Optional[str] = None,
    source_ids: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    k: int = 3,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    enable_observability: bool = False
):
    """
    Factory function to get the appropriate chain based on parameters.
    
    Args:
        chain_type: Type of chain ('chat', 'rag', 'multi_rag')
        model_name: Name of the model to use
        source_id: Single source ID (for RAG)
        source_ids: Multiple source IDs (for multi-RAG)
        session_id: Session ID for history (optional)
        k: Number of documents to retrieve
        callbacks: Optional list of callback handlers
        enable_observability: Auto-create logging/performance callbacks
        
    Returns:
        Appropriate chain instance
    """
    if chain_type == "chat":
        if session_id:
            return create_chat_chain_with_history(model_name, session_id, callbacks, enable_observability)
        else:
            return create_chat_chain(model_name, callbacks, enable_observability)
    
    elif chain_type == "rag":
        if not source_id:
            raise ValueError("source_id required for RAG chain")
        if session_id:
            return create_rag_chain_with_history(source_id, session_id, model_name, k, callbacks, enable_observability)
        else:
            return create_rag_chain(source_id, model_name, k, callbacks, enable_observability)
    
    elif chain_type == "multi_rag":
        if not source_ids:
            raise ValueError("source_ids required for multi-RAG chain")
        if session_id:
            return create_multi_pdf_rag_chain_with_history(source_ids, session_id, model_name, k, callbacks, enable_observability)
        else:
            return create_multi_pdf_rag_chain(source_ids, model_name, k, callbacks, enable_observability)
    
    else:
        raise ValueError(f"Unknown chain type: {chain_type}")


logger.info("Chains module loaded with LCEL implementations")
