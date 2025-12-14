# engine/blacklist.py
BLACKLIST_KEYWORDS = [
    "referee", "throw-in", "corners", "asian corners", "cards", "yellow card", "red card",
    "booking", "player shots", "player to be booked", "player to be carded", "offside",
    "penalty", "own goal", "goal scorer", "player goals", "first goalscorer", "anytime goalscorer",
    "correct score", "half time", "second half", "extra time", "specials", "player props",
    "btts", "both teams to score", "double chance", "handicap result", "winning margin",
    "player assists", "player tackles", "player passes", "player fouls", "player offside"
]

def is_blacklisted_event(event_name: str) -> bool:
    name = event_name.lower()
    return any(keyword in name for keyword in BLACKLIST_KEYWORDS)