"""
Text Chunker - Smart Document Splitting

Splits documents into chunks for embedding.
"""

import re
from typing import List
from modules.rag.base import TextChunker, ChunkStrategy
from utils.logger import get_logger

logger = get_logger('rag.chunker')

class SmartChunker(TextChunker):
    """
    Intelligent text chunking with overlap.
    
    Strategies:
    - Respects sentence boundaries
    - Adds overlap between chunks
    - Preserves paragraph structure
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        strategy: ChunkStrategy = ChunkStrategy.SENTENCE
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy
        
        logger.info(f"SmartChunker initialized (size={chunk_size}, overlap={overlap})")
    
    def chunk(self, text: str, chunk_size: int = None) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Override default chunk size
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or self.chunk_size
        
        if self.strategy == ChunkStrategy.SENTENCE:
            return self._chunk_by_sentences(text, chunk_size)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_by_paragraphs(text, chunk_size)
        else:  # FIXED_SIZE
            return self._chunk_fixed_size(text, chunk_size)
    
    def _chunk_by_sentences(self, text: str, chunk_size: int) -> List[str]:
        """Chunk by sentence boundaries with overlap"""
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence.split())
            
            # If single sentence is too long, split it
            if sentence_length > chunk_size:
                # Add current chunk if exists
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence into fixed-size chunks
                long_chunks = self._chunk_fixed_size(sentence, chunk_size)
                chunks.extend(long_chunks)
                continue
            
            # Check if adding this sentence exceeds limit
            if current_length + sentence_length > chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, 
                    self.overlap
                )
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s.split()) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        logger.debug(f"Split text into {len(chunks)} chunks (avg: {sum(len(c.split()) for c in chunks) / len(chunks):.0f} words)")
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, chunk_size: int) -> List[str]:
        """Chunk by paragraph boundaries"""
        
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para.split())
            
            # If single paragraph is too long, split by sentences
            if para_length > chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long paragraph
                para_chunks = self._chunk_by_sentences(para, chunk_size)
                chunks.extend(para_chunks)
                continue
            
            # Check if adding exceeds limit
            if current_length + para_length > chunk_size:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        # Add final chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _chunk_fixed_size(self, text: str, chunk_size: int) -> List[str]:
        """Simple fixed-size chunking with overlap"""
        
        words = text.split()
        chunks = []
        
        overlap_words = max(10, self.overlap)  # At least 10 words overlap
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            
            # Move forward by chunk_size minus overlap
            i += chunk_size - overlap_words
            
            if i >= len(words):
                break
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        
        # Simple sentence splitting (can be improved with nltk)
        # Matches: . ! ? followed by space and capital letter or end of string
        pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$'
        
        sentences = re.split(pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _get_overlap_sentences(self, sentences: List[str], overlap_tokens: int) -> List[str]:
        """Get last N tokens worth of sentences for overlap"""
        
        if not sentences:
            return []
        
        overlap_sentences = []
        token_count = 0
        
        # Start from end and work backwards
        for sentence in reversed(sentences):
            sentence_tokens = len(sentence.split())
            
            if token_count + sentence_tokens > overlap_tokens:
                break
            
            overlap_sentences.insert(0, sentence)
            token_count += sentence_tokens
        
        return overlap_sentences
    
    def estimate_chunks(self, text: str) -> int:
        """Estimate how many chunks will be created"""
        word_count = len(text.split())
        return max(1, (word_count + self.chunk_size - 1) // self.chunk_size)


# Convenience function

_default_chunker = None

def get_chunker() -> SmartChunker:
    """Get or create default chunker"""
    global _default_chunker
    if _default_chunker is None:
        _default_chunker = SmartChunker(
            chunk_size=500,  # 500 words = ~666 tokens
            overlap=50,      # 50 words overlap
            strategy=ChunkStrategy.SENTENCE
        )
    return _default_chunker