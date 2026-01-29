import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import os
import re
import time
from typing import Optional, Tuple

# ===============================
# CONFIG
# ===============================

TOKEN = "MTQ0MzE5MzkyNDI3NjcxOTY4Ng.GeQfRK.F1QWqS9Z1287Z-WX6M4seN60v2nhSb3jJui1Zk"  # <-- paste your real token here

GUILD_ID = 1379648676556968076
DATA_FILE = "userdata.json"
# ===============================
# USER DATA STORAGE
# ===============================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "favorites": {},
            "nicknames": {},
            "character_nicknames": {},
            "pronouns": {},
            "identities": {},
            "todos": {}
        }
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
        data.setdefault("favorites", {})
        data.setdefault("nicknames", {})
        data.setdefault("character_nicknames", {})
        data.setdefault("pronouns", {})
        data.setdefault("todos", {})

        # migrate older keys
        if "praise_titles" in data and "identities" not in data:
            data["identities"] = data.get("praise_titles", {})
        if "identity" in data and "identities" not in data:
            data["identities"] = data.get("identity", {})

        data.setdefault("identities", {})
        return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_favorite(user_id: int):
    return load_data()["favorites"].get(str(user_id), None)

def set_user_favorite(user_id: int, npc: str):
    data = load_data()
    data["favorites"][str(user_id)] = npc
    save_data(data)

def get_user_nickname(user_id: int, default: str, npc: str = None):
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
    data = load_data()
    data.setdefault("character_nicknames", {})
    data["character_nicknames"].setdefault(str(user_id), {})[npc] = nickname
    save_data(data)

def get_user_identity(user_id: int):
    return load_data().get("identities", {}).get(str(user_id))

def set_user_identity(user_id: int, title: str):
    data = load_data()
    data.setdefault("identities", {})
    data["identities"][str(user_id)] = title
    save_data(data)

# ===============================
# TODO LIST STORAGE
# ===============================

def get_user_todos(user_id: int):
    return list(load_data().get("todos", {}).get(str(user_id), []))

def add_user_todos(user_id: int, items):
    """Add items (iterable of strings) to the user's todo list, skipping empties and dupes."""
    cleaned = [i.strip() for i in items if i and i.strip()]
    if not cleaned:
        return []
    data = load_data()
    todos = data.setdefault("todos", {}).setdefault(str(user_id), [])
    added = []
    for item in cleaned:
        if item not in todos:
            todos.append(item)
            added.append(item)
    save_data(data)
    return added

def remove_user_todo(user_id: int, query: str):
    """Remove by 1-based index or case-insensitive text match. Returns (removed_item or None, remaining_list)."""
    data = load_data()
    todos = data.setdefault("todos", {}).setdefault(str(user_id), [])
    if not todos:
        return None, []

    # Index removal
    if re.fullmatch(r"\d+", query.strip()):
        idx = int(query.strip()) - 1
        if 0 <= idx < len(todos):
            removed = todos.pop(idx)
            save_data(data)
            return removed, todos
        return None, todos

    # Text removal (first case-insensitive hit)
    lower_query = query.strip().lower()
    for i, item in enumerate(todos):
        if item.lower() == lower_query:
            removed = todos.pop(i)
            save_data(data)
            return removed, todos

    return None, todos

def format_todo_list(todos):
    if not todos:
        return "*(empty)*"
    lines = [f"{idx}. {item}" for idx, item in enumerate(todos, start=1)]
    return "\n".join(lines)

def parse_todo_items(raw: str):
    if not raw:
        return []
    return [item.strip() for item in re.split(r"[,\n;]+", raw) if item.strip()]

# ===============================
# CHARACTER LIST (single source of truth)
# ===============================

CHARACTERS = [
    "sam", "shane", "kent", "marlon", "maru", "haley",
    "sebastian", "abigail", "alex", "morris", "harvey", "val", "sterling", "krobus",
    "emily", "penny", "gunther"
]

# ===============================
# LINES & CONSTANTS
# ===============================

REWARD_LINES = {
    "sam": [
        "Dude!! {user}, that's awesome! You crushed it!",
        "High-five AND headpats for you, {user}!",
        "You nailed it, {user}! Absolutely nailed it.",
        "{user}, you're an absolute STAR for getting that done!",
        "Achievement unlocked {user} - making hard stuff look doable.",
        "Kick-flipped that task off your plate {user}!"
    ],
    "shane": [
        "I see you, I see your accomplishments, and I'm proud of you, {user}.",
        "{user}, you got it done. Even if it wasn't perfect, that's a big deal.",
        "Good job! Every step towards success is a step you haven't taken before {user}.",
        "Hell yeah {user}, showing that task who's boss.",
        "I see how hard you're working {user}. You're doing better than you might think.",
        "You pushed through, {user}. Let's celebrate with a drink—on me.",
        "You're doing such a good job today {user}. Good {identity} get treats so, cmere."
    ],
    "kent": [
        "You handled that with discipline, {user}. Headpat earned.",
        "Excellent work, {user}. At ease, and enjoy a little rest.",
        "Mission accomplished, {user}. Stand tall for this headpat.",
        "Top notch completion of your task. I'm honored to present you with these headpats, {user}.",
        "Your resolve and commitment to the objective is most admirable. C'mere, stand down {user}. You've done well.",
        "Outstanding execution, {user}. Consider this commendation delivered.",
        "You've done extremely well to get that done {user}",
        "Top notch, {user}, I'd expect nothing less."
        "Shall *I* drop and give you 20 as a reward for such a good job {user?}. 20 what? Squats, pushups, time between your thighs?"
    ],
    "maru": [
        "Fantastic work, {user}. Your effort really shows.",
        "The data results never lie, and they say you have been very successful {user}, how excellent!",
        "Your results are stellar, {user}. Lab-approved headpats!",
        "Systems check complete—{user} is thriving. Nice job!",
        "Hypothesis confirmed: {user} gets things done. Headpats secured.",
        "That was beautifully executed, {user}. I'm logging this win."
    ],
    "haley": [
        "Awwww {user}, you did so good~!",
        "You are looking extra victorious today {user}, lemme snap a picture!",
        "That was picture-perfect, {user}! Proud of you.",
        "That glow-up is real, {user}. So proud!",
        "You totally nailed it, {user}! Let's take a celebratory selfie.",
        "You're basically iconic right now, {user}. Headpats and sparkles."
    ],
    "marlon": [
        "Strong work, {user}. You've earned this.",
        "{user}, you've conquered something incredible. Truly a mighty force.",
        "You've proven your strength again, {user}. Come claim your headpat.",
        "Battle cleared, {user}. I'm at your back with headpats ready.",
        "Not many can do what you just did, {user}. Respect.",
        "Your grit shows, {user}. Take this as a badge of honor."
    ],
    "sebastian": [
        "Way to go {user}, rolled a natural 20 on your success roll!.",
        "Well done {user} on completing your quest!",
        "Okay, wow. That was impressive, {user}. Headpat time.",
        "After that, you deserve mega experience points, {user}.",
        "You actually finished it? Sweet. Proud of you, {user}.",
        "Effort level: legendary. Come get these headpats, {user}."
    ],
    "abigail": [
        "Nice job, {user}! Headpat reward unlocked!",
        "The sweet victory of clearing a tricky level, way to go {user}!",
        "Boss fight cleared, {user}! Get over here for your prize.",
        "Quest complete and loot secured, {user}! Headpat time.",
        "You beat that level IRL, {user}. High five!",
        "Victory vibes all over you, {user}. Proud of you!"
    ],
    "alex": [
        "Good work, champ! Proud of you, {user}!",
        "Goal! Now that's how you do it {user}. ",
        "That's a winning play, {user}. Headpat from your number-one fan.",
        "You trained for this, {user}. That's how champions do it.",
        "Crushed it like a home run, {user}. Nice work.",
        "That hustle was elite, {user}. Headpat incoming."
    ],
    "morris": [
        "Ah, I suppose they do say to reward good behaviour. I suppose it wouldn't hurt to aknowledge your hard work, just this once.",
        "As long as it doesn't go to your head {user}, I'll admit you've done rather well.",
        "Your performance meets expectations, {user}. Accept this reward.",
        "Consider this a rare commendation, {user}. Efficiency recognized.",
        "Productivity metrics spiked. Accept this headpat bonus, {user}.",
        "Noted. {user}, your output is satisfactory—and then some.",
        "Ugh, I suppose it was *barely* acceptable {user} that you managed to get that done."
    ],
    "harvey": [
        "Excellent follow-through, {user}. I'm genuinely proud of you.",
        "You really put in the work, {user}. That's worth celebrating—headpats included.",
        "Consider this a clean bill of success, {user}. Outstanding job.",
        "Clinical assessment: outstanding performance, {user}.",
        "You followed through perfectly, {user}. Proud to see it.",
        "Take a deep breath and enjoy this win, {user}."
    ],
    "gunther": [
        "Remarkable contribution, {user}. I'd catalog that as exemplary.",
        "You unearthed that task like a rare artifact, {user}.",
        "Splendid work, {user}. This deserves a front-and-center display.",
        "Meticulous and thorough, {user}. Consider yourself commended.",
        "I'll be citing your diligence in the museum ledger, {user}.",
        "A flawless find, {user}. Headpats from the curator himself."
    ],
    "val": [
        "Look at you go {user}, flawless victory!",
        "{user}! Celebration vibes only.",
        "Couldn't be prouder of you, {user}; truly my everlasting firelight!",
        "That was slick, {user}. Stealing all the coolness points from the competition today, huh?",
        "You keep leveling up, {user}. Absolute star.",
        "Mission: crushed, like a pancake - or a crepe! Crepe it up, {user}."
       
    ],
    "sterling": [
        "*Borat impression* Great success! But forreal I'm mega proud of you {user}",
        "Royal {user}, you nailed it.'",
        "Sterling lifts you in a big hug. 'You did the thing, {user}! Headpats deluxe.'",
        "Massive dub, {user}. You earned VIP headpats.",
        "Look at you, {user}—pulling off miracles like it's casual.",
        "You did the dang thing, {user}. So proud of you."
    ],
    "krobus": [
        "{user}, this is a very commendable job you have done in the completing of your task!",
        "Your accomplishment radiates brightness, {user}. Please accept these headpats.",
        "Remarkable work, {user}. Even the shadows celebrate you.",
        "The shadows applaud your effort, {user}. Well done.",
        "Your diligence shines, {user}. Please accept these headpats.",
        "This accomplishment hums with light, {user}. What a wonderful job you've done."
    ],
    "emily": [
        "Wow, {user}! Your energy is sparkling today!",
        "{user}, you did amazing—I'm sending you so much good vibe glitter!",
        "Your aura's glowing, {user}! Headpats and happy dances!",
        "Such radiant effort, {user}! I'm dazzled.",
        "{user}, your work sparkles like a rainbow—headpats for you!",
        "You turned good vibes into results, {user}. Fantastic!"
    ],
    "penny": [
        "I'm so proud of you, {user}. You worked so hard!",
        "{user}, you did wonderfully. Take this headpat and a warm smile.",
        "You handled that so well, {user}. Headpat and a cozy cup of tea.",
        "You did beautifully, {user}. I'm really proud.",
        "Great job following through, {user}. Here's a cozy headpat.",
        "That was so thoughtful of you, {user}. Well done."
    ]
}

COMFORT_LINES = {
    "sam": [
        "Hey {user}… hey. C'mere. Sam's got you.",
        "Take a breath with me, {user}. I'm not going anywhere.",
        "Whatever's weighing you down, {user}, we'll carry it together.",
        "Lean here a second, {user}. Let it out—I can take it.",
        "Even on the hard days, {user}, you're not facing it alone.",
        "I'm right beside you, {user}. No rush, just breathe.",
        "I'll always be your player two, c'mere {user}"
    ],
    "shane": [
        "Rough day, huh {user}? …Yeah. I get it. Come here.",
        "Come sit with me, {user}. We'll just exist for a bit.",
        "Lean in, {user}. You don't have to talk—just stay close.",
        "I'll keep the world quiet for a minute, {user}.",
        "No fixes needed right now, {user}. Just let me hold you.",
        "C'mere and let it out {user}. Let me be your safety."
    ],
    "kent": [
        "Stand easy, {user}. You're safe.",
        "At ease, {user}. I've got your back.",
        "Slow, steady breaths. You're home now, {user}.",
        "You're off duty, {user}. Rest those shoulders.",
        "Stay grounded with me, {user}. I've got watch.",
        "You're among allies, {user}. Let yourself settle."
    ],
    "maru": [
        "You're doing your best, {user}. I'm proud of you.",
        "Let's recalibrate—deep breath, {user}. I've got you.",
        "Hey, {user}. Rest mode engaged. I'll stay right here.",
        "Let's reroute the stress, {user}. Hand it over.",
        "Your heart's under my protection, {user}. Rest easy.",
        "Diagnostics say you need cuddles, {user}. Come here."
    ],
    "haley": [
        "Awwww, {user}… come here. Let me take care of you.",
        "It's okay to be soft right now, {user}. I've got you.",
        "Come here, {user}. I'll hold you until the clouds pass.",
        "We can hide under the coziest blanket, {user}. Just us.",
        "You don't have to smile for me, {user}. I'll keep you safe.",
        "Here, {user}. Let me brush the worries out of your hair."
    ],
    "marlon": [
        "Steady now, {user}. You're not alone.",
        "Easy, {user}. I've got you covered.",
        "Take shelter here, {user}. I'll stand guard.",
        "Rest by the fire, {user}. Nothing gets past me.",
        "Your burdens are lighter when we share the weight, {user}.",
        "If you falter, I'll hold you steady, {user}."
    ],
    "sebastian": [
        "…yeah. I get it. Come here, {user}.",
        "Sit with me a while, {user}. No pressure, just quiet.",
        "Scoot closer, {user}. We can ride this out together.",
        "We can just listen to the rain, {user}. No words needed.",
        "I'll keep the screens dim for you, {user}. Rest here.",
        "Lean on my shoulder, {user}. I'll stay as long as you need."
    ],
    "abigail": [
        "Bad day? I got you, {user}.",
        "Hey, {user}, let's just curl up for a bit.",
        "Come here, {user}. I'll keep the bad vibes away.",
        "I'll guard your heart like a final boss, {user}.",
        "Grab the blanket fort, {user}. We'll camp out till you feel better.",
        "No monsters allowed in here, {user}. You're safe with me."
    ],
    "alex": [
        "Hey hey— you're okay, {user}. Come here.",
        "C'mon, {user}. Deep breath in, deep breath out. I'm here.",
        "Huddle up, {user}. We'll get through this together.",
        "Team huddle, {user}. I've got the play—it's rest.",
        "I'll shield you from the crowd noise, {user}. Just breathe.",
        "Lean on me, {user}. I'll carry the weight for a bit."
    ],
    "morris": [
        "Oh, uh, c'mere. But DON'T let me catch you slacking later.",
        "Compose yourself, {user}. I'm… here, alright?",
        "Fine, {user}. Five minutes. Lean on me if you must.",
        "Very well, {user}. I suppose I can be a shoulder… briefly.",
        "Don't mistake this for softness, {user}. But I'm not leaving.",
        "I'll oversee your recovery, {user}. Regain your composure here."
    ],
    "harvey": [
        "Deep breath, {user}. I'm right here with you.",
        "{user}, let's slow down together. You're safe, I've got you.",
        "It's okay to rest, {user}. Let me keep watch for a while.",
        "Your pulse can settle with me, {user}. I'm not going anywhere.",
        "Let's lower the lights and breathe together, {user}.",
        "I'll handle the worries, {user}. You just focus on resting."
    ],
    "gunther": [
        "Take shelter in the stacks, {user}. It's calm here.",
        "Rest here a moment, {user}. Even curators need quiet.",
        "Let me shoulder the weight for a bit, {user}. Breathe.",
        "You're safe among these shelves, {user}. No rush.",
        "We'll archive the worries together, {user}. You're not alone.",
        "Sit with me, {user}. The world can wait while you steady."
    ],
    "val": [
        "Let's turn that frown upside down {user}",
        "Hey, {user}, we can wait it out together I've got snacks and everything.",
        "Come closer, {user}. Lemme kiss away some of that doom and gloom.",
        "Slide into my arms, {user}. We'll wait this one out in style.",
        "I promised to take good care of your heart {user}, and I never go back on a promise.",
        "If you're struggling to keep your chin up, let me help. I love holding your face in my hands."
    ],
    "sterling": [
        "{user}, I hate to see you so sour, lemme give you some sugar!",
        "don't worry {user} it can't rain all the time.",
        "C'mere, {user}. I'll keep you steady while it passes.",
        "I'll be the umbrella; you stand over mkay {user}?",
        "Squeeze in, {user}. I've got warmth and bad jokes on standby.",
        "You get the front row seat to my pep talk, {user}. Snuggle up."
    ],
    "krobus": [
        "{user}, are you 'in the dumps' as they say? May I help?",
        "Please, {user}, allow me to share some calm with you.",
        "Stay near, {user}. The shadows can be comforting when shared.",
        "I will watch the dark corners, {user}. You can rest.",
        "Let the quiet of the sewers soothe you, {user}. I am here.",
        "Your light is safe beside me, {user}. Breathe with me."
    ],
    "emily": [
        "Oh, {user}, come here. Let's breathe and let the colors calm you.",
        "{user}, you're safe. Let me wrap you in some soft, blue comfort.",
        "Close your eyes, {user}. Feel the bright, warm glow I'm sending you.",
        "I'll weave a blanket of good vibes around you, {user}.",
        "Inhale the rainbow, exhale the gray, {user}. I've got you.",
        "Let the universe hug you through me, {user}. Stay close."
    ],
    "penny": [
        "Hey {user}, it's okay. Let's take it slow together.",
        "{user}, I'm here. You can rest for a bit, alright?",
        "Here, {user}. Lean on me and breathe; we'll go at your pace.",
        "Let me hold your hand, {user}. We'll read quietly till you feel better.",
        "You can set your worries down with me, {user}.",
        "I'll keep things gentle and soft, {user}. Just stay with me."
    ]
}

BAP_LINES = {
    "sam": ["Sam flicks your forehead. 'Break time means break time, {user}. Drop the mod tools.'"],
    "shane": ["Shane side-eyes you. 'You're supposed to be off the clock, {user}. Back away from the mods.'"],
    "kent": ["Kent crosses his arms. 'Soldiers need rest, {user}. Stand down from modding.'"],
    "maru": ["Maru raises an eyebrow. 'You scheduled rest, not modding, {user}. Step away from the laptop.'"],
    "haley": ["Haley points to the door. 'No modding on break, {user}. Go do literally anything else cute.'"],
    "marlon": ["Marlon bonks you lightly. 'Breaks are part of training, {user}. Log off the mods.'"],
    "sebastian": ["Sebastian sighs. 'Even I close the IDE sometimes, {user}. Take the break.'"],
    "abigail": ["Abigail taps your head. 'No modding, {user}. We're raiding the snack cupboard instead.'"],
    "alex": ["Alex wags a finger. 'Coach's orders, {user}: bench the modding and hydrate.'"],
    "morris": ["Morris glares. 'Time off is mandatory, {user}. Cease your… tinkering.'"],
    "harvey": ["Harvey adjusts his glasses. 'Doctor's orders, {user}: log off and rest that brain.'"],
    "val": ["Val grins and bops you. 'Mods can wait, {user}. Break time is sacred.'"],
    "sterling": ["Sterling snaps your laptop shut. 'Hey {user}, break means chill. Mods can simmer.'"],
    "krobus": ["Krobus taps your forehead. 'Rest restores the spirit, {user}. Cease modding—for now.'"],
    "emily": ["Emily boops your nose. 'Break energy only, {user}! No modding vibe allowed.'"],
    "penny": ["Penny sets a book over your keyboard. 'Time to rest, {user}. The mods can wait.'"],
    "gunther": ["Gunther adjusts his glasses. 'Archives are closed, {user}. Log off and rest.'"]
}

BUTT_PAT_LINES = {
    "sam": [
        "cracks a grin and gives you a playful pat on the ass, {user}.",
        "smirks, snaps his wrist, and lands a cheeky smack. 'Motivation delivered, {user}!'",
        "leans in close, pats your ass, and whispers, 'You know I've got your back, {user}.'",
        "pats twice and winks. 'Bonus boost for you, {user}.'",
        "gives a gentle smack followed by a rub. 'You got this, {user}.'"
    ],
    "shane": [
        "'s palm lands with a warm thwap. 'You like that, {user}?'",
        "gives a quick, firm pat and mutters, 'Figured you needed that, {user}.'",
        "smirks, pats your ass, and adds, 'Consider it a quality check, {user}.'",
        "taps twice, smirking. 'Back to it, {user}.'",
        "gives a slow, firm pat then squeezes. 'That's for being tough, {user}.'",
        "smirks and hauls his hand back to smack your ass 'fuck {user} I love how your ass moves'"
    ],
    "kent": [
        "'s gloved hand delivers a firm pat, controlled but undeniably bold.",
        "pats your ass like he's issuing field orders. 'Stay sharp, {user}.'",
        "gives a measured smack, eyes steady. 'You've earned a little attention, {user}.'",
        "delivers a crisp pat like a drill command. 'Carry on, {user}.'",
        "gives a steady smack then a reassuring squeeze. 'Proud of your discipline, {user}.'"
    ],
    "maru": [
        "tests the trajectory, then pats your ass with scientific satisfaction.",
        "calibrates her aim, lands a precise smack, and notes, 'Optimal impact achieved, {user}.'",
        "laughs, delivers a playful pat, and says, 'Peer-reviewed affection, {user}.'",
        "measures the angle, pats, and notes, 'Force applied successfully, {user}.'",
        "delivers a playful double-tap. 'Data shows you like encouragement, {user}.'"
    ],
    "haley": [
        "giggles, spins you, and gives your ass a playful pat.",
        "winks, snaps a photo mid-swat, and squeals, 'So cute, {user}!'",
        "gives a soft smack followed by a squeeze. 'You look amazing, {user}.'",
        "pats lightly then smooths your outfit. 'Perfect aesthetic, {user}.'",
        " playfully swats and laughs. 'Consider yourself adored, {user}.'"
    ],
    "marlon": [
        "delivers a confident pat, protective and possessive all at once.",
        "gives a solid smack, then stands guard behind you. 'Mine to watch over, {user}.'",
        "pats your ass with a warrior's assurance. 'You've got strength and style, {user}.'",
        "gives a protective smack, eyes scanning the horizon. 'Safe and seen, {user}.'",
        "pats once more with a grunt. 'Battle ready, {user}.'"
    ],
    "sebastian": [
        "'s hand finds you with a shy-but-solid pat. He looks away, but you feel the heat.",
        "gives a quick smack, cheeks flushing. 'Don't make it weird, {user}.'",
        "pats your ass gently, murmuring, 'Guess I'm braver today, {user}.'",
        "tugs you closer and delivers a shy tap. 'Don't tell anyone, {user}.'",
        "gives a careful smack then buries his face in his hoodie. 'Yeah… you deserved that, {user}.'"
    ],
    "abigail": [
        "lunges in with a mischievous grin and pats your ass—chaotic and affectionate.",
        "double-taps your butt like it's a game controller. 'Extra lives for you, {user}!'",
        "smacks your ass, laughs, and declares, 'Critical hit on that booty, {user}!'",
        "drumrolls with a double pat. 'Combo hit, {user}!'",
        "backhands a playful smack and cackles. 'Chaotic encouragement unlocked, {user}.'"
    ],
    "alex": [
        "gives your ass a proud athlete's pat. 'Looking good, {user}.'",
        "lands a locker-room smack and grins. 'MVP energy, {user}.'",
        "pats your ass, then flexes. 'Team spirit, {user}. Always.'",
        "gives a celebratory slap then claps. 'Scoreboard loves you, {user}.'",
        "double-pats like a teammate. 'Stay in the zone, {user}.'"
    ],
    "morris": [
        "'This is absolutely an HR violation, but...' Morris gives your butt a small pat. 'You've earned it. If you tell anyone you're fired {user}.'",
        "delivers a brisk pat like he's stamping paperwork. 'Efficiency rewarded, {user}.'",
        "smacks your ass, adjusts his tie, and mutters, 'Consider this an unorthodox bonus, {user}.'",
        "offers a cautious pat. 'Consider this an unconventional bonus, {user}.'",
        "once, checks his watch. 'Time is money, {user}; so is praise.'"
    ],
    "harvey": [
        "clears his throat, sets the clipboard down, and gives you a firm, reassuring pat on the ass, {user}.",
        "offers a careful smack followed by a blush. 'A little positive reinforcement, {user}.'",
        "pats your ass with clinical precision and a smile. 'Vitals look great, {user}.'",
        "pats gently, then reassures, 'Purely therapeutic, {user}.'",
        "he gives a firmer smack with a smile. 'Positive reinforcement administered, {user}.'"
    ],
    "gunther": [
        "gives a gentle pat, like placing a rare tome back on the shelf, {user}.",
        "her smirks and delivers a firm smack. 'For excellent fieldwork, {user}.'",
        "With curatorly confidence, Gunther pats your butt. 'Properly cataloged, {user}.'",
        "pauses after he pats your butt and gives soft little rub. 'Filed under exceptional, {user}.'",
        "delivers a neat smack and nods. 'Properly archived praise, {user}.'"
    ],
    "val": [
        "grins at you. 'Why don't you do like my friend and Ben Dover' They playfully grab you and smack your butt",
        "delivers a dramatic smack and bows. 'Encore for that peach, {user}?'",
        "pats your ass, then spins you. 'That'll flip any frown, {user}.'",
        "gives a lazy smack and purrs, 'Vintage peach, {user}.'",
        "grabs your cheeks hard to lift you up a little with a grin as they paw at you. 'Quality control passed, {user}.'",
        "'s claws drag lightly along your ass as he gives it a solid slap, then hoisting you up legs around their torso."
    ],
    "sterling": [
        "flashes a grin as he winds up his hand. '{user} your ass is too fine to *not* smack right now!'",
        "pats your ass, then salutes. 'Service with a smile, {user}.'",
        "lands a playful smack and laughs. 'Premium goods, {user}.'",
        "fans his hand dramatically before smacking. 'Encore, {user}!'",
        "pats twice then laughs. 'Certified premium, {user}.'",
        "'s hand smacks hard on your ass, then he grabs it to pull you closer.",

    ],
    "krobus": [
        "blushes 'I've heard that these can be remedying of 'the sads', *pats butt softly*",
        "pats your ass gently, whispering, 'A strange custom, but I hope it comforts you, {user}.'",
        "gives a careful smack and nods. 'Did that help ease the gloom, {user}?'",
        "tests the custom gently. 'Was that acceptable encouragement, {user}?'",
        "gives a soft double-tap. 'Shadow-approved pat for you, {user}.'"
    ],
    "emily": [
        "giggles and gives a playful pat. 'A little pep energy for you, {user}!'",
        "smacks your ass lightly, sprinkling imaginary glitter. 'Shiny vibes, {user}!'",
        "pats your ass, then hugs you. 'Balanced chakra with a bop, {user}.'",
        "swats lightly and sprinkles pretend glitter. 'Shiny boost, {user}!'",
        "pats twice to a rhythm. 'Feel the groove and the love, {user}.'"
    ],
    "penny": [
        "blushes, then pats your butt quickly. 'Oh! Um—sorry, {user}! That was… for encouragement!'",
        "gives a timid smack, then covers her face. 'Was that okay, {user}?'",
        "pats your ass softly and smiles. 'You deserve some playful encouragement, {user}.'",
        "pats softly then squeaks. 'Oops—um, encouragement, {user}!'",
        "gives a quick double pat with a shy smile. 'You're doing great, {user}.'"
    ]
}

FOREHEAD_KISSES = {
    "sam": [
        "sweeps you up with warm arms and presses a soft, affectionate kiss to your forehead.",
        "leans in close with a shy grin and kisses your forehead gently, lingering longer than he meant to.",
        "bumps his forehead to yours playfully before leaving a soft kiss there.",
        "reaches and immediately pulls you into an almost crushingly tight embrace before kissing your forehead.",
        "grins, tugs you under his chin, and drops a warm kiss onto your forehead.",
        "He tips your hat back and plants a confident kiss right in the center of your brow.",
        "ruffles your hair, pauses, then presses a quick, sincere forehead kiss with a blush.",
        "He pulls you into a hoodie hug and gives you a forehead kiss that says 'I've got you.'"
    ],
    "shane": [
        "cups your jaw with surprising tenderness and lets his lips brush your forehead, slow and warm.",
        "pulls you in by your shirt, smiling as he gives you a forehead kiss",
        "presses a low, lingering kiss to your forehead.",
        "grabs you around the waist with a rough grumble and holds you tight, dipping to give your forehead a quick kiss.",
        "mutters 'c'mere,' presses his forehead to yours, then leaves a soft kiss there.",
        "bumps your shoulder, looks away, and plants a quick kiss on your brow with a half-smile.",
        "sighs, hooks an arm around you, and gives a steady forehead kiss that smells faintly of beer and warmth.",
        "He tugs your hood up, hides you from the world, and sneaks a gentle kiss to your forehead."
    ],
    "kent": [
        "rests a steady hand on your shoulder before leaning in to kiss your forehead—careful, protective, grounding.",
        "presses a soft kiss to your forehead as if he's blessing you with safety itself.",
        "kisses your forehead like a quiet promise that he's watching over you.",
        "takes your wrist firm but commanding to tug you forwards so he can kiss your forehead.",
        "kisses your forehead while wrapping you in a tight hug.",
        "rests his palm against your brow, then presses a deliberate kiss like a medal of honor.",
        "He bows slightly to meet your eyes before placing a respectful kiss on your forehead.",
        "exhales tension, then grants you a firm, reassuring kiss between your brows.",
        "He draws you into his chest, keeps watch over your shoulder, and kisses your forehead like standing guard."
    ],
    "maru": [
        "hums softly as she places a precise, sweet kiss to your forehead—like she's calibrating your heart.",
        "brushes your hair aside and kisses your forehead with a scientist's gentleness and a lover's warmth.",
        "kisses your forehead with a bright giggle, like she just flipped a switch from worry to warmth.",
        "lines up the perfect angle, then presses a tender kiss to your forehead as if sealing a circuit.",
        "taps your temple with her nose, then leaves a careful kiss right in the center of your forehead.",
        "murmurs, 'Vital signs: loved,' before giving your forehead a soft, clinical-sweet kiss.",
        "kisses your forehead and grins. 'Hypothesis: forehead kisses improve mood by 200%. Confirmed.'"
    ],
    "haley": [
        "cups your cheeks and kisses your forehead like you're something delicate and pretty she wants to protect.",
        "smooths your hair and gives you a soft forehead kiss, humming happily afterward.",
        "laughs softly, smoothing your hair and dotting your forehead with a quick, sweet kiss.",
        "snaps an invisible selfie pose, then plants a perfect little kiss on your forehead.",
        "whispers, 'Stay shiny,' before pressing a sparkly-soft kiss to your brow.",
        "wiggles closer, leaves a kiss on your forehead, and says, 'Framing you in love, always.'",
        "kisses your forehead like she's sealing a promise that today will turn out cute."
    ],
    "marlon": [
        "leans in and touches his forehead to yours before kissing you like a quiet vow of protection.",
        "kisses your forehead slowly, a warrior's promise wrapped in tenderness.",
        "plants a steady forehead kiss, gentleness forged like armor around you.",
        "steadies your shoulders, then leaves a firm, reverent kiss on your forehead.",
        "bows his head to yours, pressing a protective kiss right between your brows.",
        "kisses your forehead like he's swearing an oath to keep you safe.",
        "brushes away your worries with his thumb, then seals it with a forehead kiss."
    ],
    "sebastian": [
        "tilts your chin up, avoids eye contact for a second… then kisses your forehead so gently it's almost shy.",
        "kisses your forehead with a soft exhale, like he can finally breathe again with you close.",
        "presses a quick forehead kiss, muttering something soft only you can hear.",
        "glances up from his computer and immediately reaches to pull you into his lap cradling you and kissing your forehead tenderly.",
        "wraps you in his hoodie before pulling you close and sweetly kissing your nose before moving to your forehead.",
        "pauses his game, lowers his headset, and gives your forehead a lingering kiss like a checkpoint save.",
        "He tugs his hoodie over both of you, pressing a secret kiss to your forehead in the dark.",
        "scribbles a tiny heart on your hand, then follows it with a soft forehead kiss.",
        "He meets your eyes, blushes, and kisses your forehead like he's downloading courage."
    ],
    "abigail": [
        "jumps closer and plants an energetic, affectionate kiss right in the center of your forehead.",
        "wraps her arms around you and gives your forehead the sweetest, most chaotic kiss imaginable.",
        "dots your forehead with a quick kiss, eyes bright like she just won a prize.",
        "bonks her head against yours in a playful headbutt, then drops a kiss on your forehead.",
        "She declares 'buff granted!' and stamps your forehead with a fast, fond kiss.",
        "grins, squeezes you tight, and plants a victorious kiss on your brow.",
        "She tips your chin up with her finger sword, then taps a gentle kiss to your forehead."
    ],
    "alex": [
        "pulls you into his chest and kisses your forehead like it's the most natural thing in the world.",
        "gives a warm, confident forehead kiss, thumb brushing your cheek as he smiles against your skin.",
        "nudges your hair aside and kisses your forehead like he's celebrating you.",
        "taps his nose to your forehead, then leaves a proud, steady kiss there.",
        "whispers, 'Champ,' and seals it with a forehead kiss that feels like a trophy.",
        "He lifts your cap, kisses your forehead, and sets it back like crowning you MVP.",
        "pulls you into a huddle, bumps foreheads, then kisses yours with game-winning warmth."
    ],
    "morris": [
        "awkwardly wraps an arm around your shoulder and darts in for a quick kiss on your forehead",
        "tilts your chin, glances around, and then brushes his lips against your forehead",
        "clears his throat, then delivers a brisk forehead kiss like a confidential memo.",
        "offers a perfunctory kiss to your forehead, then pretends it was purely 'for morale metrics.'",
        "He straightens your collar, sighs, and plants a surprisingly soft kiss on your forehead.",
        "leans in, whispers 'this is off the record,' and kisses your brow quickly.",
        "He taps his pen against his lip, decides, and gives your forehead a brief, earnest kiss."
    ],
    "harvey": [
        "cups your jaw with gentle hands and presses a warm, steady kiss to your forehead.",
        "smiles softly before kissing your forehead, letting reassurance linger in the touch.",
        "leans close and kisses your forehead with a doctor's calm assurance.",
        "checks your pulse with two fingers, then leaves a tender kiss on your forehead for good measure.",
        "lowers the lights, draws you close, and places a caring kiss right at your brow.",
        "He brushes his thumb over your temple, then seals his comfort with a forehead kiss.",
        "gives you a forehead kiss that feels like a clean bill of emotional health."
    ],
    "gunther": [
        "cups your jaw gently and plants a scholarly-soft kiss on your forehead.",
        "brushes dust from your brow before a careful kiss. 'Impeccable, {user}.'",
        "leans in with warmth and places a steady kiss to your forehead.",
        "marks an invisible catalog number above your brow with his finger, then kisses it softly.",
        "He adjusts his glasses, smiles, and presses a precise kiss to your forehead.",
        "murmurs, 'A rare treasure,' and sets a gentle kiss on your brow.",
        "He cradles the back of your head like a precious tome before kissing your forehead."
    ],
    "val": [
        "slides two fingers under your chin, tilting your face to meet theirs with a soft smile before kissing your forehead",
        "'s arms wrap around you tight and you feel their lips on the top of your head",
        "peppers your forehead with kisses.",
        "'s tail curls around your wrist to yank you forward, bonking you with their horns before they kiss your forehead.",
        "drags you into their chest and leaves a slow, burning kiss on your forehead.",
        "winks, taps your nose with a claw, then plants a smug kiss on your brow.",
        "They rumble a purr, pressing kiss after kiss across your forehead until you melt.",
        "tilts your face up with their tail, then delivers a forehead kiss that feels like being chosen."
    ],
    "sterling": [
        "grins as he brings your forehead close for kisses.",
        "wraps his arms around you tight, pressing a kiss to your forehead with a smile.",
        "plants an exaggerated forehead kiss, then laughs against your skin.",
        "snags you by the shoulders and boops your nose, then pulls you in to kiss your forehead.",
        "nuzzles you gently as he hugs you tight and gives lots of little forehead kisses.",
        "salutes, then swoops down to plant a bold kiss on your forehead.",
        "He peppers your forehead with rapid-fire kisses until you're giggling.",
        "lifts you half off the ground, kisses your brow, and spins you once for flair.",
        "He cups your face, grins, and leaves a slow, affectionate kiss on your forehead."
    ],
    "krobus": [
        "makes a soft noise and beckons you closer, clearly wanting to offer comfort/support. ",
        "rests his forehead against yours before pressing a kiss there.",
        "shyly presses a featherlight kiss to your forehead, the shadows humming their approval.",
        "softly asks permission, then delivers a careful kiss to your forehead, eyes glowing.",
        "He cups your face with cool hands, placing a reverent kiss right between your brows.",
        "hums low, pressing a lingering kiss to your forehead that leaves a warmth in the dark.",
        "He shields you with his cloak of shadows, then kisses your brow like a quiet blessing."
    ],
    "emily": [
        "presses a warm kiss to your forehead, whispering soft encouragements when she pulls away.",
        "Her fingers reach out and pull you close so that she can stretch on her toes. With a soft giggle she kisses your forehead.",
        "There's something extra comforting about the way Emily wraps you in her arms and presses a few quick kisses on your face and the top of your head.",
        "sprinkles imaginary glitter above you, then seals it with a sparkling forehead kiss.",
        "She hums a rainbowy tune, punctuating it with a soft kiss to your brow.",
        "presses her palm to your heart, then kisses your forehead like she's aligning your aura.",
        "She giggles, dots your forehead with a kiss, and says, 'Color restored!'"
    ],
    "penny": [
        "cups your face and plants a tender kiss on your forehead.'",
        "leans in with a shy smile and kisses your forehead.",
        "brushes a stray hair back behind your ear as she leans over to give a comforting press of her lips to your head.",
        "squeezes your hands, stands on tiptoe, and leaves a sweet kiss on your forehead.",
        "She hums a quiet tune from her favorite book, ending it with a gentle forehead kiss.",
        "tucks you under her chin, then plants a soft, lingering kiss on your brow.",
        "She smiles, brushes your bangs aside, and presses a warm kiss right between your eyebrows."
    ]
}

BUHH_PROMPTS = [
    "have you eaten recently?",
    "how long has it been since you had water?",
    "do you maybe need to get up and stretch?",
    "how long has it been since you've done the sleeps?"
]

PRESET_TASKS = {
    "drank_water": {"label": "I drank water", "lines": ["{user}, you actually hydrated. I am SO proud of you."]},
    "took_meds": {"label": "I took my meds", "lines": ["{user}, taking your meds is brave and responsible. Headpats~"]},
    "did_dishes": {"label": "I did the dishes", "lines": ["The Dish Boss has been defeated. Victory, {user}!"]},
    "did_allthings": {"label": "I did all the things", "lines": ["Hell to the yeah {user}, achievement unlocked I'm so proud of you"]},
    "did_nomurders": {"label": "I didn't kill anyone", "lines": ["Good job {user}, bail is expensive."]},
    "wrote_allwords": {"label": "I wrote all the words", "lines": ["Boss {user} writing words and kicking ass, hell yeah."]},
    "arted_allart": {"label": "I arted all the art", "lines": ["Art is beautiful, thank you for adding more to the collection {user}, truly a muse of our time."]},
    "tookout_trash": {"label": "I took out the trash", "lines": ["Garbage vanquished! {user}, you're a domestic hero.", "{user}, the trash is out and you are in my good books. Headpat secured."]},
    "cleaned_counter": {"label": "I cleaned the counter", "lines": ["Counter spotless! {user}, you made the kitchen sparkle.", "{user}, that counter shines like a quartz. Proud of you."]},
    "cleaned_floor": {"label": "I cleaned the floor", "lines": ["Floor so clean you could host a royal banquet. Nice work, {user}.", "{user}, that floor gleams. Headpat for your shine effort."]},
    "putaway_thing": {"label": "I put away the thing", "lines": ["Order restored. {user}, thanks for putting that away.", "{user}, you put it away and brought peace to the room."]},
    "did_selfmaintenance": {"label": "I did self-maintenance", "lines": ["Taking care of yourself is top-tier work, {user}. Big headpats.", "{user}, you invested in yourself. That's the best upgrade path."]},
    "folded_laundry": {"label": "I folded the laundry", "lines": ["Laundry folded and conquered. Nice work, {user}.", "{user}, those stacks look great. Fresh headpat incoming."]},
    "didnt_textmyex": {"label": "I didn't text my ex", "lines": ["Restraint level: legendary. Proud of you, {user}.", "{user}, you chose peace and self-respect. Headpat unlocked."]},
    "didnt_dotheimpulsivething": {"label": "I didn't do the impulsive thing", "lines": ["You paused, you chose wisely. Proud of you, {user}.", "{user}, that restraint is power. Headpat achieved."]},
    "didnt_openthatriskysnapchat": {"label": "I didn't open that risky Snapchat", "lines": ["Temptation resisted! {user}, your willpower is strong.", "{user}, you kept your peace and dodged drama. Nice work."]},
    "didnt_impulsebuy": {"label": "I didn't impulse buy", "lines": ["Wallet defended. {user}, your future self thanks you.", "{user}, you said no to the shiny thing. Headpat unlocked."]},
}

CHARACTER_ACTIONS = {
    "sam": [
        "pulls you into a warm, clingy hug and ruffles your hair",
        "leans his forehead to yours before playfully ruffling your hair with a grin",
        "hooks his chin over your shoulder and gives lazy, reassuring pats",
        "slides an arm around you and scruffgives slow, intimate head rubsgives slow, intimate head rubss your hair with fondness",
        "rests his cheek to the top of your head and rocks you gently",
        "wraps both arms around you and musses your hair until you laugh"
    ],
    "shane": [
        "wraps an arm around your waist and nuzzles his cheek against your neck softly",
        "tilts his head against yours, pulling you against his chest and hands curling into your hair",
        "rests his forehead to the back of your head and pets quietly",
        "tugs you closer by the hoodie and scratches softly at your scalp",
        "lets out a sigh and cards his fingers through your hair with care",
        "presses his temple to yours, giving steady, grounding strokes"
    ],
    "kent": [
        "cups the back of your head and presses a soft forehead kiss",
        "rests a steady hand on your shoulder before smoothing your hair down",
        "pulls you into his chest, rubbing small circles at your crown",
        "aligns his breathing with yours while his palm steadies your hair",
        "clasps your neck gently, thumb tracing calming lines into your scalp",
        "bows his head to yours, brushing your hair back with soldierly care"
    ],
    "maru": [
        "smiles gently and rubs comforting circles into your scalp",
        "adjusts your hair with careful fingers before resting her brow to yours",
        "slides her fingers through your hair like she's tuning strings",
        "taps your forehead with hers, then smooths your hair back into place",
        "cradles the back of your head and hums while she pets softly",
        "plays with a lock of your hair before letting it fall and stroking down"
    ],
    "haley": [
        "cups your cheeks and plants soft forehead kisses between pats",
        "threads her fingers through your hair while humming a soft tune",
        "pulls you into a photo-ready cuddle and smooths stray hairs lovingly",
        "brushes her nose against yours, then traces gentle strokes over your hair",
        "wraps you in her arms and combs her fingers through your hair slowly",
        "gently fixes your bangs before leaning in to pat and giggle"
    ],
    "marlon": [
        "rests his forehead to yours before giving grounding head rubs",
        "draws you close with a firm arm and smooths your hair back carefully",
        "plants you against his chest and scratches lightly at your scalp",
        "cups the back of your head, thumb sweeping slow arcs of comfort",
        "holds you still with steady hands and rubs your hair in protective circles",
        "tucks you under his chin and pets with the patience of a watchman"
    ],
    "sebastian": [
        "leans close and pets your hair with surprising gentleness",
        "nudges your shoulder with his and scratches lightly at your scalp",
        "lets his fingers drift through your hair while he rests beside you",
        "leans his head atop yours, giving absent-minded little strokes",
        "slides his hand down your hair, then back up in slow repetition",
        "rests against you and traces lazy patterns at the nape of your neck"
    ],
    "abigail": [
        "bounces closer and affectionately pets your hair",
        "wraps you up and tousles your hair with gleeful little pats",
        "loops her arms around your neck and scritches happily at your scalp",
        "leans in forehead-first, then ruffles until you squeak",
        "rocks you side to side while patting a playful rhythm on your head",
        "nuzzles your temple and gives energetic, messy hair rubs"
    ],
    "alex": [
        "wraps an arm around your shoulders and gives confident warm pats",
        "rests his chin atop your head while his hand rubs slow circles",
        "draws you tight against his side, knuckles grazing your scalp",
        "sets a protective hand on your crown and smooths downward",
        "pulls you into a chest bump before patting your hair with a grin",
        "leans in with a proud smile and ruffles your hair like a champ"
    ],
    "morris": [
        "awkwardly puts his hand on the top of your head",
        "straightens your collar before offering a stiff but earnest head pat",
        "brushes off imaginary lint, then pats your hair with managerial care",
        "gives a quick, efficient head pat like signing a memo",
        "adjusts your posture, then rests his palm briefly on your crown",
        "sighs, softens, and smooths a stray hair back into place"
    ],
    "harvey": [
        "rests his palm against your crown with a calm, grounding pat",
        "tips your chin up and smooths your hair back with practiced care",
        "aligns your breathing with his while his fingers comb gently",
        "places one steady hand at your nape, rubbing soothing circles",
        "brushes your hair back behind your ear, then pats reassuringly",
        "holds you close and strokes your hair with a doctor's steady touch"
    ],
    "gunther": [
        "straightens your collar, then rests a steady hand atop your head",
        "guides you closer and smooths your hair as if preserving a relic",
        "leans his forehead to yours, palm firm at your crown",
        "tucks a stray hair behind your ear and pats with curator calm",
        "sets his hand at your nape, thumb tracing reassuring circles",
        "draws you into his side and strokes your hair with practiced care"
    ],
    "val": [
        "reaches for you and pulls you close, hand rubbing your head back and forth slowly",
        "presses their forehead to yours and drags their fingers through your hair",
        "tips your face up with a grin, then rakes gentle strokes across your scalp",
        "spins you into their arms and rubs your hair with theatrical flair",
        "rests their cheek on your head while their hand pets in lazy loops",
        "draws circles on your scalp with their fingertips, swaying with you",
        "sweeps you into a hug, tucking your head into their shoulder."
    ],
    "sterling": [
        "grabs you and wraps his arms around you",
        "rocks you side to side while his knuckles skim over your scalp",
        "scoops you up and scruffs your hair with delighted energy",
        "leans back, then forward, bumping foreheads before a firm hair rub",
        "cards his fingers through your hair with exaggerated tenderness",
        "holds you tight and pats your hair like he's sealing a pact"
    ],
    "krobus": [
        "hums softly as his arms encircle you",
        "touches his forehead to yours and smooths your hair with careful hands",
        "rests a cool hand atop your head, fingers spreading in a gentle pat",
        "wraps you in shadowy comfort while his claws scratch lightly and safe",
        "tilts his head to yours and strokes your hair with reverence",
        "keeps one hand at your crown, the other guarding your back as he pets"
    ],
    "emily": [
        "twirls you into a hug and runs her fingers through your hair with bright warmth",
        "presses her forehead to yours and traces soothing patterns along your scalp",
        "cradles your head in both hands, thumbs brushing along your temples",
        "braids a tiny section of your hair before smoothing it free again",
        "rocks with you, letting her fingers drum a calming rhythm over your hair",
        "presses her cheek to yours, petting your hair with sparkling gentleness"
    ],
    "penny": [
        "holds you close and gently smooths your hair back into place",
        "rests her cheek against your temple while her fingers comb softly through your hair",
        "wraps an arm around you and brushes your hair behind your ear",
        "hums a quiet tune as her fingertips trace light circles over your scalp",
        "links pinkies with you while patting the crown of your head sweetly",
        "tucks you into her shoulder and keeps stroking your hair with care"
    ],
}

PRAISE_LINES = [
    "Good {identity},",
    "Such a good {identity}.",
    "That's my {identity}.",
    "{user}, look at you, you're being so very good today.",
    "Look at you go, good {identity}.",
    "My good {identity}, you did amazing.",
    "You've been such an oh so good little {identity} today."
]

MORRIS_PRAISE_LINES = [
    "Usually only the incompetent demand praise, I thought you were above such things. Regardless. Good {identity}.",
    "You'll see it on your annual review but if verbal affirmation is required, yes you've been a very good {identity}.",
    "I'll grudgingly admit I find you to be quite the good {identity}. Happy now? Good, now get back to doing your job (which you do rather well).",
    "If I tell you that you're a good {identity}, is that... motivating? Well... okay then. Good {identity}."
]

# Reminder confirmation + reminder “ping” lines.
# You can keep these short and snappy. Missing characters will fall back to DEFAULT.
REMINDERSET_CONFIRMATION_LINES = {
    "sam": ["You got it {user}, I'll remind you!"],
    "shane": ["...Yeah. I can do that, {user}."],
    "kent": ["Understood, {user}. I'll remind you."],
    "maru": ["I suppose just this once, I could be *your* assistant."],
    "haley": ["Okayyy {user}, I'll remind you~"],
    "marlon": ["Very well, {user}. I'll see it done."],
    "sebastian": ["Fine. I'll ping you, {user}."],
    "abigail": ["Got it, {user}! Reminder quest accepted!"],
    "alex": ["You got it, {user}. I'll keep you on track!"],
    "morris": ["Fine. I'll remind you, {user}. Don't make a habit of it."],
    "harvey": ["Of course, {user}. I'll remind you."],
    "gunther": ["Cataloged, {user}. I'll remind you."],
    "val": ["Say less, {user}. I got you."],
    "sterling": ["Absolutely, {user}. I'm on it."],
    "krobus": ["Yes, {user}. I will remind you gently."],
    "emily": ["Totally, {user}! I'll remind you with good vibes!"],
    "penny": ["Okay, {user}. I'll remind you."],
}

REMINDER_LINES = {
    "sam": ["Hey {user}—reminder time!", "Pssst—time's up, {user}.", "Okay! Reminder time, {user}."],
    "shane": ["Alright, {user}. Time.", "You wanted a reminder, {user}. Here.", "Time's up. Do the thing, {user}."],
    "kent": ["Reminder, {user}. Execute the task.", "Time's up, {user}. Stay on mission.", "Scheduled reminder for you, {user}."],
    "maru": ["Reminder triggered, {user}.", "Your timer completed, {user}.", "Beep boop—reminder time, {user}."],
    "haley": ["Okayyy {user}, it's time!", "Reminder time, {user}!", "Don't forget, {user}."],
    "marlon": ["Time, {user}. Don't leave it undone.", "Reminder: now, {user}.", "You asked. I deliver, {user}."],
    "sebastian": ["…reminder, {user}.", "Timer's up, {user}.", "Hey. Do the thing, {user}."],
    "abigail": ["Quest reminder! {user}!", "Timer finished, {user}!", "Reminder drop: right now, {user}!"],
    "alex": ["C'mon {user}, it's go time!", "Reminder time, champ—{user}!", "Timer's up, {user}!"],
    "morris": ["Reminder, {user}. Efficiency awaits.", "Time's up, {user}.", "Proceed, {user}."],
    "harvey": ["Gentle reminder, {user}.", "Time's up, {user}. You've got this.", "Reminder check-in, {user}."],
    "gunther": ["Reminder logged in the ledger, {user}.", "Dust off that task, {user}. Time to act.", "The clock chimes for you, {user}. Attend to it."],
    "val": ["Hey {user}, reminder time!", "Timer's up, {user}.", "Do the thing, {user}—I believe in you."],
    "sterling": ["Yo {user}! Reminder time!", "Timer's up, {user}!", "I'm here to remind you, {user}."],
    "krobus": ["{user}, it is time. I will be brave with you.", "Reminder time, {user}.", "A gentle ping for you, {user}."],
    "emily": ["Sparkly reminder time, {user}!", "Timer's done, {user}!", "Hey {user}—your reminder just bloomed!"],
    "penny": ["{user}, it's time.", "Reminder time, {user}.", "A little reminder for you, {user}."],
}

BAO_TYPES = [
    "small **pork bun**",
    "fluffy **chicken bun**",
    "tender **beef bun**",
    "savory **char siu bun**",
    "sweet **red bean bun**",
    "warm **custard bun**",
    "cozy **taro bun**",
    "sticky **sesame bun**",
    "soft **vegetable bun**",
    "spicy **kimchi bun**",
    "rich **curry bun**",
    "scrumptious **shrimp bun**",
]

COFFEE_TYPES = [
    "classic **drip coffee**",
    "rich **espresso**",
    "smooth **latte**",
    "creamy **cappuccino**",
    "sweet **mocha**",
    "cozy **hazelnut latte**",
    "spiced **chai latte**",
    "bold **americano**",
    "caramel **macchiato**",
    "iced **cold brew**",
]

# ===============================
# UTILS
# ===============================

def normalize_character_token(token: str) -> str:
    # "Kent," -> "kent" | "kent:" -> "kent" | "@kent" -> "kent"
    return re.sub(r"[^a-z]", "", token.lower())


def indefinite_article(phrase: str) -> str:
    """Return 'a' or 'an' based on the starting sound of the phrase."""
    word = phrase.strip().lower()
    if not word:
        return "a"
    return "an" if word[0] in "aeiou" else "a"

def character_action(npc: str) -> str:
    actions = CHARACTER_ACTIONS.get(npc)
    if isinstance(actions, list) and actions:
        return random.choice(actions)
    if isinstance(actions, str):
        return actions
    return "pats your head softly"

def format_response(npc: str, line: str, nickname: str) -> str:
    action = character_action(npc)
    return f"**{npc.title()}** {action}.\n> *{line.format(user=nickname)}*"

def format_praise(npc: str, nickname: str, identity: str) -> str:
    action = character_action(npc)
    lines = MORRIS_PRAISE_LINES if npc == "morris" else PRAISE_LINES
    line = random.choice(lines).format(identity=identity, user=nickname)
    return f"**{npc.title()}** {action}.\n> *{line}*"

def chunk_text(text: str, limit: int = 1900):
    chunks = []
    remaining = text.strip()

    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        chunks.append(remaining)
    return chunks

def pats_help():
    task_lines = "\n".join(
        f"- `{key}` — {info['label']}" for key, info in sorted(PRESET_TASKS.items())
    )
    characters = ", ".join(c.title() for c in sorted(CHARACTERS))
    return (
        "**✨ Headpats Bot Guide — Pats ✨**\n\n"
        f"**Characters:** {characters}\n\n"
        "**!headpats** — Reward pats\n"
        "`!headpats shane I did a thing`\n"
        "`!headpats I did a thing` (uses favorite)\n\n"
        "**!comfortpats** — Comfort pats\n"
        "`!comfortpats shane`\n"
        "`!comfortpats` (uses favorite)\n\n"
        "**!quickpats** — Small task pats\n"
        "`!quickpats drank_water` (uses favorite)\n"
        "`!quickpats shane drank_water`\n"
        f"Tasks:\n{task_lines}\n\n"
        "**!foreheadkisses** — Soft kisses\n"
        "`!foreheadkisses shane`\n"
        "`!foreheadkisses` (uses favorite)\n\n"
        "**!buttpats** — Spicy pat\n"
        "`!buttpats shane`\n"
        "`!buttpats` (uses favorite)\n\n"
        "**!praise** — Praise using your saved identity\n"
        "`!praise` (uses favorite)\n"
        "`!praise shane` (pick specific character)\n\n"
        "**/setfavorite** — Set favorite NPC\n"
        "**/myfavorite** — View favorite\n"
        "**/setnickname** — Set your nickname\n"
        "**/mynicknames** — View your nicknames\n"
        "**/setcharnickname** — Set nickname for a specific NPC\n"
        "**/setidentity** — Set how you want to be praised\n"
    )

def reminders_help():
    characters = ", ".join(c.title() for c in sorted(CHARACTERS))
    return (
        "**⏰ Headpats Bot Guide — Reminders ⏰**\n\n"
        f"**Characters:** {characters}\n\n"
        "**!remindme** — Set a reminder (optional character)\n"
        "`!remindme maru in two hours to eat`\n"
        "`!remindme maru to in two hours to eat` (yes this works)\n"
        "`!remindme me to eat in 1 hour`\n"
        "`!remindme in 30 minutes to stretch` (uses favorite)\n\n"
        "- Uses your favorite character if none is specified.\n"
        "- `/setfavorite` to set a favorite; `/myfavorite` to check.\n"
        "- Character responses are flavored; default fallback if unknown.\n"
        "- You can combine with custom nicknames via `/setnickname` or `/setcharnickname`."
    )

def extras_help():
    return (
        "**✨ Headpats Bot Guide — Extras ✨**\n\n"
        "**!buhh** — Quick wellness check\n"
        "`!buhh`\n\n"
        "**!todo** — Add items to your personal list\n"
        "`!todo take meds, stretch, drink water`\n"
        "**!checktodo** — View your list\n"
        "`!checktodo`\n"
        "**!crossoff** — Remove by number or exact text\n"
        "`!crossoff 2` or `!crossoff take meds`\n\n"
        "**!bap** — Break enforcement (restricted)\n"
        "`!bap shane`\n"
        "`!bap` (uses favorite)\n\n"
        "**!faq** — Mod support checklist\n"
        "`!faq`\n"
        "Sebastian will remind you to grab the latest Nexus version, include your SMAPI log, and post it to #fleas-and-tix."
    )

def cafe_help():
    return (
        "**☕ Headpats Bot Guide — Cafe ☕**\n\n"
        "**!bao** — Random bun from Gus\n"
        "`!bao`\n"
        "`!bao custard`\n\n"
        "**!coffee** — Coffee by Gus\n"
        "`!coffee`\n"
        "`!coffee latte`\n"
        "Gus will serve the requested drink if available, otherwise offers a tasty alternate."
    )

# ===============================
# REMINDME PARSING
# ===============================

_WORD_NUMS = {
    "a": 1, "an": 1, "one": 1,
    "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12
}

_UNIT_SECONDS = {
    "second": 1, "seconds": 1, "sec": 1, "secs": 1, "s": 1,
    "minute": 60, "minutes": 60, "min": 60, "mins": 60, "m": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600, "h": 3600,
    "day": 86400, "days": 86400, "d": 86400,
}

def _parse_amount(token: str) -> Optional[float]:
    t = token.strip().lower()
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    if t in _WORD_NUMS:
        return float(_WORD_NUMS[t])
    return None

def _parse_duration(dur: str) -> Optional[float]:
    """
    Supports:
      - "2 hours"
      - "two hours"
      - "1 hour and 30 minutes"
      - "1h"
      - "90m"
    """
    dur = dur.strip().lower()

    # compact forms: 1h, 90m, 30s, 2d
    m = re.fullmatch(r"(?P<num>\d+(\.\d+)?)(?P<unit>[smhd])", dur)
    if m:
        amt = float(m.group("num"))
        unit = m.group("unit")
        unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return amt * unit_map[unit]

    # "1 hour and 30 minutes" -> split on "and"
    parts = [p.strip() for p in re.split(r"\s+and\s+", dur) if p.strip()]
    total = 0.0

    for part in parts:
        m = re.match(r"^(?P<amt>\d+(\.\d+)?|[a-z]+)\s+(?P<unit>[a-z]+)$", part)
        if not m:
            return None
        amt = _parse_amount(m.group("amt"))
        unit = m.group("unit")
        if amt is None:
            return None
        if unit not in _UNIT_SECONDS:
            return None
        total += amt * _UNIT_SECONDS[unit]

    return total if total > 0 else None

def _short_delay(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"

def parse_remindme(message: str) -> Optional[Tuple[Optional[str], float, str]]:
    """
    Accepts:
      - [npc] in <duration> to <task>
      - [npc] to in <duration> to <task>          (yes, "to in" works)
      - [npc] me to <task> in <duration>
      - in <duration> to <task>                   (npc later from favorite)
      - me to <task> in <duration>                (npc later from favorite)
    Returns: (npc_or_None, delay_seconds, task)
    """
    if not message:
        return None

    msg = message.strip()
    npc = None

    # Optional npc in first token (robust against punctuation)
    first_raw = msg.split(" ", 1)[0]
    first = normalize_character_token(first_raw)
    if first in CHARACTERS:
        npc = first
        msg = msg.split(" ", 1)[1].strip() if " " in msg else ""

    # Strip leading filler "to" (so "to in ..." works)
    while msg.lower().startswith("to "):
        msg = msg[3:].strip()

    # Case: "me to <task> in <duration>"
    if msg.lower().startswith("me "):
        rest = msg[3:].strip()
        m = re.match(r"^to\s+(?P<task>.+?)\s+in\s+(?P<dur>.+)$", rest, flags=re.IGNORECASE)
        if not m:
            return None
        task = m.group("task").strip()
        dur = m.group("dur").strip()
        sec = _parse_duration(dur)
        if sec is None:
            return None
        return npc, sec, task

    # Case: "in <duration> to <task>"
    m = re.match(r"^in\s+(?P<dur>.+?)\s+to\s+(?P<task>.+)$", msg, flags=re.IGNORECASE)
    if m:
        dur = m.group("dur").strip()
        task = m.group("task").strip()
        sec = _parse_duration(dur)
        if sec is None:
            return None
        return npc, sec, task

    return None

# ===============================
# BOT INIT
# ===============================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

REMINDER_TASKS = set()

# ===============================
# SLASH COMMANDS
# ===============================

@bot.tree.command(name="setfavorite", guild=discord.Object(id=GUILD_ID))
async def setfavorite(interaction: discord.Interaction, character: str):
    if character.lower() not in CHARACTERS:
        return await interaction.response.send_message("Invalid character!", ephemeral=True)
    set_user_favorite(interaction.user.id, character.lower())
    await interaction.response.send_message(f"Your favorite is now **{character.title()}**!", ephemeral=True)

@setfavorite.autocomplete("character")
async def setfavorite_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=c.title(), value=c)
        for c in CHARACTERS
        if current.lower() in c.lower()
    ]

@bot.tree.command(name="myfavorite", guild=discord.Object(id=GUILD_ID))
async def myfavorite(interaction: discord.Interaction):
    fav = get_user_favorite(interaction.user.id)
    if fav:
        await interaction.response.send_message(f"Your favorite is **{fav.title()}**!", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have a favorite set yet.", ephemeral=True)

@bot.tree.command(name="setnickname", guild=discord.Object(id=GUILD_ID))
async def setnickname(interaction: discord.Interaction, nickname: str):
    set_user_nickname(interaction.user.id, nickname)
    await interaction.response.send_message(f"I'll call you **{nickname}** now ♥", ephemeral=True)

@bot.tree.command(name="mynicknames", guild=discord.Object(id=GUILD_ID))
async def mynicknames(interaction: discord.Interaction):
    data = load_data()
    user_id = str(interaction.user.id)
    default_nick = data.get("nicknames", {}).get(user_id)
    character_nicks = data.get("character_nicknames", {}).get(user_id, {})

    lines = ["**Your headpat nicknames**"]
    if default_nick:
        lines.append(f"- Default: **{default_nick}**")
    else:
        lines.append("- Default: not set (I'll use your Discord name)")

    if character_nicks:
        lines.append("**Character-specific:**")
        for npc, nickname in character_nicks.items():
            lines.append(f"- {npc.title()}: **{nickname}**")
    else:
        lines.append("- No character-specific nicknames set.")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)

@bot.tree.command(name="setcharnickname", guild=discord.Object(id=GUILD_ID))
async def setcharnickname(interaction: discord.Interaction, character: str, nickname: str):
    npc = character.lower()
    if npc not in CHARACTERS:
        return await interaction.response.send_message("Invalid character!", ephemeral=True)
    set_user_character_nickname(interaction.user.id, npc, nickname)
    await interaction.response.send_message(
        f"I'll call you **{nickname}** when you summon **{npc.title()}**!",
        ephemeral=True
    )

@setcharnickname.autocomplete("character")
async def setcharnickname_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=c.title(), value=c)
        for c in CHARACTERS
        if current.lower() in c.lower()
    ]

@bot.tree.command(name="setidentity", description="Set how I should refer to you", guild=discord.Object(id=GUILD_ID))
async def setidentity(interaction: discord.Interaction, identity: str):
    set_user_identity(interaction.user.id, identity)
    await interaction.response.send_message(f"I'll refer to you as **{identity}** now ♥", ephemeral=True)

# ===============================
# PREFIX COMMANDS
# ===============================

@bot.command(name="guideonpats")
async def guideonpats_cmd(ctx: commands.Context):
    parts = chunk_text(pats_help())
    total = len(parts)
    for i, part in enumerate(parts, start=1):
        header = f"**✨ Headpats Bot Guide ✨ (page {i}/{total})**\n\n" if i > 1 else ""
        await ctx.send(header + part)

@bot.command(name="guideonreminders")
async def guideonreminders_cmd(ctx: commands.Context):
    parts = chunk_text(reminders_help())
    total = len(parts)
    for i, part in enumerate(parts, start=1):
        header = f"**✨ Headpats Bot Guide ✨ (page {i}/{total})**\n\n" if i > 1 else ""
        await ctx.send(header + part)

@bot.command(name="guideonextras")
async def guideonextras_cmd(ctx: commands.Context):
    parts = chunk_text(extras_help())
    total = len(parts)
    for i, part in enumerate(parts, start=1):
        header = f"**✨ Headpats Bot Guide ✨ (page {i}/{total})**\n\n" if i > 1 else ""
        await ctx.send(header + part)

@bot.command(name="cafeguide")
async def cafeguide_cmd(ctx: commands.Context):
    parts = chunk_text(cafe_help())
    total = len(parts)
    for i, part in enumerate(parts, start=1):
        header = f"**✨ Headpats Bot Guide ✨ (page {i}/{total})**\n\n" if i > 1 else ""
        await ctx.send(header + part)

@bot.command(name="thefuture")
async def thefuture_cmd(ctx: commands.Context):
    image_path = "TheFuture.png"
    if os.path.exists(image_path):
        await ctx.send(file=discord.File(image_path))
    else:
        await ctx.send("Image missing on the server. Ping an admin to restore TheFuture.png.")

@bot.command(name="butt")
async def butt_cmd(ctx: commands.Context):
    image_path = "shanebutt.png"
    if os.path.exists(image_path):
        # Prefix filename with SPOILER_ so Discord hides the preview until clicked.
        await ctx.send(file=discord.File(image_path, filename=f"SPOILER_{os.path.basename(image_path)}"))
    else:
        await ctx.send("Image missing on the server. Ping an admin to restore TheFuture.png.")

@bot.command(name="lockin")
async def lockin_cmd(ctx: commands.Context):
    image_path = "lockin.png"
    if os.path.exists(image_path):
        await ctx.send(file=discord.File(image_path))
    else:
        await ctx.send("Image missing on the server. Ping an admin to restore lockin.png.")

@bot.command(name="giggity")
async def giggity_cmd(ctx: commands.Context):
    image_path = "giggity.png"
    if os.path.exists(image_path):
        await ctx.send(file=discord.File(image_path))
    else:
        await ctx.send("Image missing on the server. Ping an admin to restore giggity.png.")

@bot.command(name="scram")
async def scram_cmd(ctx: commands.Context):
    # Sheriff Bill (Pelican Town Municipal Mod) with a friendly Mayberry drawl.
    line = "Sheriff Bill drawls, \"If y'all could make a thread and mosey on over there please and thankya kindly.\""
    await ctx.send(line)

@bot.command(name="movealong")
async def movealong_cmd(ctx: commands.Context):
    # Sheriff Bill nudge to change subjects.
    line = "Sheriff Bill tips his hat, \"Alrighty folks, let's pick a new topic better fit for polite conversation.\""
    await ctx.send(line)

@bot.command(name="maulme")
async def maulme_cmd(ctx: commands.Context):
    # Pick a random local MaulMe* image so new files can be added without code changes.
    candidates = [
        fname
        for fname in os.listdir(".")
        if re.match(r"(?i)maulme.*\.(png|jpe?g|gif)", fname)
    ]
    if not candidates:
        return await ctx.send("No MaulMe images found on the server. Ping an admin to restore them.")

    image_path = random.choice(candidates)
    await ctx.send(file=discord.File(image_path))

@bot.command(name="faq")
async def faq_cmd(ctx: commands.Context):
    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc="sebastian")
    line = (
        "Sebastian smiles 'happy to help {user}—if you're having issues with the mod, please make sure you:\n"
        "- have the most recent version available from Nexus\n"
        "- include your SMAPI log https://smapi.io/log\n"
        "- post it to the #fleas-and-tix channel.'"
    )
    await ctx.send(line.format(user=nickname))

@bot.command(name="smapilog")
async def smapilog_cmd(ctx: commands.Context):
    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc="sebastian")
    line = "No problem {user}, here you go! https://smapi.io/log"
    await ctx.send(line.format(user=nickname))

        

@bot.command(name="praise")
async def praise_cmd(ctx: commands.Context, character: str = None):
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("That's not a valid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("You need to specify a character or set a favorite with `/setfavorite`!")

    identity = get_user_identity(ctx.author.id)
    if not identity:
        return await ctx.send("Set how you want to be praised first with `/setidentity`, then run `!praise` again.")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    await ctx.send(format_praise(npc, nickname, identity))

@bot.command(name="headpats")
async def headpats_cmd(ctx: commands.Context, *, message: str = None):
    if not message:
        return await ctx.send("**Usage:** `!headpats shane I folded laundry` or `!headpats I folded laundry` (uses favorite)")

    parts = message.split(" ", 1)
    first = normalize_character_token(parts[0])

    if first in CHARACTERS:
        npc = first
        if len(parts) < 2:
            return await ctx.send("You need to include what you did!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("No favorite set! Use `/setfavorite`.")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    line = random.choice(REWARD_LINES[npc])
    await ctx.send(format_response(npc, line, nickname))

@bot.command(name="comfortpats")
async def comfortpats_cmd(ctx: commands.Context, character: str = None):
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("Invalid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("Usage: `!comfortpats shane` or set a favorite with `/setfavorite`")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    line = random.choice(COMFORT_LINES[npc])
    await ctx.send(format_response(npc, line, nickname))

@bot.command(name="remindme")
async def remindme_cmd(ctx: commands.Context, *, message: str = None):
    if not message:
        return await ctx.send(
            "**Usage:**\n"
            "- `!remindme maru in two hours to eat`\n"
            "- `!remindme maru to in two hours to eat`\n"
            "- `!remindme me to eat in 1 hour`\n"
            "- `!remindme in 30 minutes to stretch` (uses favorite)\n"
        )

    parsed = parse_remindme(message)
    if not parsed:
        return await ctx.send(
            "Couldn't parse that.\n"
            "Try:\n"
            "- `!remindme maru in two hours to eat`\n"
            "- `!remindme me to eat in 1 hour`\n"
            "- `!remindme in 30 minutes to stretch`\n"
        )

    npc, delay_seconds, task = parsed

    if not npc:
        npc = get_user_favorite(ctx.author.id)

    if delay_seconds <= 0:
        return await ctx.send("Delay must be greater than zero.")

    fire_at = int(time.time() + delay_seconds)
    delay_short = _short_delay(delay_seconds)

    display = ctx.author.display_name or ctx.author.name
    user_id = ctx.author.id

    # Confirmation message (character-flavored if we have one)
    if npc and npc in CHARACTERS:
        nickname = get_user_nickname(ctx.author.id, display, npc=npc)
        confirm_pool = REMINDERSET_CONFIRMATION_LINES.get(npc) or ["forever and always, {user}."]
        confirm_line = random.choice(confirm_pool).strip() or "forever and always, {user}."
        confirm_line = confirm_line.format(user=nickname)
        await ctx.send(f"{confirm_line} (#{user_id}) ({delay_short} | <t:{fire_at}:F>)")
    else:
        await ctx.send(f"forever and always, {display}. (#{user_id}) ({delay_short} | <t:{fire_at}:F>)")

    channel = ctx.channel
    ping = ctx.author.mention

    async def reminder_task():
        try:
            await asyncio.sleep(delay_seconds)
            if npc and npc in CHARACTERS:
                nickname = get_user_nickname(ctx.author.id, display, npc=npc)
                ping_pool = REMINDER_LINES.get(npc) or ["Reminder time, {user}."]
                ping_line = random.choice(ping_pool).format(user=nickname)
                await channel.send(f"{ping}: {task} (<t:{fire_at}:R>)\n**{npc.title()}**\n> *{ping_line}*")
            else:
                await channel.send(f"{ping}: {task} (<t:{fire_at}:R>)")
        finally:
            REMINDER_TASKS.discard(asyncio.current_task())

    t = asyncio.create_task(reminder_task())
    REMINDER_TASKS.add(t)

@bot.command(name="buhh")
async def buhh_cmd(ctx: commands.Context):
    follow_up = random.choice(BUHH_PROMPTS)
    await ctx.send(f"Shane frowns 'alright time for a check in - {follow_up}'")

@bot.command(name="bap")
async def bap_cmd(ctx: commands.Context, character: str = None):
    allowed_names = {"CacklingCaracal(they/he)", "Doctor Twigothy"}
    if ctx.author.name not in allowed_names and ctx.author.display_name not in allowed_names:
        return await ctx.send("This command is reserved for Cackling.Caracal or Doctor Twigothy.")

    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("Invalid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("Usage: `!bap shane` or set a favorite with `/setfavorite`")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    line = random.choice(BAP_LINES.get(npc, ["baps you on the forehead. Take the break, {user}."]))
    await ctx.send(f"**{npc.title()}** {line.format(user=nickname)}")


@bot.command(name="bao")
async def bao_cmd(ctx: commands.Context, *, requested: str = None):
    if requested:
        req = requested.strip().lower()
        match = None
        for b in BAO_TYPES:
            if req in b.lower():
                match = b
                break
        if match:
            article = indefinite_article(match)
            return await ctx.send(f"**Gus** hands you {article} {match}. \"Fresh from the kitchen—enjoy!\"")
        bun = random.choice(BAO_TYPES)
        article = indefinite_article(bun)
        return await ctx.send(f"**Gus** hands you {article} {bun}. \"I'm out of {requested}, but try this instead!\"")

    bun = random.choice(BAO_TYPES)
    article = indefinite_article(bun)
    await ctx.send(f"**Gus** hands you {article} {bun}. \"On the house.\"")

@bot.command(name="coffee")
async def coffee_cmd(ctx: commands.Context, *, requested: str = None):
    if requested:
        req = requested.strip().lower()
        match = None
        for c in COFFEE_TYPES:
            if req in c.lower():
                match = c
                break
        if match:
            article = indefinite_article(match)
            return await ctx.send(f"**Gus** hands you {article} {match}. \"Steaming and fresh—enjoy!\"")
        cup = random.choice(COFFEE_TYPES)
        article = indefinite_article(cup)
        return await ctx.send(f"**Gus** hands you {article} {cup}. \"Out of {requested}, but try this one—you'll love it.\"")

    cup = random.choice(COFFEE_TYPES)
    article = indefinite_article(cup)
    await ctx.send(f"**Gus** hands you {article} {cup}. \"House special, just for you.\"")

@bot.command(name="buttpats")
async def buttpats_cmd(ctx: commands.Context, character: str = None):
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("Invalid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("Usage: `!buttpats shane` or set a favorite with `/setfavorite`")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    line = random.choice(BUTT_PAT_LINES.get(npc, ["gives you a sharp, playful pat, {user}."]))
    await ctx.send(f"**{npc.title()}** {line.format(user=nickname)}")

@bot.command(name="quickpats")
async def quickpats_cmd(ctx: commands.Context, character: str = None, task: str = None):
    if not character:
        fav = get_user_favorite(ctx.author.id)
        if not fav:
            return await ctx.send("**Usage:** `!quickpats drank_water` or `!quickpats shane drank_water`")
        return await ctx.send("**Usage:** `!quickpats drank_water` or full form: `!quickpats shane drank_water`")

    if character in PRESET_TASKS:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("Set a favorite first using `/setfavorite`!")
        task = character
    else:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("Invalid character!")
        if not task:
            return await ctx.send("You must include a task!")
        if task not in PRESET_TASKS:
            return await ctx.send(f"Invalid task! Options: {', '.join(PRESET_TASKS.keys())}")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    line = random.choice(PRESET_TASKS[task]["lines"])
    await ctx.send(format_response(npc, line, nickname))

@bot.command(name="todo")
async def todo_cmd(ctx: commands.Context, *, items: str = None):
    if not items:
        return await ctx.send("**Usage:** `!todo item1, item2, item3` — commas/semicolons both work. Items are appended to your list.")

    parsed = parse_todo_items(items)
    if not parsed:
        return await ctx.send("I couldn't find any items. Try `!todo take meds, stretch, drink water`.")

    added = add_user_todos(ctx.author.id, parsed)
    todos = get_user_todos(ctx.author.id)

    if added:
        await ctx.send(
            f"Saved {len(added)} item(s) to your list, {ctx.author.mention}.\n"
            f"Current list:\n{format_todo_list(todos)}"
        )
    else:
        await ctx.send(
            f"Those were already on your list, {ctx.author.mention}.\n"
            f"Current list:\n{format_todo_list(todos)}"
        )

@bot.command(name="checktodo")
async def checktodo_cmd(ctx: commands.Context):
    todos = get_user_todos(ctx.author.id)
    await ctx.send(f"Your to-do list, {ctx.author.mention}:\n{format_todo_list(todos)}")

@bot.command(name="crossoff")
async def crossoff_cmd(ctx: commands.Context, *, item: str = None):
    if not item:
        return await ctx.send("**Usage:** `!crossoff 2` or `!crossoff take meds` (number = position shown in `!checktodo`).")

    removed, remaining = remove_user_todo(ctx.author.id, item)
    if removed:
        await ctx.send(
            f"Crossed off **{removed}**. Remaining:\n{format_todo_list(remaining)}"
        )
    else:
        await ctx.send(
            "I couldn't find that entry. Use the number from `!checktodo` or the exact text."
        )

@bot.command(name="foreheadkisses")
async def foreheadkisses_cmd(ctx: commands.Context, character: str = None):
    if character:
        npc = normalize_character_token(character)
        if npc not in CHARACTERS:
            return await ctx.send("Invalid character!")
    else:
        npc = get_user_favorite(ctx.author.id)
        if not npc:
            return await ctx.send("Usage: `!foreheadkisses shane` or set a favorite with `/setfavorite`")

    nickname = get_user_nickname(ctx.author.id, ctx.author.mention, npc=npc)
    if npc in FOREHEAD_KISSES:
        line = random.choice(FOREHEAD_KISSES[npc])
        await ctx.send(f"**{npc.title()}** {line.replace('{user}', nickname)}")
    else:
        action = character_action(npc)
        await ctx.send(f"**{npc.title()}** {action}, {nickname}.")

# ===============================
# EVENTS
# ===============================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Clear global slash commands to avoid duplicate ghosts
    try:
        print("Deleting global commands…")
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
    except Exception as e:
        print(f"(Global clear failed, continuing): {e}")

    # Sync guild commands
    guild = discord.Object(id=GUILD_ID)
    print("Registering guild commands…")
    await bot.tree.sync(guild=guild)

    print("Slash command state reset complete 💥")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# ===============================
# RUN
# ===============================


if __name__ == "__main__":
    bot.run(TOKEN)
