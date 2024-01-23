
import asyncio
import discord
import json

from discord.ext import tasks 

from tak.board              import TakBoard
from clients.discord_client import DiscordClient
from clients.playtak_client import PlaytakClient

GUILDS   = [1058966677729058846]
CHANNELS = [1058966677729058849]
ROLE     = 1199150664446652468

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

@bot.slash_command(guild_ids=GUILDS)
async def ping(ctx):
    await ctx.respond(f"Pinged by <@{ctx.author.id}>.")

@tasks.loop(seconds=15)
async def update_rankings():
    playtak_cl.update_rankings()

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

class NamakoBot:
    
    def __init__(self):
        
        with open("data/secrets.json") as f:
            self.SECRETS = json.loads(f.read())

        with open("data/embeds.json") as f:
            self.EMBEDS = json.loads(f.read())

        with open("data/theme.json") as f:
            self.THEME = f.read()
        
        self.current_games = {}
    
    async def start(self):
        
        await asyncio.gather(
            
            # Log into Discord and Playtak
            discord_cl.main(self.SECRETS["BotToken"]),
            playtak_cl.main(self.SECRETS["BotUsername"], self.SECRETS["BotPassword"]),
            
            # Run NamakoBot!
            self.main()
            
        )
    
    async def main(self):
        
        # Ensure both Playtak and Discord have connected
        
        while not (playtak_cl.ready and discord_cl.ready):
            await asyncio.sleep(0.1)
        
        while True:
            
            playtak_msg = await playtak_cl.rec()
            
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
                
                embed = await self.generate_new_game_embed(msg_parse["data"])
                
                for channel in CHANNELS:
                    message = await discord_cl.send(channel, f"<@&{ROLE}>", embed=embed)
                
                self.current_games[msg_parse["data"]["game_no"]] = {
                    "message":   message,
                    "game_data": msg_parse["data"]
                }

            
            elif command_type == "end_game":
                
                game = await playtak_cl.get_playtak_game(msg_parse["data"]["game_no"])
                
                result  = game["result"]
                data    = msg_parse["data"] | {"result": result}
                message = self.current_games[msg_parse["data"]["game_no"]]["message"]
                embed   = await self.generate_new_game_embed(data)
                
                
                await discord_cl.edit(message, f"<@&{ROLE}>", embed=embed)
            
            await asyncio.sleep(0.01) # Gets things quick
    
    async def generate_new_game_embed(self, data, top=25):
        
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

        return discord.Embed.from_dict(out_format)
    
    def generate_rating_str(self, player_name: str, top=25):
        
        rank, rating = playtak_cl.rankings[player_name] if (player_name in playtak_cl.rankings) else (None, None)
        
        return (f"{rating}" if rating else "unrated") + (f", #{rank}" if rank and rank <= top else "")




if __name__ == "__main__":
    namako = NamakoBot()
    asyncio.run(namako.start())