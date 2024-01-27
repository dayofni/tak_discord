
import asyncio
import discord

from discord.ext import tasks

class DiscordClient:
    
    """
    Connects to discord.com through the bot interface.
    
    To start the client, use `asyncio.run(DiscordClient.main(__token__))`.
    
    That is, unless you have something else in mind. In which case, who am I to stop you?
    """
    
    def __init__(self, bot=None):
        self.ready = False
        
        if bot == None:
            self.bot = discord.Bot()
        
        else:
            self.bot = bot
        
    
    async def main(self, token):
        
        self.ready = True
        
        await self.bot.start(token)
    
    async def send(self, channel_num: int, msg_str: str, embed: discord.Embed) -> discord.Message:
        
        """
        Sends a message (`msg_str` & `embed`) to the given channel (`channel_num`).
        """

        # Is channel in cache?
        channel = self.get_channel(channel_num)

        # If it's not, fetch it
        if channel is None:
            channel = await self.bot.fetch_channel(channel_num)

        assert channel is not None, f"Couldn't find channel {channel_num}."

        return await channel.send(msg_str, embed=embed)

    async def edit(self, message: discord.Message, msg_str: str, embed: discord.Embed) -> discord.Message:

        return await message.edit(msg_str, embed=embed)
    