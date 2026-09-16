import requests

API = "https://api.podblendz.com"

print("\n===== PODBLENDZ READINESS AUDIT =====\n")

try:
    blends = requests.get(
        f"{API}/blends",
        timeout=30
    ).json()

    print(f"✅ Total blends: {len(blends)}")

except Exception as e:
    print("❌ Unable to load blends")
    print(e)
    raise SystemExit()


# ------------------------------------
# BOARDS
# ------------------------------------

board_counts = {}

for blend in blends:

    board = blend.get("board")

    if not board:
        board = "Uncategorized"

    board_counts[board] = (
        board_counts.get(board, 0) + 1
    )

print("\n===== BOARDS =====\n")

for board, count in sorted(
    board_counts.items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"{board}: {count}")

# ------------------------------------
# MISSING BOARD
# ------------------------------------

missing_board = [
    b for b in blends
    if not b.get("board")
]

print(
    f"\n⚠ Uncategorized blends: "
    f"{len(missing_board)}"
)

# ------------------------------------
# EPISODE METADATA
# ------------------------------------

total_episode_objects = 0
missing_titles = 0

for blend in blends:

    episodes = blend.get(
        "episode_objects",
        []
    )

    total_episode_objects += len(episodes)

    for ep in episodes:

        if not ep.get(
            "episode_title"
        ):
            missing_titles += 1

print("\n===== METADATA =====\n")

print(
    f"Episode objects: "
    f"{total_episode_objects}"
)

print(
    f"Missing titles: "
    f"{missing_titles}"
)

# ------------------------------------
# AUDIO LINKS
# ------------------------------------

missing_audio = [
    b for b in blends
    if not b.get("audio_file")
]

print("\n===== AUDIO =====\n")

print(
    f"Missing audio files: "
    f"{len(missing_audio)}"
)

# ------------------------------------
# SIGNUP READINESS
# ------------------------------------

print("\n===== LAUNCH CHECK =====\n")

checks = {
    "Boards Working":
        len(board_counts) > 1,

    "Metadata Exists":
        total_episode_objects > 0,

    "Audio Exists":
        len(missing_audio) == 0,

    "Uncategorized Under 10":
        len(missing_board) < 10,
}

for name, passed in checks.items():

    icon = "✅" if passed else "⚠️"

    print(
        f"{icon} {name}"
    )

print("\n===== END =====\n")