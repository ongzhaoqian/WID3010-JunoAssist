from __future__ import annotations
from urllib.parse import urlparse

from src.core.config import settings
from src.core.models import EmotionState
from src.core.state import robot_state


class MusicService:
    """Selects an emotion-appropriate Spotify playlist for the dashboard.

    The backend does not store Spotify secrets. It returns Spotify playlist/embed
    URLs that the dashboard can render. The presets now follow JUNO's Ekman-7
    emotion taxonomy.
    """

    def __init__(self) -> None:
        self._presets = {
            EmotionState.HAPPINESS: {
                "title": "Positive focus mix",
                "description": "Upbeat songs to maintain a positive study mood.",
                "url": settings.spotify_happiness_url,
            },
            EmotionState.NEUTRAL: {
                "title": "Deep focus mix",
                "description": "Low-distraction music for steady concentration.",
                "url": settings.spotify_neutral_url,
            },
            EmotionState.SADNESS: {
                "title": "Gentle reset mix",
                "description": "Softer tracks for a low-energy or sad moment.",
                "url": settings.spotify_sadness_url,
            },
            EmotionState.FEAR: {
                "title": "Calm study mix",
                "description": "Relaxed tracks to reduce pressure, worry, or anxiety while studying.",
                "url": settings.spotify_fear_url,
            },
            EmotionState.ANGER: {
                "title": "Cool-down mix",
                "description": "Chill songs for regaining focus after anger or frustration.",
                "url": settings.spotify_anger_url,
            },
            EmotionState.DISGUST: {
                "title": "Reset and refocus mix",
                "description": "Neutral tracks to help reset attention after discomfort or dislike.",
                "url": settings.spotify_disgust_url,
            },
            EmotionState.SURPRISE: {
                "title": "Energy stabiliser mix",
                "description": "Balanced tracks for returning to focus after a surprised reaction.",
                "url": settings.spotify_surprise_url,
            },
            EmotionState.UNKNOWN: {
                "title": "Deep focus mix",
                "description": "Default study music when no emotion estimate is available.",
                "url": settings.spotify_unknown_url,
            },
        }

    def play_soothing_music(self) -> dict:
        return self.play_for_emotion(EmotionState.UNKNOWN)

    def play_for_emotion(self, emotion: EmotionState | str | None) -> dict:
        emotion_state = self._normalise_emotion(emotion)
        preset = self._presets.get(emotion_state) or self._presets[EmotionState.UNKNOWN]
        external_url = preset["url"]
        embed_url = self._to_spotify_embed_url(external_url)
        payload = {
            "status": "playing",
            "provider": settings.music_provider,
            "title": preset["title"],
            "description": preset["description"],
            "emotion": emotion_state.value,
            "embed_url": embed_url,
            "external_url": external_url,
            "message": f"Selected {preset['title']} for your {emotion_state.value} mood on the dashboard.",
        }
        robot_state.set_music(payload)
        return payload

    def stop(self) -> dict:
        payload = {
            "status": "stopped",
            "provider": settings.music_provider,
            "title": None,
            "description": None,
            "emotion": None,
            "embed_url": None,
            "external_url": None,
            "message": "Music stopped on the dashboard.",
        }
        robot_state.set_music(payload)
        return payload

    def status(self) -> dict:
        return robot_state.snapshot()["music"]

    @staticmethod
    def _normalise_emotion(emotion: EmotionState | str | None) -> EmotionState:
        if isinstance(emotion, EmotionState):
            return emotion
        if not emotion:
            return EmotionState.UNKNOWN
        return EmotionState(str(emotion).lower())

    @staticmethod
    def _to_spotify_embed_url(url: str) -> str:
        if "/embed/" in url:
            return url
        parsed = urlparse(url)
        if "open.spotify.com" not in parsed.netloc:
            return url
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"playlist", "album", "track", "artist", "episode", "show"}:
            return f"https://open.spotify.com/embed/{parts[0]}/{parts[1]}?utm_source=generator"
        return url
