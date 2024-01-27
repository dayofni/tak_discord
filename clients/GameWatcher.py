import random
import websockets
import asyncio

URI = "ws://www.playtak.com:9999/ws"


CHARS = [chr(i+97) for i in range(26)] #all characters allowed for random tokens (a-z)




#this class creates a guest login and keeps track of a single game
class GameWatcher:

    tokens = []

    def __init__(self, gameId):
        self.gameId = gameId

        self.moves = []

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
                    self.moves.append(msg) #todo, better repr

                case ["P", sq, *piece]:
                    self.moves.append(msg)  # todo, better repr

                case ["Undo"]:
                    self.moves = self.moves[:-1]

                case ["Abandoned.", player, "quit"]:
                    pass #todo parse game end

                case ["Over", result]:
                    pass #todo parse game end