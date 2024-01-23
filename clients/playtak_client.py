
import aiohttp
import asyncio
import websockets

from typing import Optional

class PlaytakClient:
    
    def __init__(self):
        
        self.rankings = {}
        
        self.ws = None
        
        self.ready = False
    
    #? Essential functions
    
    async def send(self, msg: str):
        await self.ws.send(msg)
    
    async def rec(self, timeout=1) -> Optional[str]:
        
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            msg = msg.decode()[:-1] # Removes the linefeed
            
        except asyncio.exceptions.TimeoutError:
            return None

        return msg
    
    #? Main function loop
    
    async def main(self, username, password):
        
        async with websockets.connect("ws://playtak.com:9999/ws", subprotocols=["binary"], ping_timeout=None) as ws:
            
            self.ws = ws
            
            await self.log_into_playtak(username, password)
            
            await self.update_rankings()
            
            self.ready = True
            
            await self.keep_alive() # Keeps the connection alive, makes sure the Tak server gets its oh so important PINGs
    
    async def log_into_playtak(self, username: str, password: str):
    
        msg = None
        while msg != "Login or Register": # Wait for the server to boot
            msg = await self.rec()

        # Now we can log in

        login = f"Login {username} {password}"
        await self.send(login)

        welcome_msg = f"Welcome {username}!" # Once we get this, we know that we've logged in
        login_msg   = await self.rec()

        assert login_msg == welcome_msg, "Invalid username or password!" # If we don't... well, you've messed up the login sequence

        print(f"Playtak: Logged in as {username}!") # Show that we've logged into the account
    
    async def keep_alive(self):
        
        while True:
            
            await asyncio.sleep(25)
            
            await self.send("PING")
    
    #? Extra features
    
    async def get_playtak_game(self, game_id: int) -> dict:

        url = f"https://api.playtak.com/v1/games-history/{game_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:

                if r.status == 200:
                    js = await r.json()
                    return js
    
    async def update_rankings(self):
        
        url = "https://playtak.com/ratinglist.json"
    
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
            
                if r.status == 200:
                    js = await r.json()
                
        self.rankings = {}
        
        rank = 1
        
        for player in js:
            name = player[0].split(" ")[0]
            
            rank_val = rank if name[-3:] != "Bot" else None
            
            self.rankings[name] = (rank_val, player[1])
            
            if rank_val:
                rank += 1
    
    def parse_msg(self, msg: str) -> dict:
        
        tokens = msg.strip().split(" ")
        
        if tokens[0] == "GameList":
            
            #? Game listing commands
            
            return {
                "command_type": "new_game" if tokens[1] == "Add" else "end_game",
                "data": self.parse_game_params(tokens[2:])
            }
        
        elif tokens[0][:5] == "Game#" and tokens[1] in ["P", "M"]:
            
            #? Move commands. Please note: you'll need to recreate the game from scratch when it ends.
                
            return {
                "command_type": "move",
                "data": tokens[1:]
            }
        
        return None

    def parse_game_params(self, params: list) -> dict:
        
        # size original_time incr komi pieces capstones unrated tournament
        
        keys = [
            "game_no", 
            "player_1", 
            "player_2", 
            "size", 
            "time", 
            "increment", 
            "half_komi", 
            "pieces", 
            "capstones", 
            "unrated", 
            "tournament", 
            "extra_time_move", 
            "extra_time_amount"
        ]

        return dict(zip(keys, [int(i) if i.isnumeric() else i for i in params])) | {"result": None}