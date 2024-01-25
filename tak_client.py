
# Standard library

import json
import logging

# Personal libaries

from tak.board import TakBoard

# 3rd party libraries

import aiohttp
import asyncio
import discord
import websockets

from discord.ext import tasks


#? CONSTANTS

STANDARD_PIECES = {
    3: [10, 0],
    4: [15, 0],
    5: [21, 1],
    6: [30, 1],
    7: [40, 2],
    8: [50, 2]
}

RATINGS = {}

#? GLOBALS

bot = discord.Bot()

game_data = {}


#? LOGGING

logging.basicConfig(
    level=logging.INFO,
    filename="namako.log",
    filemode="w"
)

logging.info("NamakoBot-Discord initialised.")


#! ----------------------------

#!           PLAYTAK

#! ----------------------------


async def generate_image_link(game_id, ws, timeout=0):
    
    global game_data
    
    game_settings = game_data[game_id]["settings"]
    
    board                 = TakBoard(game_settings["size"], game_settings["komi"])
    board.player_reserves = {player:[game_settings["pieces"], game_settings["capstones"]] for player in board.player_reserves}
    
    move = "Blank Message"
    
    await send_playtak(f'Observe {game_settings["no"]}', ws)
    
    # Observe game
    
    last_move = None
    
    player = "white"
    
    while move and move.split()[0] != f'Game#{game_settings["no"]}' and move.split()[1] not in ["P", "M"]:
        move = await rec_playtak(ws)
        await asyncio.sleep(0.01)
    
    while move:
        
        # Get move
        move = await rec_playtak(ws)
        print(move)
        
        if (not move) or (move.split()[0] != f'Game#{game_settings["no"]}') or (move.split()[1] not in ["P", "M"]):
            continue
        
        server_move = board.server_to_move(move.split()[1:], player)
        print(server_move)

        # Make move
        
        board.make_move(server_move, player)
        print("Board: ", board)
        
        player = board.invert_player(player)
        
        last_move = server_move
        
        await asyncio.sleep(0.01)
    
    # Unobserve game
    
    await send_playtak(f'Unobserve {game_settings["no"]}', ws)
    
    # Generate TPS
    
    tps = board.position_to_TPS()
    
    # Send to create image
    
    url = f'https://tps.ptn.ninja/?tps={quote_plus(tps)}&imageSize=sm&caps={game_settings["capstones"]}&flats={game_settings["pieces"]}&player1={game_settings["player1"]}&player2={game_settings["player2"]}&name=game.png&theme={quote_plus(THEME)}'
    
    url += f"&hl={quote_plus(board.move_to_ptn(last_move))}" if last_move else ""
    
    print(url)
    
    return url


#! ----------------------------

#!           DISCORD

#! ----------------------------


async def playtak_loop(ws):
    
    await asyncio.sleep(5)
    
    channel = await bot.fetch_channel(1058966677729058849)
    
    while True:
        
        msg_in = await rec_playtak(ws)
        
        if not msg_in:
            await asyncio.sleep(0.5)
            continue
        
        print(msg_in)
        
        parse = await parse_playtak_msg(msg_in)
        
        if parse:
            game_data[parse["data"]["no"]] = {"settings": parse["data"]}
        
        if parse and parse["action_type"] == "new_msg":
            
            msg_out = await generate_out(parse, ws)
            message = await channel.send(embed=msg_out)
            
            game_data[parse["data"]["no"]] = {
                "settings": parse["data"],
                "message": message
            }
        
        elif parse and parse["action_type"] == "edit_msg":
            
            message = parse["message"]
            
            msg_out = await generate_out(parse, ws)
            
            await message.edit(embed=msg_out)
        
        await asyncio.sleep(0.01)

#! ----------------------------

#!            MAIN

#! ----------------------------


if __name__ == "__main__":
    asyncio.run(update_rankings())
    asyncio.run(main())