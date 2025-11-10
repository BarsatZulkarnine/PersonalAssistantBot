"""
I/O Abstraction Layer

Provides hardware-agnostic input/output interfaces.
"""

from core.io.audio_input import AudioInput, AudioInputResult, InputCapabilities
from core.io.audio_output import AudioOutput, OutputCapabilities
from core.io.factory import IOFactory

__all__ = [
    'AudioInput',
    'AudioInputResult',
    'InputCapabilities',
    'AudioOutput',
    'OutputCapabilities',
    'IOFactory'
]
