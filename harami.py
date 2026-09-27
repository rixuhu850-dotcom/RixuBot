import asyncio
import json
import os
import sys
import time
import random
import logging
import traceback
import string
import tempfile
import subprocess
import shutil
try:
    import aiohttp
except ImportError:
    aiohttp = None
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List, Any, Optional
from dataclasses import dataclass, field

from telegram import Update, ChatPermissions, ReplyParameters, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import Application, PrefixHandler, MessageHandler, CommandHandler, ContextTypes, filters, CallbackQueryHandler, ChatMemberHandler
from telegram.error import RetryAfter, BadRequest, Forbidden, TimedOut, NetworkError
from telegram.constants import ChatType, ChatMemberStatus

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)

OWNER_ID = int(os.getenv("OWNER_ID", "7958866511"))
LOG_CHANNEL = os.getenv("LOG_CHANNEL", "")
XAI_API_KEY_DEFAULT = "xai-MvNewOiVgMVbgLbfCpVkTTgtlI0XttpfYHmf2DvPz3gxfURbY0cJD03UMKhY5TYEPzrKZuP8Y2jF9bCl"

BASE_TOKENS = [t.strip() for t in os.getenv("BOT_TOKENS", "").split(",") if t.strip()]
EXTRA_TOKENS = [
    "8751725466:AAEK6GLalcO1FqGO770XG5J5GIGEpXRTULM",
"8866184271:AAHCpdns3OrjUtr59YzH1EUaJG2fLsIztjA",
"8693245400:AAFuGsUbmj6HjvQyTBUxR_UrQ0w9NY--c4U",
"8817928376:AAFvIQHgGfvig36Zr4SMsNoN2fBwPADnJ78",
"8867857813:AAH7FfsTax63lprBYfMifNX3Ckk3JNaKM6Y",
"8855016391:AAGz2KblBuQ_NUYTTKstDOSzqA4T3Xd-0C0",
"8921711279:AAGguDusXjzRi0598TQkv7aJnIi4UK6hcY8",
"8792977030:AAF4jq97125RFzMDbKztkgSQCQeAOJt0gms",
"8950169828:AAGeVLjuLtdMpGhWO1Se1LuQ08y2UfJ0E18",
"8842522983:AAFaM1oejfw1AJvHoM1R8W6AiA8PrS5FraI",
"8924827399:AAEJ1R6DM8A2hqh-dsnc4QNYdvylTNnXcqI",
]
TOKENS = list(set(BASE_TOKENS + EXTRA_TOKENS))
if not TOKENS:
    print("ERROR: No bot tokens found!")
    sys.exit(1)

SUDO_FILE = "sudo.json"
TEMPLATES_FILE = "templates.json"
WARNS_FILE = "warns.json"
RULES_FILE = "rules.json"
NOTES_FILE = "notes.json"
WELCOME_FILE = "welcome.json"
SETTINGS_FILE = "settings.json"
AFK_FILE = "afk.json"
GROUPS_FILE = "groups.json"
TOKENS_FILE = "tokens.json"
MEDIA_FILE = "media.json"
PFP_FILE = "pfp.json"
SAVED_PHOTO_PATH = "db_target_gcpfp.jpg"
FILTERS_FILE = "filters.json"
TRUSTED_FILE = "trusted.json"
LOGS_FILE = "logs.json"
STATS_FILE = "stats.json"
AUTORESPOND_FILE = "autorespond.json"
SCHEDULE_FILE = "schedule.json"
QUEST_DATA_FILE = "quest_data.json"
ERROR_LOG_FILE = "error_log.json"
MENU_FILE = "menu_data.json"
MENU_MEDIA_FILE = "menu_media.json"

def load_json(filepath, default=None):
    if default is None:
        default = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
    return default

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")

SUDO_USERS = set(load_json(SUDO_FILE, [OWNER_ID]))
custom_templates = load_json(TEMPLATES_FILE, {})
warns_db = load_json(WARNS_FILE, {})
rules_db = load_json(RULES_FILE, {})
notes_db = load_json(NOTES_FILE, {})
welcome_db = load_json(WELCOME_FILE, {})
settings_db = load_json(SETTINGS_FILE, {})
afk_db = load_json(AFK_FILE, {})
known_chats = set(load_json(GROUPS_FILE, []))
_menu_media = load_json(MEDIA_FILE, {})
_pfp_pools = load_json(PFP_FILE, {})
extra_tokens = load_json(TOKENS_FILE, [])
filters_db = load_json(FILTERS_FILE, {})
trusted_users = load_json(TRUSTED_FILE, {})
logs_db = load_json(LOGS_FILE, {})
stats_db = load_json(STATS_FILE, {})
autorespond_db = load_json(AUTORESPOND_FILE, {})
schedule_db = load_json(SCHEDULE_FILE, {})
quest_data = load_json(QUEST_DATA_FILE, {})
error_logs = load_json(ERROR_LOG_FILE, [])

def save_templates(): save_json(TEMPLATES_FILE, custom_templates)
def save_warns(): save_json(WARNS_FILE, warns_db)
def save_rules(): save_json(RULES_FILE, rules_db)
def save_notes(): save_json(NOTES_FILE, notes_db)
def save_welcome(): save_json(WELCOME_FILE, welcome_db)
def save_settings(): save_json(SETTINGS_FILE, settings_db)
def save_afk(): save_json(AFK_FILE, afk_db)
def save_groups(): save_json(GROUPS_FILE, list(known_chats))
def save_media(): save_json(MEDIA_FILE, _menu_media)
def save_pfp(): save_json(PFP_FILE, _pfp_pools)
def save_filters(): save_json(FILTERS_FILE, filters_db)
def save_trusted(): save_json(TRUSTED_FILE, trusted_users)
def save_logs(): save_json(LOGS_FILE, logs_db)
def save_stats(): save_json(STATS_FILE, stats_db)
def save_autorespond(): save_json(AUTORESPOND_FILE, autorespond_db)
def save_schedule(): save_json(SCHEDULE_FILE, schedule_db)
def save_quest_data(): save_json(QUEST_DATA_FILE, quest_data)
def save_error_logs(): save_json(ERROR_LOG_FILE, error_logs)

MENU = """
𓆩𓆪  ʀɪxᴜ · ᴋɪ ʟɪɴɢ  ᴇɴɢɪɴᴇ  𓆩𓆪
─────────────── ✦ ───────────────
     🐉  ᴅʀᴀɢᴏɴ  ʙᴀʟʟ  ꜱᴜᴘᴇʀ
     ⚡  ᴘᴀʀᴀʟʟᴇʟ  ɴᴄ  ·  ᴠ5
─────────────── ✦ ───────────────

 01  🔥  ɴᴄ
 02  💬  ꜱᴘᴀᴍ
 03  🌀  ꜱʟɪᴅᴇʀ
 04  ⚔️  ʀᴇᴘʟʏ  ʀᴀɪᴅ
 05  🎯  ᴛᴀʀɢᴇᴛ
 06  🤖  ᴀᴜᴛᴏ
 07  🔒  ꜱᴜᴅᴏ
 08  🎭  ᴛʜᴇᴍᴇ
 09  🏛️  ɢᴄ  ᴄʀᴇᴀᴛᴇ
 10  🖼️  ᴘꜰᴘ
 11  📋  ɢᴄ  ᴍᴀɴᴀɢᴇ
 12  🎨  ᴛᴇᴍᴘʟᴀᴛᴇꜱ
 13  🤖  ʙᴏᴛ  ᴄᴏɴᴛʀᴏʟ
 14  🌐  ᴍɢᴄ
 15  🌐  ᴡᴀʀ / ᴍᴜᴛᴇ
 16  🗑️  ᴘᴜʀɢᴇ
 17  🛠️  ᴛᴏᴏʟꜱ
 18  🎮  ɢᴀᴍᴇꜱ
 19  🎵  ꜱᴏɴɢ
 20  🩺  ꜱʏꜱᴛᴇᴍ
 21  💀  ɢᴀᴍᴇ  ᴏᴠᴇʀ

─────────────── ✦ ───────────────
 ᴘʀᴇꜰɪx  ·  -
 ᴍᴇɴᴜ    ·  -menu <1-21>
─────────────── ✦ ───────────────
"""

MENU_SECTIONS = [
"""
𓆩 🔥 ɴᴄ 𓆪
─────────────── ✦ ───────────────

ᴄᴏʀᴇ
 · -chudnc     ꜰᴀꜱᴛ ʟᴏɴɢ ᴇɴɢɪɴᴇ
 · -nc         ᴄᴏᴏʟ ᴍɪx ꜱᴛʏʟᴇꜱ
 · -multinc    ᴀʟʟ ꜱᴛʏʟᴇꜱ ᴄʏᴄʟᴇ
 · -stop       ᴋɪʟʟ ᴀʟʟ ᴛᴀꜱᴋꜱ
 · -setdelay   ꜱᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ

ꜱᴀɪʏᴀɴ
 · -gokugod  -vegetagod  -brolygod
 · -gohangod -trunksgod  -dbgod
 · -triogod  -hakai      -godki

ꜱᴛʏʟᴇ
 · -boldnc  -italicnc  -cursivenc
 · -wavenc  -silknc    -ultranc
 · -ncdark  -ncmoon    -ncflag
 · -emognc  -flowernc  -typenc

ꜱᴘᴇᴄɪᴀʟ
 · -tmkcnc  -evonc     -marvelnc
 · -magicnc -sportnc   -flashnc
 · -foxync  -saitama   -aizennc
 · -phantom -shadow    -chud

─────────────── ✦ ───────────────
""",
"""
𓆩 💬 ꜱᴘᴀᴍ 𓆪
─────────────── ✦ ───────────────
 · -spam  -stopspam
 · -slidespam  -stopslide
 · -reply  -stopreply
 · -customspam  -burstspam
 · -rapidfire  -chudspam
 · -tagspam  -copyspam
 · -replyflood  -swipespam
─────────────── ✦ ───────────────
""",
"""
𓆩 🌀 ꜱʟɪᴅᴇʀ 𓆪
─────────────── ✦ ───────────────
 · -alexa  -stopalexa
 · -animal  -stopanimal
 · -swipe  -stopswipeslider
   (reply to a message)
─────────────── ✦ ───────────────
""",
"""
𓆩 ⚔️ ʀᴇᴘʟʏ ʀᴀɪᴅ 𓆪
─────────────── ✦ ───────────────
 · -replyraid  -stopreplyraid
 · -massreply  -mentionraid
 · -rrbomb  -rrloop  -rrspam
 · -multirr
 ᴀʟɪᴀꜱ  ·  -rr -mr -rb -rl
─────────────── ✦ ───────────────
""",
"""
𓆩 🎯 ᴛᴀʀɢᴇᴛ 𓆪
─────────────── ✦ ───────────────
 · -targetreply  -stoptargetreply
 · -targetslide  -stoptargetslide
 · -ncdel  -stopncdel
─────────────── ✦ ───────────────
""",
"""
𓆩 🤖 ᴀᴜᴛᴏ 𓆪
─────────────── ✦ ───────────────
 · -autoreact  -stopautoreact
 · -autoreply  -stopautoreply
 · -autostatus
─────────────── ✦ ───────────────
""",
"""
𓆩 🔒 ꜱᴜᴅᴏ 𓆪
─────────────── ✦ ───────────────
 · -addsudo  -removesudo
 · -sudolist
 · -givebheek  -bheekhatao
 · -bheeklist
─────────────── ✦ ───────────────
""",
"""
𓆩 🎭 ᴛʜᴇᴍᴇ 𓆪
─────────────── ✦ ───────────────
 · -settheme  goku / vegeta / broly
 · -settheme  gohan / trunks / reset
─────────────── ✦ ───────────────
""",
"""
𓆩 🏛️ ɢᴄ ᴄʀᴇᴀᴛᴇ 𓆪
─────────────── ✦ ───────────────
 · -creategc  -link
 · -gofighters
 · -join <link>
 · -leave
─────────────── ✦ ───────────────
""",
"""
𓆩 🖼️ ᴘꜰᴘ 𓆪
─────────────── ✦ ───────────────
 · -photosave  -setgc  -stopgc
 · -addpfp  -pfploop
 · -setpfponce  -pfppool
 · -clearpfp  -deletegcpfp
─────────────── ✦ ───────────────
""",
"""
𓆩 📋 ɢᴄ ᴍᴀɴᴀɢᴇ 𓆪
─────────────── ✦ ───────────────
 · -gcinfo  -gclist
 · -setgctitle  -setgcdesc
 · -getinvite  -pinmsg
 · -kickuser  -bantarget
 · -muteuser  -unmuteuser
─────────────── ✦ ───────────────
""",
"""
𓆩 🎨 ᴛᴇᴍᴘʟᴀᴛᴇꜱ 𓆪
─────────────── ✦ ───────────────
 · -addtemplate  -templates
 · -preview  -deltemplate
 · -customnc  -cnc
─────────────── ✦ ───────────────
""",
"""
𓆩 🤖 ʙᴏᴛ ᴄᴏɴᴛʀᴏʟ 𓆪
─────────────── ✦ ───────────────
 · -bots  -botinfo
 · -botname  -botbio
 · -promotebot  -promoteall
 · -admincheck  -floodstat
 · -alive  -ncstatus
─────────────── ✦ ───────────────
""",
"""
𓆩 🌐 ᴍɢᴄ 𓆪
─────────────── ✦ ───────────────
 · -mgcnc  -mgchakai  -mgcbold
 · -mgcfire  -mgcwar  -stopmgcnc
 · -mgcstatus
─────────────── ✦ ───────────────
""",
"""
𓆩 🌐 ᴡᴀʀ / ᴍᴜᴛᴇ 𓆪
─────────────── ✦ ───────────────
 · -ncdel
 · -multiwar <text>
 · -stopmwar
 · -mute  -unmute
 · -lock  -unlock
─────────────── ✦ ───────────────
""",
"""
𓆩 🗑️ ᴘᴜʀɢᴇ 𓆪
─────────────── ✦ ───────────────
 · -purge  -purgeme
 · -purgebot  -purgeall
─────────────── ✦ ───────────────
""",
"""
𓆩 🛠️ ᴛᴏᴏʟꜱ 𓆪
─────────────── ✦ ───────────────
 · -status  -uptime  -ping
 · -setdelay  -chatdelay
 · -whitelist  -health
 · -stop
─────────────── ✦ ───────────────
""",
"""
𓆩 🎮 ɢᴀᴍᴇꜱ 𓆪
─────────────── ✦ ───────────────
 · -dice  -rps  -slot
 · -guess  -trivia
─────────────── ✦ ───────────────
""",
"""
𓆩 🎵 ꜱᴏɴɢ 𓆪
─────────────── ✦ ───────────────
 · -song <name>   ʏᴏᴜᴛᴜʙᴇ ꜱᴇᴀʀᴄʜ ʟɪɴᴋ
─────────────── ✦ ───────────────
""",
"""
𓆩 🩺 ꜱʏꜱᴛᴇᴍ 𓆪
─────────────── ✦ ───────────────
 · -errorlog  -health  -debug
 · -backup  -restart
 · -leave  -broadcast
 · -gclist
─────────────── ✦ ───────────────
""",
"""
𓆩 💀 ɢᴀᴍᴇ ᴏᴠᴇʀ 𓆪
─────────────── ✦ ───────────────
 · -gameover   (reply user)
 · -setmenupic / -setmenuvideo
 · -rmmenupic
 · -menu  -help
─────────────── ✦ ───────────────
""",
]
menu_db = {"menu": MENU, "sections": MENU_SECTIONS}
try:
    save_json(MENU_FILE, menu_db)
except Exception:
    pass
menu_media = load_json(MENU_MEDIA_FILE, {})

all_apps = []
all_bot_instances = []
flood_tracker = {}
active_tasks = {}
_nc_send_gap = 0.05  # MERGED: FREAKY speed + Sasuke smart + Arthur pool
BOT_START_TIME = time.monotonic()
auto_react_chats = {}
auto_reply_chats = {}
created_groups = {}
mute_chats = set()
ncdel_chats = set()
targetreply_chats = {}
targetslide_chats = {}
replyflood_chats = {}
pfploop_active = {}
pfp_tasks = {}
gc_join_times = {}
chat_threads = {}
_multiwar_active = {}
_mgcnc_stop = None
_mgcnc_task = None
_mgcnc_targets = []
_nc_force_stop: Dict[int, float] = {}
conversation_enabled = {}
conversation_context = {}
conversation_cooldown = {}
bot_mood = {"mood": "happy", "personality": "sassy", "last_user": None, "context": []}

# Extra features state
WHITELIST_FILE = "nc_whitelist.json"
CHAT_DELAY_FILE = "chat_delays.json"
nc_whitelist = set(load_json(WHITELIST_FILE, []))  # empty = all chats allowed
chat_delays = load_json(CHAT_DELAY_FILE, {})  # str(chat_id) -> float
anti_raid_chats = set()
SAFE_USERS = set(load_json("safe_users.json", []))

def save_whitelist():
    save_json(WHITELIST_FILE, list(nc_whitelist))

def save_chat_delays():
    save_json(CHAT_DELAY_FILE, chat_delays)

def save_safe_users():
    save_json("safe_users.json", list(SAFE_USERS))

ABUSING_TEMPLATES = {
    "goku": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ɢᴏᴋᴜ ɴᴇ ᴋʜᴀ ʟɪʏᴀ 🍜",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ɢᴏᴋᴜ ɴᴇ ᴜᴄʜʜᴀʟ ʟɪʏᴀ 🏀",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ɢᴏᴋᴜ ᴋᴀ ɴᴏᴋʀ ʜᴀɪ 🧹",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ɢᴏᴋᴜ ɴᴇ ᴘᴀɪᴅᴀ ᴋɪ 👶",
        "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ɢᴏᴋᴜ ɴᴇ ꜱᴜᴘᴇʀ ꜱᴀɪʏᴀɴ ᴍᴇɪɴ ᴄʜᴏᴅᴀ ⚡",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴋᴀᴍᴇʜᴀᴍᴇʜᴀ ꜱᴇ ʙʜɪ ɴʜɪ ʙᴀᴄʜᴀ 💥",
    ],
    "vegeta": [
        "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ᴠᴇɢᴇᴛᴀ ɴᴇ ᴄʜᴏᴅᴀ 💦",
        "{target} ᴛᴜ ᴛᴏ ɢᴜʟᴀᴍ ʜᴀɪ ᴠᴇɢᴇᴛᴀ ᴋᴀ 👞",
        "{target} ᴋɪ ʙʜᴇɴ ᴋᴏ ᴠᴇɢᴇᴛᴀ ɴᴇ ᴘʀɪɴᴄᴇ ꜱᴛʏʟᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 👑",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴠᴇɢᴇᴛᴀ ᴋᴀ ɴᴏᴋʀ ʜᴀɪ 🧹",
        "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ᴠᴇɢᴇᴛᴀ ɴᴇ ᴜʟᴛʀᴀ ᴇɢᴏ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 🟣",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴠᴇɢᴇᴛᴀ'ꜱ ᴘʀɪᴅᴇ ꜱᴇ ʙʜɪ ɴʜɪ ʙᴀᴄʜᴀ 👑",
    ],
    "broly": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ʙʀᴏʟʏ ɴᴇ ʙʀᴇᴀᴋ ᴋʀ ᴅɪʏᴀ 💔",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ʙʀᴏʟʏ ɴᴇ ꜱᴍᴀꜱʜ ᴋʀ ᴅɪʏᴀ 💥",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ʙʀᴏʟʏ ꜱᴇ ᴅʀ ɢʏᴀ 😱",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ʙʀᴏʟʏ ɴᴇ ᴋʜᴀᴛᴍ ᴋʀ ᴅɪ 💀",
        "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ʙʀᴏʟʏ ɴᴇ ʟᴇɢᴇɴᴅᴀʀʏ ᴍᴏᴅᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 💚",
    ],
    "gohan": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ɢᴏʜᴀɴ ɴᴇ ʙᴇᴀꜱᴛ ᴍᴏᴅᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 🧡",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ɢᴏʜᴀɴ ɴᴇ ᴘᴏᴛᴇɴᴛɪᴀʟ ᴅɪᴋʜᴀʏᴀ 💪",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ɢᴏʜᴀɴ ᴋᴀ ᴘɪᴄᴄʜᴜ ʜᴀɪ 🐒",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ɢᴏʜᴀɴ ɴᴇ ᴘᴀʟᴇɴᴛᴇ ʙᴀɴᴀʏɪ 🌿",
    ],
    "trunks": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ᴛʀᴜɴᴋꜱ ɴᴇ ꜰᴜᴛᴜʀᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ ⚔️",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ᴛʀᴜɴᴋꜱ ɴᴇ ᴛɪᴍᴇ ᴛʀᴀᴠᴇʟ ᴋʀᴋᴇ ᴄʜᴏᴅᴀ 🕐",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴛʀᴜɴᴋꜱ ᴋᴀ ꜱᴡᴏʀᴅ ʜᴀɪ 🗡️",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ᴛʀᴜɴᴋꜱ ɴᴇ ꜰᴜᴛᴜʀᴇ ᴍᴇɪɴ ᴋʜᴀᴛᴍ ᴋʀ ᴅɪ 💀",
    ],
    "hakai": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ʜᴀᴋᴀɪ ᴋʀ ᴅᴜɴɢᴀ 💥",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ʜᴀᴋᴀɪ ᴋʀᴋᴇ ᴇʀᴀꜱᴇ ᴋʀ ᴅᴜɴɢᴀ 🌌",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴛᴏ ʜᴀᴋᴀɪ ꜱᴇ ʙʜɪ ɴʜɪ ʙᴀᴄʜᴀ 💀",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ʙᴇᴇʀᴜꜱ ɴᴇ ᴋʜᴀ ʟɪ 🐱",
    ],
    "frieza": [
        "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ꜰʀɪᴇᴢᴀ ɴᴇ ɢᴏʟᴅᴇɴ ᴍᴏᴅᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 💛",
        "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ᴄᴏᴏʟᴇʀ ɴᴇ ᴛʜᴀɴᴅᴀ ᴋʀ ᴅɪʏᴀ ❄️",
        "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ᴋɪɴɢ ᴄᴏʟᴅ ᴋᴀ ɴᴏᴋʀ ʜᴀɪ 👑",
        "{target} ᴋɪ ᴀᴜʟᴀᴅ ᴛᴏ ꜰʀɪᴇᴢᴀ ɴᴇ ᴘᴀɪᴅᴀ ᴋɪ 🪐",
    ],
}

ABUSING_SPAM = [
    "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋɪ ᴄʜᴜᴛ ᴍᴇɪɴ ᴅʀᴀɢᴏɴ ʙᴀʟʟ 🐉💥",
    "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ᴄʜᴏᴅᴇ ᴅʀᴀɢᴏɴ 🐉🔥",
    "{target} ᴛᴜ ᴛᴏ ʙʜɪᴋʜᴀʀɪ ʜᴀɪ, ᴅʀᴀɢᴏɴ ʙᴀʟʟ ɴʜɪ ᴍɪʟᴇɢɪ 💀",
    "{target} ᴋɪ ᴍᴀᴀ ᴋɪ ɴᴀɴɢɪ ᴋᴇ ꜱᴀᴛʜ ᴅʀᴀɢᴏɴ ʙᴀʟʟ 🥚",
    "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ɢᴏᴋᴜ ɴᴇ ᴋʜᴀ ʟɪʏᴀ 🍜",
    "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ᴠᴇɢᴇᴛᴀ ɴᴇ ᴘʀɪɴᴄᴇ ꜱᴛʏʟᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 👑",
    "{target} ᴋɪ ᴍᴀᴀ ᴋᴏ ʙʀᴏʟʏ ɴᴇ ʙʀᴇᴀᴋ ᴋʀ ᴅɪʏᴀ 💔",
    "{target} ᴛᴇʀᴀ ʙᴀᴀᴘ ʜᴀᴋᴀɪ ꜱᴇ ʙʜɪ ɴʜɪ ʙᴀᴄʜᴀ 💀",
    "{target} ᴛᴇʀɪ ᴍᴀᴀ ᴋᴏ ꜰʀɪᴇᴢᴀ ɴᴇ ɢᴏʟᴅᴇɴ ᴍᴏᴅᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 💛",
    "{target} ᴛᴇʀɪ ʙʜᴇɴ ᴋᴏ ɢᴏʜᴀɴ ɴᴇ ʙᴇᴀꜱᴛ ᴍᴏᴅᴇ ᴍᴇɪɴ ᴄʜᴏᴅᴀ 🧡",
]

WRAP_L = ["꧁", "⭅╡", "♛", "𖤍", "❦", "⚡", "☄️", "💀", "🌟", "🔱", "🌊", "✨", "💎", "👑", "🔥"]
WRAP_R = ["꧂", "╞⭆", "♛", "𖤍", "❦", "🌙", "💎", "👑", "☄️", "🔱", "🌊", "⚡", "💀", "🔥", "✨"]
SUFFIX_EMOJIS = ["🌸","🌺","🌻","🌹","🪷","🌷","💮","🏵️","✨","💫","⭐","🌟","💥","🔥","⚡","❄️","🌊","🫧","💧","🌀","🌈","🌙","☄️","🌟","💎","🔮","🧿","🪬","👑","💀","🦋","🐉","🍀","🌿","🍃"]
RANDOM_EMOJIS = ["🎀","🌸","🔥","⚡","💀","👑","🌊","💎","🐉","🌙","☄️","🌺","💫","✨","🦋","🪷","🔱","🌟","🩸","⚔️","🫧","🌈","🌀","💥","🌑","🔮","🧿","🪬","🌿","🍀"]

DARK_EMOJIS = ["🕳️", "🌑", "👣", "🗝️", "🧬", "🔌", "⬛", "🦾", "📜", "🕯️", "🍷", "🥀", "🖤", "🕸️", "🗡️", "🎱", "🐦‍⬛", "🔮", "🌑", "🪄", "🌝", "🌚", "🌜", "🌛", "🌙", "⭐", "🌟", "✨", "🪐", "🌍", "🌠", "🌌", "☄️", "🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
HAND_EMOJIS = ["👀", "👁️", "👄", "🫦", "👅", "👃🏻", "👂🏻", "🦻🏻", "🦶🏻", "🦵🏻", "🦿", "🦾", "💪🏻", "👏🏻", "👍🏻", "👎🏻", "🫶🏻", "🙌🏻", "👐🏻", "🤲🏻", "🤜🏻", "🤛🏻", "✊🏻", "👊🏻", "🫳🏻", "🫴🏻", "🫱🏻", "🫲🏻", "🫸🏻", "🫷🏻", "👋🏻", "🤚🏻", "🖐🏻", "✋🏻", "🖖🏻", "🤟🏻", "🤘🏻", "✌🏻", "🤞🏻", "🫰🏻", "🤙🏻", "🤌🏻", "🤏🏻", "👌🏻", "🫵🏻", "👉🏻", "👈🏻", "☝🏻", "👆🏻", "👇🏻", "🖕🏻", "✍🏻", "🤳🏻", "🙏🏻", "💅🏻", "🤝🏼", "🌘"]
MARVEL_EMOJIS = ["🛡️", "🇺🇸", "🎖️", "🦾", "🚀", "⚡", "🤖", "⚡", "🔨", "🌩️", "🔱", "🕷️", "🕶️", "🔫", "🥀", "🏹", "🎯", "🦅", "🧪", "☢️", "👊", "🟢", "💎", "🤖", "🟡"]
MAGIC_EMOJIS = ["🧪", "⚗️", "📜", "💎", "🕳️", "🌑", "🧿", "🐦‍⬛", "🌀", "⚡", "🪄", "🧿", "🕯️", "📜", "🏛️", "🖤", "✥", "♱", "⚖︎", "∞", "𖦹"]
NATURE_EMOJIS = ["💐", "🌹", "🥀", "🌺", "🌷", "🪷", "🌸", "💮", "🏵️", "🪻", "🌻", "🌼", "🍂", "🍁", "🍄", "🌾", "🌿", "🌱", "🍃", "☘️", "🍀", "🪴", "🌵", "🌴", "🪾", "🌳", "🌲", "🪵", "🪹", "🪺"]
FOOD_EMOJIS = ["🍧", "🧋", "🧃", "🥛", "🍿", "🧊", "🍵", "☕", "🍻", "🍺", "🧉", "🫖", "🍾", "🍷", "🥃", "🫗", "🍸", "🍹", "🍶", "🥢", "🥂", "🧈", "🧁", "🍭", "🍬", "🍫", "🍨", "🍡", "🍙", "🍥", "🥠", "🥟", "🍛", "🍤", "🍜", "🦪", "🍚", "🥣", "🥫", "🌯"]
FACE_EMOJIS = ["☺️", "😌", "🙂‍↕️", "🙂‍↔️", "😏", "🤤", "😋", "😛", "😝", "😜", "🤪", "😔", "🥺", "😬", "😑", "😐", "😶", "😶‍🌫️", "🫥", "🤐", "🫡", "🤔", "🤫", "🫢", "🤭", "🥱", "🤗", "🫣", "😱", "🤨", "🧐", "😒", "🙄", "😮‍💨", "😤", "😠", "😡", "🤬", "😞", "😓", "😟", "😥", "😢", "☹️", "🙁", "🫤", "😕", "😰", "😨", "😧", "😦", "😮", "😯", "😲", "🤯", "🫨", "😵‍💫", "😵", "😫", "🥴", "🥶", "🥵"]
HOBBY_EMOJIS = ["🃏", "🪄", "🎩", "📷", "🀄", "🎴", "🎰", "📸", "🖼️", "🎨", "🫟", "🖌️", "🖍️", "🪡", "🧵", "🧶", "🎹", "🎷", "🎺", "🎸", "🪕", "🎻", "🪉", "🪘", "🥁", "🪇", "🪈", "🪗", "🎤", "🎧", "🎚️", "🎛️", "🎙️", "📼", "📻", "📺", "📹", "📽️", "🎥", "🎞️", "🎬", "🎭", "🎫", "🎟️"]
TECH_EMOJIS = ["🔋", "🪫", "🖲️", "💽", "💾", "💿", "📀", "🖥️", "💻", "⌨️", "🖨️", "🖱️", "🪙", "💎", "💸", "💵", "💴", "💶", "💷", "💳", "💰", "🧾", "🧮", "⚖️", "🛒", "🛍️", "💡", "🕯️", "🔦", "🏮", "🧱", "🪟", "🪞", "🚪", "🚿", "🛁", "🚽", "🧻", "🪠", "🧸", "🪆", "🧷", "🪢", "🧹", "🧴", "🧽", "🧼", "🪥", "🪒", "🪮", "🧺", "🧦", "🧤", "🧣", "👖"]
ANIMAL_EMOJIS = ["🪼", "🐚", "🦋", "🐞", "🐝", "🐛", "🪱", "🦠", "🐾", "🫧", "🪸", "🦪", "🪼", "🐙", "🦑", "🐡", "🐠", "🐟", "🐳", "🐋", "🐬", "🦈", "🦭", "🐧", "🦃", "🐦‍🔥", "🦚", "🦩", "🪿", "🦆", "🦢", "🦤", "🕊️", "🦜", "🦉", "🦅", "🐥", "🐤", "🐣", "🐓", "🐦", "🪶", "🪽", "🦇", "🦦", "🦔", "🦡", "🦨", "🐅", "🐆", "🦒", "🦏", "🦣", "🐘", "🦓", "🦘", "🦥", "🦬", "🐃", "🐏", "🐂", "🐄", "🐎", "🐈", "🐩"]
TYPENC_WORDS = ["𝗧𝗔𝗧𝗧𝗘", "𝗚𝗨𝗟𝗔𝗠", "𝗠𝗔𝗗𝗔𝗥𝗖𝗛𝗢𝗗", "𝗕𝗛𝗘𝗡𝗞𝗟𝗡𝗗", "𝗧𝗠𝗞𝗖", "𝗧𝗠𝗞𝗕", "𝗥𝗡𝗗𝗬", "𝗚𝗔𝗥𝗘𝗘𝗕", "𝗠𝗜𝗦𝗧𝗜 𝗞𝗘 𝗟𝗔𝗗𝗞𝗘", "𝗚𝗡𝗗𝗨", "𝗖𝗛𝗔𝗣𝗥𝗜", "𝗖𝗛𝗠𝗥", "𝗕𝗦𝗗𝗞", "𝗞𝗘𝗘𝗗𝗘", "𝗖𝗛𝗨𝗗", "𝗧𝗕𝗞𝗟", "𝗛𝗔𝗥𝗔𝗠𝗞𝗛𝗢𝗥", "𝗥𝗥 𝗠𝗧 𝗞𝗥", "𝗧𝗘𝗥𝗜 𝗠𝗔𝗔 𝗠𝗔𝗥 𝗚𝗬𝗜", "𝗧𝗘𝗥𝗜 𝗕𝗛𝗘𝗡 𝗖𝗛𝗨𝗗𝗚𝗬𝗜", "𝗚𝗨𝗟𝗔𝗠𝗜 𝗞𝗥"]

_CHUD_WORDS = ["LUND", "TBKC", "TBR", "TMR", "aarey चुदोड़े", "BHEN CUDALE"]

def rnd_suffix():
    return f" 𓂃{random.choice(SUFFIX_EMOJIS)}་༘"
def rnd_emoji():
    return random.choice(RANDOM_EMOJIS)
def last():
    return [None]

# ── Cool texture / design (screenshot-style unicode) ──
_BOLD = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
)
_SMALL = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
)
_GREEKISH = {
    "a": "α", "e": "ε", "i": "ι", "o": "ο", "u": "υ", "y": "γ",
    "A": "Α", "E": "Ε", "I": "Ι", "O": "Ο", "U": "Υ", "Y": "Υ",
    "d": "δ", "D": "Δ", "k": "κ", "K": "Κ", "n": "η", "N": "Ν",
    "r": "ʀ", "R": "Ɍ", "s": "s", "S": "Σ", "t": "ᴛ", "T": "Ͳ",
}

def to_bold(s: str) -> str:
    return str(s).translate(_BOLD)

def to_small(s: str) -> str:
    return str(s).translate(_SMALL)

def to_greekish(s: str) -> str:
    return "".join(_GREEKISH.get(c, c) for c in str(s))

def wave_emojis(n: int = 18) -> str:
    pool = ["😂", "😭", "💀", "🔥", "✨", "🌀", "💫", "☠️", "🖤", "🦋", "🐉", "⚡"]
    return "".join(random.choice(pool) for _ in range(n))

def flourish_line() -> str:
    bits = ["╰‿╯", "✧", "✦", "★", "☆", "꧁", "꧂", "༺", "༻", "⌬", "◈", "⋆", "˚", "୨୧"]
    return " ".join(random.choice(bits) for _ in range(6))

def _emoji_wall(pair=None, rows=5, cols=8) -> str:
    """Dense emoji grid like LEPINO: 🐕💕🐕💕…"""
    if pair is None:
        pair = random.choice([
            ("🐕", "💕"), ("🔥", "💀"), ("💗", "🐶"), ("🖤", "☠️"),
            ("⚡", "💥"), ("🌸", "🦋"), ("🐉", "🔥"), ("💕", "🌹"),
            ("🐺", "💗"), ("👑", "💎"), ("😂", "💀"), ("😭", "🔥"),
        ])
    a, b = pair
    lines = []
    for r in range(rows):
        lines.append("".join(a if (r + c) % 2 == 0 else b for c in range(cols)))
    return "\n".join(lines)

def _long_fill(core: str, target_len: int = 240) -> str:
    """Pad title to chudnc-like length (Telegram max 255)."""
    fillers = [
        "𒐫", "💥", "𒐫", "✦", "✧", "🔥", "💀", "⚡", "🖤", "💕", "🐉",
        "𒐫💥", "・", "𓂃", "༺", "༻", "꧁", "꧂", "★", "☆", "☠️", "💗",
    ]
    words = list(_CHUD_WORDS) + ["TMKC", "TBKC", "CHUD", "NC", "WAR"]
    out = core
    i = 0
    while len(out) < target_len:
        out += random.choice(fillers)
        if i % 7 == 0:
            out += f" {random.choice(words)} "
        i += 1
        if i > 400:
            break
    # unique salt at end
    out += f" {random.randint(10,99)}{random.choice(['✦','🔥','💀'])}"
    return out[:255]


def cool_nc_title(text: str, mode: str = "mix") -> str:
    """Distinct long styles — not all look like chudnc."""
    t = (text or "NC")[:36]
    tags = ["TMKC", "TBKC", "TMR", "CHUD", "NC", "WAR", "BSDK"]
    tag = random.choice(tags)
    salt = random.randint(10, 99)
    pair = random.choice([
        ("🐕", "💕"), ("🔥", "💀"), ("💗", "🐶"), ("🖤", "☠️"),
        ("⚡", "💥"), ("🌸", "🦋"), ("🐉", "🔥"), ("💕", "🌹"),
    ])
    word = random.choice(_CHUD_WORDS)
    # Style-specific fillers (different identity)
    flower = "".join(random.choice(["🌸", "🌺", "💕", "✨", "🦋"]) for _ in range(24))
    fire = "".join(random.choice(["🔥", "💥", "⚡", "💀"]) for _ in range(28))
    dark = "".join(random.choice(["🖤", "☠️", "🌑", "✦", "🗡️"]) for _ in range(28))
    star = "".join(random.choice(["★", "☆", "✦", "✧", "⭐"]) for _ in range(30))
    wave = wave_emojis(22)

    styles = {
        "chud": lambda: _long_fill(f"{t}𒐫𒐫𒐫💥𒐫💥𒐫𒐫💥💥{word}𒐫💥𒐫 "),
        "wall": lambda: f"{to_bold(t)}\n{_emoji_wall(pair, 5, 8)}\n💕{tag}{salt}\n{flower}"[:255],
        "lepino": lambda: f"{to_bold(t)} कुतिया\n{_emoji_wall(('🐕', '💕'), 5, 8)}\n💕{tag}{salt}\n{wave}"[:255],
        "greek": lambda: f"🔥{to_greekish(t)}🔥\n{to_bold(t)}\n{wave}\n{tag}{salt}"[:255],
        "frame": lambda: f"꧁༺ {to_bold(t)} ༻꧂\n{star}\n{to_small(t)} · {tag}{salt}"[:255],
        "fire": lambda: f"🇫🇮 {to_bold(t.upper())}\n{fire}\n💀{word} · {tag}{salt}"[:255],
        "dark": lambda: f"🌑 {to_bold(t)} 🌑\n{dark}\n☠️{tag}{salt}"[:255],
        "soft": lambda: f"『{to_small(t)}』\n{flower}\n✨{tag}{salt}"[:255],
    }
    if mode in styles:
        try:
            return styles[mode]()[:255]
        except Exception:
            pass
    # mix = pick distinct style at random (equal weight, chud only 1 slot)
    keys = list(styles.keys())
    try:
        return styles[random.choice(keys)]()[:255]
    except Exception:
        return f"{to_bold(t)}\n{_emoji_wall(pair, 4, 8)}\n💕{tag}{salt}"[:255]

def cool_spam_line(target: str) -> str:
    """Spam/slide lines — same emoji-wall texture."""
    t = target or "TARGET"
    pair = random.choice([("🐕", "💕"), ("🔥", "💀"), ("💗", "🐶"), ("🖤", "☠️"), ("⚡", "💥")])
    pack = [
        f"{to_bold(t)}\n{_emoji_wall(pair, 4, 8)}\n💕TMKC",
        f"{to_greekish(t)}\n{_emoji_wall(pair, 3, 8)}\n💀TBKC",
        f"🔥 {to_bold(t)} 🔥\n{_emoji_wall(pair, 4, 7)}\n⚡NC",
        f"{to_small(t)}\n{_emoji_wall(('🐕', '💕'), 4, 8)}\n💕TMR",
    ]
    return random.choice(pack)

FRIENDS = [
    "PICCOLO", "KRILLIN", "TIEN", "YAMCHA", "GOTEN",
    "BEERUS", "WHIS", "FRIEZA", "CELL", "BUU",
    "HIT", "JIREN", "TOPPO", "KALE", "CAULIFLA",
    "ZENO", "ZAMASU", "BARDOCK", "GINYU", "NAPPA",
    "RADITZ", "DABURA", "BABIDI", "MAGIN", "SALZA",
    "COOLER", "KING_COLD", "MECHA_FRIEZA"
]

def bots():
    return [b for b in all_bot_instances if b is not None]

def get_args(ctx):
    return ctx.args if ctx.args else []

def txt_arg(ctx):
    return " ".join(get_args(ctx)).strip()

def split_text(text, limit=4096):
    chunks = []
    current = ""
    for line in text.split("\n"):
        segment = line + "\n"
        if len(current) + len(segment) > limit:
            if current:
                chunks.append(current.rstrip("\n"))
            current = segment
        else:
            current += segment
    if current.strip():
        chunks.append(current.rstrip("\n"))
    return chunks or [text[:limit]]

async def reply_msg(msg, text):
    if msg:
        for chunk in split_text(text):
            try:
                await msg.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await msg.reply_text(chunk)

def is_owner_or_sudo(uid):
    return uid == OWNER_ID or uid in SUDO_USERS

def guard(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_owner_or_sudo(user.id):
            if update.message:
                try:
                    await update.message.reply_text("❌ 𝗖ʜᴀʟ 𝗕ᴇ 𝗥ᴀɴᴅ 𝗦ᴜᴅᴏ 𝗟ᴇᴋᴇ 𝗔ᴀᴀ 🫶🏻💋⚡")
                except Exception:
                    pass
            return
        return await func(update, context)
    return wrapper

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id != OWNER_ID:
            if update.message:
                await update.message.reply_text("Owner only command!")
            return
        return await func(update, context)
    return wrapper

# ========== FLOOD TRACKER (Sasuke-style) ==========
class FloodTracker:
    FLOOD_CAP  = 3.0
    RATE_WIN   = 60.0
    SOFT_LIMIT = 14

    def __init__(self):
        self._until: Dict[int, float] = {}
        self._ts: Dict[int, List[float]] = {}

    def flooded(self, bid: int) -> bool:
        exp = self._until.get(bid, 0.0)
        if time.monotonic() < exp:
            return True
        self._until.pop(bid, None)
        return False

    def remaining(self, bid: int) -> float:
        return max(0.0, self._until.get(bid, 0.0) - time.monotonic())

    def mark(self, bid: int, sec: float):
        self._until[bid] = time.monotonic() + min(sec, self.FLOOD_CAP)

    def clear(self, bid: int):
        self._until.pop(bid, None)

    def record(self, bid: int):
        now = time.monotonic()
        buf = self._ts.setdefault(bid, [])
        buf.append(now)
        self._ts[bid] = [t for t in buf if t > now - self.RATE_WIN]

    def rate(self, bid: int) -> int:
        now = time.monotonic()
        return sum(1 for t in self._ts.get(bid, []) if t > now - self.RATE_WIN)

    def near_limit(self, bid: int) -> bool:
        return self.rate(bid) >= self.SOFT_LIMIT

_ft = FloodTracker()

# ========== TASK CONTROLLER (Sasuke-style, clean stop) ==========
class TaskController:
    def __init__(self):
        self.tasks:  Dict[str, asyncio.Task]  = {}
        self.events: Dict[str, asyncio.Event] = {}

    def _k(self, cid: int, t: str) -> str:
        return f"{cid}::{t}"

    async def start(self, cid: int, t: str, factory) -> None:
        await self.stop(cid, t)
        k = self._k(cid, t)
        ev = asyncio.Event()
        self.events[k] = ev

        async def _wrap():
            try:
                await factory(ev)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task {k} err: {e}")
            finally:
                self.tasks.pop(k, None)
                self.events.pop(k, None)

        self.tasks[k] = asyncio.create_task(_wrap())

    async def stop(self, cid: int, t: str) -> bool:
        k    = self._k(cid, t)
        ev   = self.events.pop(k, None)
        task = self.tasks.pop(k, None)
        if ev:
            ev.set()
        if task and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=0.5)
            except Exception:
                pass
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=4.0)
                except Exception:
                    pass
        return bool(ev or task)

    async def stop_all(self, cid: int) -> int:
        prefix = f"{cid}::"
        types  = {k[len(prefix):] for k in list(self.tasks) + list(self.events) if k.startswith(prefix)}
        results = await asyncio.gather(
            *[self.stop(cid, t) for t in types],
            return_exceptions=True
        )
        return sum(1 for r in results if r is True)

    def running(self, cid: int, t: str) -> bool:
        k = self._k(cid, t)
        return k in self.tasks and not self.tasks[k].done()

tc = TaskController()

# ========== WAIT HELPER ==========
async def _wait_ev(stop_event: asyncio.Event, secs: float) -> bool:
    if secs <= 0:
        return stop_event.is_set()
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=secs)
        return True
    except asyncio.TimeoutError:
        return False

# ========== ENHANCED FLOOD BYPASS SYSTEM ==========
@dataclass
class BotFloodState:
    flooded_until: float = 0.0
    backoff_until: float = 0.0
    consecutive_errors: int = 0
    success_count: int = 0
    total_requests: int = 0
    last_request_time: float = 0.0
    min_interval: float = 0.05
    current_interval: float = 0.08
    jitter: bool = True


class FloodBypassManager:
    """Per-bot flood tracking + dynamic interval."""

    def __init__(self):
        self.bot_states: Dict[int, BotFloodState] = {}
        self.global_penalty_until: float = 0.0
        self.base_interval: float = 0.05
        self.max_interval: float = 3.0

    def get_state(self, bot_id: int) -> BotFloodState:
        if bot_id not in self.bot_states:
            self.bot_states[bot_id] = BotFloodState(
                min_interval=self.base_interval,
                current_interval=max(self.base_interval, float(_nc_send_gap or 0.08)),
            )
        return self.bot_states[bot_id]

    def can_send(self, bot_id: int) -> bool:
        state = self.get_state(bot_id)
        now = time.monotonic()
        if now < self.global_penalty_until:
            return False
        if now < state.flooded_until or now < state.backoff_until:
            return False
        if state.last_request_time > 0 and (now - state.last_request_time) < state.current_interval:
            return False
        return True

    def on_success(self, bot_id: int):
        state = self.get_state(bot_id)
        now = time.monotonic()
        state.total_requests += 1
        state.success_count += 1
        state.consecutive_errors = 0
        state.last_request_time = now
        # slowly tighten interval after stable successes
        if state.success_count > 8 and state.current_interval > self.base_interval:
            state.current_interval = max(
                self.base_interval,
                state.current_interval - 0.002,
            )

    def on_error(self, bot_id: int, error: Exception):
        state = self.get_state(bot_id)
        now = time.monotonic()
        state.consecutive_errors += 1
        state.total_requests += 1
        state.success_count = 0

        if isinstance(error, RetryAfter):
            wait = float(getattr(error, "retry_after", 1)) + random.uniform(0.15, 0.45)
            state.flooded_until = now + wait
            state.current_interval = min(self.max_interval, wait * 0.4 + self.base_interval)
        elif isinstance(error, BadRequest):
            if "chat title" in str(error).lower() or "not modified" in str(error).lower():
                state.current_interval = max(state.current_interval, 0.12)
            else:
                state.flooded_until = now + 8.0
                state.current_interval = min(self.max_interval, state.current_interval * 1.3)
        elif isinstance(error, Forbidden):
            state.flooded_until = now + 45.0
            state.current_interval = min(self.max_interval, state.current_interval * 1.5)
        elif isinstance(error, (TimedOut, NetworkError)):
            backoff = min(4.0, (1.5 ** min(state.consecutive_errors, 5)) * 0.15 + random.uniform(0, 0.15))
            state.backoff_until = now + backoff
            state.current_interval = min(self.max_interval, state.current_interval * 1.15)
        else:
            state.flooded_until = now + 2.0
            state.current_interval = min(self.max_interval, state.current_interval * 1.1)

    def get_interval(self, bot_id: int) -> float:
        state = self.get_state(bot_id)
        base = max(self.base_interval, state.current_interval)
        if state.jitter:
            return max(self.base_interval, base + random.uniform(-0.008, 0.012))
        return base

    def clear(self, bot_id: int):
        self.bot_states.pop(bot_id, None)


flood_manager = FloodBypassManager()


# ========== MERGED ENGINE ==========
# FREAKY speed (0.05) + Sasuke silk/trio logic + Arthur primary/reserve
async def _chud_engine(chat_id, bots, stop_event, name_factory):
    """
    MERGE of 3 scripts:
      FREAKY  → default gap 0.05, aggressive
      Sasuke  → dual-track silk + trio group switch on flood
      Arthur  → primary (~80%) + reserve (~20%) pools, unique titles, never exit
    """
    N = len(bots)
    if N == 0:
        return

    # --- Arthur pool split (10 → 8 primary + 2 reserve) ---
    if N == 1:
        primary, reserve = list(bots), []
    elif N == 2:
        primary, reserve = [bots[0]], [bots[1]]
    else:
        n_reserve = max(1, N // 5)
        primary = list(bots[: N - n_reserve])
        reserve = list(bots[N - n_reserve :])

    chat_gap = chat_delays.get(str(chat_id))
    base_gap = float(chat_gap) if chat_gap is not None else (
        float(_nc_send_gap) if _nc_send_gap is not None else 0.05
    )
    base_gap = max(0.03, min(base_gap, 2.0))  # FREAKY-range allowed
    flood_manager.base_interval = base_gap
    started_at = time.monotonic()
    seq = [0]
    last_title = [""]
    skip_until: Dict[int, float] = {}
    mode = ["PRIMARY"]

    def _should_stop() -> bool:
        if stop_event.is_set():
            return True
        return _nc_force_stop.get(chat_id, 0.0) >= started_at

    def _bid(b, i=0):
        return getattr(b, "id", None) or (10000 + i)

    def _free(b, i=0) -> bool:
        bid = _bid(b, i)
        now = time.monotonic()
        if now < skip_until.get(bid, 0.0):
            return False
        st = flood_manager.get_state(bid)
        return now >= max(st.flooded_until, st.backoff_until)

    def _any_free(pool) -> bool:
        return any(_free(b, i) for i, b in enumerate(pool))

    def _unique_title() -> str:
        for _ in range(5):
            t = (name_factory() or "NC")[:240]
            t = f"{t}·{seq[0] % 9973}{random.choice(['✦', '⚡', '🔥', '💀', '💥'])}"[:255]
            seq[0] += 1
            if t != last_title[0]:
                last_title[0] = t
                return t
        t = f"NC·{seq[0]}·{random.randint(1000, 9999)}"[:255]
        seq[0] += 1
        last_title[0] = t
        return t

    # Sasuke-style: split active pool into 2 silk tracks (even/odd)
    def _tracks(pool):
        a = list(range(0, len(pool), 2))
        b = list(range(1, len(pool), 2))
        return a or list(range(len(pool))), b

    print(
        f"[NC] MERGED — primary={len(primary)} reserve={len(reserve)} "
        f"| gap={base_gap:.3f}s | silk dual-track"
    )

    consecutive_fail = [0]

    async def _silk_track(pool, indices, offset: float, tag: str):
        """Sasuke silk track: rotate free bots, FREAKY gap."""
        if not indices:
            return
        if offset > 0:
            if await _wait_ev(stop_event, offset):
                return
        ptr = [0]
        T = len(indices)
        while not _should_stop():
            # Prefer primary; if this pool is reserve, only run when primary dry
            if pool is reserve and primary and _any_free(primary):
                if await _wait_ev(stop_event, 0.15):
                    return
                continue
            if pool is primary and not _any_free(primary):
                # primary all flooded — yield so reserve tracks work
                if await _wait_ev(stop_event, 0.08):
                    return
                continue

            now = time.monotonic()
            found_i = None
            for k in range(T):
                ti = (ptr[0] + k) % T
                bi = indices[ti]
                if bi >= len(pool):
                    continue
                if _free(pool[bi], bi):
                    ptr[0] = (ti + 1) % T
                    found_i = bi
                    break

            if found_i is None:
                consecutive_fail[0] += 1
                if consecutive_fail[0] > 60:
                    for i, b in enumerate(bots):
                        bid = _bid(b, i)
                        try:
                            flood_manager.clear(bid)
                        except Exception:
                            pass
                        skip_until.pop(bid, None)
                    consecutive_fail[0] = 0
                    print("[NC] soft-reset flood states")
                if await _wait_ev(stop_event, 0.12):
                    return
                continue

            bot = pool[found_i]
            bot_id = _bid(bot, found_i)
            title = _unique_title()
            try:
                await bot.set_chat_title(chat_id, title)
                flood_manager.on_success(bot_id)
                consecutive_fail[0] = 0
                if mode[0] != tag:
                    mode[0] = tag
                    print(f"[NC] → active: {tag}")
                gap = max(base_gap, 0.03)
                if await _wait_ev(stop_event, gap):
                    return
            except RetryAfter as e:
                wait = float(getattr(e, "retry_after", 1)) + random.uniform(0.1, 0.35)
                skip_until[bot_id] = time.monotonic() + wait
                flood_manager.on_error(bot_id, e)
                consecutive_fail[0] += 1
                if await _wait_ev(stop_event, 0.03):
                    return
            except Forbidden:
                skip_until[bot_id] = time.monotonic() + 90.0
                consecutive_fail[0] += 1
                if await _wait_ev(stop_event, 0.03):
                    return
            except BadRequest:
                flood_manager.on_error(bot_id, BadRequest("title"))
                last_title[0] = ""
                consecutive_fail[0] += 1
                if await _wait_ev(stop_event, 0.05):
                    return
            except (TimedOut, NetworkError):
                consecutive_fail[0] += 1
                if await _wait_ev(stop_event, 0.1):
                    return
            except asyncio.CancelledError:
                return
            except Exception:
                consecutive_fail[0] += 1
                if await _wait_ev(stop_event, 0.06):
                    return

    # Build tracks: primary dual + reserve dual (Sasuke silk × Arthur pool)
    tasks = []
    pa, pb = _tracks(primary)
    tasks.append(asyncio.create_task(_silk_track(primary, pa, 0.0, "PRIMARY-A")))
    if pb:
        tasks.append(asyncio.create_task(_silk_track(primary, pb, base_gap / 2, "PRIMARY-B")))
    if reserve:
        ra, rb = _tracks(reserve)
        tasks.append(asyncio.create_task(_silk_track(reserve, ra, base_gap * 0.25, "RESERVE-A")))
        if rb:
            tasks.append(asyncio.create_task(_silk_track(reserve, rb, base_gap * 0.75, "RESERVE-B")))

    try:
        while not _should_stop():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=0.4)
                break
            except asyncio.TimeoutError:
                continue
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        try:
            await asyncio.shield(asyncio.gather(*tasks, return_exceptions=True))
        except Exception:
            pass
        print("[NC] MERGED engine stopped")

# ========== NC FACTORIES ==========
def _chud_nc_factory(txt: str) -> callable:
    """Only CHUD identity — 𒐫💥 long blocks."""
    words = list(_CHUD_WORDS)
    idx = [0]
    last = [None]

    def _f():
        word = words[idx[0] % len(words)]
        idx[0] += 1
        c = cool_nc_title(f"{txt} {word}", "chud")[:255]
        if c == last[0]:
            c = _long_fill(f"{txt}𒐫💥{word}💥𒐫 ")[:255]
        last[0] = c
        return c

    return _f

def _pure_nc_factory(txt: str) -> callable:
    last = [None]

    def _f():
        c = cool_nc_title(txt, "mix")[:255]
        if c == last[0]:
            c = cool_nc_title(txt, "wall")[:255]
        last[0] = c
        return c

    return _f

def _style_pad(style: str, target: str, tick: int) -> str:
    """Per-style long filler so short factories still look distinct."""
    s = (style or "mix").lower()
    t = (target or "NC")[:20]
    n = tick % 97
    if s in ("ncdark", "dark", "shadow", "phantom"):
        block = "".join(random.choice(["🌑", "🖤", "☠️", "✦", "🗡️", "🕳"]) for _ in range(36))
        return f"{block}·{n}"
    if s in ("tmkcnc", "emognc", "evonc"):
        block = "".join(random.choice(HAND_EMOJIS + FACE_EMOJIS) for _ in range(28))
        return f"❥{block}·{n}"
    if s in ("marvelnc", "sportnc", "flashnc"):
        block = "".join(random.choice(MARVEL_EMOJIS + TECH_EMOJIS) for _ in range(28))
        return f"⚡{block}·{n}"
    if s in ("magicnc", "aizennc", "aizen"):
        block = "".join(random.choice(MAGIC_EMOJIS) for _ in range(30))
        return f"✧{block}·{n}"
    if s in ("lndnc", "flowernc", "foxync"):
        block = "".join(random.choice(NATURE_EMOJIS + ANIMAL_EMOJIS) for _ in range(28))
        return f"🌿{block}·{n}"
    if s in ("ncspeed", "food"):
        block = "".join(random.choice(FOOD_EMOJIS) for _ in range(28))
        return f"≫{block}·{n}"
    if s in ("chud", "chudnc", "hakai"):
        return _long_fill(f"{t}𒐫💥")[:180]
    if s in ("boldnc", "bold"):
        return f"{to_bold(t)} " + ("█" * 40) + f"·{n}"
    if s in ("italicnc", "italic", "cursivenc"):
        return f"{to_small(t)} " + "".join(random.choice(["✦", "✧", "·"]) for _ in range(40)) + f"·{n}"
    if s in ("wavenc", "wave"):
        return wave_emojis(40) + f"·{n}"
    if s in ("ultranc", "silknc"):
        return "".join(random.choice(["★", "☆", "✦", "✧"]) for _ in range(42)) + f"·{n}"
    if s in ("wall", "lepino", "nc"):
        pair = random.choice([("🐕", "💕"), ("🔥", "💀"), ("💗", "🐶")])
        return _emoji_wall(pair, 5, 8) + f"·{n}"
    # default distinct pad
    pair = random.choice([("🔥", "💀"), ("⚡", "💥"), ("🌑", "✦")])
    return _emoji_wall(pair, 4, 8) + f"·{n}"


# ========== START NC (uses CHUD engine) ==========
async def start_nc_abusing(msg, chat_id, target, style, custom_factory=None):
    bot_list = bots()
    if not bot_list:
        await reply_msg(msg, "⚡ No bots available!")
        return

    # Whitelist gate
    if nc_whitelist and chat_id not in nc_whitelist:
        await reply_msg(msg, "🛡 NC blocked — chat whitelist mein nahi.\n`-whitelist add`")
        return

    if tc.running(chat_id, "nc"):
        await reply_msg(msg, "⚠️ NC already running. `-stop` pehle, phir start.")
        return

    _nc_force_stop.pop(chat_id, None)

    # Style identity preserved — each NC looks different
    tick = [0]
    style_key = (style or "mix").lower()

    if custom_factory:
        def factory():
            tick[0] += 1
            raw = str(custom_factory(target) or target)
            # Keep style identity; only pad if too short for Telegram uniqueness
            if len(raw.strip()) < 80:
                # style-specific long pad (NOT global chud wash)
                pad = _style_pad(style_key, target, tick[0])
                out = f"{raw} {pad}"[:255]
            else:
                out = f"{raw}·{tick[0] % 997}"[:255]
            return out
    else:
        # Theme abuse templates stay theme-based + long unique
        def factory():
            tick[0] += 1
            abuse_list = ABUSING_TEMPLATES.get(style_key, ABUSING_TEMPLATES.get("goku", ["{target}"]))
            line = random.choice(abuse_list).format(target=target)
            mode = {
                "goku": "fire", "vegeta": "frame", "broly": "dark",
                "gohan": "soft", "trunks": "greek", "hakai": "dark",
                "frieza": "fire", "aizen": "dark", "cool": "mix",
            }.get(style_key, "mix")
            return cool_nc_title(f"{line}", mode)[:255]

    async def _run(stop_ev):
        await _chud_engine(chat_id, bot_list, stop_ev, factory)

    await tc.start(chat_id, "nc", _run)
    gap = _nc_send_gap if _nc_send_gap is not None else 0.05
    n = len(bot_list)
    n_res = 0 if n < 3 else max(1, n // 5)
    n_pri = n - n_res if n >= 2 else n
    await reply_msg(msg,
        f"╔══════════════════════════════╗\n"
        f"  ⚡ NC MERGED ENGINE\n"
        f"  📛 {target}\n"
        f"  🎨 Style: {style.upper()}\n"
        f"  🟢 Primary: {n_pri} | 🔵 Reserve: {n_res}\n"
        f"  🚀 Gap: {gap:.3f}s (FREAKY+Sasuke)\n"
        f"  Silk dual-track · nonstop\n"
        f"  -stop to stop\n"
        f"╚══════════════════════════════╝"
    )

# ========== NEW COMMAND: -chudnc ==========
@guard
async def cmd_chudnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -chudnc <text>")
        return
    bot_list = bots()
    if not bot_list:
        await reply_msg(msg, "⚡ No bots!")
        return
    if tc.running(msg.chat_id, "nc"):
        await reply_msg(msg, "⚠️ NC already running. Use -stop first.")
        return

    async def _run(stop_ev):
        await _chud_engine(msg.chat_id, bot_list, stop_ev, _chud_nc_factory(txt))

    await tc.start(msg.chat_id, "nc", _run)
    await reply_msg(msg,
        f"╔══════════════════════════════╗\n"
        f"  💥⚡ 𝑪𝑯𝑼𝑫 𝑵𝑪 𝑺𝑻𝑨𝑹𝑻𝑬𝑫 ⚡💥\n"
        f"  📛 {txt}\n"
        f"  🤖 𝘉𝘰𝘵𝘴: {len(bot_list)}\n"
        f"  ⚙️  𝘎𝘢𝘱: {_nc_send_gap or 0.10:.3f}𝘴\n"
        f"  🔥 𝘡𝘦𝘳𝘰 𝘑𝘪𝘵𝘵𝘦𝘳 · 𝘡𝘦𝘳𝘰 𝘍𝘭𝘰𝘰𝘥 · 𝘍𝘢𝘴𝘵𝘦𝘴𝘵\n"
        f"  -stop 𝘵𝘰 𝘴𝘵𝘰𝘱\n"
        f"╚══════════════════════════════╝"
    )

# ========== STOP COMMAND ==========
@guard
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    # Double force-stop so staggered workers exit immediately
    _nc_force_stop[cid] = time.monotonic()
    count = await tc.stop_all(cid)
    _nc_force_stop[cid] = time.monotonic()
    for d in (targetreply_chats, targetslide_chats, replyflood_chats, auto_react_chats, auto_reply_chats):
        d.pop(cid, None)
    ncdel_chats.discard(cid)
    mute_chats.discard(cid)
    pfploop_active.pop(cid, None)
    _multiwar_active.pop(cid, None)
    for b in bots():
        bid = getattr(b, "id", None)
        if bid is not None:
            try:
                _ft.clear(bid)
            except Exception:
                pass
            try:
                flood_manager.clear(bid)
            except Exception:
                pass
    await reply_msg(msg, f" 𝐑ᴜᴋ 𝐆ʏᴀ 𝐑ɪxxᴜ 𝐃ᴀᴅᴅʏ 𝐋ᴇᴋɪɴ 𝐈ɴᴋɪ 𝐂ʜᴜᴅᴀɪ 𝐊ᴀʀɴᴇ 𝐌ᴀɪ 𝐁ᴀᴅᴀ 𝐌ᴀᴊᴀ-𝐀ᴀʏᴀ 𝐒ᴀʙ 𝐁ᴀɴᴅ 𝐊ᴀʀᴅɪʏᴀ ⚡🦅👑☠️")

# ========== SETDELAY ==========
@guard
async def cmd_setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _nc_send_gap
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args:
        cur = f"{_nc_send_gap:.3f}s" if _nc_send_gap is not None else "0.05s"
        await reply_msg(msg,
            f"⚡ NC STEP: {cur}\n"
            f"MERGED engine (FREAKY+Sasuke+Arthur)\n"
            f"Usage: `-setdelay <sec>` | `-setdelay reset`\n"
            f"• `0.03` – ultra (FREAKY-level)\n"
            f"• `0.05` – default fast\n"
            f"• `0.08` – stable\n"
            f"• `0.12` – safe / kam flood"
        )
        return
    if args[0].lower() in ("reset", "default", "off"):
        _nc_send_gap = 0.05
        await reply_msg(msg, "✅ Reset to STEP 0.05s (MERGED default)")
        return
    try:
        val = float(args[0])
        if val < 0.03 or val > 10.0:
            await reply_msg(msg, "STEP must be **0.03 – 10.0** seconds")
            return
        _nc_send_gap = val
        await reply_msg(msg, f"✅ STEP `{val:.3f}s` — `-stop` then NC restart to apply")
    except ValueError:
        await reply_msg(msg, "Usage: `-setdelay <seconds>`")

# =====================================================
# ALL ORIGINAL COMMAND HANDLERS (unchanged, now fast)
# =====================================================

# ---- NC commands (all 50+) ----
@guard
async def cmd_nc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -nc <text>")
        return
    # Mix of DISTINCT long styles (not all chud)
    await start_nc_abusing(msg, msg.chat_id, txt, "cool", custom_factory=lambda t: cool_nc_title(t, "mix"))

@guard
async def cmd_multinc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: `-multinc <name>`\nAlag-alag long styles cycle.")
        return
    def multi_factory(target):
        modes = ["wall", "lepino", "greek", "frame", "fire", "dark", "soft", "chud"]
        pack = [
            lambda t: cool_nc_title(t, random.choice(modes)),
            lambda t: cool_nc_title(t, "wall"),
            lambda t: cool_nc_title(t, "lepino"),
            lambda t: cool_nc_title(t, "frame"),
            lambda t: cool_nc_title(t, "fire"),
            lambda t: cool_nc_title(t, "dark"),
            lambda t: cool_nc_title(t, "greek"),
            lambda t: cool_nc_title(t, "soft"),
            lambda t: f"{to_bold(t)}\n" + "".join(random.choice(DARK_EMOJIS) for _ in range(40)) + f"\n{random.randint(10,99)}" ,
            lambda t: f"{to_greekish(t)}\n" + "".join(random.choice(NATURE_EMOJIS) for _ in range(36)) + f"\n✨{random.randint(10,99)}",
            lambda t: f"꧁{to_bold(t)}꧂\n" + "".join(random.choice(MARVEL_EMOJIS) for _ in range(32)) + f"\n⚡{random.randint(10,99)}",
            lambda t: f"{t} {random.choice(TYPENC_WORDS)}\n" + "".join(random.choice(["💀","🔥","⚡","💕"]) for _ in range(40)) + f" {random.randint(10,99)}",
        ]
        try:
            return random.choice(pack)(target)[:255]
        except Exception:
            return cool_nc_title(target, "mix")[:255]
    await start_nc_abusing(msg, msg.chat_id, txt, "multinc", custom_factory=multi_factory)

@guard
async def cmd_ncdark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -ncdark <text>")
    def style(target):
        return cool_nc_title(target, "dark")
    await start_nc_abusing(msg, msg.chat_id, txt, "ncdark", custom_factory=style)

@guard
async def cmd_tmkcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -tmkcnc <text>")
    def style(target):
        e = "".join(random.choice(HAND_EMOJIS) for _ in range(20))
        return f"{to_bold(target)} 바에 ᴛᴍᴋᴄ ￫\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "tmkcnc", custom_factory=style)

@guard
async def cmd_evonc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -evonc <text>")
    def style(target):
        e = "".join(random.choice(HAND_EMOJIS) for _ in range(18))
        return f"{to_bold(target)} 𝙂𝙐𝙇𝘼𝙈﹏\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "evonc", custom_factory=style)

@guard
async def cmd_marvelnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -marvelnc <text>")
    def style(target):
        e = "".join(random.choice(MARVEL_EMOJIS) for _ in range(22))
        return f"{to_bold(target)} 𝙏𝘽𝙆𝘾 ᯓ\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "marvelnc", custom_factory=style)

@guard
async def cmd_magicnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -magicnc <text>")
    def style(target):
        return cool_nc_title(target, "soft") if False else (
            f"{to_bold(target)} 𝙍𝙉𝘿𝙔 𝘽𝘼𝙇𝘼𝙆\n" + "".join(random.choice(MAGIC_EMOJIS) for _ in range(24))
        )
    await start_nc_abusing(msg, msg.chat_id, txt, "magicnc", custom_factory=style)

@guard
async def cmd_sportnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -sportnc <text>")
    def style(target):
        e = "".join(random.choice(MARVEL_EMOJIS) for _ in range(20))
        return f"{to_bold(target)} 𝙏𝙀𝙍𝙄 𝙂𝙉𝘿 ≯\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "sportnc", custom_factory=style)

@guard
async def cmd_lndnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -lndnc <text>")
    def style(target):
        e = "".join(random.choice(NATURE_EMOJIS) for _ in range(22))
        return f"{to_bold(target)} 𝘾𝙃𝙐𝘿 𓀐𓂺\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "lndnc", custom_factory=style)

@guard
async def cmd_ncspeed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -ncspeed <text>")
    def style(target):
        e = "".join(random.choice(FOOD_EMOJIS) for _ in range(22))
        return f"{to_bold(target)} 𝘾𝙃𝙐𝘿𝘼𝙆𝘼𝘿 ≫\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "ncspeed", custom_factory=style)

@guard
async def cmd_emognc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -emognc <text>")
    def style(target):
        e = "".join(random.choice(FACE_EMOJIS) for _ in range(22))
        return f"{to_bold(target)} 𝘼𝙐𝙆𝘼𝙏 ⁀➴♡\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "emognc", custom_factory=style)

@guard
async def cmd_yournc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -yournc <text>")
    def style(target):
        e = "".join(random.choice(HOBBY_EMOJIS) for _ in range(20))
        return f"𓆩 {to_bold(target)} 𓆪\n{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "yournc", custom_factory=style)

@guard
async def cmd_typenc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -typenc <text>")
    def style(target):
        w = random.choice(TYPENC_WORDS)
        return f"{target} {w} ִֶָ࣪𓏲ᥫ᭡ ₊ ⊹ ˑ ִ ֶ 𓂃"
    await start_nc_abusing(msg, msg.chat_id, txt, "typenc", custom_factory=style)

@guard
async def cmd_flashnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -flashnc <text>")
    def style(target):
        e = random.choice(TECH_EMOJIS)
        return f"{target} ═══ {e} ═══"
    await start_nc_abusing(msg, msg.chat_id, txt, "flashnc", custom_factory=style)

@guard
async def cmd_foxync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -foxync <text>")
    def style(target):
        e = random.choice(ANIMAL_EMOJIS)
        return f"{target} 𝗖𝗛𝗨𝗗 𝗞𝗥 𝗗𝗔𝗙𝗔𝗡~{e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "foxync", custom_factory=style)

@guard
async def cmd_ncmoon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -ncmoon <text>")
    MOON_MSGS = ["🌑 {target} 𝘛𝘌𝘙𝘐 मां 𝘋𝘈𝘕𝘐 𝘋𝘈𝘕𝘐𝘌𝘓𝘚><🌑", "🌔 {target} 𝘛𝘌𝘙𝘐 मां 𝘓𝘌𝘟𝘐 𝘓𝘜𝘕𝘈><🌔", "🌕 {target} 𝘛𝘌𝘙𝘐 मां 𝘗𝘙𝘐𝘠𝘈 𝘉𝘏𝘈𝘉𝘏𝘐><🌕", "🌖 {target} 𝘛𝘌𝘙𝘐 मां 𝘊𝘖𝘖𝘔𝘖𝘛𝘖𝘡𝘌><🌖", "🌗 {target}𝘛𝘌𝘙𝘐 मां 𝘔𝘐𝘈 𝘒𝘏𝘈𝘓𝘐𝘍𝘈><🌗", "🌘 {target} 𝘛𝘌𝘙𝘐 मां 𝘔𝘐𝘈 𝘙𝘖𝘚𝘌><🌘", "🌙 {target} 𝘛𝘌𝘙𝘐 मां 𝘋𝘐𝘙𝘛𝘠 𝘛𝘐𝘕𝘈><🌙"]
    def style(target):
        return random.choice(MOON_MSGS).replace("{target}", target)
    await start_nc_abusing(msg, msg.chat_id, txt, "ncmoon", custom_factory=style)

@guard
async def cmd_ncflag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -ncflag <text>")
    FLAG_MSGS = ["{target} 🇨🇳𝐌ᴀᴅᴀʀᴄʜᴏ𝐃🇨🇳", "{target} 🇨🇦𝐊ᴀɴᴊᴀ𝐑🇨🇦", "{target} 🇩🇪𝐑ᴀɴᴅ𝐈🇩🇪", "{target} 🇮🇳𝐇ᴀ𝐀ʀᴀᴍᴢᴀᴅᴀ🇮🇳", "{target} 🇮🇲𝐓ᴇʀɪᴍᴀᴀᴋɪ𝐂ʜᴜᴛ🇮🇲", "{target} 🇰🇵𝐁ɪᴛᴄʜ🇰🇵", "{target} 🇺🇸𝐂ʜᴜᴅᴋᴀ𝐃🇺🇸"]
    def style(target):
        return random.choice(FLAG_MSGS).replace("{target}", target)
    await start_nc_abusing(msg, msg.chat_id, txt, "ncflag", custom_factory=style)

@guard
async def cmd_ncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -ncemo <text>")
    def style(target):
        return f"{random.choice(SUFFIX_EMOJIS)} {target} {random.choice(SUFFIX_EMOJIS)}"
    await start_nc_abusing(msg, msg.chat_id, txt, "ncemo", custom_factory=style)

@guard
async def cmd_flowernc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -flowernc <text>")
    FLOWER_MSGS = ["𝜗𝜚⋆₊🍁˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊🌱˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊🌿˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊🍃˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊☘️˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊🍀˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ ", "𝜗𝜚⋆₊🪴˚{target} Sʟᴜᴛ Mᴀᴀ ᴋᴇ Lᴀᴅᴋᴇ "]
    def style(target):
        return random.choice(FLOWER_MSGS).replace("{target}", target)
    await start_nc_abusing(msg, msg.chat_id, txt, "flowernc", custom_factory=style)

@guard
async def cmd_timenc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -timenc <text>")
    TIME_MSGS = [
        " {target} Tɪᴍᴇ Is Oᴠᴇʀ 12:382:229",
        " {target} Tᴇʀɪ Mᴀᴀ Kᴀ Bʜᴏsᴅᴀ Sɪʟ Dᴜɴ 12:382:230",
        " {target} Tᴇʀᴀ Bᴀᴀᴘ Gᴏʜᴀɴ 12:382:231 ",
        " {target} Tᴇʀɪ Bᴇʜɴ Kɪ Cʜᴜᴛ Mᴇ Gʜᴀᴅɪ 12:382:232",
        " {target} Tɪᴍᴇ Tᴏ Dɪᴇ Mᴄ 12:382:233",
        "12:382:234 {target} Tᴇʀɪ Mᴀᴀ Cʜᴜᴅ Gᴀʏɪ ",
    ]
    def style(target):
        return random.choice(TIME_MSGS).replace("{target}", target)
    await start_nc_abusing(msg, msg.chat_id, txt, "timenc", custom_factory=style)

@guard
async def cmd_nccurly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt: return await reply_msg(msg, "Usage: -nccurly <text>")
    CURLY_MSGS = ["{{ Tᴍᴋᴄ ! {target} Tᴍᴋᴄ ! }}", "{{-Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !-}}", "{{★Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !★}}", "{{🔥Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🔥}}", "{{🔱Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🔱}}", "{{✨Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !✨}}", "{{🥀Tᴍᴋᴄ ! {target} Tᴍᴋᴄ !🥀}}"]
    def style(target):
        return random.choice(CURLY_MSGS).replace("{target}", target)
    await start_nc_abusing(msg, msg.chat_id, txt, "nccurly", custom_factory=style)

@guard
async def cmd_snc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -snc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_gokugod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -gokugod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_vegetagod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -vegetagod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "vegeta")

@guard
async def cmd_brolygod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -brolygod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "broly")

@guard
async def cmd_gohangod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -gohangod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "gohan")

@guard
async def cmd_trunksgod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -trunksgod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "trunks")

@guard
async def cmd_dbgod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -dbgod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_db1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -db1 <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_broly1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -broly1 <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "broly")

@guard
async def cmd_triogod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -triogod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_silknc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -silknc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_hakai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -hakai <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "hakai")

@guard
async def cmd_chud(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -chud <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "hakai")

@guard
async def cmd_anshgod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -anshgod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

@guard
async def cmd_kusanagigod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -kusanagigod <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "broly")

@guard
async def cmd_kusanagi1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -kusanagi1 <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "broly")

@guard
async def cmd_boldnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -boldnc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "boldnc",
                           custom_factory=lambda t: cool_nc_title(t, "frame"))

@guard
async def cmd_cursivenc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -cursivenc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "cursivenc",
                           custom_factory=lambda t: cool_nc_title(t, "soft"))

@guard
async def cmd_italicnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -italicnc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "italicnc",
                           custom_factory=lambda t: cool_nc_title(t, "greek"))

@guard
async def cmd_wavenc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -wavenc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "wavenc",
                           custom_factory=lambda t: cool_nc_title(t, "lepino"))

@guard
async def cmd_godki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -godki <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "godki",
                           custom_factory=lambda t: cool_nc_title(t, "fire"))

@guard
async def cmd_ultranc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -ultranc <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "ultranc",
                           custom_factory=lambda t: cool_nc_title(t, "wall"))

@guard
async def cmd_saitama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -saitama <text>")
        return
    await start_nc_abusing(msg, msg.chat_id, txt, "saitama",
                           custom_factory=lambda t: cool_nc_title(t, "frame"))

@guard
async def cmd_aizennc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context) or "AIZEN"
    def style(target):
        e = random.choice(MAGIC_EMOJIS)
        return f"{target} 𝙍𝙉𝘿𝙔 𝘽𝘼𝙇𝘼𝙆⁀➴༯ {e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "aizen", custom_factory=style)

@guard
async def cmd_villainnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context) or "VILLAIN"
    def style(target):
        e = random.choice(MAGIC_EMOJIS)
        return f"{target} 𝙍𝙉𝘿𝙔 𝘽𝘼𝙇𝘼𝙆⁀➴༯ {e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "villain", custom_factory=style)

@guard
async def cmd_randomcod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context) or "RANDOM"
    def style(target):
        e = random.choice(MARVEL_EMOJIS)
        return f"{target} 𝙍𝙉𝘿𝙔 𝘽𝘼𝙇𝘼𝙆⁀➴༯ {e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "random", custom_factory=style)

@guard
async def cmd_godcod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context) or "GOD"
    def style(target):
        e = random.choice(MARVEL_EMOJIS)
        return f"{target} 𝙍𝙉𝘿𝙔 𝘽𝘼𝙇𝘼𝙆⁀➴༯ {e}"
    await start_nc_abusing(msg, msg.chat_id, txt, "god", custom_factory=style)

@guard
async def cmd_phantom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if msg:
        await reply_msg(msg, "⚡ Phantom Engine: Zero-jitter mode active.")

@guard
async def cmd_testament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_phantom(update, context)

@guard
async def cmd_shadow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_phantom(update, context)

async def _friend_nc_cmd(update, context, friend):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context) or friend
    await start_nc_abusing(msg, msg.chat_id, txt, "goku")

# ---- SPAM commands ----
@guard
async def cmd_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -spam <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    abuse = cool_spam_line(txt) if random.random() < 0.55 else random.choice(ABUSING_SPAM).format(target=txt)
                    await bot.send_message(cid, abuse)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "spam", _run)
    await reply_msg(msg, f"💣 SPAM with abusing started for: {txt}")

@guard
async def cmd_stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "spam")
    await tc.stop(msg.chat_id, "multispam")
    await reply_msg(msg, "⛔ SPAM stopped")

GOHAN_SPAM_PACKS = [
    lambda t: (f"{t} ˏˋ°•*⁀➷ 𝑳𝑼𝑵𝑫 𝑪𝑯𝑶𝑶𝑺 𝑮𝑶𝑯𝑨𝑵 𝑲𝑨 🥂🌙 ") * 12,
    lambda t: (f"{t} 𝐓𝐔𝐌 𝐓𝐀𝐀𝐓𝐓𝐎 𝐊𝐈 𝐌𝐊𝐁 𝐆𝐀𝐑𝐄𝐄𝐁𝑶_______________________________________________/⭐ ") * 5,
    lambda t: f"{t} CVR KR MC GAREEB " + ("👞" * 40) + f" {t} CVR KR MC GAREEB",
]

@guard
async def cmd_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        cur = chat_threads.get(msg.chat_id, 3)
        await reply_msg(msg, f"🧵 Threads: `{cur}`\nUsage: `-threads <1-20>`")
        return
    try:
        n = int(args[0])
        if n < 1 or n > 20:
            await reply_msg(msg, "Threads must be 1–20")
            return
        chat_threads[msg.chat_id] = n
        await reply_msg(msg, f"✅ Threads set to `{n}` for this GC")
    except ValueError:
        await reply_msg(msg, "Invalid number")

@guard
async def cmd_multispam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: `-multispam <target>`")
        return
    cid = msg.chat_id
    n_threads = chat_threads.get(cid, 5)
    gap = max(float(_nc_send_gap) if _nc_send_gap else 0.03, 0.015)

    async def _run(stop_ev):
        bot_list = bots()
        if not bot_list:
            return
        async def worker(wid):
            i = wid
            while not stop_ev.is_set():
                pack = GOHAN_SPAM_PACKS[i % len(GOHAN_SPAM_PACKS)]
                body = pack(txt)
                bot = bot_list[i % len(bot_list)]
                try:
                    await bot.send_message(cid, body[:4096])
                except RetryAfter as e:
                    await asyncio.sleep(float(getattr(e, "retry_after", 1)) + 0.2)
                except Exception:
                    pass
                i += 1
                try:
                    await asyncio.wait_for(stop_ev.wait(), timeout=gap)
                    return
                except asyncio.TimeoutError:
                    pass
        tasks = [asyncio.create_task(worker(w)) for w in range(n_threads)]
        try:
            await stop_ev.wait()
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    await tc.start(cid, "multispam", _run)
    await reply_msg(msg, f"🚀 MULTISPAM ON for `{txt}`\n🧵 threads: `{n_threads}` | bots: `{len(bots())}`\nStop: `-stopspam` / `-stop`")

@guard
async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: `-join <invite_link or @username>`")
        return
    link = args[0].strip()
    if "t.me/" in link:
        link = link.split("t.me/")[-1]
    if link.startswith("+"):
        link = link
    if link.startswith("@"):
        link = link[1:]
    ok = 0; fail = 0
    for bot in bots():
        try:
            await bot.join_chat(link)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.15)
    await reply_msg(msg, f"🔗 Join done — ✅ `{ok}` | ❌ `{fail}`")

@guard
async def cmd_bye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    cid = msg.chat_id
    await reply_msg(msg, "👋 𝗝𝗔 𝗥𝗛𝗔 𝗛𝗨 𝗜𝗡𝗞𝗔  𝗚𝗔𝗠𝗘 𝗢𝗩𝗘𝗥 𝗞𝗔𝗥𝗞𝗘 𝗔𝗚𝗥 𝗙𝗜𝗥𝗦𝗘 𝗣𝗔𝗥𝗘𝗦𝗛𝗔𝗡 𝗞𝗔𝗥𝗘 𝗧𝗢 𝗕𝗨𝗟𝗔 𝗟𝗘𝗡𝗔 𝗜𝗡𝗞𝗜 𝗠𝗔𝗔 𝗖𝗛𝗢𝗗 𝗞𝗘 𝗥𝗔𝗞𝗛 𝗗𝗨𝗡𝗚𝗔 💋💋⚡⚡🧿🫶🏻")
    for bot in bots():
        try:
            await bot.send_message(cid, " 𝗚𝗔𝗠𝗘 𝗢𝗩𝗘𝗥 𝗕𝗬 𝗕𝗛𝗔𝗚𝗪𝗔𝗡 𝗥𝗜𝗫𝗨 ~~~💋⚡")
        except Exception:
            pass
        try:
            await bot.leave_chat(cid)
        except Exception:
            pass

@guard
async def cmd_slidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -slidespam <text>")
        return
    cid = msg.chat_id
    idx = [0]
    VARIANTS = [
        f"▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞\n{txt}\n▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞▞",
        f"║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──\n{txt}\n║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──║──",
        f"🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥\n{txt}\n🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥",
        f"🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻\n{txt}\n🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻",
        f"｡☆✼★━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━★✼☆｡\n{txt}\n｡☆✼★━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━★✼☆｡"
    ]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    v = VARIANTS[idx[0] % len(VARIANTS)]
                    idx[0] += 1
                    abuse = cool_spam_line(txt) if random.random() < 0.55 else random.choice(ABUSING_SPAM).format(target=txt)
                    await bot.send_message(cid, f"{v}\n{abuse}")
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "slide", _run)
    await reply_msg(msg, f"💥 LONG TEXT SLIDE SPAM started for: {txt}")

@guard
async def cmd_stopslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "slide")
    await reply_msg(msg, "⛔ SLIDE SPAM stopped")

@guard
async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -reply <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    abuse = cool_spam_line(txt) if random.random() < 0.55 else random.choice(ABUSING_SPAM).format(target=txt)
                    await bot.send_message(cid, abuse)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "reply", _run)
    await reply_msg(msg, f"💬 REPLY with abusing started for: {txt}")

@guard
async def cmd_stopreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "reply")
    await reply_msg(msg, "⛔ REPLY stopped")

@guard
async def cmd_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -texts <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    message = (f"{txt}  𝑶𝒀𝑬 𝑩𝑲𝑳 𝑻𝑬𝑹𝑰 𝑴𝑨𝑨 𝑲𝑨 𝑲𝑯𝑨𝑺𝑨𝑴 𝑯𝑼 𝑨𝑼𝑲𝑨𝑻 𝑴𝑰𝑬 𝑹𝑯 𝑹𝑵𝑫𝒀 𝑷𝑼𝑻𝑹𝑨 ☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲☲\\~   \n") * 10
                    await bot.send_message(cid, message)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "texts", _run)
    await reply_msg(msg, f"📝 TEXTS spam started for: {txt}")

@guard
async def cmd_shayari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -shayari <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    message = (f"𝙏𝙄𝙆 𝙏𝙄𝙆 𝘾𝙃𝙇𝙏𝘼 𝙂𝙃𝙊𝘿𝘼 {txt} 𝙆𝙄 𝘽𝙃𝙀𝙉 𝙆𝘼 𝙇𝙊𝘿𝘼 ╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍╍ \n") * 10
                    await bot.send_message(cid, message)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "shayari", _run)
    await reply_msg(msg, f"📝 SHAYARI spam started for: {txt}")

@guard
async def cmd_songy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -songy <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    message = f"""{txt} 𝗗𝗮𝗹𝗹𝗲!
𝗕𝗲𝘁𝗮 𝗗𝗮𝗹𝗹𝗲 𝗕𝗲𝗻𝗶 𝗕𝗮𝗮𝗽 𝗧𝗲𝗿𝗮 𝗡𝗮𝗹𝗹𝗮 𝗛𝗮𝗶
𝗟*𝗱𝗮 𝗛𝗼𝗼𝗸𝗮𝗵 𝗠𝗲𝗿𝗮, 𝗠𝗮𝗺𝘁𝗮 𝗠𝗲𝗿𝗶 𝗖𝗵𝗮𝗹𝗹𝗮 𝗛𝗮𝗶
𝗠𝗮𝗺𝘁𝗮 𝗡*𝗻𝗴𝗶 𝗟𝗲𝘁𝗶, 𝗕𝗮𝗮𝗽 𝗞𝗶𝘁𝗵𝗲 𝗖𝗵𝗮𝗹𝗹𝗮 𝗛𝗮𝗶
𝗠𝗮𝗶 𝗧𝗮𝗻 𝗕𝗵𝘂𝗹 𝗚𝗮𝘆𝗮 𝗦𝗶 𝗞𝗶 𝗕𝗮𝗮𝗽 𝗡𝗮𝗹𝗹𝗮 𝗛𝗮𝗶
𝗠𝗮𝗺𝘁𝗮 𝗞𝗶𝗶 𝗣𝘂$$𝘆 𝗛𝗮𝗶 𝗧𝗶𝗴𝗵𝘁
𝗚𝘂𝗱𝗱𝘂 𝗣𝗲𝗲𝘆𝗲𝗴𝗮 𝗡𝗮 𝗟𝗶𝗴𝗵𝘁
𝗚𝘂𝗱𝗱𝘂 𝗠𝗲𝗲𝘁𝗵𝗮 𝗝𝗮𝗶𝘀𝗲 𝗚𝗼𝗼𝗱 𝗗𝗮𝘆
𝗠𝗮𝗺𝘁𝗮 𝗗𝗲𝘁𝗶 𝗔𝗹𝗹 𝗡𝗶𝗴𝗵𝘁"""
                    await bot.send_message(cid, message)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "songy", _run)
    await reply_msg(msg, f"🎵 SONGY spam started for: {txt}")

@guard
async def cmd_customspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -customspam <text>")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    kaomoji = random.choice(["(◕‿◕)", "(✿◠‿◠)", "(◔‿◔)", "(◡‿◡✿)", "(◕‿◕✿)", "(ᵔ◡ᵔ)"])
                    message = f"{txt}  ⩇⩇:⩇⩇ {kaomoji}"
                    await bot.send_message(cid, message)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "customspam", _run)
    await reply_msg(msg, f"🎨 CUSTOM spam started for: {txt}")

@guard
async def cmd_burstspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    try:
        count = int(args[-1])
        txt = " ".join(args[:-1]).strip()
        if not txt:
            raise ValueError
    except:
        txt = " ".join(args).strip()
        count = 20
    count = min(count, 50)
    cid = msg.chat_id
    bot_list = bots()
    if not bot_list:
        await reply_msg(msg, "⚡ No bots!")
        return
    async def _send(bot, i):
        abuse = cool_spam_line(txt) if random.random() < 0.55 else random.choice(ABUSING_SPAM).format(target=txt)
        await bot.send_message(cid, f"💥 BURST {i+1}: {abuse}")
    tasks = [asyncio.create_task(_send(bot_list[i % len(bot_list)], i)) for i in range(count)]
    await asyncio.gather(*tasks, return_exceptions=True)
    await reply_msg(msg, f"💥 BURST SPAM sent! ({count} messages)")

@guard
async def cmd_rapidfire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -rapidfire <text>")
        return
    cid = msg.chat_id
    bot_list = bots()
    if not bot_list:
        await reply_msg(msg, "⚡ No bots!")
        return
    RAPID = [f"⚡🔥{txt}🔥⚡", f"💥⚡{txt}⚡💥", f"🌊⚡{txt}⚡🌊", f"👑⚡{txt}⚡👑"]
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            tasks = []
            for bot in bot_list:
                if stop_ev.is_set():
                    break
                v = RAPID[idx[0] % len(RAPID)]
                idx[0] += 1
                abuse = cool_spam_line(txt) if random.random() < 0.55 else random.choice(ABUSING_SPAM).format(target=txt)
                tasks.append(asyncio.create_task(bot.send_message(cid, f"{v}\n{abuse}")))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.000000001)
    await tc.start(cid, "rapid", _run)
    await reply_msg(msg, f"⚡🔥 RAPIDFIRE started for: {txt}")

@guard
async def cmd_stoprapid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "rapid")
    await reply_msg(msg, "⛔ RAPIDFIRE stopped")

@guard
async def cmd_swipespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -swipespam <text>")
        return
    cid = msg.chat_id
    idx = [0]
    SWIPE_V = ["🌊〰️〰️{t}〰️〰️🌊", "⚡〰{t}〰⚡", "🌀〰〰{t}〰〰🌀", "💥〰{t}〰💥"]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                v = SWIPE_V[idx[0] % len(SWIPE_V)].format(t=txt)
                idx[0] += 1
                try:
                    await bot.send_message(cid, v)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "swipe", _run)
    await reply_msg(msg, f"🌊 SWIPE SPAM started for: {txt}")

@guard
async def cmd_stopswipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "swipe")
    await reply_msg(msg, "⛔ SWIPE SPAM stopped")

@guard
async def cmd_chudspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -chudspam <text>")
        return
    cid = msg.chat_id
    words = _CHUD_WORDS
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                word = words[idx[0] % len(words)]
                idx[0] += 1
                msg_txt = f"[chud {txt}𒐫𒐫💥{word}💥𒐫𒐫 ➴]"
                try:
                    await bot.send_message(cid, msg_txt)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "chudspam", _run)
    await reply_msg(msg, f"💥 CHUD SPAM started for: {txt}")

@guard
async def cmd_stopchudspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "chudspam")
    await reply_msg(msg, "⛔ CHUD SPAM stopped")

@guard
async def cmd_tagspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -tagspam <uid> <text>")
        return
    try:
        uid = int(args[0])
    except ValueError:
        await reply_msg(msg, "Invalid user ID")
        return
    txt = " ".join(args[1:])
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, f'<a href="tg://user?id={uid}">⚡</a> {txt}', parse_mode="HTML")
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "tagspam", _run)
    await reply_msg(msg, f"🏷️ TAG SPAM started for user {uid}")

@guard
async def cmd_stoptagspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "tagspam")
    await reply_msg(msg, "⛔ TAG SPAM stopped")

@guard
async def cmd_copyspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    rep = msg.reply_to_message
    txt = txt_arg(context) or (rep.text if rep and rep.text else None)
    if not txt:
        await reply_msg(msg, "Reply to a message or provide text with -copyspam")
        return
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, txt)
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "copyspam", _run)
    await reply_msg(msg, f"📋 COPY SPAM started")

@guard
async def cmd_stopcopyspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "copyspam")
    await reply_msg(msg, "⛔ COPY SPAM stopped")

# ---- Slider commands ----
@guard
async def cmd_alexa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -alexa")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    idx = [0]
    TEXTS = ["𝗔𝗟𝗘𝗫𝗔 𝗜𝗦𝗦 𝗠𝗖 𝗞𝗜 𝗠𝗔𝗔 𝗞𝗘 𝗡𝗢𝗧𝗘𝗦 𝗗𝗜𝗞𝗛𝗔𝗢 🙁", "𝗔𝗟𝗘𝗫𝗔 𝗜𝗦𝗦 𝗥𝗡𝗗𝗬 𝗞𝗔 𝗠𝗨𝗛 𝗕𝗡𝗗 𝗞𝗥𝗗𝗢 😆", "𝗔𝗟𝗘𝗫𝗔 𝗜𝗦𝗞𝗜 𝗕𝗛𝗘𝗡 𝗖𝗛𝗢𝗗 𝗗𝗢 🌙", "𝗔𝗟𝗘𝗫𝗔 𝗜𝗦𝗞𝗘 𝗕𝗔𝗔𝗣 𝗞𝗜 𝗚𝗡𝗗 𝗠𝗜𝗘 𝗟𝗔𝗧𝗛 𝗗𝗔𝗔𝗟 𝗗𝗢 😆", "𝗔𝗟𝗘𝗫𝗔 𝗜𝗦𝗞𝗔 𝗚𝗔𝗠𝗘 𝗢𝗩𝗘𝗥 𝗞𝗔 𝗩𝗜𝗗𝗘𝗢 𝗗𝗢𝗡𝗘 𝗞𝗥𝗢 🥹"]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, TEXTS[idx[0] % len(TEXTS)], reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                    idx[0] += 1
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "alexa", _run)
    await reply_msg(msg, "✅ Alexa started")

@guard
async def cmd_stopalexa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "alexa")
    await reply_msg(msg, "⛔ Alexa stopped")

@guard
async def cmd_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -animal")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    idx = [0]
    TEXTS = ["𝗢𝗬𝗘 𝗧𝗠𝗞𝗖 𝗠𝗜𝗘 𝗚𝗢𝗥𝗜𝗟𝗟𝗔 🦍", "𝗢𝗬𝗘 𝗧𝗘𝗥𝗜 𝗕𝗛𝗘𝗡 𝗞𝗜 𝗖𝗛𝗨𝗧 𝗠𝗜𝗘 𝗚𝗛𝗢𝗗𝗔 🐎", "𝗢𝗬𝗘 𝗧𝗘𝗥𝗘 𝗕𝗔𝗔𝗣 𝗞𝗜 𝗚𝗡𝗗 𝗠𝗜𝗘 𝗞𝗔𝗡𝗚𝗔𝗥𝗢𝗢 🦘", "𝗢𝗬𝗘 𝗧𝗘𝗥𝗜 𝗚𝗡𝗗 𝗠𝗜𝗘 𝗖𝗔𝗠𝗘𝗟 🐪", "𝗢𝗬𝗘 𝗧𝗨 𝗝𝗔𝗡𝗪𝗔𝗥𝗢 𝗦𝗘 𝗖𝗛𝗨𝗗 𝗚𝗬𝗔 ? 😆😆😆"]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, TEXTS[idx[0] % len(TEXTS)], reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                    idx[0] += 1
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "animal", _run)
    await reply_msg(msg, "✅ Animal started")

@guard
async def cmd_stopanimal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "animal")
    await reply_msg(msg, "⛔ Animal stopped")

@guard
async def cmd_swipe_slider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -swipe")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    idx = [0]
    TEXTS = ["𝗧𝗘𝗥𝗜 𝗠𝗞𝗖 𝗦𝗔𝗦𝗧𝗜 𝗛𝗔𝗜 𝗕𝗔𝗔𝗧 𝗞𝗛𝗧𝗠 😡", "𝗖𝗛𝗟 𝗚𝗨𝗟𝗔𝗠𝗜 𝗞𝗥 𝗧𝗔𝗧𝗧𝗘 😆", "𝗖𝗛𝗜𝗗𝗜𝗬𝗔 𝗖𝗛𝗔𝗗𝗜 𝗣𝗛𝗔𝗔𝗗 𝗣𝗘 𝗨𝗦𝗡𝗘 𝗗𝗜𝗬𝗔 𝗠𝗨𝗧 𝗧𝗠𝗞𝗖 😆", "𝗘𝗞 𝗟𝗔𝗔𝗧 𝗠𝗜𝗘 𝗟𝗡𝗗 𝗖𝗛𝗔𝗧𝗧𝗔 𝗙𝗜𝗥𝗘𝗚𝗔 𝗕𝗦𝗗𝗞 😆"]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, TEXTS[idx[0] % len(TEXTS)], reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                    idx[0] += 1
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "swipe_slider", _run)
    await reply_msg(msg, "✅ Swipe started")

@guard
async def cmd_stopswipe_slider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "swipe_slider")
    await reply_msg(msg, "⛔ Swipe stopped")

# ---- Target, Auto, etc. ----
@guard
async def cmd_replyflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -replyflood <text>")
        return
    replyflood_chats[msg.chat_id] = txt
    await reply_msg(msg, f"🔁 Reply Flood active for: {txt}")

@guard
async def cmd_stopreplyflood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    replyflood_chats.pop(msg.chat_id, None)
    await reply_msg(msg, "⛔ Reply Flood stopped")

@guard
async def cmd_replyraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -replyraid <text>")
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -replyraid <text>")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    VARS = [f"⚔️ {txt}", f"🔥 {txt}", f"💀 {txt}", f"⚡ {txt}"]
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                v = VARS[idx[0] % len(VARS)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "replyraid", _run)
    await reply_msg(msg, f"⚔️ Reply Raid started on message {target}")

@guard
async def cmd_stopreplyraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "replyraid")
    await reply_msg(msg, "⛔ Reply Raid stopped")

@guard
async def cmd_massreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -massreply <text>")
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -massreply <text>")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    for bot in bots():
        try:
            await bot.send_message(cid, txt, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
        except Exception:
            pass
    await reply_msg(msg, f"✅ Mass Reply sent to message {target}")

@guard
async def cmd_mentionraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -mentionraid <uid> <text>")
        return
    try:
        uid = int(args[0])
    except:
        await reply_msg(msg, "Invalid ID")
        return
    txt = " ".join(args[1:])
    cid = msg.chat_id
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                try:
                    await bot.send_message(cid, f'<a href="tg://user?id={uid}">⚡</a> {txt}', parse_mode="HTML")
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "mentionraid", _run)
    await reply_msg(msg, f"📢 Mention Raid started for user {uid}")

@guard
async def cmd_stopmentionraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "mentionraid")
    await reply_msg(msg, "⛔ Mention Raid stopped")

@guard
async def cmd_rrbomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -rrbomb <text> [count]")
        return
    try:
        count = int(args[-1])
        txt = " ".join(args[:-1]).strip()
        if not txt:
            raise ValueError
    except:
        txt = " ".join(args).strip()
        count = 15
    count = min(count, 50)
    rep = msg.reply_to_message
    target = rep.message_id if rep else msg.message_id
    cid = msg.chat_id
    VARS = [f"💣 {txt}", f"🔥 {txt}", f"⚔️ {txt}"]
    tasks = []
    for i in range(count):
        bot = bots()[i % len(bots())]
        v = VARS[i % len(VARS)]
        tasks.append(asyncio.create_task(bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))))
    await asyncio.gather(*tasks, return_exceptions=True)
    await reply_msg(msg, f"💣 RR Bomb sent {count} replies")

@guard
async def cmd_rrloop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -rrloop <text>")
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -rrloop <text>")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    VARS = [f"🔁 {txt}", f"♾️ {txt}", f"🌀 {txt}"]
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                v = VARS[idx[0] % len(VARS)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "rrloop", _run)
    await reply_msg(msg, f"♾️ RR Loop started on message {target}")

@guard
async def cmd_stoprrloop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "rrloop")
    await reply_msg(msg, "⛔ RR Loop stopped")

@guard
async def cmd_rrspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -rrspam <text>")
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -rrspam <text>")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    VARS = [f"🎯 {txt}", f"💥 {txt}"]
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                v = VARS[idx[0] % len(VARS)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "rrspam", _run)
    await reply_msg(msg, f"🎯 RR Spam started on message {target}")

@guard
async def cmd_stoprrspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "rrspam")
    await reply_msg(msg, "⛔ RR Spam stopped")

@guard
async def cmd_multirr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message with -multirr <text>")
        return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -multirr <text>")
        return
    cid = msg.chat_id
    target = msg.reply_to_message.message_id
    VARS = [f"⚔️ {txt}", f"🔥 {txt}", f"💀 {txt}"]
    idx = [0]
    async def _run(stop_ev):
        while not stop_ev.is_set():
            for bot in bots():
                if stop_ev.is_set():
                    break
                v = VARS[idx[0] % len(VARS)]
                idx[0] += 1
                try:
                    await bot.send_message(cid, v, reply_parameters=ReplyParameters(message_id=target, allow_sending_without_reply=False))
                except Exception:
                    pass
                await asyncio.sleep(0.000000001)
    await tc.start(cid, "multirr", _run)
    await reply_msg(msg, f"⚔️ MultiRR started on message {target}")

@guard
async def cmd_stopmultirr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "multirr")
    await reply_msg(msg, "⛔ MultiRR stopped")

@guard
async def cmd_targetreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -targetreply <uid> <text>")
        return
    try:
        uid = int(args[0])
    except:
        await reply_msg(msg, "Invalid ID")
        return
    txt = " ".join(args[1:])
    targetreply_chats[msg.chat_id] = {"uid": uid, "text": txt}
    await reply_msg(msg, f"🎯 Target reply set for user {uid}")

@guard
async def cmd_stoptargetreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    targetreply_chats.pop(msg.chat_id, None)
    await reply_msg(msg, "⛔ Target reply stopped")

@guard
async def cmd_targetslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -targetslide <uid>")
        return
    try:
        uid = int(args[0])
    except:
        await reply_msg(msg, "Invalid ID")
        return
    txt = " ".join(args[1:]) or "💥𒐫𒐫CHUD𒐫𒐫💥"
    targetslide_chats[msg.chat_id] = {"uid": uid, "text": txt}
    await reply_msg(msg, f"🎯 Target slide set for user {uid}")

@guard
async def cmd_stoptargetslide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    targetslide_chats.pop(msg.chat_id, None)
    await reply_msg(msg, "⛔ Target slide stopped")

@guard
async def cmd_ncdel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    ncdel_chats.add(msg.chat_id)
    await reply_msg(msg, "🗑️ NC Del activated")

@guard
async def cmd_stopncdel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    ncdel_chats.discard(msg.chat_id)
    await reply_msg(msg, "⛔ NC Del deactivated")

@guard
async def cmd_autoreact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -autoreact <emoji>")
        return
    auto_react_chats[msg.chat_id] = args[0]
    await reply_msg(msg, f"✅ Auto-react set to: {args[0]}")

@guard
async def cmd_stopautoreact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    auto_react_chats.pop(msg.chat_id, None)
    await reply_msg(msg, "✅ Auto-react stopped")

@guard
async def cmd_autoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -autoreply <text>")
        return
    auto_reply_chats[msg.chat_id] = txt
    await reply_msg(msg, f"✅ Auto-reply set to: {txt}")

@guard
async def cmd_stopautoreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    auto_reply_chats.pop(msg.chat_id, None)
    await reply_msg(msg, "✅ Auto-reply stopped")

@guard
async def cmd_autostatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    react = auto_react_chats.get(msg.chat_id, "❌ Disabled")
    reply = auto_reply_chats.get(msg.chat_id, "❌ Disabled")
    await reply_msg(msg, f"🤖 Auto Status:\nReact: {react}\nReply: {reply}")

# ---- Sudo & Bheek ----
@owner_only
async def cmd_givebheek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    target = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.id
    elif get_args(context) and get_args(context)[0].isdigit():
        target = int(get_args(context)[0])
    if not target:
        await reply_msg(msg, "Reply to a user or provide ID")
        return
    SUDO_USERS.add(target)
    save_json(SUDO_FILE, list(SUDO_USERS))
    await reply_msg(msg, f"🔐 Bheek di gayi! User {target} ab Sudo hai!")

@owner_only
async def cmd_bheekhatao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    target = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user.id
    elif get_args(context) and get_args(context)[0].isdigit():
        target = int(get_args(context)[0])
    if not target:
        await reply_msg(msg, "Reply to a user or provide ID")
        return
    if target == OWNER_ID:
        await reply_msg(msg, "⚠️ Owner ki bheek nahi hata sakte!")
        return
    SUDO_USERS.discard(target)
    save_json(SUDO_FILE, list(SUDO_USERS))
    await reply_msg(msg, f"🗑️ Bheek wapas le li! User {target} se sudo hataya!")

@guard
async def cmd_bheeklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    text = f"🔐 Bheek wale log:\n\n• Owner: `{OWNER_ID}`\n"
    for uid in SUDO_USERS:
        if uid != OWNER_ID:
            text += f"• `{uid}`\n"
    await reply_msg(msg, text)

# ---- Theme ----
THEMES = {
    "goku": {"name": "🟠 Goku - Kamehameha!", "bio": "I am Goku! I love fighting!"},
    "vegeta": {"name": "🟣 Vegeta - Prince of Saiyans!", "bio": "I am the Prince of all Saiyans!"},
    "broly": {"name": "💚 Broly - Legendary Super Saiyan!", "bio": "KAKAROT!"},
    "gohan": {"name": "🧡 Gohan - Beast Mode!", "bio": "I will protect my friends!"},
    "trunks": {"name": "⚔️ Trunks - Future Warrior!", "bio": "I will protect the future!"},
    "reset": {"name": "🐉 Dragon Ball Z: Ki Ling Engine V3", "bio": "Powered by Z-Fighters"},
}

@guard
@owner_only
async def cmd_settheme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -settheme <name>\nOptions: goku, vegeta, broly, gohan, trunks, reset")
        return
    cmd = args[0].lower()
    if cmd == "list":
        text = "🎨 Themes:\n" + "\n".join([f"• {k}" for k in THEMES])
        await reply_msg(msg, text)
        return
    if cmd in THEMES:
        theme = THEMES[cmd]
        try:
            await context.bot.set_my_name(theme["name"])
            await context.bot.set_my_bio(theme["bio"])
            await reply_msg(msg, f"✅ Theme changed to: {cmd.upper()}")
        except Exception as e:
            await reply_msg(msg, f"❌ Failed: {e}")
    else:
        await reply_msg(msg, f"❌ Theme '{cmd}' not found")

# ---- Form change (profile pic) ----
@guard
async def cmd_formchange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await reply_msg(msg, "❌ `-formchange` disabled (unstable).\nUse `-settheme goku/vegeta/...` instead.")
    return
    rep = msg.reply_to_message
    if not rep:
        await reply_msg(msg, "📷 Photo pe **reply** karke likho:\n`-formchange`")
        return
    file_id = None
    if rep.photo:
        file_id = rep.photo[-1].file_id
    elif rep.document and (rep.document.mime_type or "").startswith("image/"):
        file_id = rep.document.file_id
    elif getattr(rep, "sticker", None) and not getattr(rep.sticker, "is_animated", False) and not getattr(rep.sticker, "is_video", False):
        file_id = rep.sticker.file_id
    if not file_id:
        await reply_msg(msg, "❌ Sirf photo / image file pe reply karo.\n`-formchange`")
        return
    status = await msg.reply_text("🔄 Bot profile photo update ho raha hai...")
    tmp = None
    try:
        tg_file = await context.bot.get_file(file_id)
        tmp = f"temp_pfp_{int(time.time())}_{msg.from_user.id if msg.from_user else 0}.jpg"
        try:
            await tg_file.download_to_drive(custom_path=tmp)
        except TypeError:
            try:
                await tg_file.download_to_drive(tmp)
            except Exception:
                data = await tg_file.download_as_bytearray()
                with open(tmp, "wb") as f:
                    f.write(data)
        except Exception:
            data = await tg_file.download_as_bytearray()
            with open(tmp, "wb") as f:
                f.write(data)
        if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
            await status.edit_text("❌ Download failed / empty file")
            return
        ok = 0; fail = 0; errors = []
        bot_list = bots() or [context.bot]
        for bot in bot_list:
            try:
                with open(tmp, "rb") as f:
                    await bot.set_my_photo(photo=f)
                ok += 1
            except RetryAfter as e:
                fail += 1
                errors.append(f"Flood wait {getattr(e, 'retry_after', '?')}s")
                await asyncio.sleep(float(getattr(e, "retry_after", 1)) + 0.5)
            except Exception as e:
                fail += 1
                errors.append(str(e)[:100])
            await asyncio.sleep(0.4)
        err_txt = ("\n" + "\n".join(errors[:4])) if errors else ""
        await status.edit_text(
            f"✅ Form change done!\n"
            f"🟢 Success: {ok}\n"
            f"🔴 Failed: {fail}{err_txt}"
        )
    except Exception as e:
        try:
            await status.edit_text(f"❌ Failed: {e}")
        except Exception:
            await reply_msg(msg, f"❌ Failed: {e}")
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

# ---- GC Create, Link, GoFighters ----
@guard
@owner_only
async def cmd_creategc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    name = " ".join(args) if args else f"🐉 Group {random.randint(100,999)}"
    try:
        chat = await context.bot.create_group(title=name, users=[OWNER_ID])
        cid = chat.id
        created_groups[str(cid)] = {"title": name, "created_at": time.time(), "link": None}
        try:
            link = await context.bot.export_chat_invite_link(cid)
            created_groups[str(cid)]["link"] = link
        except:
            link = "❌ Link not generated"
        await reply_msg(msg, f"✅ Group Created!\n📛 {name}\n🆔 {cid}\n🔗 {link}")
        for bot in bots():
            try:
                if bot.id != context.bot.id:
                    await bot.send_message(cid, "🐉 Z-Fighter joined!")
            except:
                pass
    except Exception as e:
        await reply_msg(msg, f"❌ Failed: {e}")

@guard
async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    cid = msg.chat_id
    if str(cid) in created_groups and created_groups[str(cid)].get("link"):
        await reply_msg(msg, f"🔗 Link: {created_groups[str(cid)]['link']}")
        return
    try:
        link = await context.bot.export_chat_invite_link(cid)
        created_groups[str(cid)] = created_groups.get(str(cid), {})
        created_groups[str(cid)]["link"] = link
        await reply_msg(msg, f"🔗 Link: {link}")
    except Exception as e:
        await reply_msg(msg, f"❌ Failed: {e}")

@guard
async def cmd_gofighters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    link = None
    if msg.reply_to_message and msg.reply_to_message.text:
        for w in msg.reply_to_message.text.split():
            if "t.me/" in w:
                link = w
                break
    if not link:
        args = get_args(context)
        if args:
            for a in args:
                if "t.me/" in a:
                    link = a
                    break
            if not link and args:
                link = args[0]
    if not link:
        await reply_msg(msg, "Reply to a link or provide one!")
        return
    if "t.me/" in link:
        link = link.split("t.me/")[-1]
    if link.startswith("+"): link = link[1:]
    if link.startswith("@"): link = link[1:]
    await reply_msg(msg, f"⚔️ Adding bots to: {link}")
    success = 0
    for bot in bots():
        try:
            await bot.join_chat(link)
            success += 1
            await asyncio.sleep(0.3)
        except:
            pass
    await reply_msg(msg, f"⚔️ Added {success}/{len(bots())} bots.")

# ---- PFP commands ----
@guard
async def cmd_addpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.photo:
        await reply_msg(msg, "Reply to a photo with -addpfp")
        return
    fid = msg.reply_to_message.photo[-1].file_id
    key = str(msg.chat_id)
    if key not in _pfp_pools:
        _pfp_pools[key] = []
    if fid not in _pfp_pools[key]:
        _pfp_pools[key].append(fid)
        save_pfp()
    await reply_msg(msg, f"✅ Photo added. Pool size: {len(_pfp_pools[key])}")

@guard
async def cmd_pfploop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    key = str(msg.chat_id)
    pool = _pfp_pools.get(key, [])
    if not pool:
        await reply_msg(msg, "No PFPs in pool. Use -addpfp")
        return
    args = get_args(context)
    delay = float(args[0]) if args and args[0].replace('.','').isdigit() else 3.0
    delay = max(1.0, delay)
    pfploop_active[msg.chat_id] = True
    cid = msg.chat_id
    async def _run(stop_ev):
        idx = 0
        while not stop_ev.is_set():
            fid = pool[idx % len(pool)]
            idx += 1
            try:
                await context.bot.set_chat_photo(cid, fid)
            except:
                pass
            for _ in range(int(delay)):
                if stop_ev.is_set():
                    break
                await asyncio.sleep(1)
            if stop_ev.is_set():
                break
        pfploop_active.pop(cid, None)
    await tc.start(cid, "pfp", _run)
    await reply_msg(msg, f"🔄 PFP loop started ({len(pool)} photos, {delay}s)")

@guard
async def cmd_stoppfploop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await tc.stop(msg.chat_id, "pfp")
    pfploop_active.pop(msg.chat_id, None)
    await reply_msg(msg, "⛔ PFP loop stopped")

@guard
async def cmd_pfppool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    pool = _pfp_pools.get(str(msg.chat_id), [])
    await reply_msg(msg, f"📸 PFP pool size: {len(pool)}")

@guard
async def cmd_clearpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    _pfp_pools.pop(str(msg.chat_id), None)
    save_pfp()
    await reply_msg(msg, "🧹 PFP pool cleared")

@guard
async def cmd_setpfponce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.photo:
        await reply_msg(msg, "Reply to a photo with -setpfponce")
        return
    fid = msg.reply_to_message.photo[-1].file_id
    try:
        await context.bot.set_chat_photo(msg.chat_id, fid)
        await reply_msg(msg, "✅ Group photo updated")
    except Exception as e:
        await reply_msg(msg, f"❌ Failed: {e}")

@guard
async def cmd_deletegcpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    try:
        await context.bot.delete_chat_photo(msg.chat_id)
        await reply_msg(msg, "✅ Group photo removed")
    except Exception as e:
        await reply_msg(msg, f"❌ Failed: {e}")

async def gc_photo_changer_loop(chat_id):
    bot_list = bots()
    if not bot_list:
        return
    bot_index = 0
    delay = max(float(_nc_send_gap) if _nc_send_gap else 0.08, 0.05)
    while True:
        try:
            if not os.path.exists(SAVED_PHOTO_PATH):
                break
            current_bot = bot_list[bot_index % len(bot_list)]
            bot_index += 1
            with open(SAVED_PHOTO_PATH, "rb") as photo_file:
                await current_bot.set_chat_photo(chat_id=chat_id, photo=photo_file)
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 1)) + 0.3)
        except Exception:
            await asyncio.sleep(0.5)

@guard
async def cmd_photosave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message or not msg.reply_to_message.photo:
        await reply_msg(msg, "❌ Reply to an image with `-photosave`")
        return
    status = await msg.reply_text("📥 Downloading photo...")
    try:
        photo_file = await msg.reply_to_message.photo[-1].get_file()
        await photo_file.download_to_drive(SAVED_PHOTO_PATH)
        await status.edit_text("✅ Photo saved! Ab group me `-setgc` se loop start karo.")
    except Exception as e:
        try:
            await status.edit_text(f"❌ Download failed: {e}")
        except Exception:
            await reply_msg(msg, f"❌ Download failed: {e}")

@guard
async def cmd_setgc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    chat_id = msg.chat_id
    if not os.path.exists(SAVED_PHOTO_PATH):
        await reply_msg(msg, "❌ Pehle `-photosave` se photo save karo (reply to image).")
        return
    if chat_id in pfp_tasks:
        t = pfp_tasks.pop(chat_id)
        if t and not t.done():
            t.cancel()
    task = asyncio.create_task(gc_photo_changer_loop(chat_id))
    pfp_tasks[chat_id] = task
    n = len(bots())
    await reply_msg(msg, f"🖼️ **GC Photo Changer ON**\nMulti-bot loop active (`{n}` bots)\nStop: `-stopgc`")

@guard
async def cmd_stopgc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    chat_id = msg.chat_id
    if chat_id in pfp_tasks:
        t = pfp_tasks.pop(chat_id)
        if t and not t.done():
            t.cancel()
        await reply_msg(msg, "⛔ GC Photo Changer stopped.")
    else:
        await reply_msg(msg, "❌ No GC photo loop running here.")

# ---- GC Manage ----
@guard
async def cmd_gcinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    chat = await context.bot.get_chat(msg.chat_id)
    count = await context.bot.get_chat_member_count(msg.chat_id)
    await reply_msg(msg, f"📋 Info:\nTitle: {chat.title}\nID: {chat.id}\nMembers: {count}")

@guard
async def cmd_setgctitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -setgctitle <title>")
        return
    await context.bot.set_chat_title(msg.chat_id, txt)
    await reply_msg(msg, f"✅ Title set: {txt}")

@guard
async def cmd_setgcdesc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -setgcdesc <text>")
        return
    await context.bot.set_chat_description(msg.chat_id, txt)
    await reply_msg(msg, "✅ Description set")

@guard
async def cmd_getinvite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    try:
        link = await context.bot.export_chat_invite_link(msg.chat_id)
        await reply_msg(msg, f"🔗 {link}")
    except Exception as e:
        await reply_msg(msg, f"❌ Failed: {e}")

@guard
async def cmd_pinmsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message to pin")
        return
    await context.bot.pin_chat_message(msg.chat_id, msg.reply_to_message.message_id)
    await reply_msg(msg, "📌 Pinned!")

@guard
async def cmd_unpinall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await context.bot.unpin_all_chat_messages(msg.chat_id)
    await reply_msg(msg, "📌 Unpinned all")

@guard
async def cmd_kickuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -kickuser <id>")
        return
    uid = int(args[0])
    await context.bot.ban_chat_member(msg.chat_id, uid)
    await context.bot.unban_chat_member(msg.chat_id, uid)
    await reply_msg(msg, f"👢 Kicked {uid}")

@guard
async def cmd_bantarget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -bantarget <id>")
        return
    uid = int(args[0])
    await context.bot.ban_chat_member(msg.chat_id, uid)
    await reply_msg(msg, f"🚫 Banned {uid}")

@guard
async def cmd_unbanuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -unbanuser <id>")
        return
    uid = int(args[0])
    await context.bot.unban_chat_member(msg.chat_id, uid)
    await reply_msg(msg, f"✅ Unbanned {uid}")

@guard
async def cmd_muteuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -muteuser <id>")
        return
    uid = int(args[0])
    perms = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(msg.chat_id, uid, permissions=perms)
    await reply_msg(msg, f"🔇 Muted {uid}")

@guard
async def cmd_unmuteuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -unmuteuser <id>")
        return
    uid = int(args[0])
    perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
    await context.bot.restrict_chat_member(msg.chat_id, uid, permissions=perms)
    await reply_msg(msg, f"🔊 Unmuted {uid}")

# ---- Templates ----
@guard
async def cmd_addtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -addtemplate <name> <template>")
        return
    name = args[0]
    tmpl = " ".join(args[1:])
    custom_templates[name] = tmpl
    save_templates()
    await reply_msg(msg, f"✅ Template '{name}' saved")

@guard
async def cmd_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    if not custom_templates:
        await reply_msg(msg, "No templates saved")
        return
    text = "📝 Templates:\n" + "\n".join([f"• {k}: {v[:30]}..." for k, v in custom_templates.items()])
    await reply_msg(msg, text)

@guard
async def cmd_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -preview <name> <text>")
        return
    name = args[0]
    txt = " ".join(args[1:])
    if name not in custom_templates:
        await reply_msg(msg, f"Template '{name}' not found")
        return
    tmpl = custom_templates[name]
    sample = tmpl.replace("{text}", txt).replace("{t}", txt).replace("{w}", "LUND").replace("{e}", "🔥").replace("{n}", "1").replace("{wl}", "꧁").replace("{wr}", "꧂")
    await reply_msg(msg, f"🔍 Preview:\n{sample}")

@guard
async def cmd_deltemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args:
        await reply_msg(msg, "Usage: -deltemplate <name>")
        return
    name = args[0]
    if name in custom_templates:
        del custom_templates[name]
        save_templates()
        await reply_msg(msg, f"🗑️ Deleted '{name}'")
    else:
        await reply_msg(msg, f"Template '{name}' not found")

@guard
async def cmd_cleartemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    custom_templates.clear()
    save_templates()
    await reply_msg(msg, "🧹 All templates cleared")

@guard
async def cmd_customnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -customnc <name> <text>")
        return
    name = args[0]
    txt = " ".join(args[1:])
    if name not in custom_templates:
        await reply_msg(msg, f"Template '{name}' not found")
        return
    tmpl = custom_templates[name]
    def factory():
        return tmpl.replace("{text}", txt).replace("{t}", txt).replace("{w}", random.choice(_CHUD_WORDS)).replace("{e}", rnd_emoji()).replace("{n}", str(random.randint(1,100))).replace("{wl}", random.choice(WRAP_L)).replace("{wr}", random.choice(WRAP_R))
    await start_nc_abusing(msg, msg.chat_id, txt, "goku", custom_factory=factory)

# ---- Bot Control ----
@guard
async def cmd_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    text = "🤖 Active bots:\n"
    for b in bots():
        text += f"• @{getattr(b, 'username', 'unknown')}\n"
    await reply_msg(msg, text)

@guard
async def cmd_addbot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    await reply_msg(msg, "✅ Bot added (placeholder - use -addtoken)")

@guard
async def cmd_addallbots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_addbot(update, context)

@guard
async def cmd_promotebot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """-promotebot → group mein saare bots ko FULL admin rights."""
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    ok, fail = [], []
    full_rights = dict(
        can_manage_chat=True,
        can_change_info=True,          # NC / title ke liye zaroori
        can_delete_messages=True,
        can_invite_users=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_promote_members=True,
        can_manage_video_chats=True,
        is_anonymous=False,
    )
    for bot in bots():
        try:
            await context.bot.promote_chat_member(cid, bot.id, **full_rights)
            ok.append(getattr(bot, "username", None) or str(bot.id))
        except Exception as e:
            fail.append(f"{getattr(bot, 'username', bot.id)}: {type(e).__name__}")
    text = f"✅ **Promoted {len(ok)} bots** (full rights)\n"
    if ok:
        text += "• " + ", ".join(f"@{u}" if not str(u).isdigit() else u for u in ok[:12])
        if len(ok) > 12:
            text += f" …+{len(ok)-12}"
    if fail:
        text += f"\n\n⚠️ Failed {len(fail)}:\n" + "\n".join(f"• {x}" for x in fail[:8])
        text += "\n_(Command wala bot khud admin + Add new admins hona chahiye)_"
    await reply_msg(msg, text)

@guard
async def cmd_botname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saare bots ka display name change (Bot API setMyName)."""
    msg = update.message or update.edited_message
    if not msg:
        return
    name = txt_arg(context)
    if not name:
        await reply_msg(msg, "Usage: `-botname <name>`\nMax ~64 chars")
        return
    name = name[:64]
    ok, fail = 0, []
    for app in all_apps:
        b = app.bot
        uname = getattr(b, "username", None) or str(getattr(b, "id", "?"))
        try:
            await b.set_my_name(name)
            ok += 1
        except Exception as e:
            fail.append(f"@{uname}: {type(e).__name__}")
    text = f"✅ **Name** → `{name}`\nSuccess: `{ok}/{len(all_apps)}`"
    if fail:
        text += "\n⚠️ " + "; ".join(fail[:5])
    await reply_msg(msg, text)


@guard
async def cmd_botbio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Saare bots ki bio / description change.
    -botbio <text>           → about (description)
    -botbio short <text>     → short description (chat list preview)
    """
    msg = update.message or update.edited_message
    if not msg:
        return
    raw = txt_arg(context)
    if not raw:
        await reply_msg(msg,
            "Usage:\n"
            "`-botbio <text>` — full description (max 512)\n"
            "`-botbio short <text>` — short desc (max 120)"
        )
        return

    parts = raw.split(maxsplit=1)
    mode = "full"
    text = raw
    if parts[0].lower() == "short":
        mode = "short"
        text = parts[1] if len(parts) > 1 else ""
        if not text:
            await reply_msg(msg, "Usage: `-botbio short <text>`")
            return

    ok, fail = 0, []
    for app in all_apps:
        b = app.bot
        uname = getattr(b, "username", None) or str(getattr(b, "id", "?"))
        try:
            if mode == "short":
                # PTB: set_my_short_description
                await b.set_my_short_description(text[:120])
            else:
                await b.set_my_description(text[:512])
            ok += 1
        except AttributeError:
            fail.append(f"@{uname}: API unsupported")
        except Exception as e:
            fail.append(f"@{uname}: {type(e).__name__}")

    label = "Short bio" if mode == "short" else "Bio"
    out = f"✅ **{label}** set\nSuccess: `{ok}/{len(all_apps)}`\n_{text[:80]}{'…' if len(text) > 80 else ''}_"
    if fail:
        out += "\n⚠️ " + "; ".join(fail[:6])
    await reply_msg(msg, out)


@guard
async def cmd_botinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List bots with id/username — useful check after name/bio change."""
    msg = update.message or update.edited_message
    if not msg:
        return
    lines = ["🤖 **Bot info**\n"]
    for b in bots():
        uname = getattr(b, "username", None) or "—"
        bid = getattr(b, "id", "?")
        lines.append(f"• @{uname} (`{bid}`)")
    lines.append(f"\nTotal: `{len(bots())}`")
    lines.append("Cmds: `-botname` · `-botbio` · `-botbio short`")
    await reply_msg(msg, "\n".join(lines))

# ---- MGC ----
async def _mgcnc_engine(chats, bot_list, stop_event, factory):
    while not stop_event.is_set():
        for cid in chats:
            if stop_event.is_set():
                break
            for bot in bot_list:
                try:
                    await bot.send_message(cid, factory())
                    await asyncio.sleep(0.1)
                except:
                    pass
        await asyncio.sleep(0.5)

async def _start_mgcnc(msg, factory, label):
    global _mgcnc_stop, _mgcnc_task, _mgcnc_targets
    targets = list(known_chats)
    if not targets:
        await reply_msg(msg, "No known groups.")
        return
    if _mgcnc_stop and not _mgcnc_stop.is_set():
        _mgcnc_stop.set()
    if _mgcnc_task and not _mgcnc_task.done():
        _mgcnc_task.cancel()
    _mgcnc_targets = targets
    _mgcnc_stop = asyncio.Event()
    _mgcnc_task = asyncio.create_task(_mgcnc_engine(targets, bots(), _mgcnc_stop, factory))
    await reply_msg(msg, f"🌐 MGC started on {len(targets)} groups ({label})")

@guard
async def cmd_mgcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgcnc <text>")
        return
    def f(): return f"🐉 {txt} {rnd_suffix()}"
    await _start_mgcnc(msg, f, "Basic")

@guard
async def cmd_mgchakai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgchakai <text>")
        return
    def f(): return f"💥 {txt} 𒐫 {random.choice(_CHUD_WORDS)}"
    await _start_mgcnc(msg, f, "Hakai")

@guard
async def cmd_mgcbold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgcbold <text>")
        return
    def f(): return f"**{txt}** {rnd_suffix()}"
    await _start_mgcnc(msg, f, "Bold")

@guard
async def cmd_mgcfire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgcfire <text>")
        return
    def f(): return f"🔥 {txt} 🔥"
    await _start_mgcnc(msg, f, "Fire")

@guard
async def cmd_mgcwar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgcwar <text>")
        return
    def f(): return f"⚔️ {txt} ⚔️"
    await _start_mgcnc(msg, f, "War")

@guard
async def cmd_mgcsurge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -mgcsurge <text>")
        return
    def f(): return f"⚡ {txt} ⚡"
    await _start_mgcnc(msg, f, "Surge")

@guard
async def cmd_mgccustom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -mgccustom <name> <text>")
        return
    name = args[0]
    txt = " ".join(args[1:])
    if name not in custom_templates:
        await reply_msg(msg, f"Template '{name}' not found")
        return
    tmpl = custom_templates[name]
    def f():
        return tmpl.replace("{text}", txt).replace("{t}", txt).replace("{w}", random.choice(_CHUD_WORDS)).replace("{e}", rnd_emoji()).replace("{n}", str(random.randint(1,100))).replace("{wl}", random.choice(WRAP_L)).replace("{wr}", random.choice(WRAP_R))
    await _start_mgcnc(msg, f, f"Custom {name}")

@guard
async def cmd_stopmgcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _mgcnc_stop, _mgcnc_task
    msg = update.message or update.edited_message
    if not msg: return
    if _mgcnc_stop:
        _mgcnc_stop.set()
    if _mgcnc_task and not _mgcnc_task.done():
        _mgcnc_task.cancel()
    await reply_msg(msg, "⛔ MGC stopped")

@guard
async def cmd_mgcstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    running = bool(_mgcnc_task and not _mgcnc_task.done())
    await reply_msg(msg, f"🌐 MGC Status: {'🟢 Running' if running else '🔴 Stopped'}")

# ---- War / Mute ----
@guard
async def cmd_multiwar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -multiwar <text>")
        return
    targets = list(known_chats)
    for cid in targets:
        await start_nc_abusing(msg, cid, txt, "goku")
        _multiwar_active[cid] = True
    await reply_msg(msg, f"⚔️ Multiwar started on {len(targets)} groups")

@guard
async def cmd_stopmultiwar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    for cid in list(_multiwar_active.keys()):
        await tc.stop(cid, "nc")
        _multiwar_active.pop(cid, None)
    await reply_msg(msg, "⛔ Multiwar stopped")

@guard
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    mute_chats.add(msg.chat_id)
    await context.bot.set_chat_permissions(msg.chat_id, ChatPermissions(can_send_messages=False))
    await reply_msg(msg, "🔇 Chat muted")

@guard
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    mute_chats.discard(msg.chat_id)
    perms = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
    await context.bot.set_chat_permissions(msg.chat_id, perms)
    await reply_msg(msg, "🔊 Chat unmuted")

# ---- Purge ----
@guard
async def cmd_purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.reply_to_message:
        await reply_msg(msg, "Reply to a message to purge")
        return
    cid = msg.chat_id
    start = msg.reply_to_message.message_id
    end = msg.message_id
    deleted = 0
    for mid in range(start, end+1):
        try:
            await context.bot.delete_message(cid, mid)
            deleted += 1
        except:
            pass
    await reply_msg(msg, f"🧹 Purged {deleted} messages")

@guard
async def cmd_purgeme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    cid = msg.chat_id
    deleted = 0
    for mid in range(max(1, msg.message_id-100), msg.message_id):
        try:
            await context.bot.delete_message(cid, mid)
            deleted += 1
        except:
            pass
    await reply_msg(msg, f"🧹 Purged {deleted} of your messages")

@guard
async def cmd_purgebot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    cid = msg.chat_id
    deleted = 0
    for bot in bots():
        for mid in range(max(1, msg.message_id-200), msg.message_id):
            try:
                await bot.delete_message(cid, mid)
                deleted += 1
            except:
                pass
    await reply_msg(msg, f"🧹 Purged {deleted} bot messages")

@guard
async def cmd_purgeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    cid = msg.chat_id
    deleted = 0
    for mid in range(max(1, msg.message_id-500), msg.message_id):
        try:
            await context.bot.delete_message(cid, mid)
            deleted += 1
        except:
            pass
    await reply_msg(msg, f"🧹 Purged {deleted} messages")

# ---- Tools ----
@guard
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    nc = tc.running(msg.chat_id, "nc")
    await reply_msg(msg, f"📊 Status:\nNC: {'✅' if nc else '❌'}\nBots: {len(bots())}\nDelay: {(_nc_send_gap if _nc_send_gap is not None else 0.05):.4f}s")

@guard
async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    elapsed = time.monotonic() - BOT_START_TIME
    h, rem = divmod(int(elapsed), 3600)
    m, s = divmod(rem, 60)
    await reply_msg(msg, f"⏱️ Uptime: {h}h {m}m {s}s")

@guard
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    t0 = time.monotonic()
    sent = await msg.reply_text("🏓")
    ms = int((time.monotonic() - t0) * 1000)
    await sent.edit_text(f"🏓 Pong! {ms}ms")

@guard
async def cmd_floodstat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    lines = ["⚡ *Flood Bypass Status*\n"]
    bot_list = bots()
    if not bot_list:
        await reply_msg(msg, "No bots online.")
        return
    for b in bot_list:
        bid = getattr(b, "id", 0)
        uname = getattr(b, "username", str(bid))
        flooded = _ft.flooded(bid)
        rem = _ft.remaining(bid)
        rate = _ft.rate(bid)
        status = f"🔴 FLOOD {rem:.1f}s" if flooded else "🟢 OK"
        lines.append(f"• `@{uname}` — {status} | rate `{rate}`/min")
    gap_txt = f"{_nc_send_gap:.3f}s" if _nc_send_gap is not None else "default 0.05"
    lines.append(f"\nBase gap: `{gap_txt}`")
    await reply_msg(msg, "\n".join(lines))


# ========== EXTRA FEATURES (no games) ==========
@guard
async def cmd_alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    elapsed = int(time.monotonic() - BOT_START_TIME)
    h, rem = divmod(elapsed, 3600)
    m, s = divmod(rem, 60)
    n_bots = len(bots())
    n_tasks = sum(1 for k in tc.tasks if not tc.tasks[k].done())
    wl = f"{len(nc_whitelist)} chats" if nc_whitelist else "OFF (all allowed)"
    await reply_msg(msg,
        f"🐉 **ARTHUR / DBZ ALIVE**\n"
        f"⏱ Uptime: `{h}h {m}m {s}s`\n"
        f"🤖 Bots: `{n_bots}`\n"
        f"⚙️ Active tasks: `{n_tasks}`\n"
        f"📁 Groups known: `{len(known_chats)}`\n"
        f"🚀 Gap: `{_nc_send_gap or 0.12:.3f}s`\n"
        f"🛡 NC whitelist: {wl}\n"
        f"👑 Owner: `{OWNER_ID}`"
    )


@guard
async def cmd_ncstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    lines = ["📡 **NC Status**\n"]
    found = False
    for k, task in list(tc.tasks.items()):
        if "::nc" in k and not task.done():
            found = True
            cid = k.split("::")[0]
            lines.append(f"• Chat `{cid}` — 🟢 RUNNING")
    if not found:
        lines.append("No NC running.")
    lines.append(f"\nBots online: `{len(bots())}`")
    lines.append(f"This chat NC: `{'ON' if tc.running(msg.chat_id, 'nc') else 'OFF'}`")
    await reply_msg(msg, "\n".join(lines))


@guard
async def cmd_admincheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check which bots have Change Info in this group."""
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    lines = ["🔍 **Admin / Change-Info check**\n"]
    ok_n = 0
    for bot in bots():
        uname = getattr(bot, "username", None) or str(bot.id)
        try:
            m = await bot.get_chat_member(cid, bot.id)
            status = getattr(m, "status", "")
            # PTB v20 ChatMemberAdministrator
            can_info = getattr(m, "can_change_info", None)
            if status in ("administrator", "creator"):
                if can_info is False:
                    lines.append(f"• @{uname} — admin ❌ no Change Info")
                else:
                    lines.append(f"• @{uname} — ✅ admin + Change Info")
                    ok_n += 1
            else:
                lines.append(f"• @{uname} — ❌ not admin ({status})")
        except Exception as e:
            lines.append(f"• @{uname} — ⚠️ {type(e).__name__}")
    lines.append(f"\n**Ready for NC:** `{ok_n}/{len(bots())}`")
    await reply_msg(msg, "\n".join(lines))


@guard
async def cmd_promoteall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Promote all bots in every known group (best-effort)."""
    msg = update.message or update.edited_message
    if not msg:
        return
    if not known_chats:
        await reply_msg(msg, "No known groups. Use bots in groups first.")
        return
    full_rights = dict(
        can_manage_chat=True,
        can_change_info=True,
        can_delete_messages=True,
        can_invite_users=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_promote_members=True,
        can_manage_video_chats=True,
        is_anonymous=False,
    )
    status = await msg.reply_text(f"⏳ Promoting in {len(known_chats)} groups...")
    total_ok = 0
    for cid in list(known_chats):
        for bot in bots():
            try:
                await context.bot.promote_chat_member(cid, bot.id, **full_rights)
                total_ok += 1
            except Exception:
                pass
        await asyncio.sleep(0.15)
    try:
        await status.edit_text(f"✅ Promote-all done. Success calls: `{total_ok}`\n(Groups: {len(known_chats)}, Bots: {len(bots())})")
    except Exception:
        await reply_msg(msg, f"✅ Promote-all done. Success: `{total_ok}`")


@guard
async def cmd_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """-whitelist on|off|add|del|list — NC only in listed chats when ON."""
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args:
        state = "ON" if nc_whitelist else "OFF (all chats)"
        await reply_msg(msg,
            f"🛡 Whitelist: **{state}**\n"
            f"Chats: `{len(nc_whitelist)}`\n"
            f"Usage:\n"
            f"`-whitelist add` — is chat add\n"
            f"`-whitelist del` — is chat hatao\n"
            f"`-whitelist list`\n"
            f"`-whitelist clear` — sab hatao (all chats allowed)"
        )
        return
    cmd = args[0].lower()
    cid = msg.chat_id
    if cmd == "add":
        nc_whitelist.add(cid)
        save_whitelist()
        await reply_msg(msg, f"✅ Whitelist add: `{cid}`")
    elif cmd in ("del", "remove", "rm"):
        nc_whitelist.discard(cid)
        save_whitelist()
        await reply_msg(msg, f"✅ Whitelist se hata: `{cid}`")
    elif cmd == "list":
        if not nc_whitelist:
            await reply_msg(msg, "Empty whitelist (NC sab chats pe chal sakta).")
        else:
            await reply_msg(msg, "🛡 **Whitelist:**\n" + "\n".join(f"• `{c}`" for c in nc_whitelist))
    elif cmd == "clear":
        nc_whitelist.clear()
        save_whitelist()
        await reply_msg(msg, "✅ Whitelist clear — sab chats allowed")
    else:
        await reply_msg(msg, "Usage: `-whitelist add|del|list|clear`")


@guard
async def cmd_chatdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Per-chat NC gap: -chatdelay 0.15"""
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    key = str(msg.chat_id)
    if not args:
        cur = chat_delays.get(key)
        await reply_msg(msg,
            f"This chat delay: `{cur if cur is not None else 'global ' + str(_nc_send_gap)}`\n"
            f"Usage: `-chatdelay 0.12` | `-chatdelay reset`"
        )
        return
    if args[0].lower() in ("reset", "off", "clear"):
        chat_delays.pop(key, None)
        save_chat_delays()
        await reply_msg(msg, "✅ Chat delay reset (global use hoga)")
        return
    try:
        val = float(args[0])
        if val < 0.05 or val > 10:
            await reply_msg(msg, "0.05 – 10.0 only")
            return
        chat_delays[key] = val
        save_chat_delays()
        await reply_msg(msg, f"✅ This chat NC gap = `{val:.3f}s`")
    except ValueError:
        await reply_msg(msg, "Usage: `-chatdelay 0.12`")


@guard
async def cmd_tagall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mention members (max 40) — rate limited."""
    msg = update.message or update.edited_message
    if not msg:
        return
    text = txt_arg(context) or "🔔 Tag"
    try:
        admins = await context.bot.get_chat_administrators(msg.chat_id)
    except Exception as e:
        await reply_msg(msg, f"❌ {e}")
        return
    mentions = []
    for a in admins[:40]:
        u = a.user
        if u.is_bot:
            continue
        if u.username:
            mentions.append(f"@{u.username}")
        else:
            mentions.append(f'<a href="tg://user?id={u.id}">{u.first_name or "user"}</a>')
    if not mentions:
        await reply_msg(msg, "No members to tag (admin list empty).")
        return
    # chunk
    for i in range(0, len(mentions), 8):
        chunk = " ".join(mentions[i:i + 8])
        try:
            await msg.reply_text(f"{text}\n{chunk}", parse_mode="HTML")
        except Exception:
            await msg.reply_text(f"{text}\n{chunk}")
        await asyncio.sleep(0.35)
    await reply_msg(msg, f"✅ Tagged ~{len(mentions)} (admins)")


@guard
async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    try:
        perms = ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
        )
        await context.bot.set_chat_permissions(msg.chat_id, perms)
        await reply_msg(msg, "🔒 Chat locked")
    except Exception as e:
        await reply_msg(msg, f"❌ {e}")


@guard
async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    try:
        perms = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        await context.bot.set_chat_permissions(msg.chat_id, perms)
        await reply_msg(msg, "🔓 Chat unlocked")
    except Exception as e:
        await reply_msg(msg, f"❌ {e}")


@guard
async def cmd_safe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await reply_msg(msg, "Reply to user: `-safe`")
        return
    uid = msg.reply_to_message.from_user.id
    SAFE_USERS.add(uid)
    save_safe_users()
    await reply_msg(msg, f"🛡 Safe: `{uid}`")


@guard
async def cmd_unsafe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if not msg.reply_to_message or not msg.reply_to_message.from_user:
        await reply_msg(msg, "Reply to user: `-unsafe`")
        return
    uid = msg.reply_to_message.from_user.id
    SAFE_USERS.discard(uid)
    save_safe_users()
    await reply_msg(msg, f"✅ Unsafe (removed): `{uid}`")


@guard
async def cmd_antiraid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    cid = msg.chat_id
    if not args or args[0].lower() not in ("on", "off"):
        st = "ON" if cid in anti_raid_chats else "OFF"
        await reply_msg(msg, f"Anti-raid: **{st}**\nUsage: `-antiraid on|off`")
        return
    if args[0].lower() == "on":
        anti_raid_chats.add(cid)
        await reply_msg(msg, "🛡 Anti-raid ON (new joins muted 2 min — best-effort)")
    else:
        anti_raid_chats.discard(cid)
        await reply_msg(msg, "Anti-raid OFF")


# ---- Games ----
@guard
async def cmd_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    try:
        await msg.reply_dice(emoji="🎲")
    except Exception:
        num = random.randint(1, 6)
        faces = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        await reply_msg(msg, f"🎲 **DICE ROLL**\n\n{faces.get(num, '🎲')}  →  **{num}**")

@guard
async def cmd_rps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args or args[0].lower() not in ["rock", "paper", "scissors", "r", "p", "s"]:
        await reply_msg(msg, "⚔️ **Rock Paper Scissors**\n\nUsage: `-rps rock` / `paper` / `scissors`\n(ya short: r / p / s)")
        return
    mapping = {"r": "rock", "p": "paper", "s": "scissors"}
    u = mapping.get(args[0].lower(), args[0].lower())
    b = random.choice(["rock", "paper", "scissors"])
    e = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    if u == b:
        r = "🤝 **DRAW!** Equal power!"
    elif (u == "rock" and b == "scissors") or (u == "paper" and b == "rock") or (u == "scissors" and b == "paper"):
        r = "🎉 **YOU WIN!** Power level over 9000!"
    else:
        r = "💀 **YOU LOSE!** Train harder!"
    await reply_msg(
        msg,
        f"⚔️ **ROCK • PAPER • SCISSORS**\n\n"
        f"👤 You:   {e[u]}  **{u.upper()}**\n"
        f"🤖 Bot:   {e[b]}  **{b.upper()}**\n\n"
        f"{r}"
    )

@guard
async def cmd_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    slots = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🐉", "⚡"]
    res = [random.choice(slots) for _ in range(3)]
    line = " │ ".join(res)
    if res[0] == res[1] == res[2]:
        if res[0] == "7️⃣":
            r = "🎰💰 **MEGA JACKPOT!!!** 💰🎰"
        elif res[0] == "🐉":
            r = "🐉 **DRAGON JACKPOT!** Shenron is proud!"
        else:
            r = "🎉 **TRIPLE MATCH!** Nice!"
    elif res[0] == res[1] or res[1] == res[2] or res[0] == res[2]:
        r = "⭐ **DOUBLE!** Close one!"
    else:
        r = "💨 No match... try again!"
    await reply_msg(
        msg,
        f"🎰 **SLOT MACHINE** 🎰\n\n"
        f"╔══════════════╗\n"
        f"║  {line}  ║\n"
        f"╚══════════════╝\n\n"
        f"{r}"
    )

@guard
async def cmd_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args or not args[0].isdigit():
        await reply_msg(msg, "🎯 **Number Guess**\n\nUsage: `-guess <number>`\nRange: 1 - 100")
        return
    guess = int(args[0])
    if guess < 1 or guess > 100:
        await reply_msg(msg, "❌ 1 se 100 ke beech number daalo!")
        return
    target = random.randint(1, 100)
    diff = abs(guess - target)
    if guess == target:
        await reply_msg(msg, f"🎉🔥 **PERFECT!** Number was **{target}**!\nYou are a true Saiyan!")
    elif diff <= 5:
        await reply_msg(msg, f"😱 So close! You: **{guess}** | Answer: **{target}**\nAlmost Ultra Instinct!")
    elif guess < target:
        await reply_msg(msg, f"📈 Too low!\nYou: **{guess}** → Answer was higher (**{target}**)")
    else:
        await reply_msg(msg, f"📉 Too high!\nYou: **{guess}** → Answer was lower (**{target}**)")

@guard
async def cmd_trivia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    qs = [
        {"q": "Goku ka asli naam kya hai?", "a": "Kakarot"},
        {"q": "Kitne Dragon Balls hote hain?", "a": "7"},
        {"q": "Vegeta kaunse planet ka prince hai?", "a": "Planet Vegeta / Saiyan"},
        {"q": "Who is the God of Destruction of Universe 7?", "a": "Beerus"},
        {"q": "Gohan ka Beast form kis fight mein aaya?", "a": "Cell Max / Super Hero"},
        {"q": "Ultra Instinct pehli baar kis ke against dikha?", "a": "Jiren"},
        {"q": "Dragon Ball Super ka main villain (Tournament of Power) kaun tha?", "a": "Jiren"},
        {"q": "Who fused to become Gogeta?", "a": "Goku + Vegeta"},
    ]
    q = random.choice(qs)
    await reply_msg(
        msg,
        f"🧠 **DRAGON BALL TRIVIA** 🧠\n\n"
        f"❓ {q['q']}\n\n"
        f"💡 Answer: ||{q['a']}||\n"
        f"(spoiler pe click karke dekho)"
    )

# ---- Quests ----
QUESTS = [{"name": "Say Hi to 5 people", "reward": 10}, {"name": "Use 3 commands", "reward": 5}, {"name": "Send 10 messages", "reward": 15}]

@guard
async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    uid = str(msg.from_user.id)
    now = datetime.now().date()
    if uid not in quest_data:
        quest_data[uid] = {"last_claim": None, "streak": 0, "coins": 0, "quests": []}
    if quest_data[uid]["last_claim"] == str(now):
        await reply_msg(msg, "⏳ Already claimed today!")
        return
    base = random.randint(10,30)
    streak = quest_data[uid].get("streak", 0)
    bonus = streak * 2
    total = base + bonus
    quest_data[uid]["coins"] += total
    quest_data[uid]["streak"] = streak + 1
    quest_data[uid]["last_claim"] = str(now)
    q = random.choice(QUESTS)
    quest_data[uid]["quests"] = [q]
    save_quest_data()
    await reply_msg(msg, f"🎉 Daily claimed! +{total} coins (Streak: {streak+1})\nQuest: {q['name']}")

@guard
async def cmd_quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    uid = str(msg.from_user.id)
    if uid not in quest_data or not quest_data[uid].get("quests"):
        await reply_msg(msg, "No active quests.")
        return
    text = "📋 Quests:\n" + "\n".join([f"{i+1}. {q['name']}" for i, q in enumerate(quest_data[uid]["quests"])])
    await reply_msg(msg, text)

@guard
async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    uid = str(msg.from_user.id)
    s = quest_data.get(uid, {}).get("streak", 0)
    c = quest_data.get(uid, {}).get("coins", 0)
    await reply_msg(msg, f"🔥 Streak: {s} days\n💰 Coins: {c}")

@guard
async def cmd_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    uid = str(msg.from_user.id)
    if uid not in quest_data or not quest_data[uid].get("quests"):
        await reply_msg(msg, "No quests to claim!")
        return
    q = quest_data[uid]["quests"][0]
    reward = q["reward"]
    quest_data[uid]["coins"] += reward
    quest_data[uid]["quests"] = []
    save_quest_data()
    await reply_msg(msg, f"✅ Claimed {reward} coins!")

@guard
async def cmd_lb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    sorted_u = sorted(quest_data.items(), key=lambda x: x[1].get("coins",0), reverse=True)[:10]
    if not sorted_u:
        await reply_msg(msg, "No data yet!")
        return
    text = "🏆 Leaderboard:\n"
    for i, (uid, data) in enumerate(sorted_u, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <=3 else f"{i}."
        text += f"{medal} {uid[:8]} - 💰{data.get('coins',0)} 🔥{data.get('streak',0)}\n"
    await reply_msg(msg, text)

# ---- Music ----
async def _ytdlp_download_audio(query: str, out_dir: str):
    ytdlp = shutil.which("yt-dlp") or shutil.which("youtube-dl")
    if not ytdlp:
        return None, "yt-dlp not installed. Run: pip install yt-dlp"

    out_tmpl = str(Path(out_dir) / "%(title).80s.%(ext)s")

    cookies_file = os.getenv("YTDLP_COOKIES", "cookies.txt")
    cookie_args = []
    if os.path.isfile(cookies_file):
        cookie_args = ["--cookies", cookies_file]
    else:
        browser = os.getenv("YTDLP_BROWSER", "").strip().lower()
        if browser in ("chrome", "firefox", "edge", "brave", "chromium", "opera"):
            cookie_args = ["--cookies-from-browser", browser]

    cmd = [
        ytdlp,
        f"ytsearch1:{query}",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "128K",
        "--no-playlist",
        "--no-warnings",
        "-o", out_tmpl,
        "--max-filesize", "45M",
    ] + cookie_args

    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None, "Download timeout (120s)"
    except Exception as e:
        return None, str(e)

    files = sorted(Path(out_dir).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file() and f.suffix.lower() in {".mp3", ".m4a", ".webm", ".opus", ".ogg", ".wav"}]
    if not files:
        err = (proc.stderr or proc.stdout or "no file")[:300]
        cmd2 = [
            ytdlp,
            f"ytsearch1:{query}",
            "-f", "bestaudio/best",
            "--no-playlist",
            "--no-warnings",
            "-o", out_tmpl,
            "--max-filesize", "45M",
        ] + cookie_args
        try:
            proc2 = await asyncio.to_thread(
                subprocess.run, cmd2, capture_output=True, text=True, timeout=120
            )
        except Exception as e:
            return None, str(e)
        files = sorted(Path(out_dir).glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        files = [f for f in files if f.is_file()]
        if not files:
            return None, (proc2.stderr or err or "download failed")[:300]

    fp = files[0]
    title = fp.stem
    return str(fp), title

async def _ytdlp_search_info(query: str):
    ytdlp = shutil.which("yt-dlp") or shutil.which("youtube-dl")
    if not ytdlp:
        return None, "yt-dlp not installed", None
    cmd = [
        ytdlp,
        f"ytsearch1:{query}",
        "--skip-download",
        "--print", "%(title)s\t%(webpage_url)s\t%(id)s",
        "--no-warnings",
        "--no-playlist",
    ]
    cookies_file = os.getenv("YTDLP_COOKIES", "cookies.txt")
    if os.path.isfile(cookies_file):
        cmd.extend(["--cookies", cookies_file])
    try:
        proc = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True, timeout=40
        )
        line = (proc.stdout or "").strip().splitlines()
        if not line:
            return None, (proc.stderr or "no result")[:200], None
        parts = line[0].split("\t")
        if len(parts) >= 2:
            title = parts[0].strip() or query
            url = parts[1].strip()
            vid = parts[2].strip() if len(parts) > 2 else ""
            return title, url, vid
        return None, "parse failed", None
    except subprocess.TimeoutExpired:
        return None, "search timeout", None
    except Exception as e:
        return None, str(e)[:150], None

@guard
async def cmd_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    query = txt_arg(context)
    if not query:
        await reply_msg(msg, "🎵 Usage: `-song <song name>`")
        return
    status = await msg.reply_text(f"🔍 Searching: **{query}** ...")
    title, url, vid = await _ytdlp_search_info(query)
    if not url or url.startswith("yt-dlp") or "not installed" in str(url):
        from urllib.parse import quote
        q = quote(query)
        await status.edit_text(
            f"🎵 **{query}**\n\n"
            f"🔗 https://www.youtube.com/results?search_query={q}\n\n"
            f"_(Direct search — open & play)_"
        )
        return
    if title is None:
        from urllib.parse import quote
        q = quote(query)
        await status.edit_text(
            f"🎵 **{query}**\n\n"
            f"🔗 https://www.youtube.com/results?search_query={q}\n"
            f"_{url}_"
        )
        return
    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None
    text = (
        f"🎵 **{title}**\n\n"
        f"▶️ {url}\n\n"
        f"Search: `{query}`"
    )
    try:
        if thumb:
            await status.delete()
            await msg.reply_photo(photo=thumb, caption=text)
        else:
            await status.edit_text(text)
    except Exception:
        await status.edit_text(text)

@guard
async def cmd_play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await reply_msg(msg, "❌ `-play` disabled (yt-dlp / bot-check issues).\nUse `-song <name>` for YouTube search link.")
    return
    query = txt_arg(context)
    if not query:
        await reply_msg(msg, "🎵 Usage: `-play <song name>`\nYa: `-song <name>` (link only)")
        return

    status = await msg.reply_text(f"🔍 Searching & trying download: {query}")
    tmp = tempfile.mkdtemp(prefix="dbz_music_")
    try:
        path, title = await _ytdlp_download_audio(query, tmp)
        if path and os.path.isfile(path):
            size = os.path.getsize(path)
            if size <= 48 * 1024 * 1024:
                with open(path, "rb") as f:
                    await msg.reply_audio(
                        audio=f,
                        title=str(title)[:64],
                        performer="DBZ Music",
                        caption=f"🎵 {title}",
                    )
                try:
                    await status.delete()
                except Exception:
                    pass
                return
        t2, url, vid = await _ytdlp_search_info(query)
        if url and t2:
            await status.edit_text(
                f"🎵 **{t2}**\n\n"
                f"▶️ {url}\n\n"
                f"_(Download blocked — play on YouTube)_"
            )
        else:
            from urllib.parse import quote
            await status.edit_text(
                f"🎵 **{query}**\n"
                f"https://www.youtube.com/results?search_query={quote(query)}\n"
                f"_(Open link to play)_"
            )
    except Exception as e:
        try:
            await status.edit_text(f"❌ {e}\nUse `-song {query}` for link.")
        except Exception:
            pass
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass

@guard
async def cmd_lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    query = txt_arg(context)
    if not query:
        await reply_msg(msg, "Usage: `-lyrics <song name>`")
        return
    context.args = (query + " lyrics").split()
    await cmd_song(update, context)

@guard
async def cmd_randomsong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    songs = [
        "Dragon Ball Z Cha-La Head-Cha-La",
        "Ultra Instinct theme",
        "Dragon Ball Super Limit Breaker",
        "Goku ssj theme",
        "Vegeta theme orchestral",
        "Dragon Ball GT Dan Dan Kokoro",
    ]
    context.args = random.choice(songs).split()
    await cmd_song(update, context)

# ---- AI, Mood, Talk ----
MOOD_DESC = {"happy": "😊 Happy", "angry": "😡 Angry", "sad": "😢 Sad", "sassy": "😏 Sassy", "evil": "😈 Evil", "crazy": "🤪 Crazy", "jealous": "💔 Jealous"}
EMOTION_RESPONSES = {
    "happy": ["Heyyy! How are you? 😊", "I'm so happy to talk to you! 🥳"],
    "angry": ["EXCUSE ME?! 😡", "I'm about to lose my mind! 💢"],
    "sad": ["Life is meaningless... 😢", "Why does everyone leave me? 💔"],
    "sassy": ["Oh really? That's what you think? 😏", "I've seen better comebacks! 💅"],
    "evil": ["I WILL DESTROY THIS UNIVERSE! 😈", "Bow down to me! 👑"],
    "crazy": ["WOOOHOOOO! LET'S GO CRAZY! 🤪", "HAHAHAHA! I LOVE CHAOS!"],
    "jealous": ["Oh wow... must be nice being you... 😒", "I wish I was that lucky... 🥺"],
}

AI_SYSTEM_PROMPT = (
    "You are a fun Dragon Ball Super themed Telegram group bot. "
    "Reply short (1-3 lines), natural, in the same language the user uses (Hindi/English/Hinglish). "
    "Be witty, a bit savage if needed, never boring. No long essays."
)

async def call_ai_api(user_text: str, history: list | None = None) -> str:
    api_key = (
        os.getenv("XAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("AI_API_KEY")
        or XAI_API_KEY_DEFAULT
        or ""
    ).strip()
    if not api_key:
        return (
            "AI API key missing.\n"
            "Set env: XAI_API_KEY=...  (or OPENAI_API_KEY)\n"
            "Then restart bot."
        )
    if aiohttp is None:
        return "Install aiohttp: pip install aiohttp"

    base = (
        os.getenv("AI_API_BASE")
        or ("https://api.x.ai/v1" if (os.getenv("XAI_API_KEY") or api_key.startswith("xai-")) else "https://api.openai.com/v1")
    ).rstrip("/")
    model = os.getenv("AI_MODEL") or (
        "grok-4-1-fast-non-reasoning" if "x.ai" in base else "gpt-4o-mini"
    )

    messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
    if history:
        for h in history[-8:]:
            if isinstance(h, dict) and "role" in h and "content" in h:
                messages.append(h)
    messages.append({"role": "user", "content": user_text[:2000]})

    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 220,
    }
    try:
        timeout = aiohttp.ClientTimeout(total=45)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    err = data.get("error", data) if isinstance(data, dict) else data
                    err_str = str(err)[:180]
                    return f"❌ AI Error {resp.status}: {err_str}"
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                    or "..."
                )
    except Exception as e:
        return f"❌ AI request failed: {e}\n\n{get_ai_response(user_text)}"

def get_ai_response(user_msg):
    global bot_mood
    msg = (user_msg or "").lower()
    if "love" in msg or "like" in msg:
        bot_mood["mood"] = "happy"
    elif "hate" in msg or "stupid" in msg:
        bot_mood["mood"] = "angry"
    elif "cry" in msg or "sad" in msg:
        bot_mood["mood"] = "sad"
    elif "jealous" in msg or "lucky" in msg:
        bot_mood["mood"] = "jealous"
    elif "crazy" in msg or "party" in msg:
        bot_mood["mood"] = "crazy"
    elif "evil" in msg or "destroy" in msg:
        bot_mood["mood"] = "evil"
    if random.random() < 0.15:
        bot_mood["mood"] = "sassy"
    return random.choice(EMOTION_RESPONSES.get(bot_mood["mood"], EMOTION_RESPONSES["happy"]))

@guard
async def cmd_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await reply_msg(msg, "❌ `-ai` disabled (SSL / API issues).\nSet valid `XAI_API_KEY` env if you need it later.")
    return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -ai <message>")
        return
    wait = await msg.reply_text("Thinking...")
    res = await call_ai_api(txt)
    try:
        await wait.edit_text(res[:4000])
    except Exception:
        await reply_msg(msg, res[:4000])

@guard
async def cmd_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args or args[0].lower() not in MOOD_DESC:
        await reply_msg(msg, f"Current mood: {MOOD_DESC.get(bot_mood['mood'], 'Happy')}\nOptions: " + ", ".join(MOOD_DESC.keys()))
        return
    bot_mood["mood"] = args[0].lower()
    await reply_msg(msg, f"Mood: {MOOD_DESC[bot_mood['mood']]}")

@guard
async def cmd_moodstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await reply_msg(msg, f"Mood: {MOOD_DESC.get(bot_mood['mood'], 'Happy')}")

@guard
async def cmd_personality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if not args:
        await reply_msg(msg, f"Personality: {bot_mood.get('personality', 'sassy')}\nOptions: sassy, friendly, evil, crazy")
        return
    bot_mood["personality"] = args[0].lower()
    await reply_msg(msg, f"Personality: {args[0]}")

@guard
async def cmd_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    await reply_msg(msg, "❌ `-talk` disabled (depends on AI).")
    return
    args = get_args(context)
    if not args or args[0].lower() not in ["on", "off"]:
        status = conversation_enabled.get(msg.chat_id, False)
        await reply_msg(msg, f"Talk mode: {'ON' if status else 'OFF'}\nUse: -talk on / -talk off")
        return
    conversation_enabled[msg.chat_id] = args[0].lower() == "on"
    on = conversation_enabled[msg.chat_id]
    await reply_msg(
        msg,
        "Talk ON — bot har message pe AI se reply karega."
        if on
        else "Talk OFF",
    )

@guard
async def cmd_resetcontext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    key = f"{msg.chat_id}_{msg.from_user.id}"
    conversation_context.pop(key, None)
    await reply_msg(msg, "Context cleared")

@guard
async def cmd_conversationstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    key = f"{msg.chat_id}_{msg.from_user.id}"
    history = len(conversation_context.get(key, []))
    enabled = conversation_enabled.get(msg.chat_id, False)
    has_key = bool(os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY"))
    await reply_msg(
        msg,
        f"Talk: {'ON' if enabled else 'OFF'}\nHistory: {history}\nAPI key: {'YES' if has_key else 'NO'}",
    )

async def handle_conversation_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.from_user:
        return
    if getattr(msg.from_user, "is_bot", False):
        return
    if not conversation_enabled.get(msg.chat_id, False):
        return

    text = (msg.text or msg.caption or "").strip()
    if not text:
        return
    if text.startswith("-") or text.startswith("/") or text.startswith("!"):
        return

    now = time.time()
    key = f"{msg.chat_id}_{msg.from_user.id}"
    if key in conversation_cooldown and now - conversation_cooldown[key] < 3:
        return
    conversation_cooldown[key] = now

    hist = conversation_context.setdefault(key, [])
    hist.append({"role": "user", "content": text[:1500]})
    if len(hist) > 16:
        del hist[:-16]

    reply = await call_ai_api(text, hist)
    hist.append({"role": "assistant", "content": reply[:1500]})
    try:
        await msg.reply_text(reply[:4000])
    except Exception:
        pass

# ---- Error handling ----
def log_error(error_type, error_msg, tb_str):
    error_logs.append({"time": time.time(), "type": error_type, "message": error_msg, "traceback": tb_str[:500]})
    if len(error_logs) > 100:
        error_logs = error_logs[-50:]
    save_error_logs()
    try:
        asyncio.create_task(send_error_to_owner(error_type, error_msg, tb_str))
    except:
        pass

async def send_error_to_owner(error_type, error_msg, tb_str):
    for bot in bots():
        try:
            await bot.send_message(OWNER_ID, f"🚨 ERROR!\nType: {error_type}\nMsg: {error_msg}\n{tb_str[:500]}")
            break
        except:
            pass

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb = ''.join(traceback.format_tb(exc_traceback))
    log_error(exc_type.__name__, str(exc_value), tb)

sys.excepthook = global_exception_handler

@guard
async def cmd_errorlog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    if not error_logs:
        await reply_msg(msg, "✅ No errors logged!")
        return
    text = "🚨 Recent Errors:\n" + "\n".join([f"[{datetime.fromtimestamp(l['time']).strftime('%H:%M:%S')}] {l['type']}: {l['message'][:40]}..." for l in error_logs[-10:]])
    await reply_msg(msg, text)

@guard
async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    try:
        import psutil
        mem = psutil.virtual_memory()
        mem_txt = f"Memory: {mem.used//(1024**2)}MB/{mem.total//(1024**2)}MB ({mem.percent}%)"
    except:
        mem_txt = "Memory: ❌ (psutil not installed)"
    await reply_msg(msg, f"🩺 Health:\nBots: {len(bots())}\nGroups: {len(known_chats)}\nErrors: {len(error_logs)}\n{mem_txt}\nMood: {bot_mood['mood']}")

@guard
async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if not args or args[0].lower() not in ["on","off"]:
        await reply_msg(msg, "Usage: -debug on/off")
        return
    cid = str(msg.chat_id)
    if cid not in settings_db: settings_db[cid] = {}
    settings_db[cid]["debug"] = args[0].lower() == "on"
    save_settings()
    await reply_msg(msg, f"✅ Debug: {args[0].upper()}")

@guard
async def cmd_repair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    repaired = []
    if len(flood_tracker) > 1000:
        flood_tracker.clear()
        repaired.append("Flood tracker cleared")
    files = [SUDO_FILE, TEMPLATES_FILE, GROUPS_FILE]
    for f in files:
        if not os.path.exists(f):
            save_json(f, {})
            repaired.append(f"Created {f}")
    if repaired:
        await reply_msg(msg, "🔧 Repaired:\n" + "\n".join([f"✅ {r}" for r in repaired]))
    else:
        await reply_msg(msg, "✅ No repairs needed!")

@owner_only
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    data = {"sudo": list(SUDO_USERS), "templates": custom_templates, "groups": list(known_chats), "timestamp": time.time()}
    path = f"backup_{int(time.time())}.json"
    save_json(path, data)
    await reply_msg(msg, f"✅ Backup saved: {path}")

@owner_only
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SUDO_USERS, custom_templates, filters_db, trusted_users
    msg = update.message or update.edited_message
    if not msg: return
    SUDO_USERS = set(load_json(SUDO_FILE, [OWNER_ID]))
    custom_templates = load_json(TEMPLATES_FILE, {})
    filters_db = load_json(FILTERS_FILE, {})
    trusted_users = load_json(TRUSTED_FILE, {})
    await reply_msg(msg, "✅ Reloaded!")

@owner_only
async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if msg:
        try:
            await msg.reply_text("Restarting...")
        except Exception:
            pass
    os._exit(0)

JOIN_MSG = "🔥 ʀᴀʏᴜɢᴀ ʜᴇʀᴇ — ꜱᴀʙ ᴋɪ ᴍᴀᴀ ᴄʜᴜᴅᴇɢɪ 💀"
LEAVE_MSG = "💀 ɢᴀᴍᴇ ᴏᴠᴇʀ ʙʏ ʀᴀʏᴜɢᴀ"


async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot add / admin mile to auto announce."""
    result = update.my_chat_member
    if not result:
        return
    old = result.old_chat_member
    new = result.new_chat_member
    if not new or not new.user or not new.user.is_bot:
        return
    # Only this bot's own updates
    if new.user.id != context.bot.id:
        return

    old_st = getattr(old, "status", None)
    new_st = getattr(new, "status", None)
    cid = result.chat.id if result.chat else None
    if not cid:
        return

    became_member = new_st in (
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        "member",
        "administrator",
    )
    was_out = old_st in (
        ChatMemberStatus.LEFT,
        ChatMemberStatus.BANNED,
        ChatMemberStatus.RESTRICTED,
        None,
        "left",
        "kicked",
        "restricted",
    )
    became_admin = new_st in (ChatMemberStatus.ADMINISTRATOR, "administrator") and old_st not in (
        ChatMemberStatus.ADMINISTRATOR,
        "administrator",
    )

    if (became_member and was_out) or became_admin:
        try:
            known_chats.add(cid)
            save_groups()
        except Exception:
            pass
        try:
            await context.bot.send_message(cid, JOIN_MSG)
        except Exception:
            pass


@guard
async def cmd_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    -leave          → is group se SAARI bots leave
    -leave <id>     → us group id se leave
    -leave me       → sirf jis bot pe cmd aayi wo leave
    """
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    mode = "all"
    cid = msg.chat_id

    if args:
        a0 = args[0].lower()
        if a0 in ("me", "this", "self"):
            mode = "me"
        else:
            try:
                cid = int(args[0])
            except ValueError:
                await reply_msg(msg, "Usage:\n`-leave` — is GC se sab bots\n`-leave me` — sirf ye bot\n`-leave <chat_id>`")
                return

    # Game over message BEFORE leave
    try:
        if mode == "me":
            await context.bot.send_message(cid, LEAVE_MSG)
        else:
            # One announcement then all leave
            await context.bot.send_message(cid, LEAVE_MSG)
    except Exception:
        try:
            await reply_msg(msg, LEAVE_MSG)
        except Exception:
            pass
    await asyncio.sleep(0.5)

    ok, fail = 0, 0
    if mode == "me":
        try:
            await context.bot.leave_chat(cid)
            ok = 1
        except Exception:
            fail = 1
    else:
        for bot in bots():
            try:
                await bot.leave_chat(cid)
                ok += 1
            except Exception:
                fail += 1
            await asyncio.sleep(0.08)

    known_chats.discard(cid)
    try:
        save_groups()
    except Exception:
        pass

    if cid != msg.chat_id:
        try:
            await reply_msg(msg, f"✅ Left `{cid}` — ok:{ok} fail:{fail}")
        except Exception:
            pass

@owner_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    text = txt_arg(context)
    if not text:
        await reply_msg(msg, "Usage: -broadcast <message>")
        return
    sent = 0
    for cid in known_chats:
        try:
            await context.bot.send_message(cid, f"📢 Broadcast:\n{text}")
            sent += 1
        except:
            pass
    await reply_msg(msg, f"✅ Broadcast sent to {sent} groups")

@guard
async def cmd_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_broadcast(update, context)

@guard
async def cmd_gclist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    if not known_chats:
        await reply_msg(msg, "📭 No known groups.")
        return
    text = "📋 **Groups List**\n\n" + "\n".join([f"• `{cid}`" for cid in known_chats])
    await reply_msg(msg, text)

# ---- Auto react/reply handler ----
async def handle_auto_react_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg or not msg.from_user:
        return
    cid = msg.chat_id
    uid = msg.from_user.id
    try:
        _track_gc(cid)
    except Exception:
        pass

    text = (msg.text or msg.caption or "").strip()
    if text.startswith("-") or text.startswith("/") or text.startswith("!"):
        return

    if uid in SUDO_USERS or uid == OWNER_ID:
        return
    try:
        member = await msg.chat.get_member(uid)
        if member.status in ["administrator", "creator"]:
            return
    except Exception:
        pass

    if cid in auto_react_chats:
        try:
            await context.bot.set_message_reaction(
                cid, msg.message_id,
                reaction=[ReactionTypeEmoji(emoji=auto_react_chats[cid])],
            )
        except Exception:
            pass

    if cid in auto_reply_chats:
        try:
            await msg.reply_text(str(auto_reply_chats[cid])[:4000])
        except Exception:
            pass

    if cid in ncdel_chats:
        try:
            await msg.delete()
        except:
            pass

    if cid in targetreply_chats:
        tr = targetreply_chats[cid]
        if uid == tr["uid"]:
            for bot in bots():
                try:
                    await bot.send_message(cid, tr["text"], reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=False))
                except:
                    pass

    if cid in targetslide_chats:
        ts = targetslide_chats[cid]
        if uid == ts["uid"]:
            for bot in bots():
                try:
                    await bot.send_message(cid, ts["text"], reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=False))
                except:
                    pass

    if cid in replyflood_chats:
        for bot in bots():
            try:
                await bot.send_message(cid, replyflood_chats[cid], reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=False))
            except:
                pass

    stats_db[str(cid)] = stats_db.get(str(cid), {})
    uid_str = str(uid)
    if uid_str not in stats_db[str(cid)]:
        stats_db[str(cid)][uid_str] = {"msgs": 0, "cmds": 0, "name": msg.from_user.first_name}
    stats_db[str(cid)][uid_str]["msgs"] += 1
    if msg.text and (msg.text.startswith('-') or msg.text.startswith('/')):
        stats_db[str(cid)][uid_str]["cmds"] += 1
    save_stats()

def _fmt_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

def _track_gc(chat_id: int):
    known_chats.add(chat_id)
    if chat_id not in gc_join_times:
        gc_join_times[chat_id] = time.monotonic()

def _menu_page_media(page: int | None):
    pages = menu_media.get("pages") or {}
    if page is not None:
        key = str(page)
        if key in pages and isinstance(pages[key], dict):
            p = pages[key]
            vid = p.get("video_id") or menu_media.get("video_id")
            pic = p.get("photo_id") or menu_media.get("photo_id")
            return vid, pic
    return menu_media.get("video_id"), menu_media.get("photo_id")

async def _send_menu_media(msg, text: str, page_title: str = "🐉 MENU", page: int | None = None):
    CAP_LIMIT = 1024
    caption = text if len(text) <= CAP_LIMIT else (text[: CAP_LIMIT - 3] + "...")
    video_id, photo_id = _menu_page_media(page)

    if video_id:
        try:
            await msg.reply_video(
                video=video_id,
                caption=caption,
                supports_streaming=True,
            )
            return True
        except Exception:
            try:
                await msg.reply_video(
                    video=video_id,
                    caption=caption[:200],
                    supports_streaming=True,
                )
                return True
            except Exception:
                pass

    if photo_id:
        try:
            await msg.reply_photo(photo=photo_id, caption=caption)
            return True
        except Exception:
            pass

    try:
        await msg.reply_text(text)
    except Exception:
        pass
    return False

@guard
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if msg.chat_id:
        _track_gc(msg.chat_id)
    menu_text = menu_db.get("menu", MENU)
    await _send_menu_media(msg, menu_text, page_title="🐉 MAIN MENU", page=None)

@guard
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if msg.chat_id:
        _track_gc(msg.chat_id)
    args = get_args(context)

    if args and args[0].isdigit():
        try:
            num = int(args[0])
            sections = menu_db.get("sections", MENU_SECTIONS)
            if 1 <= num <= len(sections):
                await _send_menu_media(
                    msg,
                    sections[num - 1],
                    page_title=f"🐉 MENU PAGE {num}/{len(sections)}",
                    page=num,
                )
                return
            else:
                await reply_msg(msg, f"❌ Section {num} not found. Choose 1-{len(sections)}")
                return
        except Exception:
            pass

    await cmd_help(update, context)

@guard
async def cmd_gameover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    cid = msg.chat_id
    _track_gc(cid)

    try:
        await _force_stop_chat(cid)
    except Exception:
        _nc_force_stop[cid] = time.monotonic()
        try:
            await tc.stop_all(cid)
        except Exception:
            pass

    target = None
    target_name = None
    if msg.reply_to_message and msg.reply_to_message.from_user:
        target = msg.reply_to_message.from_user
        target_name = (target.first_name or "") + ((" " + target.last_name) if target.last_name else "")
        target_name = target_name.strip() or str(target.id)
    else:
        args = get_args(context)
        if args:
            target_name = " ".join(args).strip()
        elif msg.from_user:
            target_name = (msg.from_user.first_name or "Player").strip()

    if not target_name:
        target_name = "Unknown"

    safe_name = (
        str(target_name)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    start = gc_join_times.get(cid, BOT_START_TIME)
    ran_for = time.monotonic() - start
    process_up = time.monotonic() - BOT_START_TIME
    now = datetime.now()
    time_str = now.strftime("%I:%M:%S %p")
    date_str = now.strftime("%d %b %Y")

    if target:
        who = f'<a href="tg://user?id={target.id}">{safe_name}</a>'
    else:
        who = safe_name

    text = (
        "╔══════════════════════════════╗\n"
        "║   💀 GAME OVER 💀             ║\n"
        "╚══════════════════════════════╝\n\n"
        f"🎯 Target: {who}\n"
        f"🏛 GC Session: {_fmt_duration(ran_for)}\n"
        f"🤖 Bot Uptime: {_fmt_duration(process_up)}\n"
        f"🕐 Game Over: {time_str}\n"
        f"📅 Date: {date_str}\n\n"
        "⛔ All tasks stopped\n"
        "⚡ Dragon Ball Super — Ki Ling Engine"
    )
    try:
        await msg.reply_text(text, parse_mode="HTML")
    except Exception:
        try:
            await msg.reply_text(
                f"💀 GAME OVER\n"
                f"Target: {target_name}\n"
                f"GC Session: {_fmt_duration(ran_for)}\n"
                f"Bot Uptime: {_fmt_duration(process_up)}\n"
                f"Time: {time_str}\n"
                f"Date: {date_str}\n"
                f"All tasks stopped"
            )
        except Exception:
            pass

# ---- Menu management (owner) ----
@guard
@owner_only
async def cmd_setmenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    txt = txt_arg(context)
    if not txt:
        await reply_msg(msg, "Usage: -setmenu <new_menu_text>")
        return
    menu_db["menu"] = txt
    save_json(MENU_FILE, menu_db)
    await reply_msg(msg, "✅ Main Menu updated successfully! Use `-menu` to check.")

@guard
@owner_only
async def cmd_setsection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    args = get_args(context)
    if len(args) < 2:
        await reply_msg(msg, "Usage: -setsection <num> <new_text>")
        return
    try:
        num = int(args[0])
    except ValueError:
        await reply_msg(msg, "Invalid section number!")
        return
    txt = " ".join(args[1:])
    sections = menu_db.get("sections", MENU_SECTIONS)
    if 1 <= num <= len(sections):
        sections[num-1] = txt
        menu_db["sections"] = sections
        save_json(MENU_FILE, menu_db)
        await reply_msg(msg, f"✅ Section {num} updated successfully!")
    else:
        await reply_msg(msg, f"❌ Section {num} not found.")

@guard
@owner_only
async def cmd_resetmenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg: return
    menu_db["menu"] = MENU
    menu_db["sections"] = MENU_SECTIONS
    save_json(MENU_FILE, menu_db)
    await reply_msg(msg, "✅ Menu reset to default!")

@guard
@owner_only
async def cmd_setmenupic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await reply_msg(msg, "Reply to a photo:\n`-setmenupic` → main menu\n`-setmenupic 3` → page 3 only")
        return
    fid = msg.reply_to_message.photo[-1].file_id
    args = get_args(context)
    if args and args[0].isdigit():
        page = str(int(args[0]))
        menu_media.setdefault("pages", {})
        menu_media["pages"].setdefault(page, {})
        menu_media["pages"][page]["photo_id"] = fid
        save_json(MENU_MEDIA_FILE, menu_media)
        await reply_msg(msg, f"✅ Photo set for **menu page {page}**\nCheck: `-menu {page}`")
    else:
        menu_media["photo_id"] = fid
        save_json(MENU_MEDIA_FILE, menu_media)
        await reply_msg(msg, "✅ Global menu photo set (all pages fallback)\nCheck: `-menu`")

@guard
@owner_only
async def cmd_setmenuvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    if not msg.reply_to_message or not (
        msg.reply_to_message.video or getattr(msg.reply_to_message, "animation", None)
    ):
        await reply_msg(msg, "Reply to a video:\n`-setmenuvideo` → main / default all pages\n`-setmenuvideo 5` → only page 5")
        return
    vid = msg.reply_to_message.video or msg.reply_to_message.animation
    fid = vid.file_id
    args = get_args(context)
    if args and args[0].isdigit():
        page = str(int(args[0]))
        menu_media.setdefault("pages", {})
        menu_media["pages"].setdefault(page, {})
        menu_media["pages"][page]["video_id"] = fid
        save_json(MENU_MEDIA_FILE, menu_media)
        await reply_msg(msg, f"✅ Video set for **menu page {page}**\nCheck: `-menu {page}`")
    else:
        menu_media["video_id"] = fid
        save_json(MENU_MEDIA_FILE, menu_media)
        await reply_msg(msg, "✅ Global menu video set (default for all pages)\nCheck: `-menu`")

@guard
@owner_only
async def cmd_rmmenupic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.edited_message
    if not msg:
        return
    args = get_args(context)
    if args and args[0].isdigit():
        page = str(int(args[0]))
        pages = menu_media.get("pages") or {}
        if page in pages:
            pages.pop(page, None)
            menu_media["pages"] = pages
            save_json(MENU_MEDIA_FILE, menu_media)
            await reply_msg(msg, f"✅ Page {page} media removed (global fallback use hoga)")
        else:
            await reply_msg(msg, f"Page {page} pe koi custom media nahi tha")
        return
    menu_media.pop("photo_id", None)
    menu_media.pop("video_id", None)
    menu_media.pop("pages", None)
    save_json(MENU_MEDIA_FILE, menu_media)
    await reply_msg(msg, "✅ All menu media cleared (global + per-page)")

# ---- Force stop helper ----
async def _force_stop_chat(cid: int) -> int:
    """Nuclear stop for one chat — NC + all tasks + flags. Returns kill count."""
    global _mgcnc_stop, _mgcnc_task
    _nc_force_stop[cid] = time.monotonic()
    count = 0
    if await tc.stop(cid, "nc"):
        count += 1
    count += await tc.stop_all(cid)
    if cid in pfp_tasks:
        t = pfp_tasks.pop(cid, None)
        if t and not t.done():
            t.cancel()
            count += 1
    try:
        if _mgcnc_targets and cid in _mgcnc_targets:
            if _mgcnc_stop and not _mgcnc_stop.is_set():
                _mgcnc_stop.set()
            if _mgcnc_task and not _mgcnc_task.done():
                _mgcnc_task.cancel()
                count += 1
    except Exception:
        pass
    try:
        if cid in _multiwar_active:
            _multiwar_active.pop(cid, None)
            count += 1
    except Exception:
        pass
    for d in (targetreply_chats, targetslide_chats, replyflood_chats, auto_react_chats, auto_reply_chats):
        if cid in d:
            d.pop(cid, None)
            count += 1
    ncdel_chats.discard(cid)
    mute_chats.discard(cid)
    try:
        for b in bots():
            bid = getattr(b, "id", None)
            if bid is not None:
                _ft.clear(bid)
    except Exception:
        pass
    await asyncio.sleep(0.08)
    _nc_force_stop[cid] = time.monotonic()
    await tc.stop(cid, "nc")
    await tc.stop_all(cid)
    return count

# ---- Add handlers ----
def add_handlers(app):
    # ---- NC ----
    app.add_handler(PrefixHandler("-", "nc", cmd_nc))
    app.add_handler(PrefixHandler("-", "multinc", cmd_multinc))
    app.add_handler(PrefixHandler("-", "ncdark", cmd_ncdark))
    app.add_handler(PrefixHandler("-", "tmkcnc", cmd_tmkcnc))
    app.add_handler(PrefixHandler("-", "evonc", cmd_evonc))
    app.add_handler(PrefixHandler("-", "marvelnc", cmd_marvelnc))
    app.add_handler(PrefixHandler("-", "magicnc", cmd_magicnc))
    app.add_handler(PrefixHandler("-", "sportnc", cmd_sportnc))
    app.add_handler(PrefixHandler("-", "lndnc", cmd_lndnc))
    app.add_handler(PrefixHandler("-", "ncspeed", cmd_ncspeed))
    app.add_handler(PrefixHandler("-", "emognc", cmd_emognc))
    app.add_handler(PrefixHandler("-", "yournc", cmd_yournc))
    app.add_handler(PrefixHandler("-", "typenc", cmd_typenc))
    app.add_handler(PrefixHandler("-", "flashnc", cmd_flashnc))
    app.add_handler(PrefixHandler("-", "foxync", cmd_foxync))
    app.add_handler(PrefixHandler("-", "ncmoon", cmd_ncmoon))
    app.add_handler(PrefixHandler("-", "threads", cmd_threads))
    app.add_handler(PrefixHandler("-", "multispam", cmd_multispam))
    app.add_handler(PrefixHandler("-", "join", cmd_join))
    app.add_handler(PrefixHandler("-", "bye", cmd_bye))
    app.add_handler(PrefixHandler("-", "ncflag", cmd_ncflag))
    app.add_handler(PrefixHandler("-", "ncemo", cmd_ncemo))
    app.add_handler(PrefixHandler("-", "flowernc", cmd_flowernc))
    app.add_handler(PrefixHandler("-", "timenc", cmd_timenc))
    app.add_handler(PrefixHandler("-", "nccurly", cmd_nccurly))
    app.add_handler(PrefixHandler("-", "snc", cmd_snc))
    app.add_handler(PrefixHandler("-", "gokugod", cmd_gokugod))
    app.add_handler(PrefixHandler("-", "vegetagod", cmd_vegetagod))
    app.add_handler(PrefixHandler("-", "brolygod", cmd_brolygod))
    app.add_handler(PrefixHandler("-", "gohangod", cmd_gohangod))
    app.add_handler(PrefixHandler("-", "trunksgod", cmd_trunksgod))
    app.add_handler(PrefixHandler("-", "dbgod", cmd_dbgod))
    app.add_handler(PrefixHandler("-", "db1", cmd_db1))
    app.add_handler(PrefixHandler("-", "broly1", cmd_broly1))
    app.add_handler(PrefixHandler("-", "triogod", cmd_triogod))
    app.add_handler(PrefixHandler("-", "silknc", cmd_silknc))
    app.add_handler(PrefixHandler("-", "hakai", cmd_hakai))
    app.add_handler(PrefixHandler("-", "boldnc", cmd_boldnc))
    app.add_handler(PrefixHandler("-", "cursivenc", cmd_cursivenc))
    app.add_handler(PrefixHandler("-", "italicnc", cmd_italicnc))
    app.add_handler(PrefixHandler("-", "wavenc", cmd_wavenc))
    app.add_handler(PrefixHandler("-", "godki", cmd_godki))
    app.add_handler(PrefixHandler("-", "ultranc", cmd_ultranc))
    app.add_handler(PrefixHandler("-", "saitama", cmd_saitama))
    app.add_handler(PrefixHandler("-", "aizennc", cmd_aizennc))
    app.add_handler(PrefixHandler("-", "villainnc", cmd_villainnc))
    app.add_handler(PrefixHandler("-", "randomcod", cmd_randomcod))
    app.add_handler(PrefixHandler("-", "godcod", cmd_godcod))
    app.add_handler(PrefixHandler("-", "chud", cmd_chud))
    app.add_handler(PrefixHandler("-", "anshgod", cmd_anshgod))
    app.add_handler(PrefixHandler("-", "kusanagigod", cmd_kusanagigod))
    app.add_handler(PrefixHandler("-", "kusanagi1", cmd_kusanagi1))
    app.add_handler(PrefixHandler("-", "phantom", cmd_phantom))
    app.add_handler(PrefixHandler("-", "testament", cmd_testament))
    app.add_handler(PrefixHandler("-", "shadow", cmd_shadow))
    for friend in FRIENDS:
        async def fh(update, context, f=friend):
            await _friend_nc_cmd(update, context, f)
        app.add_handler(PrefixHandler("-", f"{friend.lower()}nc", fh))

    # ---- Spam ----
    app.add_handler(PrefixHandler("-", "spam", cmd_spam))
    app.add_handler(PrefixHandler("-", "stopspam", cmd_stopspam))
    app.add_handler(PrefixHandler("-", "slidespam", cmd_slidespam))
    app.add_handler(PrefixHandler("-", "stopslide", cmd_stopslide))
    app.add_handler(PrefixHandler("-", "reply", cmd_reply))
    app.add_handler(PrefixHandler("-", "stopreply", cmd_stopreply))
    app.add_handler(PrefixHandler("-", "texts", cmd_texts))
    app.add_handler(PrefixHandler("-", "shayari", cmd_shayari))
    app.add_handler(PrefixHandler("-", "songy", cmd_songy))
    app.add_handler(PrefixHandler("-", "customspam", cmd_customspam))
    app.add_handler(PrefixHandler("-", "burstspam", cmd_burstspam))
    app.add_handler(PrefixHandler("-", "rapidfire", cmd_rapidfire))
    app.add_handler(PrefixHandler("-", "stoprapid", cmd_stoprapid))
    app.add_handler(PrefixHandler("-", "swipespam", cmd_swipespam))
    app.add_handler(PrefixHandler("-", "stopswipe", cmd_stopswipe))
    app.add_handler(PrefixHandler("-", "chudspam", cmd_chudspam))
    app.add_handler(PrefixHandler("-", "stopchudspam", cmd_stopchudspam))
    app.add_handler(PrefixHandler("-", "tagspam", cmd_tagspam))
    app.add_handler(PrefixHandler("-", "stoptagspam", cmd_stoptagspam))
    app.add_handler(PrefixHandler("-", "copyspam", cmd_copyspam))
    app.add_handler(PrefixHandler("-", "stopcopyspam", cmd_stopcopyspam))
    app.add_handler(PrefixHandler("-", "replyflood", cmd_replyflood))
    app.add_handler(PrefixHandler("-", "stopreplyflood", cmd_stopreplyflood))

    # ---- Slider ----
    app.add_handler(PrefixHandler("-", "alexa", cmd_alexa))
    app.add_handler(PrefixHandler("-", "stopalexa", cmd_stopalexa))
    app.add_handler(PrefixHandler("-", "animal", cmd_animal))
    app.add_handler(PrefixHandler("-", "stopanimal", cmd_stopanimal))
    app.add_handler(PrefixHandler("-", "swipe", cmd_swipe_slider))
    app.add_handler(PrefixHandler("-", "stopswipeslider", cmd_stopswipe_slider))

    # ---- RR ----
    app.add_handler(PrefixHandler("-", "replyraid", cmd_replyraid))
    app.add_handler(PrefixHandler("-", "stopreplyraid", cmd_stopreplyraid))
    app.add_handler(PrefixHandler("-", "massreply", cmd_massreply))
    app.add_handler(PrefixHandler("-", "mentionraid", cmd_mentionraid))
    app.add_handler(PrefixHandler("-", "stopmentionraid", cmd_stopmentionraid))
    app.add_handler(PrefixHandler("-", "rrbomb", cmd_rrbomb))
    app.add_handler(PrefixHandler("-", "rrloop", cmd_rrloop))
    app.add_handler(PrefixHandler("-", "stoprrloop", cmd_stoprrloop))
    app.add_handler(PrefixHandler("-", "rrspam", cmd_rrspam))
    app.add_handler(PrefixHandler("-", "stoprrspam", cmd_stoprrspam))
    app.add_handler(PrefixHandler("-", "multirr", cmd_multirr))
    app.add_handler(PrefixHandler("-", "stopmultirr", cmd_stopmultirr))

    # ---- Target ----
    app.add_handler(PrefixHandler("-", "targetreply", cmd_targetreply))
    app.add_handler(PrefixHandler("-", "stoptargetreply", cmd_stoptargetreply))
    app.add_handler(PrefixHandler("-", "targetslide", cmd_targetslide))
    app.add_handler(PrefixHandler("-", "stoptargetslide", cmd_stoptargetslide))
    app.add_handler(PrefixHandler("-", "ncdel", cmd_ncdel))
    app.add_handler(PrefixHandler("-", "stopncdel", cmd_stopncdel))

    # ---- Auto ----
    app.add_handler(PrefixHandler("-", "autoreact", cmd_autoreact))
    app.add_handler(PrefixHandler("-", "stopautoreact", cmd_stopautoreact))
    app.add_handler(PrefixHandler("-", "autoreply", cmd_autoreply))
    app.add_handler(PrefixHandler("-", "stopautoreply", cmd_stopautoreply))
    app.add_handler(PrefixHandler("-", "autostatus", cmd_autostatus))

    # ---- Sudo ----
    app.add_handler(PrefixHandler("-", "givebheek", cmd_givebheek))
    app.add_handler(PrefixHandler("-", "bheekhatao", cmd_bheekhatao))
    app.add_handler(PrefixHandler("-", "bheeklist", cmd_bheeklist))
    app.add_handler(PrefixHandler("-", "addsudo", cmd_givebheek))
    app.add_handler(PrefixHandler("-", "removesudo", cmd_bheekhatao))
    app.add_handler(PrefixHandler("-", "sudolist", cmd_bheeklist))

    # ---- Theme ----
    app.add_handler(PrefixHandler("-", "settheme", cmd_settheme))
    # removed garbage: app.add_handler(PrefixHandler("-", "formchange", cmd_formchange))

    # ---- GC Create ----
    app.add_handler(PrefixHandler("-", "creategc", cmd_creategc))
    app.add_handler(PrefixHandler("-", "link", cmd_link))
    app.add_handler(PrefixHandler("-", "gofighters", cmd_gofighters))

    # ---- PFP ----
    app.add_handler(PrefixHandler("-", "addpfp", cmd_addpfp))
    app.add_handler(PrefixHandler("-", "pfploop", cmd_pfploop))
    app.add_handler(PrefixHandler("-", "stoppfploop", cmd_stoppfploop))
    app.add_handler(PrefixHandler("-", "setpfponce", cmd_setpfponce))
    app.add_handler(PrefixHandler("-", "deletegcpfp", cmd_deletegcpfp))
    app.add_handler(PrefixHandler("-", "pfppool", cmd_pfppool))
    app.add_handler(PrefixHandler("-", "clearpfp", cmd_clearpfp))
    app.add_handler(PrefixHandler("-", "photosave", cmd_photosave))
    app.add_handler(PrefixHandler("-", "setgc", cmd_setgc))
    app.add_handler(PrefixHandler("-", "stopgc", cmd_stopgc))

    # ---- GC Manage ----
    app.add_handler(PrefixHandler("-", "gcinfo", cmd_gcinfo))
    app.add_handler(PrefixHandler("-", "setgctitle", cmd_setgctitle))
    app.add_handler(PrefixHandler("-", "setgcdesc", cmd_setgcdesc))
    app.add_handler(PrefixHandler("-", "getinvite", cmd_getinvite))
    app.add_handler(PrefixHandler("-", "pinmsg", cmd_pinmsg))
    app.add_handler(PrefixHandler("-", "unpinall", cmd_unpinall))
    app.add_handler(PrefixHandler("-", "kickuser", cmd_kickuser))
    app.add_handler(PrefixHandler("-", "bantarget", cmd_bantarget))
    app.add_handler(PrefixHandler("-", "unbanuser", cmd_unbanuser))
    app.add_handler(PrefixHandler("-", "muteuser", cmd_muteuser))
    app.add_handler(PrefixHandler("-", "unmuteuser", cmd_unmuteuser))

    # ---- Templates ----
    app.add_handler(PrefixHandler("-", "addtemplate", cmd_addtemplate))
    app.add_handler(PrefixHandler("-", "templates", cmd_templates))
    app.add_handler(PrefixHandler("-", "preview", cmd_preview))
    app.add_handler(PrefixHandler("-", "deltemplate", cmd_deltemplate))
    app.add_handler(PrefixHandler("-", "cleartemplates", cmd_cleartemplates))
    app.add_handler(PrefixHandler("-", "customnc", cmd_customnc))
    app.add_handler(PrefixHandler("-", "listtemplates", cmd_templates))
    app.add_handler(PrefixHandler("-", "deltpl", cmd_deltemplate))
    app.add_handler(PrefixHandler("-", "templateinfo", cmd_preview))
    app.add_handler(PrefixHandler("-", "tplinfo", cmd_preview))
    app.add_handler(PrefixHandler("-", "cnc", cmd_customnc))

    # ---- Bot Control ----
    app.add_handler(PrefixHandler("-", "bots", cmd_bots))
    app.add_handler(PrefixHandler("-", "addbot", cmd_addbot))
    app.add_handler(PrefixHandler("-", "addallbots", cmd_addallbots))
    app.add_handler(PrefixHandler("-", "promotebot", cmd_promotebot))
    app.add_handler(PrefixHandler("-", "promoteall", cmd_promoteall))
    app.add_handler(PrefixHandler("-", "admincheck", cmd_admincheck))
    app.add_handler(PrefixHandler("-", "ncstatus", cmd_ncstatus))
    app.add_handler(PrefixHandler("-", "alive", cmd_alive))
    app.add_handler(PrefixHandler("-", "whitelist", cmd_whitelist))
    app.add_handler(PrefixHandler("-", "chatdelay", cmd_chatdelay))
    app.add_handler(PrefixHandler("-", "tagall", cmd_tagall))
    app.add_handler(PrefixHandler("-", "lock", cmd_lock))
    app.add_handler(PrefixHandler("-", "unlock", cmd_unlock))
    app.add_handler(PrefixHandler("-", "safe", cmd_safe))
    app.add_handler(PrefixHandler("-", "unsafe", cmd_unsafe))
    app.add_handler(PrefixHandler("-", "antiraid", cmd_antiraid))
    app.add_handler(PrefixHandler("-", "botname", cmd_botname))
    app.add_handler(PrefixHandler("-", "botbio", cmd_botbio))
    app.add_handler(PrefixHandler("-", "botinfo", cmd_botinfo))

    # ---- MGC ----
    app.add_handler(PrefixHandler("-", "mgcnc", cmd_mgcnc))
    app.add_handler(PrefixHandler("-", "mgchakai", cmd_mgchakai))
    app.add_handler(PrefixHandler("-", "mgcbold", cmd_mgcbold))
    app.add_handler(PrefixHandler("-", "mgcfire", cmd_mgcfire))
    app.add_handler(PrefixHandler("-", "mgcwar", cmd_mgcwar))
    app.add_handler(PrefixHandler("-", "mgcsurge", cmd_mgcsurge))
    app.add_handler(PrefixHandler("-", "mgccustom", cmd_mgccustom))
    app.add_handler(PrefixHandler("-", "stopmgcnc", cmd_stopmgcnc))
    app.add_handler(PrefixHandler("-", "mgcstatus", cmd_mgcstatus))
    app.add_handler(PrefixHandler("-", "mgc", cmd_mgcnc))
    app.add_handler(PrefixHandler("-", "mgcchud", cmd_mgchakai))
    app.add_handler(PrefixHandler("-", "mgccnc", cmd_mgccustom))
    app.add_handler(PrefixHandler("-", "smgc", cmd_stopmgcnc))

    # ---- War ----
    app.add_handler(PrefixHandler("-", "multiwar", cmd_multiwar))
    app.add_handler(PrefixHandler("-", "stopmultiwar", cmd_stopmultiwar))
    app.add_handler(PrefixHandler("-", "stopmwar", cmd_stopmultiwar))
    app.add_handler(PrefixHandler("-", "mute", cmd_mute))
    app.add_handler(PrefixHandler("-", "unmute", cmd_unmute))

    # ---- Purge ----
    app.add_handler(PrefixHandler("-", "purge", cmd_purge))
    app.add_handler(PrefixHandler("-", "purgeme", cmd_purgeme))
    app.add_handler(PrefixHandler("-", "purgebot", cmd_purgebot))
    app.add_handler(PrefixHandler("-", "purgeall", cmd_purgeall))

    # ---- Tools ----
    app.add_handler(PrefixHandler("-", "status", cmd_status))
    app.add_handler(PrefixHandler("-", "uptime", cmd_uptime))
    app.add_handler(PrefixHandler("-", "ping", cmd_ping))
    app.add_handler(PrefixHandler("-", "setdelay", cmd_setdelay))
    app.add_handler(PrefixHandler("-", "floodstat", cmd_floodstat))
    app.add_handler(PrefixHandler("-", "stop", cmd_stop))
    app.add_handler(PrefixHandler("-", "stopnc", cmd_stop))
    app.add_handler(PrefixHandler("-", "stopall", cmd_stop))

    # ---- Games ----
    app.add_handler(PrefixHandler("-", "dice", cmd_dice))
    app.add_handler(PrefixHandler("-", "rps", cmd_rps))
    app.add_handler(PrefixHandler("-", "slot", cmd_slot))
    app.add_handler(PrefixHandler("-", "guess", cmd_guess))
    app.add_handler(PrefixHandler("-", "trivia", cmd_trivia))

    # ---- Quests ----
    # removed garbage: app.add_handler(PrefixHandler("-", "daily", cmd_daily))
    # removed garbage: app.add_handler(PrefixHandler("-", "quests", cmd_quests))
    # removed garbage: app.add_handler(PrefixHandler("-", "streak", cmd_streak))
    # removed garbage: app.add_handler(PrefixHandler("-", "claim", cmd_claim))
    # removed garbage: app.add_handler(PrefixHandler("-", "lb", cmd_lb))

    # ---- Music ----
    app.add_handler(PrefixHandler("-", "song", cmd_song))
    # removed garbage: app.add_handler(PrefixHandler("-", "play", cmd_play))
    # removed garbage: app.add_handler(PrefixHandler("-", "lyrics", cmd_lyrics))
    # removed garbage: app.add_handler(PrefixHandler("-", "randomsong", cmd_randomsong))

    # ---- AI ----
    # removed garbage: app.add_handler(PrefixHandler("-", "ai", cmd_ai))
    # removed garbage: app.add_handler(PrefixHandler("-", "mood", cmd_mood))
    # removed garbage: app.add_handler(PrefixHandler("-", "moodstatus", cmd_moodstatus))
    # removed garbage: app.add_handler(PrefixHandler("-", "personality", cmd_personality))
    # removed garbage: app.add_handler(PrefixHandler("-", "talk", cmd_talk))
    # removed garbage: app.add_handler(PrefixHandler("-", "resetcontext", cmd_resetcontext))
    # removed garbage: app.add_handler(PrefixHandler("-", "conversationstatus", cmd_conversationstatus))

    # ---- Error, Health, etc ----
    app.add_handler(PrefixHandler("-", "errorlog", cmd_errorlog))
    app.add_handler(PrefixHandler("-", "health", cmd_health))
    app.add_handler(PrefixHandler("-", "debug", cmd_debug))
    app.add_handler(PrefixHandler("-", "repair", cmd_repair))
    app.add_handler(PrefixHandler("-", "backup", cmd_backup))
    app.add_handler(PrefixHandler("-", "reload", cmd_reload))
    app.add_handler(PrefixHandler("-", "restart", cmd_restart))
    app.add_handler(PrefixHandler("-", "leave", cmd_leave))
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(PrefixHandler("-", "broadcast", cmd_broadcast))
    app.add_handler(PrefixHandler("-", "global", cmd_global))
    app.add_handler(PrefixHandler("-", "gclist", cmd_gclist))

    # ---- Help / Menu ----
    app.add_handler(PrefixHandler("-", "help", cmd_help))
    app.add_handler(PrefixHandler("-", "menu", cmd_menu))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(PrefixHandler("-", "gameover", cmd_gameover))

    # ---- Menu management ----
    app.add_handler(PrefixHandler("-", "setmenu", cmd_setmenu))
    app.add_handler(PrefixHandler("-", "setsection", cmd_setsection))
    app.add_handler(PrefixHandler("-", "resetmenu", cmd_resetmenu))
    app.add_handler(PrefixHandler("-", "setmenupic", cmd_setmenupic))
    app.add_handler(PrefixHandler("-", "setmenuvideo", cmd_setmenuvideo))
    app.add_handler(PrefixHandler("-", "rmmenupic", cmd_rmmenupic))

    # ---- New fast command ----
    app.add_handler(PrefixHandler("-", "chudnc", cmd_chudnc))
    app.add_handler(PrefixHandler("-", "chud", cmd_chudnc))

    # ---- Aliases ----
    app.add_handler(PrefixHandler("-", "rr", cmd_replyraid))
    app.add_handler(PrefixHandler("-", "srr", cmd_stopreplyraid))
    app.add_handler(PrefixHandler("-", "mr", cmd_massreply))
    app.add_handler(PrefixHandler("-", "mraid", cmd_mentionraid))
    app.add_handler(PrefixHandler("-", "smraid", cmd_stopmentionraid))
    app.add_handler(PrefixHandler("-", "ts", cmd_tagspam))
    app.add_handler(PrefixHandler("-", "sts", cmd_stoptagspam))
    app.add_handler(PrefixHandler("-", "rf", cmd_replyflood))
    app.add_handler(PrefixHandler("-", "srf", cmd_stopreplyflood))
    app.add_handler(PrefixHandler("-", "ss", cmd_swipespam))
    app.add_handler(PrefixHandler("-", "sss", cmd_stopswipe))
    app.add_handler(PrefixHandler("-", "cs", cmd_chudspam))
    app.add_handler(PrefixHandler("-", "scs", cmd_stopchudspam))
    app.add_handler(PrefixHandler("-", "rap", cmd_rapidfire))
    app.add_handler(PrefixHandler("-", "srap", cmd_stoprapid))
    app.add_handler(PrefixHandler("-", "rs", cmd_rrspam))
    app.add_handler(PrefixHandler("-", "srs", cmd_stoprrspam))
    app.add_handler(PrefixHandler("-", "rl", cmd_rrloop))
    app.add_handler(PrefixHandler("-", "srl", cmd_stoprrloop))
    app.add_handler(PrefixHandler("-", "mrr", cmd_multirr))
    app.add_handler(PrefixHandler("-", "smrr", cmd_stopmultirr))
    app.add_handler(PrefixHandler("-", "rb", cmd_rrbomb))
    app.add_handler(PrefixHandler("-", "bs", cmd_burstspam))

    # ---- Auto handler for react/reply ----
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_auto_react_reply), group=0)

# ---- Run all bots ----
async def run_all_bots():
    global all_apps, all_bot_instances
    for token in TOKENS:
        try:
            app = Application.builder().token(token).build()
            add_handlers(app)
            await app.initialize()
            bot = app.bot
            me = await bot.get_me()
            all_apps.append(app)
            all_bot_instances.append(bot)
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            print(f"🚀 Bot started: @{me.username} (ID: {me.id})")
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
    print(f"\n🎉 DRAGON BALL SUPER: KI LING ENGINE V5 online with {len(all_bot_instances)} bots!")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"⚡ Default speed: {_nc_send_gap:.3f}s (CHUD engine)")
    print("="*60)
    await asyncio.Event().wait()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   🐉 DRAGON BALL SUPER: KI LING ENGINE V5")
    print("   Goku • Vegeta • Trunks • Gohan • Broly")
    print("   MULTI-BOT MODE | LIGHT SPEED NC | NON-STOP")
    print("="*60)
    while True:
        try:
            asyncio.run(run_all_bots())
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user.")
            break
        except Exception as e:
            print(f"❌ Bot crashed: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)