
import asyncio
import discord
import json

from clients.GameWatcher import GameWatcher
from clients.discord_client import DiscordClient
from clients.playtak_client import PlaytakClient

from discord import TextChannel


# Guilds included because global commands take ages to start up.
# Will be removed once I release 1.0.

KNOWN_GUILDS = [1201101141115674694]

GUILDS   = {1201101141115674694: 1201108655110639626}

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


def ratingStr(player_name: str, top=25):
    rank, rating = playtak_cl.rankings[player_name] if (player_name in playtak_cl.rankings) else (None, None)
    return (f"{rating}" if rating else "unrated") + (f", #{rank}" if rank and rank <= top else "")

#? Namako [Playtak Bridge]

class NamakoBot:
    
    def __init__(self):
        
        with open("data/secrets.json") as f:
            self.SECRETS = json.loads(f.read())
        
        self.current_games = set()


    async def start(self):
        
        await asyncio.gather(
            
            # Log into Discord and Playtak
            discord_cl.main(self.SECRETS["BotToken"]),
            playtak_cl.main(self.SECRETS["BotUsername"], self.SECRETS["BotPassword"]),
            
            # Run NamakoBot!
            self.main(),
        )
    
    async def main(self):
        
        global UPDATE_IMAGES
        
        # Ensure both Playtak and Discord have connected
        
        while not (playtak_cl.ready and discord_cl.ready):
            await asyncio.sleep(1)
        
        while True:
            msg = (await playtak_cl.ws.recv()).decode()[:-1] #no reason to timeout i think?

            if not msg.startswith("GameList Add"): # The GameWatcher can handle the game end
                continue

            data = msg.split()[2:]
            data = playtak_cl.parse_game_params(data)

            # A new game has begun on playtak!
            player_1_rank = ratingStr(data['player_1'])
            player_2_rank = ratingStr(data['player_2'])

            header = f"**{data['player_1']}** ({player_1_rank}) vs. **{data['player_2']}** ({player_2_rank}) is live on [playtak.com](https://playtak.com)!\n"

            gw = GameWatcher(data, header, discord_cl, GUILDS)
            task = asyncio.create_task(gw.start())
            self.current_games.add(task) # keep a hard reference here, so the garbage-collector doesn't kill it
            task.add_done_callback(self.current_games.discard) # task removes itself when done

if __name__ == "__main__":
    namako = NamakoBot()
    asyncio.run(namako.start())