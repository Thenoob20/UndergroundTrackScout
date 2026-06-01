APP_NAME = "Underground Track Scout"
APP_VERSION = "0.8.3"

DEFAULT_GENRES = [
    "tech house", "latin house", "afro house", "deep house", "house", "techno",
    "underground hip hop", "jersey club", "baile funk", "future beats"
]

MAX_PLAYS = 50000

DJ_FRIENDLY_KEYWORDS = [
    "extended", "club", "edit", "remix", "dub", "tool", "intro", "bootleg", "refix",
    "percussion", "groove", "rolling", "warehouse", "latin", "afro"
]
NEGATIVE_KEYWORDS = ["tiktok", "viral", "festival anthem", "mainstage", "edm pop", "cover"]

NON_TRACK_KEYWORDS = [
    "dj set", "live set", "podcast", "radio show", "mix 202", "hour mix", "1 hour",
    "full set", "boiler room", "playlist", "best of", "episode", "vol.", "volume", "session", "sessions", "guest mix", "mixtape", "recorded live", "essential mix",
]

TRACKED_LABELS = [
    "Solid Grooves", "Hot Creations", "Sola", "Elrow", "Repopulate Mars", "Nervous",
    "Defected", "Toolroom", "Relief", "Dirtybird", "Moon Harbour", "Cuttin' Headz",
    "No Art", "PIV", "Saved", "Knee Deep In Sound", "Innervisions", "Keinemusik",
    "Anjunadeep", "Diynamic", "Drumcode", "Afterlife", "HATE", "Houseum"
]

DATA_DIR = "data"
EXPORT_DIR = "data/exports"
DB_PATH = "data/underground_scout.db"


SOUNDCLOUD_TAG_EXPANSIONS = {
    "tech house": [
        "#techhouse", "tech house", "deep tech", "#deeptech", "minimal tech", "#minimaltech",
        "latin tech", "#latintech", "percussion house", "#percussionhouse", "underground house",
        "#undergroundhouse", "club edit", "#clubedit", "dj edit", "#djedit", "bootleg",
        "#bootleg", "refix", "#refix", "extended mix", "warehouse house"
    ],
    "latin house": [
        "#latinhouse", "latin house", "latin tech", "#latintech", "afro latin", "#afrolatin",
        "percussion house", "#percussionhouse", "tribal house", "#tribalhouse", "club edit",
        "#clubedit", "dj edit", "#djedit", "latin remix", "latin bootleg"
    ],
    "afro house": [
        "#afrohouse", "afro house", "afro tech", "#afrotech", "afro latin", "#afrolatin",
        "tribal house", "#tribalhouse", "deep afro house", "#deepafrohouse", "percussion house",
        "#percussionhouse", "afro remix", "afro edit"
    ],
    "deep house": [
        "#deephouse", "deep house", "melodic house", "#melodichouse", "organic house",
        "#organichouse", "deep tech", "#deeptech", "underground house", "#undergroundhouse",
        "deep house edit", "deep house remix"
    ],
    "house": [
        "#housemusic", "house music", "underground house", "#undergroundhouse", "deep house",
        "#deephouse", "club edit", "#clubedit", "dj edit", "#djedit", "house bootleg",
        "house remix"
    ],
}

DISCOVERY_MODES = {
    "Balanced": {"max_queries": 10, "pages": 2, "pool_multiplier": 5},
    "Deep Dig": {"max_queries": 18, "pages": 4, "pool_multiplier": 10},
    "Edits & Bootlegs": {"extra_terms": ["club edit", "dj edit", "bootleg", "refix", "remix", "extended mix"], "max_queries": 18, "pages": 4, "pool_multiplier": 10},
    "New Uploads": {"extra_terms": ["new", "2026", "fresh", "promo"], "max_queries": 14, "pages": 3, "pool_multiplier": 8},
    "Weird Underground": {"extra_terms": ["underground", "raw", "warehouse", "minimal", "leftfield", "dub"], "max_queries": 20, "pages": 4, "pool_multiplier": 12},
}

FILTER_STRICTNESS = ["Strict", "Balanced", "Loose"]

FEEDBACK_SETTINGS_PATH = "data/feedback_settings.json"
FEEDBACK_EXPORT_DIR = "data/feedback"
DEFAULT_GOOGLE_FORM_URL = "https://forms.gle/1JBeiXKLNJSWU7QN9"
