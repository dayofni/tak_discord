import random
from urllib.parse import quote_plus

import discord
import websockets
import asyncio

from namako import playtak_cl, discord_cl, GUILDS
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
ROLE = ""

def timestamp(t):
    return f"{t}s" if t < 60 else f"{t // 60}:{t % 60:0=2}"


def ratingStr(player_name: str, top=25):
    rank, rating = playtak_cl.rankings[player_name] if (player_name in playtak_cl.rankings) else (None, None)
    return (f"{rating}" if rating else "unrated") + (f", #{rank}" if rank and rank <= top else "")


#this class creates a guest login and keeps track of a single game
class GameWatcher:
    #currently active guest tokens
    tokens = []

    def __init__(self, gameId, data, theme, template):
        self.gameId = gameId
        self.data = data
        self.theme = theme
        self.template = template

        self.moves = []

        self.player = "white"
        self.engine = TakBoard(data["size"], data["half_komi"])


        #create and log a unique token
        self.token = random.choices(CHARS, k=20)
        while self.token in self.tokens:
            self.token = random.choices(CHARS, k=20)

        self.tokens.append(self.token)


        self.embed = await self.generateEmbed()
        self.messages = []

        for channel in GUILDS.values():
            message = await discord_cl.send(channel, f"<@&{ROLE}>", embed=self.embed)
            self.messages.append(message)

        # login using token, and start observing game
        async with websockets.connect("ws://playtak.com:9999/ws", subprotocols=["binary"], ping_timeout=None) as ws:
            # the idea is that unique tokens create unique guest accounts, lets hope thats in fact the case
            await ws.send(f"Login Guest {self.token}")
            await ws.send(f"Observe {gameId}")

            await self.mainLoop(ws)

    async def mainLoop(self, ws):
        while True:
            msg = (await ws.recv()).decode()[:-1]

            if not msg.startswith(f"Game#{self.gameId}"): continue #unimportant message

            msg = msg.split()[1:]
            match msg:
                case ["M", *_] | ["P", *_]:
                    self.makeMove(msg)
                    self.updateEmbed()

                case ["Undo"]:
                    self.undoMove()
                    self.updateEmbed()

                case ["Abandoned.", player, "quit"]:
                    self.cleanUp()
                    break

                case ["Over", result]:
                    self.cleanUp()
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
        theme = quote_plus(self.theme)

        tps = quote_plus(self.engine.position_to_TPS())  # quote_plus to ensure URL compat

        last_move = "&hl=" + quote_plus(self.engine.move_to_ptn(self.moves[-1]))

        return f"https://tps.ptn.ninja/?tps={tps}&imageSize=sm&caps={caps}&flats={flats}&player1={player_1}&player2={player_2}&name=game.png&theme={theme}" + last_move

    def generateEmbed(self, top=25):

        out_format = self.template

        # PLAYER DATA
        player_1 = self.data["player_1"]
        player_2 = self.data["player_2"]

        player_1_rank = ratingStr(player_1, top=top)
        player_2_rank = ratingStr(player_2, top=top)

        desc = f"**{player_1}** ({player_1_rank}) vs. **{player_2}** ({player_2_rank}) is live on [playtak.com](https://playtak.com)!\n"
        desc += f"\n**Game ID:** {self.gameId}"

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

    def updateEmbed(self):
        for message in self.messages:
            embed = self.generateEmbed()
            await discord_cl.edit(message, embed=embed)

    def cleanUp(self):
        self.tokens.remove(self.token)