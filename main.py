from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    Message,
)
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant, RPCError, FloodWait
from asyncio import sleep
from os import environ, remove
from threading import Thread
from json import load
from re import search
from time import time
from db import DB
import bypasser
import freewall

# Load config data
with open("config.json", "r") as f:
    DATA: dict = load(f)

def getenv(var):
    return environ.get(var) or DATA.get(var, None)

# Bot setup
bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
channel_id = int(getenv("CHANNEL_ID"))  # Ensure CHANNEL_ID is an integer

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# DB setup
db_api = getenv("DB_API")
db_owner = getenv("DB_OWNER")
db_name = getenv("DB_NAME")
try:
    database = DB(api_key=db_api, db_owner=db_owner, db_name=db_name)
except:
    print("Database is not set")
    database = None

# Force subscribe handler
async def handle_force_sub(bot: Client, cmd: Message):
    try:
        user = await bot.get_chat_member(chat_id=channel_id, user_id=cmd.from_user.id)
        if user.status in (ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED):
            await cmd.reply_text(
                text="Sorry, You are Banned to use me. Contact my [Support Group](https://t.me/greymatters_bots_discussion).",
                disable_web_page_preview=True,
            )
            return 0
    except UserNotParticipant:
        try:
            await cmd.reply_text(
                text="**Please Join My Updates Channel to use me!**\n\n"
                     "Due to Overload, Only Channel Subscribers can use the Bot!",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🤖 Join Updates Channel",
                            url="t.me/bypassbot_update",
                        )
                    ],
                ]),
            )
            return 0
        except RPCError as e:
            print(e.MESSAGE)
    except FloodWait as ee:
        await sleep(ee.value + 3)
        await cmd.reply_text("Try later, flooded!")
        return 0
    except Exception:
        await cmd.reply_text(
            text="Something went Wrong! Contact my [Support Group](https://t.me/bypassbot_update)",
            disable_web_page_preview=True,
        )
        return 0
    return 1

# Link verification
async def verifylink(url: str) -> int:
    return 1 if url and "//t.me/" not in url and url.startswith("https://") else 0

# Handle index links
def handleIndex(ele: str, message: Message, msg: Message):
    result = bypasser.scrapeIndex(ele)
    try:
        app.delete_messages(message.chat.id, msg.id)
    except:
        pass
    if database and result:
        database.insert(ele, result)
    for page in result:
        app.send_message(
            message.chat.id,
            page,
            reply_to_message_id=message.id,
            disable_web_page_preview=True,
        )

# Bypassing logic
def loopthread(message: Message, otherss=False):
    urls = []
    texts = message.caption if otherss else message.text
    if not texts:
        return
    urls = [ele for ele in texts.split() if "http://" in ele or "https://" in ele]
    if not urls:
        return

    msg = app.send_message(message.chat.id, "🔎 __bypassing...__", reply_to_message_id=message.id)
    strt = time()
    links = ""
    temp = None

    for ele in urls:
        if database:
            df_find = database.find(ele)
        else:
            df_find = None
        if df_find:
            temp = df_find
        else:
            try:
                temp = bypasser.shortners(ele)
            except Exception as e:
                temp = "**Error**: " + str(e)
        if temp:
            if not df_find and "http" in temp and database:
                database.insert(ele, temp)
            links += temp + "\n"

    end = time()
    app.edit_message_text(
        message.chat.id, msg.id, f"__{links}__", disable_web_page_preview=True
    )

# Bot commands
@app.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await handle_force_sub(client, message):
        return
    await app.send_message(
        message.chat.id,
        f"👋 Hi **{message.from_user.mention}**, I am a Link Bypasser Bot! Send me supported links to get results.\nCheckout /help for more info.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌐 Join Channel", url="https://t.me/bypassbot_update"),
            ],
        ]),
        reply_to_message_id=message.id,
    )

@app.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    if not await handle_force_sub(client, message):
        return
    await app.send_message(
        message.chat.id,
        "I can bypass links for supported services. Just send me a link!",
        reply_to_message_id=message.id,
        disable_web_page_preview=True,
    )

@app.on_message(filters.text)
async def receive(client: Client, message: Message):
    if not await handle_force_sub(client, message):
        return
    Thread(target=lambda: loopthread(message), daemon=True).start()

# Run the bot
print("Bot Starting...")
app.run()
