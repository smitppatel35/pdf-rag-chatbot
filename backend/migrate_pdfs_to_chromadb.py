"""
Migration Script: Move existing PDF data from MongoDB to ChromaDB

This script migrates PDF documents that were processed with the old system
(manual embeddings + pdf_rag_cache) to the new ChromaDB vector store.

Usage:
    python migrate_pdfs_to_chromadb.py [--dry-run] [--limit N]
    
Options:
    --dry-run: Show what would be migrated without making changes
    --limit N: Only migrate first N PDFs (for testing)
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict
import logging

from db_manager import _db_manager
from config import get_settings
from ai_engine import _load_and_store_pdf, _get_collection_name
from vectorstore_manager import get_vectorstore_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def find_all_pdf_paths() -> List[str]:
    """
    Find all PDF file paths from MongoDB chat sessions.
    
    Returns:
        List of PDF file paths that exist on disk
    """
    logger.info("Scanning MongoDB for PDF file paths...")
    
    try:
        # Get all chat sessions
        chat_sessions = await _db_manager.chat_sessions.find({}).to_list(length=None)
        logger.info(f"Found {len(chat_sessions)} chat sessions")
        
        pdf_paths = set()
        
        for session in chat_sessions:
            sources = session.get('sources', [])
            for source in sources:
                filepath = source.get('filepath')
                if filepath and filepath.lower().endswith('.pdf'):
                    if os.path.exists(filepath):
                        pdf_paths.add(filepath)
                    else:
                        logger.warning(f"PDF file not found on disk: {filepath}")
        
        logger.info(f"Found {len(pdf_paths)} unique PDF files on disk")
        return list(pdf_paths)
        
    except Exception as e:
        logger.error(f"Error scanning MongoDB: {e}")
        raise


async def migrate_pdf_to_chromadb(pdf_path: str, dry_run: bool = False) -> tuple:
    """
    Migrate a single PDF to ChromaDB.
    
    Args:
        pdf_path: Path to the PDF file
        dry_run: If True, don't actually migrate, just report what would happen
        
    Returns:
        Tuple of (success: bool, message: str, chunk_count: int)
    """
    try:
        collection_name = _get_collection_name(pdf_path)
        mgr = get_vectorstore_manager()
        
        # Check if already migrated
        if mgr.collection_exists(collection_name):
            count = mgr.get_collection_count(collection_name)
            if count > 0:
                logger.info(f"✅ Already migrated: {pdf_path} ({count} chunks)")
                return (True, "already_migrated", count)
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate: {pdf_path}")
            return (True, "would_migrate", 0)
        
        # Load and store PDF in ChromaDB
        logger.info(f"Migrating: {pdf_path}")
        collection_name = _load_and_store_pdf(pdf_path)
        
        # Get chunk count
        chunk_count = mgr.get_collection_count(collection_name)
        logger.info(f"âœ… Successfully migrated: {pdf_path} ({chunk_count} chunks)")
        
        return (True, "migrated", chunk_count)
        
    except Exception as e:
        logger.error(f"â�Œ Failed to migrate {pdf_path}: {e}")
        return (False, str(e), 0)


async def migrate_all_pdfs(dry_run: bool = False, limit: int = None):
    """
    Migrate all PDFs from MongoDB to ChromaDB.
    
    Args:
        dry_run: If True, don't actually migrate, just report what would happen
        limit: If set, only migrate first N PDFs
    """
    settings = get_settings()
    
    # Connect to MongoDB
    logger.info(f"Connecting to MongoDB: {settings.MONGODB_URI}")
    await _db_manager.connect(settings.MONGODB_URI, settings.MONGODB_DB_NAME)
    
    try:
        # Find all PDFs
        pdf_paths = await find_all_pdf_paths()
        
        if limit:
            pdf_paths = pdf_paths[:limit]
            logger.info(f"Limited to first {limit} PDFs")
        
        if not pdf_paths:
            logger.info("No PDFs found to migrate")
            return
        
        logger.info(f"\\n{'=' * 60}")
        logger.info(f"MIGRATION PLAN: {len(pdf_paths)} PDFs")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")
        logger.info(f"{'=' * 60}\\n")
        
        # Migrate each PDF
        results = {
            'success': 0,
            'already_migrated': 0,
            'would_migrate': 0,
            'failed': 0,
            'total_chunks': 0
        }
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            logger.info(f"\\n[{i}/{len(pdf_paths)}] Processing: {pdf_path}")
            
            success, message, chunk_count = await migrate_pdf_to_chromadb(pdf_path, dry_run)
            
            if success:
                if message == "already_migrated":
                    results['already_migrated'] += 1
                elif message == "would_migrate":
                    results['would_migrate'] += 1
                else:
                    results['success'] += 1
                results['total_chunks'] += chunk_count
            else:
                results['failed'] += 1
                logger.error(f"   Error: {message}")
        
        # Summary
        logger.info(f"\\n{'=' * 60}")
        logger.info("MIGRATION SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total PDFs processed: {len(pdf_paths)}")
        
        if dry_run:
            logger.info(f"Would migrate: {results['would_migrate']}")
            logger.info(f"Already migrated: {results['already_migrated']}")
        else:
            logger.info(f"Successfully migrated: {results['success']}")
            logger.info(f"Already migrated: {results['already_migrated']}")
            logger.info(f"Failed: {results['failed']}")
            logger.info(f"Total chunks stored: {results['total_chunks']}")
        
        logger.info(f"{'=' * 60}\\n")
        
        if not dry_run and results['failed'] > 0:
            logger.warning(f"⚠️ {results['failed']} PDF(s) failed to migrate. Check logs above for details.")
        
    finally:
        # Disconnect from MongoDB
        await _db_manager.close()
        logger.info("MongoDB connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate PDF documents from MongoDB to ChromaDB vector store"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        '--limit',
        type=int,
        help="Only migrate first N PDFs (for testing)"
    )
    
    args = parser.parse_args()
    
    logger.info("\\n" + "=" * 60)
    logger.info("PDF TO CHROMADB MIGRATION SCRIPT")
    logger.info("=" * 60 + "\\n")
    
    try:
        asyncio.run(migrate_all_pdfs(dry_run=args.dry_run, limit=args.limit))
        logger.info("\\n✅ Migration complete!")
        return 0
    except KeyboardInterrupt:
        logger.info("\\n⚠️ Migration interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\\n❌ Migration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
