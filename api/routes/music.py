"""
Music Routes - Music Control Endpoints
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.models import MusicControlRequest, MusicStatusResponse
from api.dependencies import require_music_player, get_music_player
from utils.logger import get_logger

logger = get_logger('api.routes.music')

router = APIRouter(prefix="/api/music", tags=["music"])


# Event bus import
try:
    from core.event_bus import emit_music_event
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False


@router.post("/control")
async def control_music(request: MusicControlRequest):
    """
    Control music playback
    
    Example:
    ```json
    POST /api/music/control
    {
        "action": "play",
        "song_name": "jazz music"
    }
    ```
    """
    player = require_music_player()
    
    try:
        action = request.action.lower()
        
        if action == "play":
            if not request.song_name:
                raise HTTPException(
                    status_code=400,
                    detail="song_name required for play action"
                )
            
            song = player._find_song(request.song_name)
            if not song:
                return {
                    "success": False,
                    "message": f"Song '{request.song_name}' not found"
                }
            
            player.play(song)
            message = f"Playing: {song.name}"
        
        elif action == "pause":
            player.pause()
            message = "Music paused"
        
        elif action == "resume":
            player.resume()
            message = "Music resumed"
        
        elif action == "stop":
            player.stop()
            message = "Music stopped"
        
        elif action == "next":
            player.next_track()
            message = "Skipped to next track"
        
        elif action == "previous":
            player.previous_track()
            message = "Playing previous track"
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {action}"
            )
        
        # Emit music event
        if EVENT_BUS_AVAILABLE:
            await emit_music_event(
                action=action,
                song_name=player.current_song.name if player.current_song else None
            )
        
        return {
            "success": True,
            "message": message,
            "status": player.get_status()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Music control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{song_name}")
async def stream_music(song_name: str):
    """
    Stream local music file to client.
    
    Usage: Pi/UI requests this URL for playback
    """
    player = require_music_player()
    
    try:
        # Find song
        song = player._find_song(song_name)
        
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        
        # Only stream local files
        if song.type != 'local':
            raise HTTPException(
                status_code=400,
                detail="Only local files can be streamed. YouTube plays directly on client."
            )
        
        # Check file exists
        file_path = Path(song.path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Stream file
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Music streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=MusicStatusResponse)
async def get_music_status():
    """Get current music player status"""
    player = get_music_player()
    
    if not player:
        return MusicStatusResponse(
            state="not_available",
            current_song=None,
            volume=0.0,
            shuffle=False,
            repeat="none",
            queue_length=0,
            library_size=0
        )
    
    try:
        status = player.get_status()
        return MusicStatusResponse(
            state=status['state'],
            current_song=status['current_song'],
            volume=status['volume'],
            shuffle=status['shuffle'],
            repeat=status['repeat'],
            queue_length=status['queue_length'],
            library_size=status['library_size']
        )
        
    except Exception as e:
        logger.error(f"Music status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/library")
async def get_music_library():
    """Get list of available songs"""
    player = require_music_player()
    
    try:
        songs = [
            {
                'name': song.name,
                'type': song.type,
                'artist': song.artist,
                'album': song.album,
                'duration': song.duration
            }
            for song in player.library
        ]
        
        return {
            "total": len(songs),
            "songs": songs
        }
        
    except Exception as e:
        logger.error(f"Music library error: {e}")
        raise HTTPException(status_code=500, detail=str(e))