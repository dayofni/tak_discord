
# Standard library

import json
import logging

# 3rd party libraries

import aiohttp
import asyncio
import discord
import websockets


#? CONSTANTS

with open("data/secrets.json") as f:
    SECRETS = json.loads(f.read())

with open(("data/embeds.json")) as f2:
    EMBEDS = json.loads(f2.read())

STANDARD_PIECES = {
    3: [10, 0],
    4: [15, 0],
    5: [21, 1],
    6: [30, 1],
    7: [40, 2],
    8: [50, 2]
}

#? GLOBALS

bot = discord.Bot()

game_data = {}


#? LOGGING

logging.basicConfig(
    level=logging.INFO,
    filename="namako.log",
    filemode="w"
)

logging.info("NamakoBot-Discord initialised.")



#! ----------------------------

#!           PLAYTAK

#! ----------------------------


async def log_into_playtak(username: str, password: str, ws):
    
    msg = None
    while msg != "Login or Register": # Wait for the server to boot
        msg = await rec_playtak(ws)
    
    # Now we can log in
    
    login = f"Login {username} {password}"
    await asyncio.gather(send_playtak(login, ws))
    
    welcome_msg = f"Welcome {username}!" # Once we get this, we know that we've logged in
    login_msg   = await rec_playtak(ws)
    
    if login_msg != welcome_msg:
        logging.error("Invalid username or password given to playtak login!")
        
    assert login_msg == welcome_msg, "Invalid username or password!" # If we don't... well, you've messed up the login sequence
    
    print(f"Playtak: Logged in as {username}!") # Show that we've logged into the account
    
    logging.info(f"Playtak: Logged in as {username}!")

async def send_playtak(msg: str, ws):
    await ws.send(msg)

async def rec_playtak(ws, timeout=2):
    
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
        msg = msg.decode()[:-1] # Removes the linefeed
    except asyncio.exceptions.TimeoutError:
        return None
    
    return msg

async def get_playtak_game(game_id):

    url = f"https://api.playtak.com/v1/games-history/{game_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            
            if r.status == 200:
                js = await r.json()
                return js


#! ----------------------------

#!           DISCORD

#! ----------------------------

@bot.event
async def on_ready():
    
    print(f"Discord: Logged in as {bot.user}!")
    logging.info(f"Discord: Logged in as {bot.user}!")

async def main():
    
    async with websockets.connect("ws://playtak.com:9999/ws", subprotocols=["binary"], ping_timeout=None) as ws:
        
        await log_into_playtak(
            username = SECRETS["BotUsername"], 
            password = SECRETS["BotPassword"],
            ws       = ws
        )
        
        await asyncio.gather(
            bot.start(SECRETS["BotToken"]),
            playtak_loop(ws)
        )

async def playtak_loop(ws):
    
    await asyncio.sleep(5)
    
    channel = await bot.fetch_channel(1058966677729058849)
    
    while True:
        
        msg_in = await rec_playtak(ws)
        
        if not msg_in:
            await asyncio.sleep(0.5)
            continue
        
        print(msg_in)
        
        parse = await parse_playtak_msg(msg_in)
        
        if parse and parse["action_type"] == "new_msg":
            
            msg_out = generate_out(parse)
            message = await channel.send(embed=msg_out)
            
            game_data[parse["data"]["no"]] = message
        
        elif parse and parse["action_type"] == "edit_msg":
            
            message = parse["message"]
            
            msg_out = generate_out(parse)
            
            message = await message.edit(embed=msg_out)
        
        await asyncio.sleep(0.01)

def generate_out(parse: dict, override={}):
    
    data = parse["data"] | override
    out_format = EMBEDS[parse["parse_type"]]["embeds"][0]
    
    if parse["parse_type"] == "new_game":
        
        # We need to generate a player string.
        
        players = f'**{data["player1"]}** vs. **{data["player2"]}** is live on [playtak.com](https://playtak.com)!'
        
        game = f'**Parameters:** {data["size"]}s' + (f' w/ {inty_division(data["komi"], 2)} komi' if data["komi"] > 0 else "") + " | "
        time = f'{get_timestamp(data["time"])}+{get_timestamp(data["increment"])}'
        extra_time = "" if not data["extra_time"] else f' (+{get_timestamp(data["extra_time"])}@{data["extra_time_move"]})'
        
        std_stones = STANDARD_PIECES[data["size"]]
        stones = ""
        
        if std_stones != [data["pieces"], data["capstones"]]:
            
            capstone = "capstone" if data["capstones"] == 1 else "capstones"
            
            stones = f'\n**Altered counts:** {data["pieces"]} pieces, {data["capstones"]} {capstone}.'
        
        result = "**Result:** Ongoing"
        
        if data["result"]:
            result = f'**Result:** {data["result"]} ([playtak.com](https://playtak.com/games/{data["no"]}/playtakviewer) or [ptn.ninja](https://playtak.com/games/{data["no"]}/ninjaviewer))'
        
        parameters = players + "\n\n" + game + time + extra_time + stones + "\n" + result
        
        out_format["description"] = parameters
    
    return discord.Embed.from_dict(out_format)
        
def inty_division(n, div):
     
    a = n / div
    
    if int(a) == a: return int(a)
    
    return a
        
def get_timestamp(sec):
    
    seconds = sec %  60
    minutes = sec // 60
    
    if seconds == 0 and minutes == 0:
        return "0s"
    
    minutes_format = ""
    seconds_format = "00"
    
    if minutes > 0:
        minutes_format = f"{minutes}:"
    
    if seconds > 0:
        digits = len(str(seconds))
        seconds_format = "0" * (2 - digits) + str(seconds)
    
    if minutes == 0:
        return f"{minutes_format}{seconds_format}s"
    
    return f"{minutes_format}{seconds_format}"

def parse_typical(tokens):
    
    ex_time_move = int(tokens[13]) if tokens[13] != "0" else None
    
    return {
        "no": int(tokens[2]),
        "player1": tokens[3],
        "player2": tokens[4],
        "size": int(tokens[5]),
        "time": int(tokens[6]),
        "increment": int(tokens[7]),
        "komi": int(tokens[8]),
        "pieces": int(tokens[9]),
        "capstones": int(tokens[10]),
        "tournament": tokens[12] == "1",
        "extra_time_move": ex_time_move,
        "extra_time": int(tokens[14]) if ex_time_move else None,
        "result": None
    }

async def parse_playtak_msg(msg: str, tournament_only=False):
    
    tokens = msg.strip().split()
    
    if tokens[:2] == "GameList Add".split():
        
        # GameList Add 600638 BeginnerBot dayofni 5         600  30        0    21     1         0       0          0             0        
        # Seek new     no     white       black   boardsize time increment komi pieces capstones unrated tournament extratimemove extratime
        
        parse = parse_typical(tokens)
        
        if tournament_only and not parse["tournament"]:
            return None
        
        return {
            "parse_type": "new_game",
            "action_type": "new_msg",
            "data": parse
        }
    
    elif tokens[:2] == "GameList Remove".split():
        
        game_num = int(tokens[2])
        
        if game_num not in game_data:
            return None
        
        parse = parse_typical(tokens)
        game = await get_playtak_game(game_num)
        message = game_data.pop(game_num)
        
        return {
            "parse_type": "new_game",
            "action_type": "edit_msg",
            "message": message,
            "data": parse | {"result": game["result"]}
        }
    
    return None

#! ----------------------------

#!            MAIN

#! ----------------------------


if __name__ == "__main__":
    asyncio.run(main())