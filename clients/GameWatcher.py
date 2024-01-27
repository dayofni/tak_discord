import random
from urllib.parse import quote_plus

import websockets
import asyncio

from tak.board import TakBoard

URI = "ws://www.playtak.com:9999/ws"


CHARS = [chr(i+97) for i in range(26)] #all characters allowed for random tokens (a-z)

#this class creates a guest login and keeps track of a single game
class GameWatcher:

    tokens = []

    def __init__(self, gameId, data):
        self.gameId = gameId
        self.data = data
        self.moves = []

        self.player = "white"
        self.engine = TakBoard(data["size"], data["half_komi"])


        #create and log a unique token
        self.token = random.choices(CHARS, k=20)
        while self.token in self.tokens:
            self.token = random.choices(CHARS, k=20)

        self.tokens.append(self.token)

        # login using token, and start observing game
        async with websockets.connect("ws://playtak.com:9999/ws", subprotocols=["binary"], ping_timeout=None) as ws:
            # the idea is that unique tokens create unique guest accounts, lets hope thats in fact the case
            await ws.send(f"Login Guest {self.token}")
            await ws.send(f"Observe {gameId}")

            self.mainLoop(ws)

    def mainLoop(self, ws):
        while True:
            msg = ws.recv().decode()[:-1]

            if not msg.startswith(f"Game#{self.gameId}"): continue #unimportant message

            msg = msg.split()[1:]
            match msg:
                case ["M", sq1, sq2, *drops]:
                    self.makeMove(msg)

                case ["P", sq, *piece]:
                    self.makeMove(msg)

                case ["Undo"]:
                    self.undoMove()

                case ["Abandoned.", player, "quit"]:
                    pass #todo parse game end

                case ["Over", result]:
                    pass #todo parse game end

    def makeMove(self, server_move):
        move = self.engine.server_to_move(server_move)
        self.moves.append(move)
        self.engine.make_move(move, self.player)
        self.player = self.engine.invert_player(self.player)


    def undoMove(self):
        move = self.moves[-1]
        self.moves = self.moves[:-1]
        self.player = self.engine.invert_player(self.player)
        self.engine.undo_move(move, self.player)


    def generate_image_link(self):
        size, half_komi = self.data["size"], self.data["half_komi"]
        caps, flats = self.data["capstones"], self.data["pieces"]

        # have to ensure compat with URL
        player_1, player_2 = quote_plus(self.data["player_1"]), quote_plus(self.data["player_2"])
        theme = quote_plus(self.THEME)

        tps = quote_plus(self.engine.position_to_TPS())  # quote_plus to ensure URL compat

        last_move = "&hl=" + quote_plus(self.engine.move_to_ptn(self.moves[-1]))

        return f"https://tps.ptn.ninja/?tps={tps}&imageSize=sm&caps={caps}&flats={flats}&player1={player_1}&player2={player_2}&name=game.png&theme={theme}" + last_move

