
# Gen 3 Pokemon Python+LUA Bot for mGBA Emulator

  

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/nVEONn19lZY/0.jpg)](https://www.youtube.com/watch?v=nVEONn19lZY)

These scripts are currently being used to complete and [stream](https://www.youtube.com/watch?v=nVEONn19lZY) a Prof. Oak living ✨shiny✨ dex challenge in Pokemon emerald to YouTube. Feel free to join the [Discord](https://discord.gg/CXQDjGSeyV) for the stream to discuss/get help.

# How it works

The LUA script (`mgba_helper.lua`) runs in the [mGBA scripting API](https://mgba.io/docs/scripting.html), every frame it checks a few locations in memory and writes the data to a YAML file. These memory locations include the Pokemon structures of the opponent and all Pokemon in the party, as well as some X/Y co-ordinates and map information.

As the Python script (main bot) runs, it will be reading the LUA output constantly, I read and write to a RAM disk R:\ but it's not strictly necessary, if you write to a slow disk you may not be able to speed up the emulator. I also tested using websockets to interface Python and LUA but couldn't get it working very well.

The Python script "enriches" a lot of the data output by LUA, such as [calculating shininess](https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess), adding an array of move information (accuracy, name, power), held item name, met location name etc.

- See [here](https://github.com/40Cakes/gen3-pokemon-mgba-bot/blob/main/example/stats/party.json) for an example of a Pokemon output
- See [here](https://github.com/40Cakes/gen3-pokemon-mgba-bot/blob/main/example/stats/player.json) for an example of the player output
- See [here](https://github.com/40Cakes/gen3-pokemon-mgba-bot/blob/main/example/stats/totals.json) for an example of the stat totals

The bot uses [PyAutoGUI](https://pyautogui.readthedocs.io/en/latest/index.html) to control the mouse and keyboard input, as well as an image matching library, it can detect if certain text or images are present in the mGBA window; this library is primarily used for menu navigation.

Combine all this together, run it through a few infinite loops and you get a bot that can pretty well hunt shiny Pokemon 24/7 around the clock. You could easily reconfigure the bot to catch any Pokemon with any IVs you were after.

You can start the script with these flags for specific use cases:

-  `-y` set to run/surf along the Y-axis (up and down until obstructed)
-  `-x` set to run/surf along the X-axis (left and right until obstructed)
![running](https://i.imgur.com/3MIvzzv.gif)
- `-f` set to use fishing rod - must be facing the water with the preferred rod registered to the select button
![fishing](https://i.imgur.com/k81gvib.gif)
-  `-b` set to battle wild pokemon until lead Pokemon is out of PP or HP (it will also walk to a Poke Center but only a few routes have been pathed, see the `pokecenter()` function in `bot.py`)
-  `-p` set to buy 10x pokeballs for premier balls - must be in shop menu with poke balls selected
![buying premier balls](https://i.imgur.com/S8HnICO.gif)
-  `-s` set to automatically save the game when the bot starts (it will also automatically save after a shiny is caught)
![save](https://i.imgur.com/0wbQp9P.gif)
 - `-t` set to soft reset for starter pokemon - must save and stand to the right of the bag, facing it
![starter soft resets](https://i.imgur.com/q0ZDBhI.gif) 
 - `-w` set to use Sweet Scent - first Pokemon in the part must have the move
 - `-m` set to Monitor/Manual Mode (bot will check for shinies and updates stats without providing any input besides running from wild Pokemon, it will also output to console player X and Y co-ords plus map bank and map ID for debugging)

# Requirements
- Python + all Python packages from `requirements.txt` (`pip install -r requirements.txt`)
- Windows (uses `win32gui` to detect window)
# How to get it working
The scripts have some hard-coded config, please inspect `bot.py` and `mgba_helper.lua` to modify the config at the top of each file to suit your environment.
```
bot.py
------

mgba_version =  "0.10.0"  # This is just used to find the mGBA window
mgba_frame_size =  1  # mGBA > Audio/Video > Frame size (note: smaller game window = faster image detection)
mgba_speed =  1  # mGBA > Emulation > Fast forward speed (warning: may become unstable at higher speeds + diminishing returns on image detection speeds)
mgba_lua_dir =  "C:/Temp/"  # The directory that mgba_helper.lua script is writing to
mgba_x_padding =  10  # Adds x pixels to the mGBA window width, "debug/mgba_region.png" is generated at script run time to help tune, make sure the entire mGBA window is visible
mgba_y_padding =  25  # Adds y pixels to the mGBA window height
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
```

```
mgba_helper.lua
---------------

-- Directory to save game data (ensure the directory exists AND bot.py is pointing to the same location)
file_dir =  "C:\\Temp\\"
```

Load `mgba_helper.lua` in mGBA (Tools > Scripting > File > Load Script...).
Check to make sure mGBA is outputting .yml files in the `file_dir` you set.

Run the `bot.py` Python script to begin the bot with the flags listed above, make sure your game is in a state that the bot can begin from (typically just standing in the overworld).

# Notes

This is just the result of a bored holiday, I am by no means a Python or LUA developer so I apologise for the very scuffed code you have just stumbled upon, it goes without saying that this comes with no warranty.

`mgba_helper.lua` **only works for Emerald** right now. It *could* work for all generation 3 Pokemon games (Ruby, Sapphire, Emerald, Fire Red and Leaf Green), however I have not taken the time to map the memory of these other games yet.

I really have only tested these scripts properly at 1x game speed, I have varying results with speeds up to 3x but beyond that it falls apart.

I have only tested this on "Frame Style" type 1, there's a good chance it won't work on any other types (untested).

# TODO

- Run between set co-ords (rather than running between obstacles)
- Breeding (visiting daycare) + hatching eggs
