"""
Request Pipeline

Defines the flow of request processing through the system.
"""

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum
import time

class PipelineStage(Enum):
    """Stages in the request pipeline"""
    WAKE_WORD = "wake_word"
    RECORDING = "recording"
    TRANSCRIPTION = "transcription"
    INTENT_DETECTION = "intent_detection"
    ACTION_EXECUTION = "action_execution"
    RESPONSE_GENERATION = "response_generation"
    SPEECH_OUTPUT = "speech_output"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class PipelineContext:
    """
    Context object passed through pipeline stages.
    Contains all data accumulated during processing.
    """
    # Input
    audio_data: Optional[bytes] = None
    transcribed_text: str = ""
    
    # Intent
    intent_type: Optional[str] = None
    intent_confidence: float = 0.0
    
    # Action
    action_name: Optional[str] = None
    action_params: Optional[dict] = None
    
    # Output
    response_text: str = ""
    
    # Metadata
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    start_time: float = 0.0
    current_stage: PipelineStage = PipelineStage.WAKE_WORD
    
    # Timing
    stage_timings: dict = None
    
    def __post_init__(self):
        if self.stage_timings is None:
            self.stage_timings = {}
        if self.start_time == 0.0:
            self.start_time = time.time()
    
    def mark_stage_complete(self, stage: PipelineStage, duration_ms: float):
        """Mark a stage as complete with timing"""
        self.stage_timings[stage.value] = duration_ms
        self.current_stage = stage
    
    def get_total_time(self) -> float:
        """Get total processing time in milliseconds"""
        return (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            'transcribed_text': self.transcribed_text,
            'intent_type': self.intent_type,
            'intent_confidence': self.intent_confidence,
            'action_name': self.action_name,
            'response_text': self.response_text,
            'current_stage': self.current_stage.value,
            'total_time_ms': self.get_total_time(),
            'stage_timings': self.stage_timings
        }

class Pipeline:
    """
    Request processing pipeline.
    
    Defines the stages and flow of request processing.
    """
    
    @staticmethod
    def get_stages() -> list:
        """Get ordered list of pipeline stages"""
        return [
            PipelineStage.WAKE_WORD,
            PipelineStage.RECORDING,
            PipelineStage.TRANSCRIPTION,
            PipelineStage.INTENT_DETECTION,
            PipelineStage.ACTION_EXECUTION,
            PipelineStage.RESPONSE_GENERATION,
            PipelineStage.SPEECH_OUTPUT,
            PipelineStage.COMPLETE
        ]
    
    @staticmethod
    def create_context() -> PipelineContext:
        """Create a new pipeline context"""
        return PipelineContext()