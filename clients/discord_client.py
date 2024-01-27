
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
        
        self.known_channels = []
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
        
        got_channel = False
        
        # Is channel in cache?
        
        if channel_num in self.known_channels:
            channel = self.bot.get_channel(channel_num)
            got_channel = channel != None
        
        # Fetch channel manually (slower)
            
        if not got_channel:
            channel = await self.bot.fetch_channel(channel_num)
            got_channel = channel != None
        
        # Make sure we have a channel
        
        assert got_channel, f"Couldn't find channel {channel_num}."
        
        # Add channel to cache
        
        self.known_channels.append(channel_num)
        
        message = await channel.send(msg_str, embed=embed)
        
        return message
    
    async def edit(self, message: discord.Message, msg_str: str, embed: discord.Embed, timeout=1) -> discord.Message:
        
        try:
            new_message = await asyncio.wait_for(message.edit(msg_str, embed=embed), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        
        return new_message
    
    