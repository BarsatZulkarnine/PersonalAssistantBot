"""
API Routes Module

Organizes all API endpoints into logical groups.
"""

from api.routes import chat, music, memory, rag, system, sessions

__all__ = ['chat', 'music', 'memory', 'rag', 'system', 'sessions']