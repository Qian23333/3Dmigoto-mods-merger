English | [中文](README_CN.md)

# 3dmigoto Mods Merger (Namespace Edition)

A Python script to merge multiple 3dmigoto mods into a single, switchable mod pack. This allows you to cycle through different mods in-game using a hotkey.

This script is based on the "namespace" technique, which isolates mod files to prevent conflicts and allows for dynamic loading.

## Features

-   Merges multiple 3dmigoto mods into one.
-   Allows in-game switching between mods with a configurable hotkey.
-   Optional "back" key to return to the previous mod.
-   Automatically detects and processes `.ini` files.
-   Can limit mod swapping to only affect the on-screen character.
-   Interactively prompts for mod merge order, character name, and hotkeys.
-   Can disable original mod files to prevent them from loading alongside the merged mod.
-   Can re-enable previously disabled mod files.

## Prerequisites

-   [Python 3](https://www.python.org/downloads/)

## How to Use

1.  **Prepare your mods:**
    -   Create a main folder for your mods.
    -   Place each mod you want to merge into its own subfolder inside the main folder.
    -   Place the `3dm_merge_mods.py` script into the main folder. Your structure should look like this:

    ```
    /MyMods/
    |-- 3dm_merge_mods.py
    |-- Mod1/
    |   |-- Mod1.ini
    |   |-- ... (other mod files)
    |-- Mod2/
    |   |-- Mod2.ini
    |   |-- ... (other mod files)
    |-- Mod3/
        |-- Mod3.ini
        |-- ... (other mod files)
    ```

2.  **Run the script:**
    -   Open a command prompt or terminal in your main folder (e.g., `MyMods`).
    -   Run the script using `python 3dm_merge_mods.py`.

3.  **Follow the prompts:**
    -   **Mod Order:** The script will list all found `.ini` files. Enter the desired merge order as numbers separated by spaces (e.g., `1 0 2`). Press Enter to use the default order.
    -   **Character Name:** The script will suggest a character name based on the first mod. You can accept it by pressing Enter or provide a custom name. This name is used for generated files.
    -   **Hotkeys:** You will be prompted to enter a key to cycle through the mods (e.g., `K` or a virtual key code like `VK_RIGHT`) and an optional key to go back.

4.  **Done!**
    -   The script will create a `merged.ini` file (or the name you specified) and a folder named after your character (e.g., `CharacterName.namespace/`).
    -   The original mod `.ini` files will be disabled by renaming them to `DISABLED...`.
    -   Copy the newly generated `merged.ini` and the `CharacterName.namespace` folder to your game's `Mods` directory where 3dmigoto is installed.

## Command-Line Arguments

You can customize the script's behavior with these arguments:

| Argument | Short | Description | Default |
|---|---|---|---|
| `--root <path>` | `-r` | The directory where your mod folders are located. | `.` (current directory) |
| `--name <filename>` | `-n` | The name for the final merged `.ini` file. | `merged.ini` |
| `--key <key>` | `-k` | The hotkey to cycle through mods. | Prompts user |
| `--back_key <key>` | `-b` | The hotkey to cycle backwards. | Prompts user |
| `--store` | `-s` | Keep the original `.ini` files enabled after merging. | Disabled |
| `--active` | `-a` | Only swaps the mod for the currently active character on screen. | Enabled |
| `--enable` | `-e` | A utility function to re-enable all disabled `.ini` files in the root folder. | Disabled |

**Example:**
```bash
python 3dm_merge_mods.py -n "MyAwesomePack.ini" -k "VK_F5"
```

## Credits

-   **Qian23333:** Author of this script.
-   **SilentNightSound#7430:** Original script framework.
-   **Takoyaki#0697:** Proof of concept and principle demonstration.
-   **HazrateGolabi#1364:** Code for limiting toggles to the on-screen character.