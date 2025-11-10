"""
Test I/O Adapters - Phase 2

Tests that I/O abstraction works correctly.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.io import AudioInput, AudioOutput, IOFactory
from core.io.input.keyboard_input import KeyboardInput
from core.io.input.microphone_input import MicrophoneInput
from core.io.output.console_output import ConsoleOutput
from core.io.output.speaker_output import SpeakerOutput


class TestKeyboardInput:
    """Test keyboard input (no hardware needed)"""
    
    def test_initialization(self):
        """Test keyboard input initializes"""
        keyboard = KeyboardInput()
        assert keyboard is not None
        assert keyboard.prompt == "> "
    
    def test_custom_prompt(self):
        """Test custom prompt"""
        keyboard = KeyboardInput(prompt="Enter: ")
        assert keyboard.prompt == "Enter: "
    
    def test_is_available(self):
        """Test keyboard is always available"""
        keyboard = KeyboardInput()
        assert keyboard.is_available() == True
    
    def test_capabilities(self):
        """Test keyboard capabilities"""
        keyboard = KeyboardInput()
        caps = keyboard.get_capabilities()
        
        assert caps.supports_wake_word == False
        assert caps.supports_streaming == False
        assert caps.requires_network == False
        assert caps.input_type == 'text'
    
    @patch('builtins.input', return_value='Hello')
    def test_listen(self, mock_input):
        """Test listening via keyboard"""
        keyboard = KeyboardInput()
        result = keyboard.listen()
        
        assert result.text == 'Hello'
        assert result.confidence == 1.0
        assert result.source == 'keyboard'
        assert result.is_empty() == False
    
    @patch('builtins.input', return_value='')
    def test_listen_empty(self, mock_input):
        """Test empty input"""
        keyboard = KeyboardInput()
        result = keyboard.listen()
        
        assert result.text == ''
        assert result.is_empty() == True
    
    @patch('builtins.input', side_effect=EOFError)
    def test_listen_eof(self, mock_input):
        """Test EOF (Ctrl+D)"""
        keyboard = KeyboardInput()
        result = keyboard.listen()
        
        assert result.text == ''
        assert result.is_empty() == True


class TestConsoleOutput:
    """Test console output (no hardware needed)"""
    
    def test_initialization(self):
        """Test console output initializes"""
        console = ConsoleOutput()
        assert console is not None
        assert console.prefix == "Assistant: "
    
    def test_custom_prefix(self):
        """Test custom prefix"""
        console = ConsoleOutput(prefix="Bot: ")
        assert console.prefix == "Bot: "
    
    def test_is_available(self):
        """Test console is always available"""
        console = ConsoleOutput()
        assert console.is_available() == True
    
    def test_capabilities(self):
        """Test console capabilities"""
        console = ConsoleOutput()
        caps = console.get_capabilities()
        
        assert caps.supports_audio == False
        assert caps.supports_streaming == False
        assert caps.requires_network == False
        assert caps.output_type == 'text'
    
    @patch('builtins.print')
    def test_output(self, mock_print):
        """Test output to console"""
        console = ConsoleOutput()
        result = console.output("Hello!")
        
        assert result == True
        mock_print.assert_called_once()


class TestMicrophoneInput:
    """Test microphone input (with mocked STT)"""
    
    def test_initialization(self):
        """Test microphone input initializes"""
        mock_stt = Mock()
        mic = MicrophoneInput(mock_stt)
        
        assert mic is not None
        assert mic.stt == mock_stt
    
    def test_capabilities(self):
        """Test microphone capabilities"""
        mock_stt = Mock()
        mic = MicrophoneInput(mock_stt)
        caps = mic.get_capabilities()
        
        assert caps.supports_wake_word == True
        assert caps.input_type == 'audio'
        assert caps.requires_network == True  # Google STT
    
    def test_listen_success(self):
        """Test successful transcription"""
        # Mock STT result
        mock_stt_result = Mock()
        mock_stt_result.text = "Hello world"
        mock_stt_result.confidence = 0.95
        
        mock_stt = Mock()
        mock_stt.listen.return_value = mock_stt_result
        
        mic = MicrophoneInput(mock_stt)
        result = mic.listen()
        
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.source == 'microphone'
        assert result.is_empty() == False
    
    def test_listen_empty(self):
        """Test empty transcription"""
        mock_stt_result = Mock()
        mock_stt_result.text = ""
        mock_stt_result.confidence = 0.0
        
        mock_stt = Mock()
        mock_stt.listen.return_value = mock_stt_result
        
        mic = MicrophoneInput(mock_stt)
        result = mic.listen()
        
        assert result.text == ""
        assert result.is_empty() == True
    
    def test_listen_error(self):
        """Test error during transcription"""
        mock_stt = Mock()
        mock_stt.listen.side_effect = Exception("Mic error")
        
        mic = MicrophoneInput(mock_stt)
        result = mic.listen()
        
        assert result.text == ""
        assert result.is_empty() == True


class TestSpeakerOutput:
    """Test speaker output (with mocked TTS)"""
    
    def test_initialization(self):
        """Test speaker output initializes"""
        mock_tts = Mock()
        speaker = SpeakerOutput(mock_tts)
        
        assert speaker is not None
        assert speaker.tts == mock_tts
    
    def test_capabilities(self):
        """Test speaker capabilities"""
        mock_tts = Mock()
        mock_tts.config.streaming_enabled = True
        
        speaker = SpeakerOutput(mock_tts)
        caps = speaker.get_capabilities()
        
        assert caps.supports_audio == True
        assert caps.supports_streaming == True
        assert caps.output_type == 'audio'
    
    def test_output_with_streaming(self):
        """Test output with streaming enabled"""
        mock_tts = Mock()
        mock_tts.config.streaming_enabled = True
        
        speaker = SpeakerOutput(mock_tts)
        result = speaker.output("Hello!")
        
        assert result == True
        mock_tts.stream_speak.assert_called_once_with("Hello!")
        mock_tts.speak.assert_not_called()
    
    def test_output_without_streaming(self):
        """Test output without streaming"""
        mock_tts = Mock()
        mock_tts.config.streaming_enabled = False
        
        speaker = SpeakerOutput(mock_tts)
        result = speaker.output("Hello!")
        
        assert result == True
        mock_tts.speak.assert_called_once_with("Hello!")
        mock_tts.stream_speak.assert_not_called()
    
    def test_output_error(self):
        """Test error during output"""
        mock_tts = Mock()
        mock_tts.config.streaming_enabled = False
        mock_tts.speak.side_effect = Exception("Speaker error")
        
        speaker = SpeakerOutput(mock_tts)
        result = speaker.output("Hello!")
        
        assert result == False


class TestIOFactory:
    """Test I/O factory"""
    
    def test_create_keyboard_input(self):
        """Test creating keyboard input"""
        audio_input = IOFactory.create_input('keyboard')
        
        assert isinstance(audio_input, KeyboardInput)
    
    def test_create_microphone_input(self):
        """Test creating microphone input"""
        mock_stt = Mock()
        audio_input = IOFactory.create_input('microphone', stt_provider=mock_stt)
        
        assert isinstance(audio_input, MicrophoneInput)
    
    def test_create_console_output(self):
        """Test creating console output"""
        audio_output = IOFactory.create_output('console')
        
        assert isinstance(audio_output, ConsoleOutput)
    
    def test_create_speaker_output(self):
        """Test creating speaker output"""
        mock_tts = Mock()
        audio_output = IOFactory.create_output('speaker', tts_provider=mock_tts)
        
        assert isinstance(audio_output, SpeakerOutput)
    
    @patch('core.io.input.microphone_input.MicrophoneInput.is_available', return_value=True)
    def test_auto_input_with_mic_available(self, mock_available):
        """Test auto mode selects microphone when available"""
        mock_stt = Mock()
        audio_input = IOFactory.create_input('auto', stt_provider=mock_stt)
        
        assert isinstance(audio_input, MicrophoneInput)
    
    @patch('core.io.input.microphone_input.MicrophoneInput.is_available', return_value=False)
    def test_auto_input_fallback_to_keyboard(self, mock_available):
        """Test auto mode falls back to keyboard"""
        mock_stt = Mock()
        audio_input = IOFactory.create_input('auto', stt_provider=mock_stt, fallback=True)
        
        assert isinstance(audio_input, KeyboardInput)
    
    @patch('core.io.output.speaker_output.SpeakerOutput.is_available', return_value=True)
    def test_auto_output_with_speaker_available(self, mock_available):
        """Test auto mode selects speaker when available"""
        mock_tts = Mock()
        audio_output = IOFactory.create_output('auto', tts_provider=mock_tts)
        
        assert isinstance(audio_output, SpeakerOutput)
    
    @patch('core.io.output.speaker_output.SpeakerOutput.is_available', return_value=False)
    def test_auto_output_fallback_to_console(self, mock_available):
        """Test auto mode falls back to console"""
        mock_tts = Mock()
        audio_output = IOFactory.create_output('auto', tts_provider=mock_tts, fallback=True)
        
        assert isinstance(audio_output, ConsoleOutput)
    
    def test_create_io_pair(self):
        """Test creating I/O pair"""
        mock_stt = Mock()
        mock_tts = Mock()
        
        audio_input, audio_output = IOFactory.create_io_pair(
            input_mode='keyboard',
            output_mode='console',
            stt_provider=mock_stt,
            tts_provider=mock_tts
        )
        
        assert isinstance(audio_input, KeyboardInput)
        assert isinstance(audio_output, ConsoleOutput)
    
    def test_invalid_input_mode(self):
        """Test invalid input mode raises error"""
        with pytest.raises(ValueError, match="Unknown input mode"):
            IOFactory.create_input('invalid_mode')
    
    def test_invalid_output_mode(self):
        """Test invalid output mode raises error"""
        with pytest.raises(ValueError, match="Unknown output mode"):
            IOFactory.create_output('invalid_mode')
    
    def test_microphone_without_stt_provider(self):
        """Test microphone mode without STT provider raises error"""
        with pytest.raises(ValueError, match="STT provider required"):
            IOFactory.create_input('microphone', stt_provider=None)
    
    def test_speaker_without_tts_provider(self):
        """Test speaker mode without TTS provider raises error"""
        with pytest.raises(ValueError, match="TTS provider required"):
            IOFactory.create_output('speaker', tts_provider=None)


class TestInputResult:
    """Test AudioInputResult data class"""
    
    def test_is_empty_with_text(self):
        """Test is_empty with text"""
        from core.io.audio_input import AudioInputResult
        
        result = AudioInputResult(text="Hello")
        assert result.is_empty() == False
    
    def test_is_empty_without_text(self):
        """Test is_empty without text"""
        from core.io.audio_input import AudioInputResult
        
        result = AudioInputResult(text="")
        assert result.is_empty() == True
    
    def test_is_empty_with_whitespace(self):
        """Test is_empty with whitespace"""
        from core.io.audio_input import AudioInputResult
        
        result = AudioInputResult(text="   ")
        assert result.is_empty() == True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])