
# KNOWN BUGS

1. Occasionally crashing from Playtak client (end frame). Needs to be fixed before full release.

2. Not showing as online occassionally? Eh, no big deal as it still works, but...

3. Discord heartbeat interrupted. A lot.

# TO DO

1. Add timeouts to *every* single thing interfacing with the internet, then apply a short (0.01s) cooldown to fix bugs.

2. Move `TaskScheduler()` to a seperate file. 

3. Learn how asyncio works. Like, not just the basics. And actually learn the thing this time.
  - What the fuck's a task?
  - Being able to run "threads" in parallel using websocket connections
  - Async file structure and classes - cogs?

4. Revamp Namako structure.
  - Work *with* async, not against it.

  - __Namako__:
    - Manage multiple playtak clients.

    - Main thread (Namako Login):
      - Manage temporary Guest subprocesses
    
    - Subprocesses (Guest login):
      - `Observe` games.
      - Generate images on command
      - Quit once not needed

  - __Discord__:
    - Let heartbeat continue during operation.
  
  - __Playtak__:
    - ...



# DATA

IDEA:

{
  "content": "@Tournament Spectator",
  "tts": false,
  "embeds": [
    {
      "id": 302228431,
      "description": "**dayofni** (1666) vs. **SABLE** (999) is live on [playtak.com](https://playtak.com)!\n---------------------------------------------------------------\n**Parameters:** 6s; 10:00+15\n**Tournament:** 2024 USTA Beginner's Tournament\n**Result:** Ongoing.",
      "fields": [],
      "author": {
        "name": "Playtak Tournament Game",
        "url": "https://playtak.com",
        "icon_url": "https://playtak.com/favicon.svg"
      },
      "color": 16713584,
      "image": {
        "url": "https://tps.ptn.ninja/?tps=x4,1,1/x2,2,1221121,121,1/1,1,21C,12C,1,x/x,2,1S,x2,2S/x2,2,1,x2/2,2,2,1,x2 2 23&imageSize=sm&moveNumber=23&stackCounts=false&caps=1&flats=30&player1=dayofni&player2=SABLE&hl=2e4%2B11&name=dayofni%20vs%20SABLE%206x6%20R-0%202024.01.09-22.21.40%20-%2044.png&theme=luna"
      }
    }
  ],
  "components": [],
  "actions": {},
  "username": "NamakoBot"
}

{"id":"namako","boardStyle":"grid2","boardChecker":false,"vars":{"piece-border-width":0},"colors":{"primary":"#ff388b","secondary":"#FFFFFF","ui":"#277357","accent":"#5d8f3c","panel":"#d9d9d9cc","board1":"#b39976","board2":"#a8906f","board3":"#998365","player1":"#dbdbdb","player1road":"#ffffff","player1flat":"#f2f2f2","player1special":"#ffffff","player1border":"#000000","player2":"#424242","player2road":"#2b2b2b","player2flat":"#2b2b2b","player2special":"#2b2b2b","player2border":"#000000","textLight":"#fafafacd","textDark":"#212121cd","umbra":"#00000055","bg":"#ffffffff","panelOpaque":"#d9d9d9ff","panelOpaqueHover":"#c5c5c5ff","panelClear":"#d9d9d900","panelClearHover":"#c5c5c500","player1clear":"#dbdbdb00","player2clear":"#42424200"},"primaryDark":true,"secondaryDark":false,"board1Dark":true,"board2Dark":true,"isDark":true,"accentDark":true,"panelDark":false,"player1Dark":false,"player2Dark":true,"name":"Namako"}

https://tps.ptn.ninja/?tps=x4,1,1/21,1,2221,1,121,1/1,12,21C,12C,1,x/x2,1S,x2,2S/x2,2,1,x2/2,2,2,1,x2%202%2024&imageSize=sm&moveNumber=24&stackCounts=false&caps=1&flats=30&player1=dayofni&player2=SABLE&hl=6d5%3C312&name=dayofni%20vs%20SABLE%206x6%20R-0%202024.01.09-22.21.40%20-%2046.png&theme=%7B%22id%22%3A%22namako%22%2C%22boardStyle%22%3A%22grid2%22%2C%22boardChecker%22%3Afalse%2C%22vars%22%3A%7B%22piece-border-width%22%3A0%7D%2C%22colors%22%3A%7B%22primary%22%3A%22%23ff388b%22%2C%22secondary%22%3A%22%2300000000%22%2C%22board1%22%3A%22%23b39976%22%2C%22board2%22%3A%22%23a8906f%22%2C%22board3%22%3A%22%23998365%22%2C%22player1%22%3A%22%23dbdbdb%22%2C%22player1road%22%3A%22%23ffffff%22%2C%22player1flat%22%3A%22%23f2f2f2%22%2C%22player1special%22%3A%22%23ffffff%22%2C%22player1border%22%3A%22%23000000%22%2C%22player2%22%3A%22%23424242%22%2C%22player2road%22%3A%22%232b2b2b%22%2C%22player2flat%22%3A%22%232b2b2b%22%2C%22player2special%22%3A%22%232b2b2b%22%2C%22player2border%22%3A%22%23000000%22%2C%22textLight%22%3A%22%23ffffffff%22%2C%22textDark%22%3A%22%23000000ff%22%2C%22umbra%22%3A%22%2300000055%22%7D%2C%22player1Dark%22%3Afalse%2C%22player2Dark%22%3Atrue%2C%22secondaryDark%22%3Atrue%7D

What's necessary?

https://tps.ptn.ninja/?tps={tps}&komi={komi}&imageSize=sm&caps={caps}&flats={flats}&player1={player1}&player2={player2}&hl={last_move}&name=game.png&theme={theme}

https://tps.ptn.ninja/?tps={tps}&imageSize=sm&komi=1&hl=e4&name=6x6%20(1)%20-%202.png&theme=%7B%22id%22%3A%22namako%22%2C%22boardStyle%22%3A%22grid2%22%2C%22boardChecker%22%3Afalse%2C%22vars%22%3A%7B%22piece-border-width%22%3A0%7D%2C%22colors%22%3A%7B%22primary%22%3A%22%23ff388b%22%2C%22secondary%22%3A%22%2300000000%22%2C%22board1%22%3A%22%23b39976%22%2C%22board2%22%3A%22%23a8906f%22%2C%22board3%22%3A%22%23998365%22%2C%22player1%22%3A%22%23dbdbdb%22%2C%22player1road%22%3A%22%23ffffff%22%2C%22player1flat%22%3A%22%23f2f2f2%22%2C%22player1special%22%3A%22%23ffffff%22%2C%22player1border%22%3A%22%23000000%22%2C%22player2%22%3A%22%23424242%22%2C%22player2road%22%3A%22%232b2b2b%22%2C%22player2flat%22%3A%22%232b2b2b%22%2C%22player2special%22%3A%22%232b2b2b%22%2C%22player2border%22%3A%22%23000000%22%2C%22textLight%22%3A%22%23ffffffff%22%2C%22textDark%22%3A%22%23000000ff%22%2C%22umbra%22%3A%22%2300000055%22%7D%2C%22player1Dark%22%3Afalse%2C%22player2Dark%22%3Atrue%2C%22secondaryDark%22%3Atrue%7D

https://tps.ptn.ninja/?tps={tps}&imageSize=sm&moveNumber=1&stackCounts=false&komi=1&name=6x6%20(1)%20-%20-1-.png&theme=%7B%22id%22%3A%22namako%22%2C%22boardStyle%22%3A%22grid2%22%2C%22boardChecker%22%3Afalse%2C%22vars%22%3A%7B%22piece-border-width%22%3A0%7D%2C%22colors%22%3A%7B%22primary%22%3A%22%23ff388b%22%2C%22secondary%22%3A%22%2300000000%22%2C%22board1%22%3A%22%23b39976%22%2C%22board2%22%3A%22%23a8906f%22%2C%22board3%22%3A%22%23998365%22%2C%22player1%22%3A%22%23dbdbdb%22%2C%22player1road%22%3A%22%23ffffff%22%2C%22player1flat%22%3A%22%23f2f2f2%22%2C%22player1special%22%3A%22%23ffffff%22%2C%22player1border%22%3A%22%23000000%22%2C%22player2%22%3A%22%23424242%22%2C%22player2road%22%3A%22%232b2b2b%22%2C%22player2flat%22%3A%22%232b2b2b%22%2C%22player2special%22%3A%22%232b2b2b%22%2C%22player2border%22%3A%22%23000000%22%2C%22textLight%22%3A%22%23ffffffff%22%2C%22textDark%22%3A%22%23000000ff%22%2C%22umbra%22%3A%22%2300000055%22%7D%2C%22player1Dark%22%3Afalse%2C%22player2Dark%22%3Atrue%2C%22secondaryDark%22%3Atrue%7D

Game#no P Sq C|W 	                  The 'Place' move played by the other player in game number no. The format is same as the command from client to server
Game#no M Sq1 Sq2 no1 no2... 	      The 'Move' move played by the other player in game number no. The format is same as the command from client to server
Game#no Undo