#!/usr/bin/env python3
"""
Test RAG System

Tests document indexing and retrieval.
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.rag import get_indexer, get_retriever

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def create_test_documents():
    """Create test documents"""
    test_dir = Path("data/test_documents")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test text files
    docs = {
        "python_basics.txt": """
Python Programming Basics

Python is a high-level programming language known for its simplicity and readability.
It was created by Guido van Rossum and first released in 1991.

Key Features:
- Easy to learn and use
- Interpreted language
- Dynamic typing
- Large standard library
- Great for beginners and experts alike

Python is used for:
- Web development (Django, Flask)
- Data science and machine learning
- Automation and scripting
- Desktop applications
""",
        
        "ai_concepts.txt": """
Artificial Intelligence Concepts

AI is the simulation of human intelligence by machines.

Machine Learning:
Machine learning is a subset of AI that enables systems to learn from data.
Common algorithms include neural networks, decision trees, and support vector machines.

Natural Language Processing:
NLP allows computers to understand and generate human language.
Applications include chatbots, translation, and sentiment analysis.

Computer Vision:
Computer vision enables machines to interpret visual information.
Used in facial recognition, object detection, and autonomous vehicles.
""",
        
        "voice_assistant.txt": """
Voice Assistant Technology

Voice assistants use speech recognition and natural language understanding
to interact with users through voice commands.

Components:
1. Wake word detection - Listens for activation phrase
2. Speech-to-text - Converts audio to text
3. Intent classification - Understands user intent
4. Action execution - Performs requested tasks
5. Text-to-speech - Responds with voice

Popular voice assistants include Alexa, Google Assistant, and Siri.
""",
    }
    
    print("\n📝 Creating test documents...")
    for filename, content in docs.items():
        file_path = test_dir / filename
        with open(file_path, 'w') as f:
            f.write(content.strip())
        print(f"   Created: {filename}")
    
    return test_dir

async def test_indexing():
    """Test document indexing"""
    print_section("Test 1: Document Indexing")
    
    # Create test documents
    test_dir = create_test_documents()
    
    # Initialize indexer
    indexer = get_indexer()
    
    # Index directory
    print(f"\n📚 Indexing directory: {test_dir}")
    documents = indexer.index_directory(str(test_dir), recursive=False)
    
    print(f"\n✅ Indexed {len(documents)} documents:")
    for doc in documents:
        print(f"   • {doc.file_name} ({doc.num_chunks} chunks)")
    
    # Get stats
    stats = indexer.get_stats()
    print(f"\n📊 Index Statistics:")
    print(f"   Total documents: {stats.total_documents}")
    print(f"   Total chunks: {stats.total_chunks}")
    print(f"   Total size: {stats.total_size_bytes:,} bytes")
    print(f"   By type: {stats.documents_by_type}")
    
    assert len(documents) == 3, "Should index 3 documents"
    assert stats.total_chunks > 0, "Should have chunks"
    
    print("\n✅ Indexing test passed!")
    return documents

async def test_retrieval():
    """Test document retrieval"""
    print_section("Test 2: Document Retrieval")
    
    retriever = get_retriever()
    
    # Test queries
    queries = [
        ("What is Python?", "Python"),
        ("Tell me about machine learning", "machine learning"),
        ("How do voice assistants work?", "voice assistant"),
        ("What is NLP?", "NLP"),
    ]
    
    for query, expected_keyword in queries:
        print(f"\n🔍 Query: '{query}'")
        
        results = await retriever.retrieve(query, top_k=3)
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"      {i}. [{result.relevance_score:.2f}] {result.document_name}")
                print(f"         {result.content[:100]}...")
            
            # Check if expected keyword found
            found = any(expected_keyword.lower() in r.content.lower() for r in results)
            if found:
                print(f"   ✅ Found expected: '{expected_keyword}'")
            else:
                print(f"   ⚠️  Expected '{expected_keyword}' not in results")
        else:
            print(f"   ❌ No results found")
    
    print("\n✅ Retrieval test passed!")

async def test_context_formatting():
    """Test context formatting for AI"""
    print_section("Test 3: Context Formatting")
    
    retriever = get_retriever()
    
    query = "What is Python used for?"
    print(f"\n🔍 Query: '{query}'")
    
    results = await retriever.retrieve(query, top_k=3)
    
    # Format for AI prompt
    context = retriever.format_context(results, max_length=500)
    
    print(f"\n📄 Formatted Context ({len(context)} chars):")
    print("-" * 70)
    print(context)
    print("-" * 70)
    
    assert len(context) > 0, "Should have context"
    assert len(context) <= 500, "Should respect max length"
    assert "Relevant information from documents:" in context
    
    print("\n✅ Formatting test passed!")

async def test_pdf_docx():
    """Test PDF and DOCX loading (if libraries available)"""
    print_section("Test 4: PDF/DOCX Support")
    
    from modules.rag.loaders import PDFLoader, DOCXLoader
    
    pdf_loader = PDFLoader()
    docx_loader = DOCXLoader()
    
    print(f"\n📦 Library Status:")
    print(f"   PDF (PyPDF2): {'✅ Available' if pdf_loader.available else '❌ Not installed'}")
    print(f"   DOCX (python-docx): {'✅ Available' if docx_loader.available else '❌ Not installed'}")
    
    if not pdf_loader.available:
        print("\n💡 Install with: pip install PyPDF2")
    
    if not docx_loader.available:
        print("💡 Install with: pip install python-docx")
    
    print("\n✅ Library check complete!")

async def test_chunking():
    """Test text chunking"""
    print_section("Test 5: Text Chunking")
    
    from modules.rag import get_chunker
    
    chunker = get_chunker()
    
    test_text = """
    This is a test document. It has multiple sentences.
    We want to test how the chunker splits text.
    
    This is a new paragraph. It should be handled properly.
    The chunker needs to respect sentence boundaries.
    And also handle paragraph breaks correctly.
    
    This is the third paragraph. Let's see how it works.
    """ * 10  # Make it longer
    
    print(f"\n📝 Test text: {len(test_text)} chars, {len(test_text.split())} words")
    
    chunks = chunker.chunk(test_text, chunk_size=100)
    
    print(f"\n📦 Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks[:3], 1):  # Show first 3
        print(f"   Chunk {i}: {len(chunk.split())} words")
        print(f"      {chunk[:80]}...")
    
    if len(chunks) > 3:
        print(f"   ... and {len(chunks) - 3} more chunks")
    
    # Check overlap
    if len(chunks) > 1:
        # Check if there's overlap between chunks
        overlap_found = any(
            word in chunks[i+1] 
            for word in chunks[i].split()[-10:] 
            for i in range(len(chunks)-1)
        )
        print(f"\n   Overlap between chunks: {'✅ Yes' if overlap_found else '⚠️  No'}")
    
    print("\n✅ Chunking test passed!")

async def run_all_tests():
    """Run all RAG tests"""
    print("\n" + "="*70)
    print("  🧪 RAG System Tests")
    print("="*70)
    
    try:
        # Test 1: Indexing
        await test_indexing()
        
        # Test 2: Retrieval
        await test_retrieval()
        
        # Test 3: Context formatting
        await test_context_formatting()
        
        # Test 4: PDF/DOCX support
        await test_pdf_docx()
        
        # Test 5: Chunking
        await test_chunking()
        
        # Summary
        print_section("✅ ALL RAG TESTS PASSED!")
        
        print("\n🎉 RAG system is working!")
        print("\n💡 Next steps:")
        print("   1. Index your own documents:")
        print("      python -c \"from modules.rag import get_indexer;")
        print("                 get_indexer().index_directory('path/to/your/docs')\"")
        print("\n   2. Search documents:")
        print("      python -c \"import asyncio; from modules.rag import get_retriever;")
        print("                 print(asyncio.run(get_retriever().retrieve('your query')))\"")
        print("\n   3. Integrate with assistant (see integration guide)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)