
import asyncio
import discord
import json

from discord.ext import tasks 

from tak.board              import TakBoard
from clients.discord_client import DiscordClient
from clients.playtak_client import PlaytakClient

GUILDS = [1058966677729058846]

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

class NamakoBot:
    
    def __init__(self):
        
        with open("data/secrets.json") as f:
            self.SECRETS = json.loads(f.read())

        with open("data/embeds.json") as f:
            self.EMBEDS = json.loads(f.read())

        with open("data/theme.json") as f:
            self.THEME = f.read()
    
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
            
            #msg_parse = await playtak_cl.parse_msg(playtak_msg)
            
            await asyncio.sleep(0.01) # Gets things quick



if __name__ == "__main__":
    namako = NamakoBot()
    asyncio.run(namako.start())