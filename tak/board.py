
from itertools import permutations
from copy import deepcopy

RANDOM_SEED = [3141592653589, 644204232404]

def getrandbits(bits: int) -> int:
    
    """
    Get a psuedo-random number given two random int seeds.
    
    Implements XOR-shift algorithm. Exists because I don't want to mess up the `random` library.
    
    And may be vaguely faster.
    """
    
    global RANDOM_SEED
    
    limit = 1 << bits - 1
    
    seed = RANDOM_SEED[0]
    
    seed ^= seed >> 12
    seed ^= seed << 25
    seed ^= seed >> 27
    seed ^= RANDOM_SEED[1] - (RANDOM_SEED[1] >> 5)
    
    RANDOM_SEED.append(seed)
    del RANDOM_SEED[0]
    
    return seed % limit

class Stone:
    
    """
    A singular stone for the superb game of Tak.
    
    (what were you expecting???)
    """
    
    def __init__(self, colour: str, stone_type: str) -> None:
        
        self.colour = colour
        self.stone_type = stone_type
    
    def crush(self) -> None:
        
        """
        Capstone crush. Doesn't care if the stone is flat already.
        
        # ALL SHALL FALL TO THE ALMIGHTY CAPSTONE
        """
        
        self.stone_type = "flat"
    
    def __repr__(self) -> None:
        return f"<Stone {self.colour}, {self.stone_type}>"
    
    def __eq__(self, other) -> bool:
        return (self.colour == other.colour) and (self.stone_type == other.stone_type)

class Stack:
    
    """
    A stack of `Stones`. Has multiple functions designed to handle them.
    """
    
    def __init__(self) -> None:
        
        self.top = None
        self.stack = []
    
    def add_stone(self, stone: Stone) -> None:
        
        """
        Adds a stone to the stack. (appends stone to `Stack.stack`)
        """
        
        if self.stack != []:
        
            if stone.stone_type == "cap": # Set stone to a flat, no matter what
                self.stack[-1].crush()
        
            elif self.stack[-1].stone_type == "wall": # Can't be a cap, must disallow placement.
                return False
        
        self.stack.append(stone)
        self.top = stone
    
    def get_stones(self, num: int) -> list[Stone]:
        
        """
        Get `num` stones from the top of the stack. (does not impact stack)
        """
        
        return self.stack[-num:]
    
    def pop_stones(self, num: int) -> list[Stone]:
        
        """
        Remove `num` stones from the top of the stack.
        """
        
        temp = self.stack[-num:]
        
        del self.stack[-num:]
        
        if self.stack == []:
            self.top = None
        
        else:
            self.top = self.stack[-1]
        
        return temp.copy()
    
    def __repr__(self):
        return f"<Stack {self.top} {self.stack}>"
    
    def __eq__(self, other):
        return (self.top == other.top) and (self.stack == other.stack)

class TakBoard:
    
    """
    Board representation for the game of Tak.
    
    `board_size` is the length of one side - a 6x6 board (6s) would be `board_size=6`.
    """
    
    def __init__(self, board_size: int, half_komi: int) -> None:
        
        self.size = board_size
        self.half_komi = half_komi
        self.state = [Stack() for i in range(board_size ** 2)]
        self.ply = 0
                
        self.SPREAD_PRECALC = self._precalc_move_distances()
        
        self.RESERVE_COUNTS = {
            3: [10, 0],
            4: [15, 0],
            5: [21, 1],
            6: [30, 1],
            7: [40, 2],
            8: [50, 2]
        }
        
        self.player_reserves = {n:self.RESERVE_COUNTS[self.size].copy() for n in ["white", "black"]}
        self.std_reserves    = self.RESERVE_COUNTS[self.size]
        self.terminal = False
        self.winning_player = None
        self.win_type = None
        
        self.legal_moves = self.get_valid_moves("white")
        
        self.ZOBRIST_CONSTANTS = self._generate_zobrist_keys()
        self.zobrist_hash      = self.generate_zobrist_hash("white")
        
        self.TRANSFORMATIONS    = self._generate_transformations()
    
    #? Helper functions
    
    def pos_to_index(self, pos: str) -> int:
        
        """
        Transforms a board position string (e.g., a1, f4) to an index to `self.state`.
        """
        
        file, rank = tuple([i for i in pos.lower()])
        position = self.get_index(int(rank) - 1, "abcdefgh".index(file))
        
        return position

    def get_pos(self, index: int) -> str:
        
        """
        Transforms an index to `self.state` to a board position string (e.g., a1, f4). 
        """
        
        rank = index // self.size
        file = index % self.size
        
        return "abcdefgh"[file] + str(rank + 1)
    
    def get_index(self, rank: int, file: int) -> int:
        
        """
        Returns an index to `self.state` given a rank and file. (Rank and file both start at 0.)
        """
        
        assert (rank > -1) and (file > -1), "Rank or file is negative."
        return (rank * self.size) + file
    
    def get_rank_file(self, index: int) -> tuple[int, int]:
        
        """
        Returns the rank and file of an index to `self.state`. (Rank and file both start at 0.)
        """
        
        rank = index // self.size
        file = index % self.size
        
        return rank, file
    
    def invert_player(self, player: str) -> str:
        
        """
        Returns the opposite player, given the two players "black" and "white".
        
        ##### [Will be deprecated once I move to int representation of players!]
        """
        
        return "black" if player == "white" else "white"
    
    def count_flats(self) -> dict[str: int]:
        
        """
        Counts number of flats for each player.
        """
        
        stacks = [pos for pos in self.state if pos.stack != [] and pos.top.stone_type == "flat"]
        
        white = len([s for s in stacks if s.top.colour == "white"])
        black = len(stacks) - white
        
        return {"white": white, "black": black + self.half_komi / 2}
    
    #? Move generation
    
    def get_valid_places(self, player: str) -> list[dict]:
        
        """
        Returns all legal place moves (e.g., a1, Sf4, Cc3) for player `player`.
        
        The format for all place moves:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        ```
        """
        
        empty_spaces = [n for n, pos in enumerate(self.state) if not pos.top]
        
        places = []
        
        if self.player_reserves[player][0] > 0:
        
            places += [{
                "move_type": "place",
                "colour": player,
                "position": pos,
                "stone_type": stone_type
            } for pos in empty_spaces for stone_type in ["flat", "wall"]]
        
        if self.player_reserves[player][1] > 0:
            
            places += [{
                "move_type": "place",
                "colour": player,
                "position": pos,
                "stone_type": "cap"
            } for pos in empty_spaces]
        
        return places
    
    def get_valid_spreads(self, player: str) -> list[dict]:
        
        """
        Returns all legal stack spread moves (e.g., a1>, 2f4+11, 6c3<312) for player `player`.
        
        The format for all place moves:
        
        ```
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        """
        
        stack_moves = []
        
        filled_positions = [(n, pos) for n, pos in enumerate(self.state) if pos.top]
        stacks           = [(n, pos) for n, pos in filled_positions if pos.top.colour == player]
        
        for pos, stack in stacks:
        
            movements = self.get_spread_distances(pos, stack)
            
            max_stones = min(len(stack.stack), self.size)
            
            for direction, movement in movements.items():
                
                if movement["squares"] == [] and movement["cap"]:
                    
                    stack_moves.append({
                        "move_type": "spread",
                        "position": pos,
                        "movement": (movement["cap"],),
                        "stacks": (1,),
                    })
                
                for stones in range(1, max_stones + 1):
                    
                    for s in range(1, len(movement["squares"]) + 1):
                        
                        if s > stones:
                            break
                        
                        spaces = tuple(movement["squares"][:s])
                        
                        stack_moves += [{
                            "move_type": "spread",
                            "position": pos,
                            "movement": spaces,
                            "stacks": stack_move
                        } for stack_move in self.SPREAD_PRECALC[s, stones]]

                    dist = len(movement["squares"])
                    
                    if movement["cap"] and (dist >= 1) and (stones > 1) and (stones >= dist):
                        
                        if dist == stones:
                            
                            temp = [{
                                "move_type": "spread",
                                "position": pos,
                                "movement": tuple(list(spaces) + [movement["cap"]]),
                                "stacks": tuple(1 for _ in range(dist))
                            }]
                        
                        else:
                            
                            temp = [{
                                "move_type": "spread",
                                "position": pos,
                                "movement": tuple(list(spaces) + [movement["cap"]]),
                                "stacks": tuple(list(stack_move) + [1])
                            } for stack_move in self.SPREAD_PRECALC[dist, stones - 1] ]
                        
                        stack_moves += temp
        
        
        for m, move in enumerate(stack_moves):
            
            if self.state[move["position"]].top.stone_type != "cap":
                stack_moves[m]["crush"] = False
                continue
            
            if move["stacks"][-1] > 1:
                stack_moves[m]["crush"] = False
                continue
            
            end = self.state[move["movement"][-1]].top.stone_type if self.state[move["movement"][-1]].stack else None
            
            stack_moves[m]["crush"] = end == "wall"
        
        return stack_moves
    
    def get_spread_distances(self, pos: int, stack: Stack) -> dict[str: dict]:
        
        """
        Return all spaces a spread can span, for all possible directions (orthogonal).
        
        ```
        DISTANCE_FORMAT = {
            "squares": list[int], # a list of all positions a spread can span
            "cap":     Optional[int] # optional space where a capstone crush works
        }
        ```
        
        """
        
        movements = {i:{"squares": [], "cap": None} for i in "+-><"} # N S E W 
        row = None
        
        ADD_DIR = {
            "+": self.size,
            "-": -self.size,
            ">": 1,
            "<": -1
        }
        
        walled_spaces = [n for n, pos in enumerate(self.state) if (pos.top) and (pos.top.stone_type in ["wall", "cap"])]
        
        for direction, movement in ADD_DIR.items(): # THIS WORKS I THINK
        
            hori_check = abs(movement) == 1
            current = pos
            cap = False
            
            if hori_check: # E/W
                row = pos // self.size
            
            i = 0
            
            while ((current + movement) < len(self.state)) and ((current + movement) >= 0) and (i < len(stack.stack)):
                
                current += movement
                
                if hori_check and (current // self.size != row):
                    break
                
                wall_stack = self.state[current].top and self.state[current].top.stone_type == "wall"
                
                if current in walled_spaces: # if you've got a cap and there's a wall
                    
                    if stack.top.stone_type == "cap" and wall_stack:
                        movements[direction]["cap"] = current
                    break
                
                movements[direction]["squares"].append(current)
                i += 1
        
        return movements
    
    def get_valid_moves(self, player: str) -> list[dict]:
        
        
        """
        Returns all legal moves from the current position for player `player`.
        
        Internal move formats are below:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "direction": "+ / - / < / >" # pick one, will be deprecated soonish because we want *speed*
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        """
        
        terminal = self.determine_win(player)
        
        if terminal: return None
        
        empty_spaces = [n for n, pos in enumerate(self.state) if not pos.top]
        
        if self.ply <= 1:
            # Only valid places
            return [{
                "move_type": "place",
                "colour": "black" if player == "white" else "white",
                "position": pos,
                "stone_type": "flat"
            } for pos in empty_spaces]
        
        places = self.get_valid_places(player)
        
        spreads = self.get_valid_spreads(player)
        
        return places + spreads
        
    def _precalc_move_distances(self) -> dict[tuple[int, int]: list[tuple[int]]]:
        
        """
        Precalculate all possible stack spreads given the `distance` of the spread and the number of `stones` involved.
        
        Not intended for external use. It's run during `TakBoard.__init__`.
        
        Just get the results from `TakBoard.SPREAD_PRECALC`.
        """
        
        precalc = {}
       
        for stones, distance in ((stones, distance) for distance in range(1, self.size) for stones in range(1, self.size + 1)):       # max move distance  = self.size - 1
               
            if distance > stones:
                continue
            
            # Step 1, calculate possible moves
            
            # . Find base position
            
            spreads = []
            
            average   = stones // distance
            remainder = stones  % distance
            
            spread = [average for i in range(distance)]
            spread[0] += remainder
            shift_digit = self._fsd(spread)
            
            spreads += permutations(spread)
            
            while shift_digit != None:
                
                spread[shift_digit]     -= 1
                spread[shift_digit + 1] += 1 
                
                spreads += permutations(spread)
                
                shift_digit = self._fsd(spread)
            
            spreads = list(set(spreads))
            
            precalc[(distance, stones)] = spreads
        
        return precalc
    
    def _fsd(self, seq: list): # "Find shift digit"
        
        """
        Found within `TakBoard._precalc_move_distances()`. As such, not intended for external use.
        
        Creates the digit to change to create a new permutation. Honestly, I'm not sure how else to describe it.
        """
        
        shift = [n for n, val in enumerate(seq) if val > 1]
        
        if len(shift) == 0 or len(seq) == 1:
            return None
        
        shift_digit = min(shift)
        
        if shift_digit == len(seq) - 1:
            return None
        
        return shift_digit
    
    #? Move making
    
    def make_move(self, move: dict, player: str) -> bool:
        
        """
        Attempt to make the move `move` for player `player`.
        
        Will not perform illegal moves from the position for that player.
        
        Returns `True` if successful, else returns `False`.
        
        """
        
        if move in self.legal_moves:
            
            if move["move_type"] == "place":
                
                if move["stone_type"] in ["flat", "wall"]:
                    self.player_reserves[player][0] -= 1
                else:
                    self.player_reserves[player][1] -= 1
                
                self.state[move["position"]].add_stone(Stone(move["colour"], move["stone_type"]))
                
                # Adding to the Zobrist hash
                
                self.zobrist_hash ^= self.get_zobrist_piece_key(move["position"], 0, move["stone_type"], move["colour"])
            
            elif move["move_type"] == "spread": #! Zobrist is currently broken
                
                # Get stones
                
                if move["crush"]:
                    end = move["movement"][-1]
                    end_stack = self.state[end]
                    
                    self.zobrist_hash ^= self.get_zobrist_piece_key(
                        end,
                        len(end_stack.stack) - 1,
                        "wall",
                        end_stack.top.colour
                    )
                    
                    self.zobrist_hash ^= self.get_zobrist_piece_key(
                        end,
                        len(end_stack.stack) - 1,
                        "flat",
                        end_stack.top.colour
                    )
                
                original_height = len(self.state[move["position"]].stack)
                current_height  = original_height - sum(move["stacks"])
                
                stones = self.state[move["position"]].pop_stones(sum(move["stacks"]))
                
                for position, amount in zip(move["movement"], move["stacks"]):
                    
                    for stone in stones[:amount]:
                        
                        self.state[position].add_stone(stone)
                        
                        self.zobrist_hash ^= self.get_zobrist_piece_key(
                            position,
                            len(self.state[position].stack) - 1,
                            stone.stone_type,
                            stone.colour
                        )
                    
                    for stone in stones[:amount]:
                        
                        self.zobrist_hash ^= self.get_zobrist_piece_key(
                            move["position"], 
                            current_height, 
                            stone.stone_type, 
                            stone.colour
                        )
                        
                        current_height += 1

                    del stones[:amount]
        
        else:
            return False
        
        # XOR current player
        
        self.zobrist_hash ^= self.ZOBRIST_CONSTANTS["black_to_move"]
          
        self.ply += 1
        
        self.legal_moves = self.get_valid_moves(self.invert_player(player))
        
        return True
    
    def undo_move(self, move: dict, player: str) -> bool:
        
        """
        Undoes the move `move` for player `player`. (That is, the player who's turn we're going back to.)
        
        Unlike `TakBoard.make_move`, this *does not* check legality.
        
        Returns `True` if successful. (redundant, but eh, who cares)
        
        
        ###### [Note from dayofni: this f****** function had so many bugs istg-]
        """
        
        if move["move_type"] == "place":
            
            self.state[move["position"]].stack = []
            self.state[move["position"]].top   = None
            
            self.player_reserves[player][1 if move["stone_type"] == "cap" else 0] += 1
            
            self.zobrist_hash ^= self.get_zobrist_piece_key(move["position"], 0, move["stone_type"], move["colour"])
        
        elif move["move_type"] == "spread":
            
            stones = []
            
            
            # To undo the hash:
            #  . First, deal with the spreads
            #    -> For each stack, remove the stones from the hash
            #  . Second, add the stones back to the main stack
                
            for position, amount in zip(move["movement"], move["stacks"]):
                
                cut = self.state[position].pop_stones(amount)
                
                for h, stone in enumerate(cut):
                    
                    # remove from stack
                    
                    self.zobrist_hash ^= self.get_zobrist_piece_key(
                        position,
                        len(self.state[position].stack) + h, # calc
                        stone.stone_type,
                        stone.colour
                    )
                
                stones += cut
                
            for stone in stones:
                
                self.state[move["position"]].add_stone(stone)
                
                self.zobrist_hash ^= self.get_zobrist_piece_key(
                    move["position"],
                    len(self.state[move["position"]].stack) - 1, # calc
                    stone.stone_type,
                    stone.colour
                )
            
            if move["crush"]:
                
                last_space = move["movement"][-1]
                last_pos = self.state[last_space]
                
                self.state[last_space].stack[-1].stone_type = "wall"
                self.state[last_space].top = self.state[last_space].stack[-1]
                
                self.zobrist_hash ^= self.get_zobrist_piece_key(
                    last_space,
                    len(last_pos.stack) - 1, # calc
                    "flat",
                    last_pos.top.colour
                )
                
                self.zobrist_hash ^= self.get_zobrist_piece_key(
                    last_space,
                    len(last_pos.stack) - 1, # calc
                    "wall",
                    last_pos.top.colour
                )
        
        self.zobrist_hash ^= self.ZOBRIST_CONSTANTS["black_to_move"]
        
        self.terminal = False
        self.winning_player = None
        self.win_type = None
        self.ply -= 1
        
        self.legal_moves = self.get_valid_moves(player)
        
        return True
    
    #? PTN handling
    
    def ptn_to_move(self, ptn_string: str, player: str) -> dict:
        
        """
        Converts a given PTN string to the `TakBoard` internal format.
        
        Internal move formats are below:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        """
        
        # How to check
        
        # [Num / FSC] <position> [-+><] [stack_move] | [*]['"][?!]  <- unimportant
        
        # thou shalt cleanse thine inputs
        
        ptn_string = ptn_string.strip().lower()
        ptn_string = ptn_string.replace("!", "").replace("?", "").replace("'", "").replace("\"", "").replace("*", "")

        if len(ptn_string) < 2: # sanity check, saves some time
            return None

        if not ptn_string[0].isalnum():
            return None
        
        STONES = {
            "f": "flat",
            "s": "wall",
            "c": "cap"
        }
        
        ALPHA = "abcdefgh"
        
        ARROWS = {
            "↑": "+",
            "↓": "-",
            "←": "<",
            "→": ">"
        }
        
        ADD_DIR = {
            "+": self.size,
            "-": -self.size,
            ">": 1,
            "<": -1
        }
        
        stone_type = None
        num_stones = None
        
        move_type = "spread" if any([i in "+-<>↑↓←→" for i in ptn_string]) else "place"
        
        if ptn_string[0] in STONES and not ptn_string[1].isnumeric():

            if move_type != "place": return None

            stone_type = STONES[ptn_string[0]]
            ptn_string = ptn_string[1:]
        
        elif ptn_string[0].isnumeric():
            
            if move_type != "spread": return None
            
            num_stones = int(ptn_string[0])
            ptn_string = ptn_string[1:]
        
        if move_type == "place"  and stone_type == None: stone_type = "flat"
        if move_type == "spread" and num_stones == None: num_stones = 1
        
        file, rank = tuple([i for i in ptn_string[:2]])
        position = self.get_index(int(rank) - 1, ALPHA.index(file))
        
        if move_type == "place":
            return {
                "move_type": "place",
                "position": position,
                "colour": self.invert_player(player) if self.ply <= 1 else player,
                "stone_type": stone_type
            }
        
        #! ONLY CAN BE SPREADS FROM HERE ON OUT
        
        direction = ptn_string[2]
        ptn_string = ptn_string[3:]
        
        #? Ensure that the stack has pieces
        
        if not self.state[position].stack:
            print("Position fail")
            return None
        
        #? Normalise arrow format
        
        if direction in ARROWS: direction = ARROWS[direction]
        
        #? Parse spread data
        
        if len(ptn_string) > 0:
            
            stacks = []

            while len(ptn_string) > 0 and ptn_string[0].isnumeric():
                stacks.append(int(ptn_string[0]))
                ptn_string = ptn_string[1:]

            if sum(stacks) != num_stones:
                print("Stones != movement!")
                return None
        
        else: stacks = [num_stones]
        
        #? Determine spaces spread covers
        
        movement = [position + (i * ADD_DIR[direction]) for i in range(1, len(stacks) + 1)]
        
        #? Check that the move doesn't go out of bounds.
        
        if any([i < 0 or i > len(self.state) for i in movement]):
            print("OOB vertical")
            return None
            
        if direction in "<>" and any([(i // self.size) != (position // self.size) for i in movement]):
            print("OOB horizontal")
            return None
        
        #? Is the move a cap crush?
        
        cap_check = self.state[position].top.stone_type == "cap"
        wall_check = stacks[-1] == 1 and self.state[movement[-1]].stack and self.state[movement[-1]].top.stone_type == "wall"
        
        if cap_check and wall_check:
            crush = True
        else:
            crush = False
        
        return {
            "move_type": "spread",
            "position": position,
            "movement": tuple(movement),
            "stacks": tuple(stacks),
            "crush": crush
        }
    
    def move_to_ptn(self, move: dict) -> str:
        
        """
        Converts a move in the `TakBoard` format to a PTN string.
        
        Internal move formats are below:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        
        ###### [Note from dayofni: Kinda funny how this function's shorter than the inverse...]
        """
        
        position = self.get_pos(move["position"])
        
        directions = {
            self.size: "+",
            -self.size: "-",
            -1: "<",
            1: ">"
        }
        
        if move["move_type"] == "place":
            stone_type = {"flat": "", "wall": "S", "cap": "C"}[move["stone_type"]]
            return f"{stone_type}{position}"
        
        if move["move_type"] == "spread":
            
            stone_num = str(sum(move["stacks"])) if sum(move["stacks"]) > 1 else ""
            stacks    = "".join([str(i) for i in move["stacks"]])
            stacks    = stacks if str(sum(move["stacks"])) != stacks else ""
            cap       = "*" if move["crush"] else ""
            
            direction = directions[move["movement"][0] - move["position"]]

            return f"{stone_num}{position}{direction}{stacks}{cap}"
        
        return None

    #? Server move format handling
    
    def server_to_move(self, server_move: str, player: str) -> dict:
        
        """
        Converts a given playtak move command to the `TakBoard` internal format.
        
        Internal move formats are below:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "direction": "+ / - / < / >" # pick one, will be deprecated soonish because we want *speed*
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        """
        
        move_type, data = server_move[0], server_move[1:]

        position = self.pos_to_index(data[0])
        
        if move_type == "P":
            
            stone_type = "flat"
            
            if   "C" in data: stone_type = "cap"
            elif "W" in data: stone_type = "wall"
            
            return {
                "move_type": "place",
                "position": position,
                "colour": self.invert_player(player) if self.ply <= 1 else player,
                "stone_type": stone_type
            }
        
        elif move_type == "M":
            
            end, stacks = self.pos_to_index(data[1]), [int(i) for i in data[2:]]
            
            # Determine direction
            
            diff = end - position
            
            to_mult = lambda diff: 1 if abs(diff) == diff else -1
            
            if abs(diff) > self.size - 1:
                
                direction = self.size * to_mult(diff)
            
            else:
                direction = to_mult(diff)
            
            # Determine all positions between end and position. (i.e., the spread)
            
            movement = []
            
            pos = position
            
            for _ in stacks:
                pos += direction
                movement.append(pos)
            
            # Determine whether it's a crush
            
            crush = False
            
            if self.state[end].stack and self.state[end].top.stone_type == "wall" and self.state[position].top.stone_type == "cap" and stacks[-1] == 1:
                crush = True
            
            return {
                "move_type": "spread",
                "position": position,
                "movement": tuple(movement),
                "stacks": tuple(stacks),
                "crush": crush
            }
        
        return None
    
    def move_to_server(self, move: dict) -> str:
        
        """
        Converts a move in the `TakBoard` format to the playtak command format.
        
        Internal move formats are below:
        
        ```
        PLACE_FORMAT = {
            "move_type": "place",
            "colour": player, # (necessary because of swap opening)
            "position": int, # index to self.state
            "stone_type": "flat / wall / cap" # pick one
        }
        
        SPREAD_FORMAT = {
            "move_type": "spread",
            "position": int, # index to self.state
            "direction": "+ / - / < / >" # pick one, will be deprecated soonish because we want *speed*
            "movement": tuple[int], # tuple of all spaces the spread covers
            "stacks": tuple[int] # how many pieces per space?
        }
        ```
        
        ###### [Note from dayofni: Again, it's hilarious that this is shorter than the inverse operation...]
        """
        
        position = self.get_pos(move["position"]).upper()
        move_type = {"place": "P", "spread": "M"}[move["move_type"]]
        
        if move_type == "P":
            
            stone_type = {"flat": "", "wall": " W", "cap": " C"}[move["stone_type"]]
            
            return f"{move_type} {position}{stone_type}"
        
        elif move_type == "M":
            
            end, spreads = self.get_pos(move["movement"][-1]).upper(), " ".join([str(i) for i in move["stacks"]])
            
            return f"{move_type} {position} {end} {spreads}"
        
        return None

    #? TPS handling
        
    def position_to_TPS(self) -> str:

        """
        Creates a string representation of the current position using the TPS (Tak Position Notation) format.
        """
        
        tps_string = []
        
        for row_num in range(self.size):
            
            current = []
            
            current_row = self.size - row_num - 1
            
            start, end = (self.size * current_row), (self.size * current_row + 6)
            row = self.state[start:end]
            
            # Collapse
            
            x_num = 0
            stack = ""
            
            for pos in row:
                
                if pos.top is None:
                    x_num += 1
                    continue
                
                elif x_num:
                    add = str(x_num if x_num > 1 else "")
                    current.append(f"x{add}")
                    x_num = 0
                
                stack = ""
                
                for stone in pos.stack:
                    stack += str(1 if stone.colour == "white" else 2)
                
                if pos.top.stone_type == "cap":
                    stack += "C"
                
                if pos.top.stone_type == "wall":
                    stack += "S"
                
                current.append(stack)
                stack = ""
            
            if x_num:
                add = str(x_num if x_num > 1 else "")
                current.append(f"x{add}")
            
            if stack:
                current.append(stack)
                stack = ""
                
            tps_string.append(",".join(current))
        
        player = (self.ply) % 2 + 1
        current_round = self.ply // 2
        
        return "/".join(tps_string) + f" {player} {current_round}"

    def load_from_TPS(self, tps_string: str) -> None:
        
        """
        ### WARNING: BUGGY!
        
        Loads a position from a TPS (Tak Positional Notation) string representation.
        
        """
        
        tps_string = tps_string.upper().strip()
        
        position, player_turn, ply = tps_string.split(" ")
        
        player_turn = "white" if int(player_turn) == 1 else "black"
        self.ply = int(ply)
        
        # generate position
        
        rows = position.split("/")
        
        if self.size != len(rows):
            return False
        
        new_state = []
        
        # row construction
        
        for row in reversed(rows):
            
            row_data = row.split(",")
            
            new_row = []
            
            for pos in row_data:
                
                if pos[0] == "X" and len(pos) > 1:
                    for _ in range(int(pos[1])): new_row.append(Stack())
                    continue
                
                elif pos[0] == "X":
                    new_row.append(Stack())
                    continue
                
                new_row.append(Stack())
                
                if pos[-1].isalpha():                        # pos -1 is a letter, ergo must be SC
                    top = {"S": "wall", "C": "cap"}[pos[-1]] # hehe dictionary go brrrrr
                    pos = pos[:-1]
                else:
                    top = "flat"
                
                for s, stone in enumerate(pos):
                    
                    if s == len(pos) - 1:
                        stone = Stone("white" if stone == "1" else "black", top)
                    else:
                        stone = Stone("white" if stone == "1" else "black", "flat")

                    # Subtract from supply
                    # If supply == 0
                    
                    reserve = 1 if stone.stone_type == "cap" else 0
                    supply = self.player_reserves[stone.colour][reserve]
                    
                    if supply == 0: return False
                    
                    self.player_reserves[stone.colour][reserve] -= 1
                    
                    new_row[-1].add_stone(stone)
                
            
            new_state += new_row
            
        self.state = new_state
        
        self.legal_moves = self.get_valid_moves(player_turn)
        
        # determine legal moves for player 
    
    #? Win determination
    
    def determine_win(self, current_player: str) -> bool:
        
        """
        Determines whether the current position is a terminal position.
        
        If so, sets winning player to `TakBoard.winning_player`. (It may not be the current player!)
        
        #### Going to fix this function later
        """
        
        road_win = self.determine_road_win(current_player)
        
        if road_win:
            return road_win
        
        flat_win = self.determine_flat_win()
        
        if flat_win:
            return flat_win
        
        return None
     
    def determine_flat_win(self) -> tuple[bool, str]:
        
        """
        Determines whether a flat win exists at the current position.
        
        If so, returns `(True, player)`, where `player` is the winning player.
        """
        
        reserves = [flat + cap for player, (flat, cap) in self.player_reserves.items()]
        
        reserves_out = any([i == 0 for i in reserves])
        
        if len([pos for pos in self.state if pos.stack == []]) and not reserves_out:
            return None
        
        flats = self.count_flats()
        
        if flats["white"] == flats["black"]:
            player = None
        else:
            player = max(flats.items(), key=lambda a: a[1])[0]
        
        self.terminal = True
        self.winning_player = player
        self.win_type = "flat"
        
        return True, player
    
    def determine_road_win(self, current_player) -> tuple[bool, str]:
        
        """
        Determines whether a road win exists at the current position.
        
        If so, returns `(True, player)`, where `player` is the winning player.
        """
        
        north_edges = [self.size * (self.size - 1) + i for i in range(self.size)]
        south_edges = list(range(self.size))
        east_edges  = [n * self.size for n in range(self.size)]
        west_edges  = [n * self.size + self.size - 1 for n in range(self.size)]
        
        groups = self.find_connections()
        
        dragon = False
        
        for (_, player), group in groups.items():
            
            north_connection = any([i in north_edges for i in group])
            south_connection = any([i in south_edges for i in group])
            east_connection  = any([i in east_edges for i in group])
            west_connection  = any([i in west_edges for i in group])
            
            if (north_connection and south_connection) or (east_connection and west_connection):
                
                if player == current_player:
                
                    self.terminal = True
                    self.winning_player = current_player
                    self.win_type = "road"
                    
                    return (True, current_player)

                else: dragon = player
            
        if dragon:
            
            self.terminal = True
            self.winning_player = self.invert_player(current_player)
            self.win_type = "road"
            
            return (True, self.winning_player)
        
        return None
    
    def find_connections(self) -> dict[tuple[int, str]: tuple]:
        
        """
        Implements a flood-fill algorithm that finds all road connections.
        """
        
        nodes = {n: i.top.colour for n, i in enumerate(self.state) if i.stack != [] and i.top.stone_type != "wall"}
        
        groups = {}
        
        directions = [self.size, -self.size, 1, -1]
        
        while len(nodes) > 0:
            
            start_pos, start_colour = tuple(nodes.items())[0]
            del nodes[start_pos]
            
            check = []
            group = [start_pos]
            
            check.append(start_pos)
            
            while len(check) > 0:
                
                pos = check[0]
                row = pos // self.size
                
                del check[0]
                
                for direction in directions:
                    
                    neighbour = pos + direction
                    neighbour_row = neighbour // self.size
                    
                    if neighbour in check:
                        continue
                    
                    if neighbour_row != row and abs(direction) == 1:
                        continue
                    
                    if neighbour not in nodes:
                        continue
                    
                    if nodes[neighbour] != start_colour:
                        continue
                    
                    if neighbour in group:
                        continue
                    
                    check.append(neighbour)
                    group.append(neighbour)
                    del nodes[neighbour]
            
            groups[(start_pos, start_colour)] = tuple(group)
        
        return groups
    
    def find_edges(self) -> list[int]:
        
        """
        Short little function to find the edges of the board.
        """
        
        edges = [self.size * (self.size - 1) + i for i in range(self.size)] + \
                    list(range(self.size)) + \
                        [n * self.size for n in range(1, self.size - 1)] + \
                            [n * self.size + self.size - 1 for n in range(1, self.size - 1)]
        
        return edges

    #? ASCII Representation
    
    def generate_win_str(self):
        
        """
        Generates a string representation of the terminal state of the board.
        
        If White wins: `R-0` (road) or `1-0` (flats)
        
        If Black wins: `0-R` (road) or `0-1` (flats)
        
        If it's a draw: `1/2-1/2`
        """
        
        if not self.terminal: return None
        
        win_type = {"flat": "1", "road": "R"}[self.win_type]
        
        if self.winning_player == None:
            return "1/2-1/2"
        
        elif self.winning_player == "white":
            return f"{win_type}-0"
        
        else:
            return f"0-{win_type}"
    
    def to_str(self, piece_count=True, tps=True):
        
        """
        Generates a string representation of the board.
        
        It's recommended to use `str(TakBoard)` unless you need to change from default settings.
        """
        
        ret = ""
        
        stone_str = ""
        
        flat_count = self.count_flats()
        
        if piece_count:
        
            for player in ["white", "black"]:

                colour = "\u001b[31;1m" if player == "white" else "\u001b[34;1m"
                clear  = "\u001b[34;0m"
                reserves = self.player_reserves[player][0]
                cap      = self.player_reserves[player][1]

                if int(flat_count[player]) == flat_count[player]:
                    flats = int(flat_count[player])
                else:
                    flats = flat_count[player]

                stone_str += f"{clear}{cap} x {colour}o{clear}, {reserves} x {colour}#{clear} ({flats})\n"
        
            ret += stone_str + "\n"
        
        for rank in reversed(range(self.size)): # size = 6: [5, 4, 3, 2, 1, 0]
            ret += f"{rank+1} "
            for file in range(self.size):       # size = 6: [0, 1, 2, 3, 4, 5]
                
                pos = self.state[self.get_index(rank, file)].top
                
                if pos is None:
                    ret += "."
                    continue
                
                if pos.colour == "white":
                    ret += "\u001b[31;1m"
                
                elif pos.colour == "black":
                    ret += "\u001b[34;1m"
                
                if pos.stone_type == "flat":
                    ret += "#"
                
                elif pos.stone_type == "wall":
                    ret += "/"
                
                elif pos.stone_type == "cap":
                    ret += "o"
                
                ret += "\u001b[34;0m"
            
            ret += "\n"
        
        if tps:
            
            ret += "  %s\n\n%s"%("abcdefgh"[:self.size], self.position_to_TPS())
        
        if self.terminal: # Add extra bit that 
            
            ret += f"\n\nResult: {self.generate_win_str()}"
        
        return ret.strip()

    def __str__(self):
        return self.to_str()
    
    #? Hashing - it should now be done!!!!!!!!!
    
    def _generate_zobrist_keys(self) -> dict[str: int]:
        
        """
        Generates all Zobrist keys required for the Zobrist hashing function.
        """
        
        ZOBRIST_BITS = 64
        
        reserves = self.std_reserves
        
        board_size   = self.size ** 2
        stone_number = 6
        max_height   = 2 * reserves[0] + (1 if reserves[1] else 0)
        
        ZOBRIST_KEYS = {
            "stack": [],
            "black_to_move": None
        }
        
        used_keys = []
        
        while len(ZOBRIST_KEYS["stack"]) < (board_size * stone_number * max_height):
            key = getrandbits(ZOBRIST_BITS)
            
            if key in used_keys:
                continue
            
            used_keys.append(key)
            ZOBRIST_KEYS["stack"].append(key)

        ZOBRIST_KEYS["stack"] = tuple(ZOBRIST_KEYS["stack"])

        while not ZOBRIST_KEYS["black_to_move"]:
            key = getrandbits(ZOBRIST_BITS)
            
            if key in used_keys:
                continue
            
            ZOBRIST_KEYS["black_to_move"] = key
        
        # Number of different stones * board size * max height + current_player
        # reset random seed
        
        return ZOBRIST_KEYS
    
    def get_zobrist_piece_key(self, position: int, height: int, stone_type: str, stone_colour: str) -> int:
        
        """
        Returns the Zobrist key for the given position, height, and stone.
        """
        
        board_size = self.size ** 2
        
        # stone type 1-3 and stone colour 1-2
        stone = {"flat": 0, "wall": 1, "cap": 2}[stone_type] + (0 if stone_colour == "white" else 3)
        
        # Treat each input as another number base
        
        index = stone + (6 * position) + (6 * board_size * height)
        
        return self.ZOBRIST_CONSTANTS["stack"][index]

    def get_zobrist_stack_key(self, position: int, stack: Stack):
        
        """
        Generates the Zobrist hash for an individual stack.
        """
        
        key = 0
        
        if not stack.stack:
            return None
        
        for height, stone in enumerate(stack.stack):
            stone_type   = stone.stone_type
            stone_colour = stone.colour
            
            key ^= self.get_zobrist_piece_key(position, height, stone_type, stone_colour)

        return key
    
    def generate_zobrist_hash(self, player: str):
        
        """
        Generates the full Zobrist hash for a given position.
        """
        
        current_hash = self.ZOBRIST_CONSTANTS["black_to_move"] if player == "black" else 0
        
        for position in enumerate(self.state):
            
            if not position[1].stack: continue
            
            current_hash ^= self.get_zobrist_stack_key(*position)
        
        return current_hash
    
    def __hash__(self):
        
        """
        Returns the Zobrist hash of the position.
        """
        
        return self.zobrist_hash
    
    #? Board transformations
    
    def _generate_transformations(self) -> dict[tuple[str, int]: tuple[int]]:
        
        """
        Generate all board transformations.
        
        Tak has 8-fold symmetry - the board can be transformed in multiple ways.
        Might as well write a function to do that for me.
        """
        
        transforms = {}
        
        normal    = tuple(range(self.size ** 2))
        
        mirror    = lambda a: tuple([a[((rank - 1) * self.size) + file] for rank in range(self.size, 0, -1) for file in range(self.size)])
        rotate_90 = lambda a: tuple([a[((file - 1) * self.size) + rank] for rank in range(self.size)        for file in range(self.size, 0, -1)])
        
        transforms[("normal", 0)] = normal
        transforms[("mirror", 0)] = mirror(normal)
        
        normal_rot = normal
        mirror_rot = mirror(normal)
        
        for rotation in range(270, 0, -90):
            
            normal_rot, mirror_rot = rotate_90(normal_rot), rotate_90(mirror_rot)
            
            transforms[("normal", rotation)] = normal_rot
            transforms[("mirror", rotation)] = mirror_rot

        return transforms
        
    def get_transform(self, board: str, rotation: int) -> list[Stack]:
        
        """
        Returns the transform of the current board state using a set transform.
        
        ```
        board:    "normal" or "mirror", # Which board do we start from?
        rotation: int                   # Given in degrees (0, 90, 180, 270)
        ```
        
        """
        
        return [self.state[i] for i in self.TRANSFORMATIONS[(board, rotation)]]

    def get_transform_free(self, transform: tuple[int]) -> list[Stack]:
        
        """
        Returns the transform of the current board state using `transform`.
        
        Example:
        ```
        Transform: (
            2, 1, 0, 
            5, 4, 3, 
            8, 7, 6
        )
        
        Original: (
            "a", "b", "c",
            "d", "e", "f",
            "g", "h", "i"
        )
        
        Output: (
            "c", "b", "a",
            "f", "e", "d", 
            "i", "g", "h"
        )
        ```
        """
        
        return [self.state[i] for i in transform]
    
    def transform_board(self, board: str, rotation: int) -> None:
        
        """
        Transforms the current board state using a set transform.
        
        ```
        board:    "normal" or "mirror", # Which board do we start from?
        rotation: int                   # Given in degrees (0, 90, 180, 270)
        ```
        
        """
        
        self.state = [self.state[i] for i in self.TRANSFORMATIONS[(board, rotation)]]
        
        self.legal_moves = [self.transform_move(m, board, rotation) for m in self.legal_moves]

    def transform_board_free(self, transform: tuple[int]) -> None:
        
        """
        Transforms the current board state using `transform`.
        
        Example:
        ```
        Transform: (
            2, 1, 0, 
            5, 4, 3, 
            8, 7, 6
        )
        
        Original: (
            "a", "b", "c",
            "d", "e", "f",
            "g", "h", "i"
        )
        
        Output: (
            "c", "b", "a",
            "f", "e", "d", 
            "i", "g", "h"
        )
        ```
        """
        
        self.state = [self.state[i] for i in transform]
        
        self.legal_moves = [self.transform_move_free(m, transform) for m in self.legal_moves]
    
    def undo_transform(self, board: str, rotation: int) -> None:
        
        """
        Undoes a set transform on the current board state.
        
        ```
        board:    "normal" or "mirror", # Which board do we start from?
        rotation: int                   # Given in degrees (0, 90, 180, 270)
        ```
        """
        
        if board == "normal":
            new_transform = (board, (360 - rotation) % 360)
        else:
            new_transform = (board, rotation)
        
        self.transform_board(*new_transform)

    def transform_move(self, move: dict, board: str, rotation: int) -> dict:
        
        move = deepcopy(move) # NO REFERENCES!
        
        transform = self.TRANSFORMATIONS[(board, rotation)]
        
        pos_to_new = lambda a: transform.index(a)
        
        move["position"] = pos_to_new(move["position"])
        
        if move["move_type"] == "spread":
            
            move["movement"] = tuple(pos_to_new(i) for i in move["movement"])
        
        return move
    
    def transform_move_free(self, move: dict, transform: tuple[int]) -> dict:
        
        move = deepcopy(move) # NO REFERENCES!
        
        pos_to_new = lambda a: transform.index(a)
        
        move["position"] = pos_to_new(move["position"])
        
        if move["move_type"] == "spread":
            
            move["movement"] = tuple(pos_to_new(i) for i in move["movement"])
        
        return move