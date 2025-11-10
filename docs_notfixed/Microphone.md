# Microphone Input - Detailed Explanation

## The Problem We're Solving

**Before Phase 2:**
```python
# Orchestrator directly used STT
class AssistantOrchestrator:
    def listen_to_user(self) -> str:
        result = self.stt.listen()  # Direct dependency on STT module
        return result.text
```

**Issues:**
- ❌ Orchestrator tightly coupled to STT implementation
- ❌ Can't swap input sources without changing orchestrator
- ❌ Can't test without real microphone hardware
- ❌ Can't add network audio easily

---

## The Solution: Wrapper Pattern

**MicrophoneInput wraps the existing STT module** to make it conform to the `AudioInput` interface.

### What "Wrapping" Means

Think of it like an adapter plug:
- **STT Module** = European plug (existing code)
- **AudioInput Interface** = Universal socket (new standard)
- **MicrophoneInput** = Adapter (makes old plug fit new socket)

```
┌─────────────────────┐
│   Orchestrator      │
│   (uses AudioInput) │
└──────────┬──────────┘
           │ Uses abstract interface
           ▼
┌─────────────────────┐
│  MicrophoneInput    │  ← WRAPPER
│  (implements        │
│   AudioInput)       │
└──────────┬──────────┘
           │ Wraps existing code
           ▼
┌─────────────────────┐
│   GoogleSTT         │  ← EXISTING MODULE
│   (your STT module) │
└─────────────────────┘
```

---

## Code Walkthrough

### 1. The Interface (Contract)

```python
# core/io/audio_input.py
class AudioInput(ABC):
    """Abstract interface - all inputs must implement this"""
    
    @abstractmethod
    def listen(self) -> AudioInputResult:
        """Listen for input - EVERY input must have this method"""
        pass
```

**This says:** "Any input source (mic, keyboard, robot sensor) MUST have a `listen()` method that returns `AudioInputResult`."

---

### 2. The Wrapper (Adapter)

```python
# core/io/input/microphone_input.py
class MicrophoneInput(AudioInput):
    """Wraps existing STT module to fit AudioInput interface"""
    
    def __init__(self, stt_provider: STTProvider):
        """Store reference to existing STT module"""
        self.stt = stt_provider  # ← We keep the old module inside!
```

**What's happening:**
- `MicrophoneInput` **contains** the old STT module
- It doesn't replace it - it wraps it
- Think: "gift wrapping" - the gift (STT) is inside the wrapper

---

### 3. The Wrapper's listen() Method

```python
def listen(self) -> AudioInputResult:
    """
    Implements AudioInput interface by calling the wrapped STT module
    """
    start_time = time.time()
    
    try:
        # Call the EXISTING STT module
        result = self.stt.listen()  # ← Using the wrapped module
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Convert STT result to AudioInputResult (interface format)
        return AudioInputResult(
            text=result.text,           # ← Take STT's text
            confidence=result.confidence, # ← Take STT's confidence
            duration_ms=duration_ms,
            source='microphone'         # ← Add our own metadata
        )
        
    except Exception as e:
        # Handle errors gracefully
        return AudioInputResult(text="", confidence=0.0, source='microphone')
```

**What's happening:**
1. **Call existing code:** `self.stt.listen()` - uses your Google STT module
2. **Transform result:** Convert from `STTResult` to `AudioInputResult`
3. **Add metadata:** Track timing, add source info
4. **Handle errors:** Return empty result on error (graceful degradation)

---

## Why This Is Powerful

### Example 1: Orchestrator Doesn't Care About Implementation

```python
# Orchestrator just uses the interface
class AssistantOrchestrator:
    def __init__(self, input_mode='auto'):
        # Factory creates appropriate implementation
        self.audio_input = IOFactory.create_input(input_mode, self.stt)
        # Could be MicrophoneInput, KeyboardInput, WebSocketInput...
    
    async def run_loop(self):
        # Same code for ALL input types!
        result = self.audio_input.listen()  # ← Works for any input
        response = await self.process_user_input(result.text)
```

**Benefit:** Orchestrator code never changes when you add new input types!

---

### Example 2: Easy to Add New Inputs

```python
# Want to add WebSocket input? Just implement the interface!
class WebSocketInput(AudioInput):
    def __init__(self, websocket_url):
        self.url = websocket_url
        self.ws = websocket.connect(url)
    
    def listen(self) -> AudioInputResult:
        # Receive audio/text from network
        data = self.ws.recv()
        return AudioInputResult(
            text=data,
            source='websocket'
        )
```

**Benefit:** Add new inputs without touching orchestrator or existing code!

---

### Example 3: Easy to Test

```python
# Create a fake input for testing (NO HARDWARE NEEDED)
class FakeInput(AudioInput):
    def __init__(self, fake_responses):
        self.responses = fake_responses
        self.index = 0
    
    def listen(self) -> AudioInputResult:
        text = self.responses[self.index]
        self.index += 1
        return AudioInputResult(text=text, source='fake')

# Use in tests
def test_conversation():
    fake_input = FakeInput(["Hello", "How are you?", "Goodbye"])
    orchestrator = AssistantOrchestrator(audio_input=fake_input)
    # Test without real microphone!
```

**Benefit:** Test all your logic without any hardware!

---

## Real-World Analogy

Imagine you have:
- **Old appliance:** European plug (STT module)
- **New outlet:** US socket (AudioInput interface)

**Option 1 (Bad):** Rewire the entire appliance
- Have to modify the appliance
- Risk breaking it
- Expensive and time-consuming

**Option 2 (Good):** Use an adapter (MicrophoneInput wrapper)
- Appliance stays unchanged
- Adapter makes it work with new outlet
- Can swap appliances easily
- Can add more appliances with same adapter pattern

---

## The Key Insight

```python
# Phase 1: Tight coupling
orchestrator.listen_to_user()
    └─> Directly calls self.stt.listen()
    └─> Locked to STT implementation

# Phase 2: Loose coupling via wrapper
orchestrator.audio_input.listen()
    └─> Calls AudioInput.listen() (interface)
        └─> MicrophoneInput.listen() (wrapper)
            └─> self.stt.listen() (existing code)

# The wrapper adds a layer of indirection that gives flexibility!
```

**Design Principle:** "Program to an interface, not an implementation"

---

## Common Questions

### Q: Why not just modify the STT module directly?
**A:** Because:
1. STT module might be used elsewhere
2. You'd have to modify every provider (Google, Whisper, Azure...)
3. Breaking changes to existing code
4. Wrapper is non-invasive

### Q: Isn't wrapping adding extra code?
**A:** Yes, but the benefits outweigh the cost:
- ✅ Flexibility (swap implementations)
- ✅ Testability (mock inputs)
- ✅ Maintainability (interface contract)
- ✅ Extensibility (add new inputs easily)

### Q: Does wrapping add performance overhead?
**A:** Negligible (~0.1ms) compared to actual I/O (500ms+ for STT)

### Q: When would I NOT use a wrapper?
**A:** When:
- You'll never swap implementations
- Performance is ultra-critical (real-time systems)
- The interface would be awkward/forced

---

## Visualization: Data Flow

```
User speaks into mic
        ↓
  🎤 Hardware Microphone
        ↓
  📦 MicrophoneInput.listen()  ← WRAPPER
        ↓ (wraps)
  🔌 GoogleSTT.listen()  ← EXISTING MODULE
        ↓ (transcribes)
  📝 STTResult(text="hello")
        ↓ (converts to)
  📋 AudioInputResult(text="hello", source="microphone")
        ↓
  🧠 Orchestrator processes text
        ↓
  💬 Response generated
```

**vs. Keyboard (same interface, different implementation):**

```
User types on keyboard
        ↓
  ⌨️ input() function
        ↓
  📦 KeyboardInput.listen()  ← DIFFERENT WRAPPER
        ↓ (reads from)
  🔌 Python input()  ← NO STT NEEDED
        ↓
  📋 AudioInputResult(text="hello", source="keyboard")
        ↓
  🧠 Orchestrator processes text (SAME CODE!)
        ↓
  💬 Response generated
```

**Key point:** Orchestrator code is identical for both paths!

---

## Summary

**MicrophoneInput wraps your existing STT module to:**
1. Make it conform to the `AudioInput` interface
2. Allow orchestrator to use it without knowing implementation details
3. Enable swapping with other inputs (keyboard, websocket, robot)
4. Make testing possible without hardware
5. Keep existing STT code untouched and reusable

**It's an adapter pattern** - making old code work with new interfaces without modification.