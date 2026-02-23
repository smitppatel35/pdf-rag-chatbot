"""
Vector Store Manager for MongoDB Atlas Vector Search integration.

This module provides a clean abstraction layer for MongoDB Atlas Vector Search operations,
including document storage and retrieval using LangChain.
"""

from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from pymongo.collection import Collection
from typing import List, Optional, Tuple, Dict, Any
import logging
import asyncio

from config import get_settings
from db_manager import COLLECTION_PDF_VECTORS
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Get settings instance
settings = get_settings()


class VectorStoreManager:
    """Manages MongoDB Atlas Vector Search operations for PDF document retrieval."""
    
    def __init__(self, openai_api_key: str = None):
        """Initialize MongoDB Vector Search and embeddings model.
        
        Args:
            openai_api_key: OpenAI API key for embeddings. Falls back to
                            OPENAI_API_KEY env var if not provided.
        """
        self._embeddings = None
        self._vectorstore = None
        self._sync_client = None
        self._openai_api_key = openai_api_key
        
    @property
    def sync_client(self) -> MongoClient:
        """Lazy initialization of synchronous MongoClient."""
        if self._sync_client is None:
            # Create a synchronous client for LangChain
            import os as _os
            mongo_uri = _os.getenv("MONGODB_URI", settings.MONGODB_URI)
            is_dev = _os.getenv("ENVIRONMENT", "development") == "development"
            
            client_kwargs = {}
            if is_dev and mongo_uri.startswith("mongodb+srv://"):
                client_kwargs["tlsAllowInvalidCertificates"] = True
                
            self._sync_client = MongoClient(mongo_uri, **client_kwargs)
            logger.info("Synchronous MongoClient initialized for Vector Search")
        return self._sync_client
        
    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Lazy initialization of OpenAI embeddings model."""
        if self._embeddings is None:
            import os
            api_key = self._openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key is required for embeddings. "
                    "Set it via OPENAI_API_KEY env var or pass it to get_vectorstore_manager()."
                )
            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=api_key
            )
            logger.info("OpenAI Embeddings initialized (text-embedding-3-small)")
        return self._embeddings
    
    @property
    def collection(self) -> Collection:
        """Get the synchronous MongoDB collection used for vectors."""
        # LangChain's MongoDBAtlasVectorSearch requires a standard PyMongo Collection
        import os as _os
        db_name = _os.getenv("MONGODB_DB_NAME", settings.MONGODB_DB_NAME)
        return self.sync_client[db_name][COLLECTION_PDF_VECTORS]
    
    def get_vectorstore(self) -> MongoDBAtlasVectorSearch:
        """
        Get or create the MongoDBAtlasVectorSearch instance.
        
        Returns:
            MongoDBAtlasVectorSearch instance
        """
        if self._vectorstore is None:
            self._vectorstore = MongoDBAtlasVectorSearch(
                collection=self.collection,
                embedding=self.embeddings,
                index_name=settings.MONGODB_VECTOR_INDEX_NAME,
                text_key="text",
                embedding_key="embedding"
            )
            logger.info(f"MongoDBAtlasVectorSearch initialized on collection: {COLLECTION_PDF_VECTORS}")
        
        return self._vectorstore
    
    async def add_documents(
        self,
        documents: List[Document],
        source_id: str,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to MongoDB Atlas Vector Search.
        Automatically tags them with the source_id in metadata for filtering.
        
        Args:
            documents: List of LangChain Document objects with page_content and metadata
            source_id: The ID of the PDF to tag these chunks with
            ids: Optional list of document IDs (will auto-generate if not provided)
            
        Returns:
            List of document IDs that were added
        """
        vectorstore = self.get_vectorstore()
        
        # Ensure every document has the source_id in its metadata so we can filter later
        for doc in documents:
            if "source_id" not in doc.metadata:
                doc.metadata["source_id"] = source_id
                
        try:
            # Since we are using a synchronous PyMongo client for LangChain,
            # we must use the sync add_documents method, but run it in a threadpool so we don't block
            loop = asyncio.get_running_loop()
            doc_ids = await loop.run_in_executor(
                None, 
                lambda: vectorstore.add_documents(documents=documents, ids=ids)
            )
            logger.info(f"Added {len(documents)} documents to MongoDB for source '{source_id}'")
            return doc_ids
        except Exception as e:
            logger.error(f"Failed to add documents for source '{source_id}': {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        source_id: str,
        k: Optional[int] = None,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        Perform similarity search in MongoDB filtered by source_id.
        
        Args:
            query: Query text to search for
            source_id: The ID of the PDF to search within
            k: Number of results to return (defaults to settings.VECTOR_STORE_K)
            filter: Additional optional metadata filters
            
        Returns:
            List of Document objects ordered by similarity
        """
        vectorstore = self.get_vectorstore()
        k = k or settings.VECTOR_STORE_K
        
        # MongoDB Atlas Vector Search uses specific pre-filter syntax
        match_filter = {"source_id": {"$eq": source_id}}
        if filter:
            match_filter.update(filter)
            
        try:
            # asimilarity_search is only available when backed by an async client.
            # We are backed by a sync client, so we must use the sync similarity_search in a thread
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: vectorstore.similarity_search(
                    query=query, 
                    k=k, 
                    pre_filter=match_filter
                )
            )
            logger.info(f"Found {len(results)} results for query in source '{source_id}'")
            return results
        except Exception as e:
            logger.error(f"Similarity search failed in source '{source_id}': {e}")
            raise
    
    async def similarity_search_with_score(
        self,
        query: str,
        source_id: str,
        k: Optional[int] = None,
        filter: Optional[dict] = None
    ) -> List[Tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query: Query text to search for
            source_id: The ID of the PDF to search within
            k: Number of results to return (defaults to settings.VECTOR_STORE_K)
            filter: Optional metadata filter
            
        Returns:
            List of (Document, score) tuples ordered by similarity
        """
        vectorstore = self.get_vectorstore()
        k = k or settings.VECTOR_STORE_K
        
        match_filter = {"source_id": {"$eq": source_id}}
        if filter:
            match_filter.update(filter)
            
        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: vectorstore.similarity_search_with_score(
                    query=query, 
                    k=k, 
                    pre_filter=match_filter
                )
            )
            logger.info(f"Found {len(results)} results with scores for query in source '{source_id}'")
            return results
        except Exception as e:
            logger.error(f"Similarity search with score failed in source '{source_id}': {e}")
            raise
    
    async def delete_source_documents(self, source_id: str) -> None:
        """
        Delete all documents belonging to a specific source/PDF.
        
        Args:
            source_id: ID of the source PDF to delete
        """
        try:
            # Use raw motor client to delete efficiently
            result = await self.collection.delete_many({"source_id": source_id})
            logger.info(f"Deleted {result.deleted_count} vector documents for source: {source_id}")
        except Exception as e:
            logger.error(f"Failed to delete vector documents for source '{source_id}': {e}")
            raise
    
    async def source_exists(self, source_id: str) -> bool:
        """
        Check if any vectors exist for a specific source_id.
        
        Args:
            source_id: ID of the source PDF to check
            
        Returns:
            True if vectors exist, False otherwise
        """
        try:
            count = self.collection.count_documents({"source_id": source_id}, limit=1)
            return count > 0
        except Exception as e:
            logger.error(f"Failed to check vector existence for source '{source_id}': {e}")
            return False
    
    async def get_source_document_count(self, source_id: str) -> int:
        """
        Get the number of vector chunks for a specific source_id.
        
        Args:
            source_id: ID of the source PDF
            
        Returns:
            Number of vector chunks
        """
        try:
            return self.collection.count_documents({"source_id": source_id})
        except Exception as e:
            logger.error(f"Failed to get vector count for source '{source_id}': {e}")
            return 0
    
    def as_retriever(self, source_id: str, **kwargs):
        """
        Get a LangChain retriever interface pre-filtered for a specific source.
        
        Args:
            source_id: ID of the source PDF
            **kwargs: Additional arguments for retriever configuration
                     (search_type, search_kwargs, etc.)
            
        Returns:
            VectorStoreRetriever instance
        """
        vectorstore = self.get_vectorstore()
        
        # Set defaults from settings if not provided
        search_type = kwargs.get('search_type', settings.VECTOR_STORE_SEARCH_TYPE)
        search_kwargs = kwargs.get('search_kwargs', {'k': settings.VECTOR_STORE_K})
        
        # Force pre-filter by source_id so the retriever only returns documents for this PDF
        base_pre_filter = {"source_id": {"$eq": source_id}}
        if "pre_filter" in search_kwargs:
            search_kwargs["pre_filter"].update(base_pre_filter)
        else:
            search_kwargs["pre_filter"] = base_pre_filter
            
        return vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )


# Global singleton instance
_vectorstore_manager = None


def get_vectorstore_manager(openai_api_key: str = None) -> VectorStoreManager:
    """Get or create the VectorStoreManager singleton instance.
    
    If openai_api_key is provided and differs from the existing instance's key,
    a new instance is created so embeddings use the correct key.
    """
    global _vectorstore_manager
    if _vectorstore_manager is None or (
        openai_api_key and openai_api_key != _vectorstore_manager._openai_api_key
    ):
        _vectorstore_manager = VectorStoreManager(openai_api_key=openai_api_key)
    return _vectorstore_manager
