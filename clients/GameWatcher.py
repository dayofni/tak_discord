import json
import random
from urllib.parse import quote_plus

import discord
import websockets

# from namako import playtak_cl, discord_cl, GUILDS
from tak.board import TakBoard

#playtak websocket uri
URI = "ws://www.playtak.com:9999/ws"

#default reserve counts by size
RESERVE_COUNTS = {
    3: [10, 0],
    4: [15, 0],
    5: [21, 1],
    6: [30, 1],
    7: [40, 2],
    8: [50, 2]
}

#all characters allowed for random tokens (a-z)
CHARS = [chr(i+97) for i in range(26)]

#role to ping
ROLE = 1201108541445001399

with open("data/embeds.json") as f:
    EMBEDS = json.loads(f.read())

with open("data/theme.json") as f:  # just need the string <3
    THEME = f.read()

def timestamp(t):
    return f"{t}s" if t < 60 else f"{t // 60}:{t % 60:0=2}"


#this class creates a guest login and keeps track of a single game
class GameWatcher:
    #currently active guest tokens
    tokens = []

    def __init__(self, data, header, discord_cl, guilds):
        self.gameId = data["game_no"]
        self.data = data
        self.head = header
        self.discord_cl = discord_cl
        self.guilds = guilds

        self.moves = []

        self.player = "white"
        self.engine = TakBoard(data["size"], data["half_komi"])


        #create and log a unique token
        self.token = ''.join(random.choices(CHARS, k=20))
        while self.token in self.tokens:
            self.token = ''.join(random.choices(CHARS, k=20))

        self.tokens.append(self.token)


        self.embed = self.generateEmbed()
        self.messages = []

    # Starts sending messages and kick off the mainloop
    async def start(self):
        for channel in self.guilds.values():
            message = await self.discord_cl.send(channel, f"<@&{ROLE}>", embed=self.embed)
            self.messages.append(message)

        # login using token, and start observing game
        async with websockets.connect("ws://playtak.com:9999/ws", subprotocols=["binary"], ping_timeout=None) as ws:
            # the idea is that unique tokens create unique guest accounts, lets hope thats in fact the case
            await ws.send(f"Login Guest {self.token}")
            await ws.send(f"Observe {self.gameId}")

            print(f"Started watching {self.gameId}")

            await self.mainLoop(ws)

        #we always get an error here, but i cant catch it, and it doesnt stop the program, so its fine i guess?
        #it just clogs the console ;-;

        print(f"Ended watching {self.gameId}")


    # Main listener coroutine
    async def mainLoop(self, ws):
        async for msg in ws:
            msg = msg.decode()[:-1]
            if msg.startswith(f"GameList Remove {self.gameId}"):
                # if we receive the remove, we usually won't receive the Game Over after that
                # so calculate result manually
                self.data['result'] = self.engine.generate_win_str()
                self.data['result'] = self.data['result'] if self.data['result'] is not None else "unknown"
                break

            if not msg.startswith(f"Game#{self.gameId}"):
                continue


            msg = msg.split()[1:]
            match msg:
                case ["M", *_] | ["P", *_]:
                    self.makeMove(msg)
                    await self.updateEmbed()

                case ["Undo"]:
                    self.undoMove()
                    await self.updateEmbed()

                case ["Abandoned.", player, "quit"]:
                    self.data["result"] = "1-0" if player == self.data["player_1"] else "0-1"
                    await self.cleanUp()
                    break

                case ["Over", result]:
                    self.data["result"] = result
                    await self.cleanUp()
                    break


    def makeMove(self, server_move):
        move = self.engine.server_to_move(server_move, self.player)
        self.moves.append(move)
        self.engine.make_move(move, self.player)
        self.player = self.engine.invert_player(self.player)

    def undoMove(self):
        move = self.moves[-1]
        self.moves = self.moves[:-1]
        self.player = self.engine.invert_player(self.player)
        self.engine.undo_move(move, self.player)

    def generateImageLink(self):
        size, half_komi = self.data["size"], self.data["half_komi"]
        caps, flats = self.data["capstones"], self.data["pieces"]

        # have to ensure compat with URL
        player_1, player_2 = quote_plus(self.data["player_1"]), quote_plus(self.data["player_2"])
        theme = quote_plus(THEME)

        tps = quote_plus(self.engine.position_to_TPS())  # quote_plus to ensure URL compat


        last_move = "&hl=" + quote_plus(self.engine.move_to_ptn(self.moves[-1])) if len(self.moves) > 0 else ""

        return f"https://tps.ptn.ninja/?tps={tps}&imageSize=sm&caps={caps}&flats={flats}&player1={player_1}&player2={player_2}&name=game.png&theme={theme}" + last_move

    def generateEmbed(self, top=25):

        out_format = EMBEDS["new_game"]
        desc = self.head + f"\n**Game ID:** {self.gameId}"

        # STANDARD PARAMETERS
        size = self.data["size"]
        komi = f" w/ {self.data['half_komi']/2:g} komi" if self.data['half_komi'] > 0 else ""

        extra_time = "" if not self.data["extra_time_amount"] else f'(+{timestamp(self.data["extra_time_amount"])}@{self.data["extra_time_move"]})'
        time_str = f"{timestamp(self.data['time'])}+{timestamp(self.data['increment'])} {extra_time}"

        desc += f"\n**Parameters:** {size}s {komi} | {time_str}"

        # STONE COUNTS
        pieces = self.data["pieces"]
        capstones = self.data["capstones"]

        std_stones = RESERVE_COUNTS[size]

        if std_stones != [pieces, capstones]:
            pl_capstone = "capstone" if self.data["capstones"] == 1 else "capstones"
            desc += f"\n**Altered counts:** {pieces} pieces, {capstones} {pl_capstone}."

        # GAME RESULT
        result_str = "Ongoing"
        if self.data["result"]:
            link_str = f"([playtak.com](https://playtak.com/games/{self.gameId}/playtakviewer) or [ptn.ninja](https://playtak.com/games/{self.gameId}/ninjaviewer))"
            result_str = f"{self.data['result']} {link_str}"
        desc += f"\n**Result:** {result_str}"

        out_format["description"] = desc

        # IMAGE
        image_url = self.generateImageLink()

        out_format["image"] = {"url": image_url}

        return discord.Embed.from_dict(out_format)

    async def updateEmbed(self):
        embed = self.generateEmbed()
        for message in self.messages:
            await self.discord_cl.edit(message, embed=embed)

    async def cleanUp(self):
        await self.updateEmbed()
        self.tokens.remove(self.token)
