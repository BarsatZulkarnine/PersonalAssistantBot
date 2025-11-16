"""
RAG Routes - Document Upload & Search
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

from api.models import DocumentUploadResponse
from api.dependencies import get_conversation_service
from utils.logger import get_logger

logger = get_logger('api.routes.rag')

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = "default_user"
):
    """
    Upload document for RAG indexing
    
    Supports: PDF, TXT, MD, DOCX
    """
    service = get_conversation_service()
    
    if not service.rag:
        raise HTTPException(
            status_code=503,
            detail="RAG system not available"
        )
    
    try:
        from modules.rag import get_indexer
        
        # Save uploaded file temporarily
        temp_path = Path(f"data/temp/{file.filename}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await file.read()
        temp_path.write_bytes(content)
        
        # Index document
        indexer = get_indexer()
        chunks = await indexer.index_document(str(temp_path))
        
        # Clean up
        temp_path.unlink()
        
        return DocumentUploadResponse(
            success=True,
            filename=file.filename,
            chunks=chunks,
            message=f"Document indexed successfully ({chunks} chunks)"
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    service = get_conversation_service()
    
    if not service.rag:
        return {"error": "RAG system not available"}
    
    try:
        from modules.rag import get_indexer
        indexer = get_indexer()
        stats = indexer.get_stats()
        
        return {
            "total_documents": stats.total_documents,
            "total_chunks": stats.total_chunks,
            "average_chunk_size": stats.avg_chunk_size
        }
        
    except Exception as e:
        logger.error(f"RAG stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))