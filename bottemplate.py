"""
Headpats Discord Bot Template
A simple Discord bot for custom character interactions with praise, comfort, rewards, and more.
Easily customizable with your own characters, lines, and images.

Setup:
1. Replace TOKEN with your bot token (get from Discord Developer Portal)
2. Update GUILD_ID with your server's ID
3. Create a Discord bot application and add it to your server with these scopes:
   - bot
   - applications.commands
4. Grant permissions:
   - Send Messages
   - Embed Links
   - Attach Files
5. Create the data/ folder and add JSON files (see examples below)
6. Create an images/ folder with subfolders for each character (e.g., images/sam/)
7. Run: python3 -m bot_template
"""

import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import re
from pathlib import Path
from typing import Optional

# ===============================
# CONFIGURATION
# ===============================

TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from Discord Developer Portal
PREFIX = "!"
GUILD_ID = 1234567890123456789  # Replace with your server ID
DATA_FILE = "userdata.json"
BASE_DIR = Path(__file__).parent
LINES_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "images"

# User IDs allowed to submit/edit lines (optional feature)
TRUSTED_LINE_EDITORS = {
    # 123456789012345678,  # Replace with your Discord user IDs
}

# ===============================
# LOAD JSON DATA FILES
# ===============================

def load_json(filename: str, default):
    """Load JSON from data/ folder with fallback."""
    path = LINES_DIR / filename
    if not path.exists():
        print(f"Warning: Missing data file: {path}")
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading {path}: {e}")
        return default

# Load line pools from JSON
REWARD_LINES = load_json("reward_lines.json", {})
COMFORT_LINES = load_json("comfort_lines.json", {})
COMFORT_ACTIONS = load_json("comfort_actions.json", {})
PRAISE_LINES = load_json("praise_lines.json", {})
CHARACTER_ACTIONS = load_json("character_actions.json", {})

# ===============================
# CHARACTER LIST & DISPLAY NAMES
# ===============================

CHARACTERS = [
    # Stardew Valley
    "sam", "shane", "kent", "marlon", "maru", "haley",
    "leah", "elliott", "sebastian", "abigail", "alex", 
    "morris", "harvey", "krobus", "emily", "penny", 
    "gunther", "wizard", "dwarf",
    
    # Custom examples - add your own!
    "oc1", "oc2", "oc3"
]

DISPLAY_NAMES = {
    # Custom display names (optional - used for titles/embeds)
    # "oc1": "Your Character Name",
}

def display_name(npc: str) -> str:
    """Get display name for a character."""
    return DISPLAY_NAMES.get(npc, npc.title())

# ===============================
# IMAGE RANDOMIZATION SYSTEM
# ===============================

VALID_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp")

class ShuffleCycle:
    """Ensures images/lines don't repeat until pool is exhausted."""
    
    def __init__(self, builder_func):
        self.builder_func = builder_func
        self.deck = []
        self.index = 0
        self.known_items = set()
        self.last_item = None

    def _refresh_deck(self, items):
        self.deck = list(items)
        random.shuffle(self.deck)
        # Avoid repeating the last item at the start of a new shuffle
        if self.last_item and len(self.deck) > 1 and self.deck[0] == self.last_item:
            self.deck[0], self.deck[1] = self.deck[1], self.deck[0]
        self.index = 0
        self.known_items = set(items)

    def next(self):
        current_items = self.builder_func()
        if not current_items:
            return None
        if set(current_items) != self.known_items:
            self._refresh_deck(current_items)
        if not self.deck or self.index >= len(self.deck):
            self._refresh_deck(current_items)
        item = self.deck[self.index]
        self.index += 1
        self.last_item = item
        return item

def natural_sort_key(name: str):
    """Sort filenames naturally (file1, file2, file10) instead of (file1, file10, file2)."""
    text = re.split(r"(\d+)", name.lower())
    return [int(part) if part.isdigit() else part for part in text]

def build_images(folder_name: str):
    """Build a list of images from images/<folder_name>/."""
    folder = IMAGES_DIR / folder_name.lower()
    if not folder.exists():
        return []
    images = [
        str(path) for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in VALID_IMAGE_EXTS
    ]
    return sorted(images, key=lambda p: natural_sort_key(os.path.basename(p)))

def get_image_picker(folder_name: str):
    """Get an image picker for a character."""
    return ShuffleCycle(lambda: build_images(folder_name))

# Line pickers for shuffled text output
LINE_PICKERS = {}

def pick_line(key: str, lines, fallback="Good job!"):
    """Pick a random line from a pool, avoiding repeats."""
    if isinstance(lines, str):
        return lines
    if not isinstance(lines, list) or not lines:
        return fallback
    
    picker = LINE_PICKERS.get(key)
    if picker is None:
        picker = ShuffleCycle(lambda source=lines: source)
        LINE_PICKERS[key] = picker
    
    picked = picker.next()
    return picked if picked is not None else fallback

# Image pickers for each character
IMAGE_PICKERS = {char: get_image_picker(char) for char in CHARACTERS}

# ===============================
# USER DATA PERSISTENCE
# ===============================

def load_data():
    """Load persistent user data (favorites, nicknames, identities)."""
    if not os.path.exists(DATA_FILE):
        return {
            "favorites": {},
            "nicknames": {},
            "character_nicknames": {},
            "identities": {},
            "character_identities": {},
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        data.setdefault("favorites", {})
        data.setdefault("nicknames", {})
        data.setdefault("character_nicknames", {})
        data.setdefault("identities", {})
        data.setdefault("character_identities", {})
        return data

def save_data(data):
    """Save persistent user data."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_favorite(user_id: int):
    return load_data()["favorites"].get(str(user_id))

def set_user_favorite(user_id: int, npc: str):
    data = load_data()
    data["favorites"][str(user_id)] = npc
    save_data(data)

def get_user_nickname(user_id: int, default: str, npc: str = None):
    """Get user's nickname, optionally character-specific."""
    data = load_data()
    if npc:
        char_name = data.get("character_nicknames", {}).get(str(user_id), {}).get(npc)
        if char_name:
            return char_name
    return data.get("nicknames", {}).get(str(user_id), default)

def set_user_nickname(user_id: int, nickname: str):
    data = load_data()
    data["nicknames"][str(user_id)] = nickname
    save_data(data)

def set_user_character_nickname(user_id: int, npc: str, nickname: str):
    """Set a character-specific nickname for a user."""
    data = load_data()
    data.setdefault("character_nicknames", {})
    data["character_nicknames"].setdefault(str(user_id), {})[npc] = nickname
    save_data(data)

def get_user_identity(user_id: int, npc: str = None):
    """Get user's identity (praise title), optionally character-specific."""
    data = load_data()
    if npc:
        char_identity = data.get("character_identities", {}).get(str(user_id), {}).get(npc)
        if char_identity:
            return char_identity
    return data.get("identities", {}).get(str(user_id))

def set_user_identity(user_id: int, title: str):
    data = load_data()
    data.setdefault("identities", {})
    data["identities"][str(user_id)] = title
    save_data(data)

def set_user_character_identity(user_id: int, npc: str, title: str):
    """Set a character-specific identity for a user."""
    data = load_data()
    data.setdefault("character_identities", {})
    data["character_identities"].setdefault(str(user_id), {})[npc] = title
    save_data(data)

# ===============================
# HELPER FUNCTIONS
# ===============================

def normalize_character_token(token: str) -> str:
    """Convert user input to character name (e.g., 'Sam' -> 'sam', 'Seb' -> 'sebastian')."""
    token = token.lower().strip()
    # Add your own aliases here
    aliases = {
        "seb": "sebastian",
        
    }
    cleaned = re.sub(r"[^a-z]", "", token)
    return aliases.get(cleaned, cleaned)

def character_action(npc: str) -> str:
    """Get a random action for a character (e.g., 'pats your head')."""
    if npc not in CHARACTER_ACTIONS or not CHARACTER_ACTIONS[npc]:
        return "does something nice for you"
    actions = CHARACTER_ACTIONS[npc]
    return random.choice(actions) if isinstance(actions, list) else actions

async def send_image_message(ctx, image_path: str, credit_line: str = ""):
    """Send an image with optional credit line."""
    if not os.path.exists(image_path):
        await ctx.send(f"Image not found: {image_path}")
        return
    
    file = discord.File(image_path)
    embed = discord.Embed(title=display_name(ctx.command.name) if hasattr(ctx, 'command') else "Image")
    if credit_line:
        embed.set_footer(text=credit_line)
    embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
    
    await ctx.send(file=file, embed=embed)

def format_praise(npc: str, nickname: str, identity: str) -> str:
    """Format a praise response with action and line."""
    action = character_action(npc)
    
    # Prefer a real nickname over the identity, while avoiding generic Discord mentions
    display_identity = identity
    if nickname and not nickname.startswith("<@"):
        display_identity = nickname
    
    # Get praise lines for this character, with fallback to default
    if isinstance(PRAISE_LINES, dict):
        lines = PRAISE_LINES.get(npc, PRAISE_LINES.get("default", []))
    else:
        lines = PRAISE_LINES
    
    if not lines:
        line = "Good job."
    else:
        line = pick_line(f"praise:{npc}", lines).format(identity=display_identity, user=nickname)
    
    return f"**{display_name(npc)}** {action}.\n> *{line}*"

def format_comfort_response(npc: str, nickname: str) -> str:
    """Format a comfort response with action and line."""
    action = character_action(npc)
    lines = COMFORT_LINES.get(npc, []) if isinstance(COMFORT_LINES, dict) else COMFORT_LINES
    line = pick_line(f"comfort:{npc}", lines, "I'm here for you.")
    return f"**{display_name(npc)}** {action}.\n> *{line.format(user=nickname)}*"

def format_response(npc: str, line: str, nickname: str) -> str:
    """Generic response formatter."""
    action = character_action(npc)
    return f"**{display_name(npc)}** {action}.\n> *{line.format(user=nickname)}*"

# ===============================
# DISCORD BOT SETUP
# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync(guild=discord.Object(GUILD_ID))
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"{bot.user} is now running!")

# ===============================
# COMMANDS - CORE
# ===============================

@bot.command(name="praise")
async def praise_cmd(ctx: commands.Context, character: str = None):
    """
    Praise a character!
    Usage: !praise [character]
    """
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("That's not a valid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("No favorite set! Use `/setfavorite` to pick one, or do `!praise [character]`")

    identity = get_user_identity(ctx.author.id, npc=npc)
    if not identity:
        return await ctx.send(f"Set your identity first! Use `/setidentity` to set a default, or `/setcharidentity` for {npc}-specific.")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    await ctx.send(format_praise(npc, nickname, identity))

@bot.command(name="comfort")
async def comfort_cmd(ctx: commands.Context, character: str = None):
    """
    Get comfort from a character.
    Usage: !comfort [character]
    """
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("That's not a valid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("No favorite set! Use `/setfavorite`, or do `!comfort [character]`")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    await ctx.send(format_comfort_response(npc, nickname))

@bot.command(name="pat")
async def pat_cmd(ctx: commands.Context, character: str = None):
    """
    Get a headpat reward!
    Usage: !pat [character] [task description]
    """
    message = " ".join(ctx.message.content.split()[1:])  # Get everything after !pat
    if not message:
        return await ctx.send("Usage: `!pat [character] [what you did]`")
    
    parts = message.split(" ", 1)
    first = normalize_character_token(parts[0])
    
    if first in CHARACTERS:
        npc = first
        task = parts[1] if len(parts) > 1 else ""
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("No favorite set! Use `/setfavorite` first.")
        task = message
    
    if not task:
        return await ctx.send("Tell me what you did!")
    
    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    lines = REWARD_LINES.get(npc, []) if isinstance(REWARD_LINES, dict) else REWARD_LINES
    line = pick_line(f"reward:{npc}", lines, f"Great job, {nickname}!")
    await ctx.send(format_response(npc, line, nickname))

# ===============================
# AUTOCOMPLETE HANDLERS
# ===============================

async def character_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for character names, limited to 25 choices matching user input."""
    choices = [char for char in CHARACTERS if char.startswith(current.lower())]
    # Discord limits autocomplete to 25 choices maximum
    return [
        app_commands.Choice(name=char, value=char)
        for char in sorted(choices)[:25]
    ]

# ===============================
# SLASH COMMANDS - SETUP
# ===============================

@bot.tree.command(name="setfavorite", guild=discord.Object(GUILD_ID))
@app_commands.describe(character="Who's your favorite?")
@app_commands.autocomplete(character=character_autocomplete)
async def setfavorite_cmd(interaction: discord.Interaction, character: str):
    """Set your favorite character for quick commands."""
    npc = normalize_character_token(character)
    if npc not in CHARACTERS:
        await interaction.response.send_message(f"Invalid character! Valid options: {', '.join(CHARACTERS)}")
        return
    
    set_user_favorite(interaction.user.id, npc)
    await interaction.response.send_message(f"✓ Favorite set to **{display_name(npc)}**!")

@bot.tree.command(name="setnickname", guild=discord.Object(GUILD_ID))
@app_commands.describe(nickname="What should characters call you?")
async def setnickname_cmd(interaction: discord.Interaction, nickname: str):
    """Set your nickname for responses."""
    set_user_nickname(interaction.user.id, nickname)
    await interaction.response.send_message(f"✓ Nickname set to **{nickname}**!")

@bot.tree.command(name="setidentity", guild=discord.Object(GUILD_ID))
@app_commands.describe(identity="What's your identity? (e.g., 'good girl', 'hero', 'silly goose')")
async def setidentity_cmd(interaction: discord.Interaction, identity: str):
    """Set your identity/role for praise responses."""
    set_user_identity(interaction.user.id, identity)
    await interaction.response.send_message(f"✓ Identity set to **{identity}**!")

@bot.tree.command(name="setcharidentity", guild=discord.Object(GUILD_ID))
@app_commands.describe(
    character="Which character?",
    identity="Their special name for you"
)
@app_commands.autocomplete(character=character_autocomplete)
async def setcharidentity_cmd(interaction: discord.Interaction, character: str, identity: str):
    """Set a character-specific identity."""
    npc = normalize_character_token(character)
    if npc not in CHARACTERS:
        await interaction.response.send_message(f"Invalid character! Valid options: {', '.join(CHARACTERS)}")
        return
    
    set_user_character_identity(interaction.user.id, npc, identity)
    await interaction.response.send_message(f"✓ {display_name(npc)} will call you **{identity}**!")

@bot.tree.command(name="setcharnickname", guild=discord.Object(GUILD_ID))
@app_commands.describe(
    character="Which character?",
    nickname="Their special nickname for you"
)
@app_commands.autocomplete(character=character_autocomplete)
async def setcharnickname_cmd(interaction: discord.Interaction, character: str, nickname: str):
    """Set a character-specific nickname."""
    npc = normalize_character_token(character)
    if npc not in CHARACTERS:
        await interaction.response.send_message(f"Invalid character! Valid options: {', '.join(CHARACTERS)}")
        return
    
    set_user_character_nickname(interaction.user.id, npc, nickname)
    await interaction.response.send_message(f"✓ {display_name(npc)}'s nickname for you: **{nickname}**!")

# ===============================
# RUN BOT
# ===============================

if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Update TOKEN in the config section!")
        exit(1)
    if GUILD_ID == 1234567890123456789:
        print("ERROR: Update GUILD_ID in the config section!")
        exit(1)
    
    bot.run(TOKEN)
