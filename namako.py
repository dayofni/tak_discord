
import asyncio
import discord
import json

from discord.ext import tasks 

from tak.board              import TakBoard
from clients.discord_client import DiscordClient
from clients.playtak_client import PlaytakClient

GUILDS   = [1058966677729058846]
CHANNELS = [1058966677729058849]

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
        
        await asyncio.sleep(5)
        
        while True:
            
            playtak_msg = await playtak_cl.rec()
            
            if not playtak_msg:          # go into waiting mode
                await asyncio.sleep(0.5)
                continue
            
            print(playtak_msg)
            
            msg_parse = playtak_cl.parse_msg(playtak_msg)
            
            if not msg_parse:
                await asyncio.sleep(0.01) # There's probably another message after it, we shouldn't wait
                continue
            
            command_type = msg_parse["command_type"]
            
            # A new game has begun on playtak!
            
            if command_type == "new_game":
                
                embed = await self.generate_new_game_embed(msg_parse["data"])
                
                for channel in CHANNELS:
                    message = await discord_cl.send(channel, None, embed=embed)
                
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
                
                
                await discord_cl.edit(message, None, embed=embed)
            
            await asyncio.sleep(0.01) # Gets things quick
    
    async def generate_new_game_embed(self, data, top=25):
        
        out_format = self.EMBEDS["new_game"]
        
        player1, player2 = data["player_1"], data["player_2"]
        
        rank_p1, rating_p1 = playtak_cl.rankings[player1] if player1 in playtak_cl.rankings else (None, None)
        rank_p2, rating_p2 = playtak_cl.rankings[player2] if player2 in playtak_cl.rankings else (None, None)
        
        rating_str_p1 = (f"{rating_p1}" if rating_p1 else "unrated") + (f", #{rank_p1}" if rank_p1 and rank_p1 <= top else "")
        rating_str_p2 = (f"{rating_p2}" if rating_p2 else "unrated") + (f", #{rank_p2}" if rank_p2 and rank_p2 <= top else "")
        
        players = f'**{player1}** ({rating_str_p1}) vs. **{player2}** ({rating_str_p2}) is live on [playtak.com](https://playtak.com)!'
        
        # Get game info
        
        game = f'**Parameters:** {data["size"]}s' + (f' w/ {inty_division(data["half_komi"], 2)} komi' if data["half_komi"] > 0 else "") + " | "
        time = f'{get_timestamp(data["time"])}+{get_timestamp(data["increment"])}'
        
        extra_time = "" if not data["extra_time_amount"] else f' (+{get_timestamp(data["extra_time_amount"])}@{data["extra_time_move"]})'
        
        std_stones = TakBoard(6, 0).RESERVE_COUNTS[data["size"]]
        stones = ""
        
        if std_stones != [data["pieces"], data["capstones"]]:
        
            capstone = "capstone" if data["capstones"] == 1 else "capstones"
            stones = f'\n**Altered counts:** {data["pieces"]} pieces, {data["capstones"]} {capstone}.'
        
        # Game result
        result = "**Result:** Ongoing"
        if data["result"]:
            result = f'**Result:** {data["result"]} ([playtak.com](https://playtak.com/games/{data["game_no"]}/playtakviewer) or [ptn.ninja](https://playtak.com/games/{data["game_no"]}/ninjaviewer))'
        
        parameters = players + "\n\n" + game + time + extra_time + stones + "\n" + result
        out_format["description"] = parameters
        
        #image_link = await generate_image_link(data["no"])
        #out_format["image"] = {"url": image_link}

        return discord.Embed.from_dict(out_format)




if __name__ == "__main__":
    namako = NamakoBot()
    asyncio.run(namako.start())