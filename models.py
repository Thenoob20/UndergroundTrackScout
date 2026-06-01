from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class TrackCandidate:
    artist: str
    title: str
    genre: str
    platform: str
    url: str
    artist_url: str = ""
    artwork_url: str = ""
    upload_date: Optional[str] = None
    plays: Optional[int] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    comments: Optional[int] = None
    source_reputation: float = 0.0
    source_confidence: float = 0.0
    spotify_found: bool = False
    spotify_artist_popularity: Optional[int] = None
    spotify_artist_followers: Optional[int] = None
    spotify_track_popularity: Optional[int] = None
    spotify_mainstream_penalty: float = 0.0
    spotify_note: str = ""
    spotify_url: str = ""
    label: str = ""
    label_signal: str = ""
    hidden_gem: bool = False
    track_type: str = "Unknown"
    seen_count: int = 0
    taste_score: float = 0.0
    rising_artist: bool = False
    discovery_score: float = 0.0
    reason: str = ""
    found_at: str = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SourceResult:
    tracks: list[TrackCandidate]
    errors: list[str]
