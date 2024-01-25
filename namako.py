
import asyncio
import discord
import json

from tak.board              import TakBoard
from clients.discord_client import DiscordClient
from clients.playtak_client import PlaytakClient

from discord import TextChannel

from urllib.parse import quote_plus


# Guilds included because global commands take ages to start up.
# Will be removed once I release 1.0.

KNOWN_GUILDS = [1058966677729058846] # , 176389490762448897] 

GUILDS   = {}

ROLE     = 1199150664446652468

UPDATE_IMAGES = False

RESERVE_COUNTS = {
    3: [10, 0],
    4: [15, 0],
    5: [21, 1],
    6: [30, 1],
    7: [40, 2],
    8: [50, 2]
}

bot = discord.Bot()
discord_cl = DiscordClient(bot=bot)
playtak_cl = PlaytakClient()

ready = False

#? Slash commands

@bot.event
async def on_ready():
    global ready
    
    if not ready:
        print(f"Discord: Logged in as {bot.user}!")
        ready = True

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def ping(ctx):
    await ctx.respond(f"Pinged by <@{ctx.author.id}>.")

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def set_channel(ctx, channel: TextChannel):
    guild = ctx.guild.id
    GUILDS[guild] = channel.id
    await ctx.respond(f"Output channel set to channel {channel.id}.")

#? Namako [Playtak Bridge]

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

class TaskScheduler:
    
    def __init__(self):
        
        self.tasks = []
    
    async def main(self):
        
        while True:
            
            await asyncio.sleep(1)
            
            for task in self.tasks:
                task["last_run"] += 1
                
                if task["last_run"] >= task["interval"]:
                    task["function"]()
                    task["last_run"] = 0
    
    def schedule_task(self, function, interval_sec: int):
        
        self.tasks.append({
            "function": function,
            "interval": interval_sec,
            "last_run": 0
        })


def update_imgs():
    global UPDATE_IMAGES
    UPDATE_IMAGES = True

class NamakoBot:
    
    def __init__(self):
        
        with open("data/secrets.json") as f:
            self.SECRETS = json.loads(f.read())

        with open("data/embeds.json") as f:
            self.EMBEDS = json.loads(f.read())

        with open("data/theme.json") as f: # just need the string <3
            self.THEME = f.read()
        
        self.current_games = {}
        self.queue = []
        self.scheduler = TaskScheduler()
        
        self.scheduler.schedule_task(update_imgs, 15)
    
    async def start(self):
        
        await asyncio.gather(
            
            # Log into Discord and Playtak
            discord_cl.main(self.SECRETS["BotToken"]),
            playtak_cl.main(self.SECRETS["BotUsername"], self.SECRETS["BotPassword"]),
            
            # Run NamakoBot!
            self.main(),
            self.scheduler.main() # task scheduler
            
        )
    
    async def main(self):
        
        global UPDATE_IMAGES
        
        # Ensure both Playtak and Discord have connected
        
        while not (playtak_cl.ready and discord_cl.ready):
            await asyncio.sleep(0.1)
        
        while True:
            
            if UPDATE_IMAGES:
                await self.update_all_embeds()
                continue
            
            if not self.queue:
                playtak_msg = await playtak_cl.rec()
            
            else:
                playtak_msg = self.queue.pop(0)
            
            if not playtak_msg:          # go into waiting mode
                await asyncio.sleep(0.5)
                continue
            
            msg_parse = playtak_cl.parse_msg(playtak_msg)
            
            if msg_parse:
                print(playtak_msg)
            
            if not msg_parse:
                await asyncio.sleep(0.01) # There's probably another message after it, we shouldn't wait
                continue
            
            command_type = msg_parse["command_type"]
            
            # A new game has begun on playtak!
            
            if command_type == "new_game":
                
                game_id = msg_parse["data"]["game_no"]
                
                await self.handle_new_game(msg_parse, game_id)

            elif command_type == "end_game":
                
                game_id = msg_parse["data"]["game_no"]
                
                await self.handle_end_game(msg_parse, game_id)
                
                self.current_games.pop(game_id)
            
            await asyncio.sleep(0.01) # Gets things quick
    
    #? Image generation functions
    
    async def handle_new_game(self, msg, game_id):
        
        self.current_games[game_id] = { # hack to get this to work
            "game_data": msg["data"],
            "message":   None,
            "link":      None
        }
        
        embed = await self.generate_new_game_embed(game_id)
        
        for channel in GUILDS.values():
            message = await discord_cl.send(channel, f"<@&{ROLE}>", embed=embed)
        
        self.current_games[game_id]["message"] = message
    
    async def handle_end_game(self, msg, game_id):
        game = await playtak_cl.get_playtak_game(game_id)
                
        self.current_games[game_id]["game_data"] = msg["data"] | {"result": game["result"]}
                
        moves = [i.split(" ") for i in game["notation"].split(",")]
                
        self.current_games[game_id]["link"] = await self.generate_image_link(game_id, moves=moves)
                
        await self.update_embed(game_id, update_attach=False)
    
    async def update_embed(self, game_id, update_attach=False):
        
        message = self.current_games[game_id]["message"]
        embed   = await self.generate_new_game_embed(game_id, update_attach=update_attach)
                        
        await discord_cl.edit(message, f"<@&{ROLE}>", embed=embed)
    
    async def generate_new_game_embed(self, game_id, top=25, update_attach=True):
        
        data = self.current_games[game_id]["game_data"]
        
        out_format = self.EMBEDS["new_game"]
        
        player_1 = data["player_1"]
        player_2 = data["player_2"]
        
        player_1_rank = self.generate_rating_str(player_1, top=top)
        player_2_rank = self.generate_rating_str(player_2, top=top)
        
        game_id    = data["game_no"]
        size       = data["size"]
        komi       = inty_division(data["half_komi"], 2)
        result     = data["result"]
        
        time       = get_timestamp(data["time"])
        incr       = get_timestamp(data["increment"])
        extra_time = data["extra_time_amount"]
        extra_move = data["extra_time_move"]
        
        pieces     = data["pieces"]
        capstones  = data["capstones"]
        
        std_stones = RESERVE_COUNTS[size]
        
        komi_str = f" w/ {komi} komi" if komi > 0 else ""
        extra_time = "" if not extra_time else f' (+{get_timestamp(extra_time)}@{extra_move})'
        time_str   = f"{time}+{incr}" + extra_time
        
        pl_capstone = "capstone" if data["capstones"] == 1 else "capstones"
        stone_str   = ""
        result_str  = "**Result:** Ongoing"
        
        if std_stones != [pieces, capstones]:
            stone_str = f"**Altered counts:** {pieces} pieces, {capstones} {pl_capstone}."
        
        if data["result"]:
            link_str   = f"([playtak.com](https://playtak.com/games/{game_id}/playtakviewer) or [ptn.ninja](https://playtak.com/games/{game_id}/ninjaviewer))"
            result_str = f"**Result:** {result} {link_str}"
        
        parameters = [
            f"**{player_1}** ({player_1_rank}) vs. **{player_2}** ({player_2_rank}) is live on [playtak.com](https://playtak.com)!\n",
            f"**Game ID:** {game_id}",
            f"**Parameters:** {size}s {komi_str} | {time_str}",
            stone_str,
            result_str
        ]
        
        out_format["description"] = "\n".join([i for i in parameters if i])
        
        if update_attach:
            image_url = await self.generate_image_link(game_id)
            
            if not image_url:
                image_url = self.current_games[game_id]["link"]
                
        
        else:
            image_url = self.current_games[game_id]["link"]
        
        out_format["image"] = {"url": image_url}

        return discord.Embed.from_dict(out_format)

    def generate_rating_str(self, player_name: str, top=25):
        
        rank, rating = playtak_cl.rankings[player_name] if (player_name in playtak_cl.rankings) else (None, None)
        
        return (f"{rating}" if rating else "unrated") + (f", #{rank}" if rank and rank <= top else "")

    async def update_all_embeds(self):
        
        global UPDATE_IMAGES
        
        for game_no, game in self.current_games.items():
            
            data = game["game_data"]
            await self.update_embed(game_no, data)
        
        UPDATE_IMAGES = False
    
    async def generate_image_link(self, game_id, moves=None):
        
        
        
        if not moves:
            moves = await self.get_game_moves(game_id)
        
        if moves == None:
            return None
        
        game = self.current_games[game_id]["game_data"]
        
        size, half_komi    = game["size"],                 game["half_komi"]
        caps, flats        = game["capstones"],            game["pieces"]
        player_1, player_2 = quote_plus(game["player_1"]), quote_plus(game["player_2"]) # have to ensure compat with URL
        theme              = quote_plus(self.THEME)
        
        engine = TakBoard(size, half_komi)
        player = "white"
        
        move = None
        
        for server_move in moves:
            
            move = engine.server_to_move(server_move, player)
            
            engine.make_move(move, player)
            
            player = engine.invert_player(player)
        
        tps       = quote_plus(engine.position_to_TPS()) # quote_plus to ensure URL compat
        last_move = ""
        
        if move != None:
            last_move = "&hl=" + quote_plus(engine.move_to_ptn(move))
        
        
        url = f"https://tps.ptn.ninja/?tps={tps}&imageSize=sm&caps={caps}&flats={flats}&player1={player_1}&player2={player_2}&name=game.png&theme={theme}" + last_move
        
        return url
    
    async def get_game_moves(self, game_id: int) -> list[list[str]]:
        
        # Observe game
        
        msg   = "blank"
        moves = []
        
        await playtak_cl.send(f"Observe {game_id}")
        
        while msg:
            
            msg = await playtak_cl.rec()

            if not msg: # just found a None - couldn't get the message through
                break
            
            tokens = msg.split(" ")
            
            if tokens[0][:5] != "Game#":          # Not a Game command
                
                self.queue.append(msg)
                
                await asyncio.sleep(0.01)
                continue
            
            command = tokens[1]
            
            if command not in ["P", "M", "Undo"]: # Not a place/move command (coming from Observe). Undo is kept because weird shit could happen.
                await asyncio.sleep(0.01)
                continue
            
            if command in ["P", "M"]:
                moves.append(tokens[1:])
            
            elif command == "Undo" and len(moves) > 1:
                moves.pop(-1)
            
            elif command in ["Abandoned.", "Over"]: # EXIT. ABORT. GAME'S OVER, DON'T SPEND TIME HERE
                
                await playtak_cl.send(f"Unobserve {game_id}")
                
                print("Game over, exiting...")
                
                return None
            
            await asyncio.sleep(0.01)
        
        await playtak_cl.send(f"Unobserve {game_id}")
        
        return moves




if __name__ == "__main__":
    namako = NamakoBot()
    asyncio.run(namako.start())