import pyautogui
import json
import yaml
import random
import glob
import os
import re
import sys
import win32gui
import argparse
import timeago
import time
from datetime import datetime
from PIL import Image
from rich.console import Console

# General Config
mgba_version = "0.10.0" # This is just used to find the mGBA window
mgba_frame_size = 1 # mGBA > Audio/Video > Frame size (note: smaller game window = faster image detection)
mgba_speed = 1 # mGBA > Emulation > Fast forward speed (warning: may become unstable at higher speeds + diminishing returns on image detection speeds)
mgba_lua_dir = "C:/Temp/" # The directory that mgba_helper.lua script is writing to
mgba_x_padding = 15 # Adds x pixels to the mGBA window width, "debug/mgba_region.png" is generated at script run time to help tune, make sure the entire mGBA window is visible
mgba_y_padding = 60 # Adds y pixels to the mGBA window height
mgba_controls = { # See list of keys - https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys
    "a": "x",
    "b": "z",
    "l": "a",
    "r": "s",
    "up": "up",
    "right": "right",
    "down": "down",
    "left": "left",
    "select": "backspace",
    "start": "enter",
    "reset_emu": ["ctrl", "r"] # Must be a key-combo
}

bot_config = { # Default bot config
    "starter_pokemon": "Mudkip", # ["Treecko", "Torchic", "Mudkip"]
    "method": "Running/Surfing (Up/Down)", # ["Sweet Scent", "Running/Surfing (Up/Down)", "Running/Surfing (Left/Right)", "Fishing", "Starters"]
    "battle_pokemon": "Run", # ["Battle", "Run"]
    "save_game_on_launch": False, # True/False
    "banned_moves": ["None", "Bide", "Bind", "Counter", "Destiny Bond", "Dig", "Dive", "Doom Desire", "Explosion", "Fake Out", "False Swipe", "Fly", "Future Sight", "Mirror Coat", "Nature Power", "Perish Song", "Present", "Razor Wind", "Revenge", "Selfdestruct", "Sky Attack", "Snore", "Spit Up", "Whirlwind", "Wrap"] # Disallow these moves if battling wild Pokemon
}

pyautogui.PAUSE = 0.035/mgba_speed # Pause interval after each pyautogui function (defaults to 0.1)
pyautogui.FAILSAFE = True # pyautogui failsafe (ram mouse into top right of screen to kill script)

# Override default bot config with args
parser = argparse.ArgumentParser()
parser.add_argument('-p', action='store_true') # -p flag: set to buy 10x pokeballs for premier balls - must be in shop menu with poke balls selected
parser.add_argument('-s', action='store_true') # -s flag: set to automatically save the game when the bot starts
parser.add_argument('-m', action='store_true') # -m flag: set to Monitor/Manual Mode (bot will check for shinies and updates stats without providing any input besides running from wild Pokemon)
parser.add_argument('-b', action='store_true') # -b flag: set to battle wild pokemon until lead Pokemon is out of PP or HP
parser.add_argument('-y', action='store_true') # -y flag: set to run/surf along the Y-axis (up and down until obstructed) # TODO add run between X/Y co-ords for areas without obstacles
parser.add_argument('-x', action='store_true') # -x flag: set to run/surf along the X-axis (left and right until obstructed) # TODO add run between X/Y co-ords for areas without obstacles
parser.add_argument('-c1', action='store', type=int)
parser.add_argument('-c2', action='store', type=int)
parser.add_argument('-f', action='store_true') # -f flag: set to use fishing rod - must be facing the water with the preferred rod registered to "select"
parser.add_argument('-w', action='store_true') # -w flag: set to use sweet scent - first Pokemon in the part must have the move
parser.add_argument('-t', action='store_true') # -t flag: set to soft reset for starter pokemon - must save and stand to the right of the bag, facing it
args = parser.parse_args()
if args.s: bot_config["save_game_on_launch"] = True
if args.b: bot_config["battle_pokemon"] = "Battle"
if args.m: bot_config["method"] = "Manual Mode"
if args.y: bot_config["method"] = "Running/Surfing (Up/Down)"
if args.x: bot_config["method"] = "Running/Surfing (Left/Right)"
if args.f: bot_config["method"] = "Fishing"
if args.w: bot_config["method"] = "Sweet Scent"
if args.t: bot_config["method"] = "Starters"

# Functions
def read_file(file: str): # Function to read data from a file
    start_time = time.time()
    if os.path.isfile(file):
        with open(file, mode="r", encoding="utf-8") as open_file:
            file_data = open_file.read()
            console.log(f"Reading [bold blue]'{file}'[/] ([bold green]{round((time.time() - start_time)*1000, 3)}ms[/])")
            return file_data
    else:
        console.log(f"[red bold blink]Failed to open '{file}'![/]")
        return False

def write_file(file: str, value: str): # Function to set a value in a file
    start_time = time.time()
    try:
        with open(file, mode="w", encoding="utf-8") as save_file:
            save_file.write(value)
            console.log(f"Writing [bold blue]'{file}'[/] ([bold green]{round((time.time() - start_time)*1000, 3)}ms[/])")
    except:
        console.log(f"[red bold blink]Failed to update file '{file}'![/]")

def find_image(file: str): # Function to find an image in mGBA
    start_time = time.time()

    def scale(dimensions, factor):
        return (dimensions[0]*factor, dimensions[1]*factor)

    try:
        image = Image.open(file)
        image = image.resize(scale(image.size, mgba_frame_size), Image.NEAREST)
        locate = pyautogui.locateOnScreen(image, region=mgba_region)
    except:
        locate = None
    console.log(f"Searching for [bold blue]'{file}'[/] on-screen ([bold green]{round((time.time() - start_time)*1000, 3)}ms[/])")
    return locate

def press_key(key: str): # Function to pass single input to mGBA
    pyautogui.keyDown(key)
    pyautogui.keyUp(key)

def press_key_combo(keys: list, delay: int = None): # Function to pass key combo to mGBA
    console.log(f"Pressing key combo: [bold orange1]{[x for x in keys]}[/]...")
    for key in keys:
        pyautogui.keyDown(key)
    if delay:
        time.sleep(delay/mgba_speed)
    for key in reversed(keys):
        pyautogui.keyUp(key)

def key_sequence(sequence: list): # Function to run a sequence of keys to mGBA
    console.log(f"Pressing key sequence [bold orange1]{[x for x in sequence]}[/]...")
    sleep_pattern = "^\d*\.?\d*sec$"

    for key in sequence:
        if re.match(sleep_pattern, key):
            delay = float(re.sub(r"sec$", "", key))
            time.sleep(delay/mgba_speed)
        else:
            press_key(key)

def release_keys(): # Release all mGBA keys
    for key in mgba_controls.keys():
        if isinstance(key, str):
            pyautogui.keyUp(key)

def walk_until_obstructed(direction: str, run: bool = False): # Function to run until player position stops changing
    if run:
        pyautogui.keyDown(mgba_controls["b"])

    player_info = get_player_info()
    last_x = player_info["posX"]
    last_y = player_info["posY"]

    dir_unchanged = 0
    while dir_unchanged < 4:
        time.sleep(0.015/mgba_speed)
        player_info = get_player_info()
        pyautogui.keyDown(direction)
        if direction == mgba_controls["left"] or direction == mgba_controls["right"]:
            if last_x == player_info["posX"]:
                dir_unchanged += 1
            else:
                last_x = player_info["posX"]
                dir_unchanged = 0
        if direction == mgba_controls["up"] or direction == mgba_controls["down"]:
            if last_y == player_info["posY"]:
                dir_unchanged += 1
            else:
                last_y = player_info["posY"]
                dir_unchanged = 0
    pyautogui.keyUp(direction)
    if run:
        pyautogui.keyUp(mgba_controls["b"])

def catch_pokemon(): # Function to catch the shiny pokemon
    console.log("Catching Pokemon...")
    while find_image("states/battle/fight.png") == None:
        key_sequence([mgba_controls["b"], mgba_controls["up"], mgba_controls["left"]]) # Press B + up + left until FIGHT menu is visible

    # Use Spore to put opponent to sleep to make catches much easier
    opponent = get_opponent_info()
    lead_pokemon = get_party_info(1)
    i, spore_pp = 0, 0

    if (opponent["status"] == 0) and (opponent["name"] not in ["Hoothoot", "Noctowl", "Spinarak", "Ariados", "Murkrow", "Delibird", "Shuppet", "Banette", "Honchkrow", "Pumpkaboo", "Ghourgeist"]): # Pokemon with Insomnia
        for move in lead_pokemon["enrichedMoves"]:
            if move["name"] == "Spore":
                spore_pp = move["pp"]
                spore_move_num = i
            i += 1

        if spore_pp != 0:
            key_sequence([mgba_controls["a"], "0.1sec"])
            if spore_move_num == 0: seq = [mgba_controls["up"], mgba_controls["left"]]
            elif spore_move_num == 1: seq = [mgba_controls["up"], mgba_controls["right"]]
            elif spore_move_num == 2: seq = [mgba_controls["left"], mgba_controls["down"]]
            elif spore_move_num == 3: seq = [mgba_controls["right"], mgba_controls["down"]]

            while find_image("states/spore.png") == None:
                key_sequence(seq)

            key_sequence([mgba_controls["a"], "4sec"]) # Select move and wait for animations

    while True:
        press_key(mgba_controls["b"])
        if find_image("states/battle/fight.png"):
            key_sequence([mgba_controls["right"], "0.05sec"]) # Press right to select BAG

        if find_image("states/battle/bag.png"):
            press_key(mgba_controls["a"])
            opponent = get_opponent_info()

            #if opponent["metLocationName"] == "Safari Zone": # TODO Safari Zone
            #    while find_image("states/battle/safari_zone/ball.png") == None:
            #        player_info = get_player_info()
            #        if player_info["state"] == 80: # State 80 = overworld
            #            player_info = get_player_info()
            #            return False
            #        key_sequence([mgba_controls["b"], mgba_controls["up"], mgba_controls["left"]]) # Press B + up + left until BALL menu is visible

            # Preferred ball order to catch wild mons with + exceptions # TODO move to config section at top
            if bag_menu(category="pokeballs", item="premier_ball") == False and opponent["name"] not in ["Abra"]:
                if bag_menu(category="pokeballs", item="ultra_ball") == False:
                    if bag_menu(category="pokeballs", item="great_ball") == False:
                        if bag_menu(category="pokeballs", item="poke_ball") == False:
                            console.log("[red bold blink]No balls to catch the Pokemon found. Killing the script![red bold blink]")
                            sys.exit()

        if find_image("states/gotcha.png"): # Check for gotcha! text when a pokemon is successfully caught
            console.rule("[green bold]Pokemon caught!")

            player_info = get_player_info()
            while player_info["state"] != 80: # State 80 = overworld
                player_info = get_player_info()
                press_key(mgba_controls["b"])
            time.sleep(2/mgba_speed) # Wait for animations
            save_game()
            return True

        player_info = get_player_info()
        if player_info["state"] == 80: # State 80 = overworld
            return False

def battle(): # Function to battle wild pokemon
    # This will only battle with the lead pokemon of the party, and will run if it dies or runs out of PP
    console.log("Battling Pokemon...")
    opponent = get_opponent_info()
    lead_pokemon = get_party_info(1)

    while opponent["hp"] != 0 and lead_pokemon["hp"] != 0:
        while find_image("states/battle/fight.png") == None:
            player_info = get_player_info()
            if player_info["state"] == 80: # State 80 = overworld
                player_info = get_player_info()
                return
            key_sequence([mgba_controls["b"], mgba_controls["up"], mgba_controls["left"]]) # Press B + up + left until FIGHT menu is visible

        console.log("Finding a damaging attack with PP...")

        i, effective_pp, power_pp = 0, 0, 0
        for move in lead_pokemon["enrichedMoves"]:
            if move["name"] not in bot_config["banned_moves"]:
                if move["power"] != 0:
                    power_pp += lead_pokemon["pp"][i]
                    for type in opponent["type"]:
                        if type in type_list[move["type"]]["immunes"] or type in type_list[move["type"]]["weaknesses"]:
                            console.log(f"Opponent type [purple bold]{opponent['type']}[/] is immune/weak against move [purple bold]{move['name']}[/]") 
                        else:
                            effective_pp += lead_pokemon["pp"][i]
            i += 1

        if effective_pp == 0 and power_pp > 0:
            console.log("[red bold]Lead Pokemon has no effective PP to damage opponent![/]")
            run_from_battle()
            return False

        if effective_pp == 0 and power_pp == 0:
            console.log("[red bold]Lead Pokemon has no more damaging PP![/]")
            run_from_battle()
            pokecenter()
            return False

        i = 0
        if effective_pp > 0:
            for move in lead_pokemon["enrichedMoves"]:
                immune = False
                if move["name"] not in bot_config["banned_moves"]:
                    if move["power"] != 0:
                        for type in opponent["type"]:
                            if type in type_list[move["type"]]["immunes"]: # TODO or type in type_list[move["type"]]["weaknesses"]
                                immune = True
                            
                        if lead_pokemon["pp"][i] != 0 and not immune:
                            key_sequence([mgba_controls["a"], "0.05sec"])
                            if i == 0:
                                key_sequence([mgba_controls["up"], mgba_controls["left"]])
                                break
                            elif i == 1:
                                key_sequence([mgba_controls["up"], mgba_controls["right"]])
                                break
                            elif i == 2:
                                key_sequence([mgba_controls["left"], mgba_controls["down"]])
                                break
                            elif i == 3:
                                key_sequence([mgba_controls["right"], mgba_controls["down"]])
                                break
                i += 1
            if i <= 3:
                key_sequence([mgba_controls["a"], "4sec"]) # Select move and wait for animations
                opponent = get_opponent_info()
                lead_pokemon = get_party_info(1)

    if lead_pokemon["hp"] == 0:
        console.log("[red bold]Lead Pokemon out of HP![/]")
        run_from_battle()
        pokecenter()
        return False

    player_info = get_player_info()
    while player_info["state"] != 80: # State 80 = overworld
        player_info = get_player_info()
        if find_image("states/stop_learning.png"): # Check if our Pokemon is trying to learn a move and skip learning
            press_key(mgba_controls["a"])
        press_key(mgba_controls["b"])

    if opponent["hp"] == 0:
        console.rule("[bold green]Battle won!")
        return True

def run_from_battle(): # Function to run from wild pokemon
    console.log("Running from battle...")
    while find_image("states/battle/fight.png") == None:
        player_info = get_player_info()
        if player_info["state"] == 80: # State 80 = overworld
            player_info = get_player_info()
            return
        key_sequence([mgba_controls["b"], mgba_controls["up"], mgba_controls["left"]]) # Press B + up + left until FIGHT menu is visible

    while find_image("states/battle/run.png") == None:
        key_sequence([mgba_controls["right"], mgba_controls["down"], "0.05sec"]) # Press right + down until RUN is selected

    press_key(mgba_controls["a"])

    i = 0
    player_info = get_player_info()
    while player_info["state"] != 80 and i < 50: # State 80 = overworld
        player_info = get_player_info()
        key_sequence([mgba_controls["b"], "0.05sec"])
        i += 1
    if i >= 50:
        run_from_battle()
        return

def start_menu(entry: str): # Function to open any start menu item - presses START, finds the menu entry and opens it
    if entry in ["bag", "bot", "exit", "option", "pokedex", "pokemon", "pokenav", "save"]:
        console.log(f"Opening start menu entry: [bold orange1]{entry}[/]")
        filename = f"states/start_menu/{entry.lower()}.png"

        key_sequence([mgba_controls["start"], "0.2sec"]) # Open start menu
        while find_image(filename) == None: # Select menu entry
            press_key(mgba_controls["down"])
        key_sequence(["0.5sec", mgba_controls["a"], "1.5sec"]) # Open menu entry
    else:
        return False

def bag_menu(category: str, item: str): # Function to find an item in the bag and use item in battle such as a pokeball
    if category in ["berries", "items", "key_items", "pokeballs", "tms&hms"]:
        console.log(f"Scrolling to bag category: [bold orange1]{category}[/]...")

        while find_image(f"states/start_menu/bag/{category.lower()}.png") == None:
            key_sequence([mgba_controls["right"], "0.5sec"]) # Press right until the correct category is selected
        time.sleep(2/mgba_speed) # Wait for animations

        console.log(f"Scanning for item: [bold orange1]{item}[/]...")
        i = 0
        while (find_image(f"states/start_menu/bag/items/{item}.png") == None) and i < 50:
            if i < 25:
                press_key(mgba_controls["down"])
            else:
                press_key(mgba_controls["up"])
            i += 1

        if i < 50:
            console.log(f"Using item: [bold orange1]{item}[/]...")
            key_sequence([mgba_controls["a"], "0.5sec", mgba_controls["a"]]) # Press A twice to use the item
            return True
        else:
            console.log(f"Could not find item: [bold orange1]{item}[/], backing out of all menus...")
            for i in range(10):
                key_sequence([mgba_controls["b"], "0.5sec"]) # Press B
            return False

def pickup_items(): # If using a team of Pokemon with the ability "pickup", this function will take the items from the pokemon in your party if 3 or more Pokemon have an item
    console.log("Checking for pickup items...")
    item_count = 0
    pickup_pokemon = ["ZIGZAGOON", "LINOONE"]
    party = get_party_info()

    for i in range(1, 6):
        try:
            pokemon = party[i]
            if pokemon["speciesName"] in pickup_pokemon:
                console.log(f"Pokemon {i}: [bold orange1]{pokemon['speciesName']}[/] has item: [bold orange1]{item_list[pokemon['heldItem']]}[/]")
                if pokemon["heldItem"] != 0:
                    item_count += 1
        except:
            pass

    if item_count >= 3: # Only run if 3 or more Pokemon have an item
        time.sleep(0.3/mgba_speed) # Wait for animations
        start_menu("pokemon") # Open Pokemon menu

        for i in range(1, 6):
            pokemon = party[i]

            if item_count > 0:
                if pokemon["speciesName"] in pickup_pokemon:
                    if pokemon["heldItem"] != 0:
                        key_sequence([mgba_controls["down"], "0.05sec", mgba_controls["a"], "0.05sec", mgba_controls["down"], "0.05sec", mgba_controls["down"], "0.05sec", mgba_controls["a"], "0.05sec", mgba_controls["down"], "0.05sec", mgba_controls["a"], "1sec", mgba_controls["b"], "0.05sec"]) # Take the item from the pokemon
                        party = get_party_info()
                        item_count -= 1
                    else:
                        key_sequence(["0.05sec", mgba_controls["down"]])
        key_sequence([mgba_controls["b"], "1.5sec", mgba_controls["b"]]) # Close out of menus

def save_game(): # Function to save the game via the save option in the start menu
    console.log("Saving the game...")
    start_menu("save")
    while find_image("states/start_menu/save/yes.png") == None:
        time.sleep(0.5/mgba_speed)
    press_key(mgba_controls["a"])
    while find_image("states/start_menu/save/yes.png") == None:
        time.sleep(0.5/mgba_speed)
    key_sequence([mgba_controls["a"], "7sec"])

def run_to_pos(run: bool = True, x: int = -1, y: int = -1, new_map_bank: int = -1, new_map_id: int = -1): # Function to run a direction until posX, posY mapBank or mapId matches input
    if run:
        pyautogui.keyDown(mgba_controls["b"])

    if y != -1:
        directions = [mgba_controls["up"], mgba_controls["down"]]
        axis = "posY"
        end_pos = y
    if x != -1:
        directions = [mgba_controls["left"], mgba_controls["right"]]
        axis = "posX"
        end_pos = x

    def target_pos():
        console.log(f"Running to coord: [cyan bold]{end_pos}[/]")
        if end_pos < player_info[axis]:
            pyautogui.keyDown(directions[0])
            return False
        elif end_pos > player_info[axis]:
            pyautogui.keyDown(directions[1])
            return False
        else:
            return True

    stuck = 0
    player_info = get_player_info()

    if new_map_bank != -1 or new_map_id != -1:
        while (player_info["mapBank"] != new_map_bank or player_info["mapId"] != new_map_id) and stuck < 1000:
            if not opponent_changed():
                try:
                    player_info = get_player_info()
                    target_pos()
                    stuck += 1
                except:
                    pass
            else:
                pyautogui.keyUp(mgba_controls["b"])
                return False
    else:
        while player_info[axis] != end_pos and stuck < 1000:
            if not opponent_changed():
                try:
                    player_info = get_player_info()
                    target_pos()
                    stuck += 1
                except:
                    pass
            else:
                return False

    release_keys()    
    return True

def pokecenter(): # Experimental function to run to poke center and back for long exp grinding sessions
    def heal_at_counter(): # Function to walk from PC entry, heal party and walk out - function should work for all PCs
        run_to_pos(y=4)

        pokemon = get_party_info(1) # The lead of the must NOT have full HP or PP for this to work
        pp_sum = sum(pokemon["pp"])
        last_pp_sum = pp_sum
        last_hp_sum = pokemon["hp"]

        while pp_sum == last_pp_sum and last_hp_sum == pokemon["hp"]:
            pp_sum = sum(pokemon["pp"])
            key_sequence([mgba_controls["a"], "0.2sec"])
            pokemon = get_party_info(1)

        key_sequence([mgba_controls["b"], "0.1sec"]*20)

        player_info = get_player_info()
        pc_map_bank, pc_map_id = player_info["mapBank"], player_info["mapId"]

        while player_info["mapBank"] == pc_map_bank and player_info["mapId"] == pc_map_id:
            player_info = get_player_info()
            pyautogui.keyDown(mgba_controls["down"]) # Run down to PC door until map changes
        pyautogui.keyUp(mgba_controls["down"])

    player_info = get_player_info()

    # TODO move this route maps to a different file
    # Route 102 south west grass patch
    if (player_info["mapBank"] == 0 and player_info["mapId"] == 17 and
        6 <= player_info["posX"] <= 7 and 12 <= player_info["posY"] <= 17):
            while not run_to_pos(y=12): identify_pokemon()
            while not run_to_pos(x=8): identify_pokemon()
            run_to_pos(y=9)
            run_to_pos(new_map_bank=0, new_map_id=0, x=-99) # 0.0 Petalburg City
            run_to_pos(x=20)
            run_to_pos(new_map_bank=8, new_map_id=4, y=0) # 8.4 Petalburg PC
            heal_at_counter()
            run_to_pos(y=18)
            run_to_pos(new_map_bank=0, new_map_id=17, x=99) # 0.17 Route 102
            run_to_pos(x=8)
            run_to_pos(y=12)
            run_to_pos(x=7)

    # Route 104 grass patch
    if (player_info["mapBank"] == 0 and player_info["mapId"] == 19 and
        20 <= player_info["posX"] <= 29 and 56 <= player_info["posY"] <= 57):
            while not run_to_pos(x=29): identify_pokemon()
            while not run_to_pos(y=63): identify_pokemon()
            run_to_pos(new_map_bank=0, new_map_id=0, x=99) # 0.0 Petalburg City
            run_to_pos(x=18)
            run_to_pos(y=17)
            run_to_pos(x=20)
            run_to_pos(new_map_bank=8, new_map_id=4, y=0) # 8.4 Petalburg PC
            heal_at_counter()
            run_to_pos(y=18)
            run_to_pos(x=18)
            run_to_pos(y=13)
            run_to_pos(new_map_bank=0, new_map_id=19, x=-99) # 0.19 Route 104
            run_to_pos(x=29)
            while not run_to_pos(y=57): identify_pokemon()

    # Route 116 south west grass patch
    if (player_info["mapBank"] == 0 and player_info["mapId"] == 31 and
        player_info["posX"] == 7 and 13 <= player_info["posY"] <= 17):
            while not run_to_pos(y=13): identify_pokemon()
            while not run_to_pos(x=3): identify_pokemon()
            run_to_pos(y=12)
            run_to_pos(new_map_bank=0, new_map_id=3, x=-99) # 0.3 Rustboro City
            run_to_pos(x=20)
            run_to_pos(y=39)
            run_to_pos(x=16)
            run_to_pos(new_map_bank=11, new_map_id=5, y=0) # 11.5 Rustboro PC
            heal_at_counter()
            run_to_pos(x=20)
            run_to_pos(y=12)
            run_to_pos(new_map_bank=0, new_map_id=31, x=99) # 0.31 Route 116
            run_to_pos(x=2)
            run_to_pos(y=13)
            while not run_to_pos(x=7): identify_pokemon()

def enrich_mon_data(pokemon: dict): # Function to add information to the pokemon data extracted from mGBA
    pokemon["name"] = pokemon["speciesName"].capitalize() # Capitalise name
    pokemon["metLocationName"] = location_list[pokemon["metLocation"]] # Add a human readable location
    pokemon["type"] = pokemon_list[pokemon["name"]]["type"] # Get pokemon types
    pokemon["zeroPadNumber"] = f"{pokemon_list[pokemon['name']]['number']:03}" # Get zero pad number - e.g.: #5 becomes #005
    pokemon["itemName"] = item_list[pokemon['heldItem']] # Get held item's name
    pokemon["personalityBin"] = format(pokemon["personality"], "032b") # Convert personality ID to binary
    pokemon["personalityF"] = int(pokemon["personalityBin"][:16], 2) # Get first 16 bits of binary PID
    pokemon["personalityL"] = int(pokemon["personalityBin"][16:], 2) # Get last 16 bits of binary PID

    pokemon["enrichedMoves"] = []
    for move in pokemon["moves"]: # Add information about it's moves to the Pokemon object
        pokemon["enrichedMoves"].append(move_list[move])

    player_info = get_player_info()
    pokemon["shinyNum"] = int(bin(pokemon["personalityF"] ^ pokemon["personalityL"] ^ player_info["tid"] ^ player_info["sid"])[2:], 2) # https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess

    if pokemon["shinyNum"] < 8: # Determine shininess
        pokemon["shiny"] = True
    else:
        pokemon["shiny"] = False

    if pokemon["pokerus"] != 0: # TODO get number of days infectious, see - https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9rus#Technical_information
        if pokemon["pokerus"] % 10:
            pokemon["pokerusStatus"] = "infected"
        else:
            pokemon["pokerusStatus"] = "cured"
    else:
        pokemon["pokerusStatus"] = "none"

    return pokemon

def get_party_info(index: int = 0): # Function to update the party.json file - returns whole party if a party index (1-6) is not specified
    try:
        def read_party_file():
            return yaml.load(read_file(f"{mgba_lua_dir}party.yml"), Loader=yaml.Loader)

        party = read_party_file()
        party_obj = []

        for pokemon in party["pokemon"]:
            pokemon = enrich_mon_data(pokemon)
            party_obj.append(pokemon)

        write_file("stats/party.json", json.dumps(party_obj, indent=4, sort_keys=True))

        if index > 0 and index <= 6:
            return party_obj[index-1]
        else:
            return party_obj
    except:
        return False

def get_opponent_info(): # Function to get info about the current in-game opponent in mGBA
    try:
        def read_opponent_file():
            return yaml.load(read_file(f"{mgba_lua_dir}opponent.yml"), Loader=yaml.Loader)

        opponent = read_opponent_file()

        if (opponent == False): # Check to see if it's a real pokemon, sometimes read the file from mGBA can bug out
            opponent = read_opponent_file()
            time.sleep(1/mgba_speed)
        if opponent["pokemon"][0]["speciesName"].capitalize() not in pokemon_list:
            opponent = read_opponent_file()
            time.sleep(1/mgba_speed)

        try:
            opponent = opponent["pokemon"][0]
        except IndexError:
            return False

        opponent = enrich_mon_data(opponent)

        write_file("stats/opponent.json", json.dumps(opponent, indent=4, sort_keys=True))
        return opponent

    except:
        return False

def get_player_info(save: bool = False): # Function to update the player.json file for the stream overlay - returns information about the player
    try:
        player = yaml.load(read_file(f"{mgba_lua_dir}player.yml"), Loader=yaml.Loader)
        if save:
            write_file("stats/player.json", json.dumps(player["player"][0], indent=4, sort_keys=True))
        console.log(f"X: [cyan bold]{player['player'][0]['posX']}[/], Y: [cyan bold]{player['player'][0]['posY']}[/], Map bank: [cyan bold]{player['player'][0]['mapBank']}[/], Map ID: [cyan bold]{player['player'][0]['mapId']}[/]")
        return player["player"][0]
    except:
        return False

def opponent_changed(): # This function detects if there is a new opponent, indicating the game state is now in a battle
    global last_opponent_personality
    try:
        opponent = get_opponent_info()
    except:
        return False

    if opponent:
        if last_opponent_personality != opponent["personality"]:
            last_opponent_personality = opponent["personality"]
            return True
        else:
            return False
    else:
        return False

def identify_pokemon(starter: bool = False): # Loop to identify opponent pokemon and incremement statistics, returns True if shiny, else False
    def common_stats():
        total_species_encounters = stats["pokemon"][pokemon["name"]]["non_shiny"] + stats["pokemon"][pokemon["name"]]["shiny_seen"]
        total_species_shiny_encounters = stats["pokemon"][pokemon["name"]]["shiny_seen"]
        total_encounters = stats["totals"]["non_shiny"] + stats["totals"]["shiny_seen"]
        total_shiny_encounters = stats["totals"]["shiny_seen"]
        current_streak_non_shiny = stats["totals"]["current_streak_non_shiny"]

        if pokemon["shiny"] == True:
            stats["shiny_log"].append({
                        "pokemon": pokemon["name"],
                        "location": pokemon["metLocationName"],
                        "time_encountered": str(datetime.now()),
                        "caught": False,
                        "escaped": False,
                        "total_species_encounters": total_species_encounters,
                        "total_species_shiny_encounters": total_species_shiny_encounters,
                        "total_encounters": total_encounters,
                        "total_shiny_encounters": total_shiny_encounters
            })

        # Save totals stat files
        write_file("stats/totals.json", json.dumps(stats, indent=4, sort_keys=True))

    console.rule("[bold blue]Identifying Pokemon...", style="blue")
    if not starter: time.sleep(4/mgba_speed) # Wait for battle start animation + takes a few secs for player state to update
    else: time.sleep(0.5/mgba_speed)

    release_keys()

    if starter:
        pokemon = get_party_info(1)
    else:
        pokemon = get_opponent_info()

    console.log(pokemon)

    caught = False
    stats = json.loads(read_file("stats/totals.json")) # Open totals stats file
    if not pokemon["name"] in stats["pokemon"]: # Set up pokemon stats if first encounter
        stats["pokemon"].update({pokemon["name"]: {"non_shiny": 0, "shiny_seen": 0, "shiny_caught": 0}})

    if pokemon["shiny"]:
        console.rule("[bold yellow]Shiny detected!", style="yellow")

        stats["pokemon"][pokemon["name"]]["shiny_seen"] += 1
        stats["totals"]["shiny_seen"] += 1
        prev_streak_non_shiny = stats["totals"]["current_streak_non_shiny"]
        stats["totals"]["current_streak_non_shiny"] = 0
        stats["totals"]["lowest_shiny_value_phase"] = 65535
        stats["totals"]["lowest_shiny_value_phase_pokemon"] = ""

        common_stats()

        if not starter and bot_config["method"] != "Monitor Mode":
            caught = catch_pokemon()
        else:
            caught = True

        if caught:
            stats["shiny_log"][-1]["caught"] = True
            stats["pokemon"][pokemon["name"]]["shiny_caught"] += 1
            stats["totals"]["shiny_caught"] += 1
        else:
            stats["shiny_log"][-1]["escaped"] = True
        write_file("stats/totals.json", json.dumps(stats, indent=4, sort_keys=True))

    else:
        console.rule("[bold blue]Non shiny detected...[/]", style="blue")

        stats["pokemon"][pokemon["name"]]["non_shiny"] += 1
        stats["totals"]["non_shiny"] += 1
        stats["totals"]["current_streak_non_shiny"] += 1

        if stats["totals"]["current_streak_non_shiny"] > stats["totals"]["longest_streak_non_shiny"]:
            stats["totals"]["longest_streak_non_shiny"] = stats["totals"]["current_streak_non_shiny"]
        if pokemon["shinyNum"] < stats["totals"]["lowest_shiny_value_phase"]:
            stats["totals"]["lowest_shiny_value_phase"] = pokemon["shinyNum"]
            stats["totals"]["lowest_shiny_value_phase_pokemon"] = pokemon["name"]

        common_stats()

        if not starter and bot_config["method"] != "Monitor Mode":
            if battle_pokemon == "Run": run_from_battle()
            elif battle_pokemon == "Battle": battle()

        return False

# Prepare script before main loop
console = Console(log_path=False, log_time=False) # Set up rich console object
item_list = json.loads(read_file("data/items.json"))
location_list = json.loads(read_file("data/locations.json"))
move_list = json.loads(read_file("data/moves.json"))
pokemon_list = json.loads(read_file("data/pokemon.json"))
type_list = json.loads(read_file("data/types.json"))
battle_pokemon = bot_config["battle_pokemon"]
get_player_info(save=True)
opponent = get_opponent_info()
if opponent: last_opponent_personality = opponent["personality"]
else: last_opponent_personality = 0

if bot_config["method"] == "Starters":
    battle_pokemon = "Run"
    rng_wait = 0.000

if "Up/Down" in bot_config["method"]:
    action_1, action_2 = mgba_controls["up"], mgba_controls["down"]
elif "Left/Right" in bot_config["method"]:
    action_1, action_2 = mgba_controls["left"], mgba_controls["right"]

class WindowMgr:
    def find_window_wildcard(self, wildcard):
        self._handle = None
        win32gui.EnumWindows(self.window_enum_callback, wildcard)

    def window_enum_callback(self, hwnd, wildcard):
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
            self._handle = hwnd

    def set_foreground(self):
        win32gui.SetForegroundWindow(self._handle)

    def get_rectangle(self):
        self._rect = win32gui.GetWindowRect(self._handle)

w = WindowMgr()
window_regexp = f"^mGBA.+?(?={mgba_version})"
w.find_window_wildcard(window_regexp)
w.set_foreground()
w.get_rectangle()
mgba_region = (w._rect[0],w._rect[1],(240*mgba_frame_size)+mgba_x_padding,(160*mgba_frame_size)+mgba_y_padding)

if not os.path.exists("debug"):
    os.makedirs("debug")
pyautogui.screenshot("debug/mgba_region.png", region=mgba_region)

# 🔁 Main loop
while True:
    if re.match(window_regexp, win32gui.GetWindowText(win32gui.GetForegroundWindow())): # Check if mGBA is the focused window
        release_keys()

        if args.p: # Buy 10x pokeballs method
            while True: key_sequence([mgba_controls["a"], "1sec", mgba_controls["right"], mgba_controls["down"], mgba_controls["a"], "1sec", mgba_controls["a"], "0.8sec", mgba_controls["a"], "0.8sec", mgba_controls["a"]])

        if bot_config["save_game_on_launch"]:
            bot_config["save_game_on_launch"] = False
            save_game()

        if bot_config["method"] == "Manual Mode":
            while opponent_changed() == False:
                time.sleep(2/mgba_speed)
                get_party_info()
                get_player_info()
            identify_pokemon()
        elif battle_pokemon == "Battle":
            pickup_items()
        else:
            get_party_info()
            get_player_info()

        # 🌸 Sweet scent method
        if bot_config["method"] == "Sweet Scent":
            start_menu("pokemon")
            key_sequence([mgba_controls["a"]]) # Select first pokemon in party
            while find_image("states/sweet_scent.png") == None: # Search for sweet scent in menu
                press_key(mgba_controls["down"])
            key_sequence([mgba_controls["a"], "5sec"]) # Select sweet scent and wait for animation

            identify_pokemon()

        # 🏃‍♂️🏄‍♂️ Running/surfing method
        if "Running/Surfing" in bot_config["method"]:
            while opponent_changed() == False:
                try:
                    if (args.c1 != None) and (args.c2 != None):
                        if "Up/Down" in bot_config["method"]:
                            while not run_to_pos(y=args.c1, run=True): identify_pokemon()
                            while not run_to_pos(y=args.c2, run=True): identify_pokemon()
                        elif "Left/Right" in bot_config["method"]:
                            while not run_to_pos(x=args.c1, run=True): identify_pokemon()
                            while not run_to_pos(x=args.c2, run=True): identify_pokemon()
                    else:
                        walk_until_obstructed(action_1, run=True)
                        walk_until_obstructed(action_2, run=True)
                except:
                    pass

            identify_pokemon()

        # 🐠 Fishing method
        if bot_config["method"] == "Fishing":
            player_info = get_player_info()
            press_key(mgba_controls["select"])
            while opponent_changed() == False or player_info["state"] != 80: # State 80 = overworld
                player_info = get_player_info()
                if find_image("states/oh_a_bite.png") or find_image("states/on_the_hook.png"):
                    press_key(mgba_controls["a"])
                if find_image("states/not_even_a_nibble.png") or find_image("states/it_got_away.png"):
                    key_sequence([mgba_controls["b"], "0.1sec", mgba_controls["select"]])

            identify_pokemon()

        # ➕ Starters soft reset method
        if bot_config["method"] == "Starters":
            player_info = get_player_info()
            while player_info["state"] != 80: # State 80 = overworld
                player_info = get_player_info()
                key_sequence([mgba_controls["a"], "0.5sec"])
            time.sleep(0.5/mgba_speed) # Allow time for title menu fade in
            key_sequence([f"{rng_wait}sec", mgba_controls["a"], "1sec"]) # Wait for precise time before selecting bag (Emerald broken RNG)
            if bot_config["starter_pokemon"] == "Mudkip":
                key_sequence([mgba_controls["right"], "0.1sec", mgba_controls["a"]])
            elif bot_config["starter_pokemon"] == "Treecko":
                key_sequence([mgba_controls["left"], "0.1sec", mgba_controls["a"]])
            elif bot_config["starter_pokemon"] == "Torchic":
                press_key(mgba_controls["a"])
            time.sleep(0.3/mgba_speed)
            press_key(mgba_controls["a"]) # Press A to select starter 

            while True:
                if (get_party_info(index=1) != False):
                    if identify_pokemon(starter=True):
                        sys.exit() # Kill script and wait for manual intervention to manually catch the shiny starter
                    else:
                        if rng_wait < 10: # Reset RNG wait if length is over 10s
                            rng_wait += round(random.uniform(0.014/mgba_speed, 0.018/mgba_speed), 3) # Roughly 1 frame with a bit of random variance
                        else:
                            rng_wait = 0.000
                        rng_wait = round(rng_wait, 3)
                        press_key_combo(mgba_controls["reset_emu"])
                        break

    else:
        console.log("[red bold]mGBA window is not focused![/]")
        time.sleep(0.5)
