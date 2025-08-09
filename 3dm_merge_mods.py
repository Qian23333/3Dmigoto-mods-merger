# Author: Qian23333
# Version: v0.1.0
# Special Thanks:
#   SilentNightSound#7430 (for the original script framework)
#   Takoyaki#0697 (for demonstrating principle and creating the first proof of concept)
#   HazrateGolabi#1364 (for implementing the code to limit toggles to the on-screen character)

import os
import re
import argparse

def safe_read_file(file_path):
    """
    Safely read a file with basic error handling.
    Returns file content as string or None if failed.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def safe_write_file(file_path, content, max_retries=3):
    """
    Safely write content to a file with retry mechanism.
    Returns True if successful, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except (IOError, OSError) as e:
            print(f"Error writing to {file_path} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                input("Press ENTER to retry, or Ctrl+C to cancel...")
            else:
                print(f"Failed to write {file_path} after {max_retries} attempts")
    return False

def safe_rename_file(old_path, new_path, max_retries=3):
    """
    Safely rename a file with retry mechanism.
    Returns True if successful, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            os.rename(old_path, new_path)
            return True
        except OSError as e:
            print(f"Error renaming {old_path} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                input("Press ENTER to retry, or Ctrl+C to cancel...")
            else:
                print(f"Failed to rename {old_path} after {max_retries} attempts")
    return False

def extract_character_name(ini_path):
    """
    Extract character name from the first TextureOverride section.
    Returns the first capitalized word after TextureOverride.
    """
    content = safe_read_file(ini_path)
    if not content:
        return ""

    for line in content.splitlines():
        stripped_line = line.strip()
        if stripped_line.lower().startswith('[textureoverride'):
            # Extract the suffix after TextureOverride
            suffix = stripped_line[len('[TextureOverride'):-1]
            # Find first capitalized word using regex
            match = re.search(r'[A-Z][a-z]*(?=[A-Z]|$)', suffix)
            if match:
                return match.group(0)
            break
    return ""

def process_ini_content(original_content, character_name, namespace, remove_hash=False):
    """
    Process ini content with various transformations.
    Returns processed content as string.
    """
    lines = [f"namespace = {character_name}\\{namespace}\n"]

    # Process each line
    inside_override_section = False

    for line in original_content.splitlines(keepends=True):
        stripped = line.strip().lower()
        is_texture_override = stripped.startswith('[textureoverride')
        is_shader_override = stripped.startswith('[shaderoverride')

        # Check if we're entering a new section
        if stripped.startswith('['):
            if is_texture_override or is_shader_override:
                inside_override_section = True
            else:
                inside_override_section = False

        # Skip hash/match_first_index/filter_index lines if requested AND we're inside an override section
        skip_keys = ['hash', 'match_first_index', 'filter_index', 'match_priority']
        if (remove_hash and inside_override_section and
            any(stripped.startswith(key) and '=' in stripped for key in skip_keys)):
            continue

        # Convert Override to CommandList
        if is_texture_override or is_shader_override:
            original_section_name = line.strip()[1:-1]
            lines.append(f"[CommandList{original_section_name}]\n")
        else:
            lines.append(line)

    return ''.join(lines)

def write_namespace_ini(original_content, namespace, original_path, character_name):
    """
    Write namespace ini file with hash lines removed.
    """
    processed_content = process_ini_content(original_content, character_name, namespace, remove_hash=True)

    output_dir = os.path.dirname(original_path)
    filename = f"{character_name}.namespace"
    output_path = os.path.join(output_dir, f"{filename}.ini")

    if safe_write_file(output_path, processed_content):
        print(f" -> Saved namespace file to {output_path}")
        return output_path
    else:
        return None

def create_master_ini(file_data, args, character_name):
    """
    Creates the master ini file by grouping command lists by (hash, index).
    Uses file_data (list of (path, content) tuples) for processing.
    """
    print("\nCreating master .ini file...")

    command_groups = {}
    order_map = {str(i): i for i in range(len(file_data))}

    for i, (ini_path, original_content) in enumerate(file_data):
        namespace = str(i)
        print(f"Processing {ini_path} with namespace '{namespace}'...")

        processed_content = process_ini_content(original_content, character_name, namespace, remove_hash=False)
        print(f" -> Processed {ini_path} in memory")

        current_section_data = {}
        # Add a sentinel section header to trigger processing for the last real section
        for line in processed_content.split('\n') + ['[EOF]']:
            stripped = line.strip()
            if not stripped or stripped.startswith(';') or stripped.startswith('namespace'):
                continue

            if stripped.startswith('[') and stripped.endswith(']'):
                # A new section header triggers processing of the previous section.
                if current_section_data.get('hash'):
                    # Determine index type and value
                    if 'match_first_index' in current_section_data:
                        index = current_section_data['match_first_index']
                        index_type = 'match_first_index'
                    elif 'filter_index' in current_section_data:
                        index = current_section_data['filter_index']
                        index_type = 'filter_index'
                    else:
                        index = '-1'
                        index_type = None

                    if 'match_priority' in current_section_data:
                        priority = current_section_data['match_priority']
                    else:
                        priority = None

                    key = (current_section_data['hash'], index, index_type, priority)
                    if key not in command_groups:
                        command_groups[key] = []
                    command_groups[key].append(current_section_data)

                # Reset for the new section.
                cmd_name = stripped[1:-1]
                original_section_name = cmd_name[len('CommandList'):] if cmd_name.lower().startswith('commandlist') else ''
                current_section_data = {'namespace': namespace, 'original_section_name': original_section_name}

            elif '=' in stripped:
                key, val = stripped.split('=', 1)
                key, val = key.strip(), val.strip()
                if key.lower() in ['hash', 'match_first_index', 'filter_index', 'match_priority']:
                    current_section_data[key.lower()] = val

    ini_content = []
    # Extract paths from file_data for the comment
    paths = [path for path, _ in file_data]
    ini_content.append(f"; Merged Mod: {', '.join(paths)}\n\n")

    swap_count = len(file_data)
    ini_content.append("[Constants]")
    ini_content.append(f"global persist $swapvar = 0")
    if args.active:
        ini_content.append(f"global $active = 0")
    ini_content.append("\n[KeySwap]")
    if args.active:
        ini_content.append(f"condition = $active == 1")
    ini_content.append(f"key = {args.key}")
    if args.back_key:
        ini_content.append(f"back = {args.back_key}")
    ini_content.append(f"type = cycle")
    ini_content.append(f"$swapvar = {','.join([str(x) for x in range(swap_count)])}")
    ini_content.append("\n")
    if args.active:
        ini_content.append("[Present]")
        ini_content.append("post $active = 0\n\n")

    ini_content.append("; Master Overrides\n")
    for (hash_val, index, index_type, priority), commands in command_groups.items():
        sorted_commands = sorted(commands, key=lambda x: order_map.get(x['namespace'], 999))

        original_section_name = sorted_commands[0]['original_section_name']
        ini_content.append(f"[{original_section_name}]")
        ini_content.append(f"hash = {hash_val}")
        if index != '-1' and index_type:
            ini_content.append(f"{index_type} = {index}")
        if priority:
            ini_content.append(f"match_priority = {priority}")

        for i, command_data in enumerate(sorted_commands):
            mod_index = order_map.get(command_data['namespace'])
            if mod_index is not None:
                condition = "if" if i == 0 else "else if"
                run_target = f"CommandList\\{character_name}\\{command_data['namespace']}\\{command_data['original_section_name']}"
                ini_content.append(f"{condition} $swapvar == {mod_index}")
                ini_content.append(f"\trun = {run_target}")

        if commands:
            ini_content.append("endif")

        if args.active and "position" in original_section_name.lower():
             ini_content.append("$active = 1")
        ini_content.append("\n")

    ini_content.append("; .ini generated by 3Dmigoto mods merger script\n")
    ini_content.append("; If you have any issues or find any bugs, please open a ticket at https://github.com/Qian23333/3Dmigoto-mods-merger\n")

    content = "\n".join(ini_content)
    if safe_write_file(args.name, content):
        print(f"Master file '{args.name}' created successfully.")

def collect_ini(path, ignore):
    ini_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if root == path and ignore.lower() in file.lower():
                continue
            if "disabled" in root.lower() or "disabled" in file.lower():
                continue
            if "namespace" in file.lower():
                continue
            if os.path.splitext(file)[1] == ".ini":
                ini_files.append(os.path.join(root, file))
    return ini_files

def enable_ini(path):
    """
    Recursively finds and re-enables .ini files.
    It processes the first directory in a branch that contains .ini files and then skips deeper directories in that branch.
    This function will always check all top-level subdirectories.
    """
    subdirs = [d.path for d in os.scandir(path) if d.is_dir()]

    for subdir in subdirs:
        for root, dirs, files in os.walk(subdir, topdown=True):
            ini_files_in_dir = [f for f in files if f.lower().endswith('.ini')]

            if ini_files_in_dir:
                print(f"Found .ini files in {root}, processing this directory...")
                for file in ini_files_in_dir:
                    file_path = os.path.join(root, file)
                    if "disabled" in file.lower():
                        print(f"\tRe-enabling {file_path}")
                        dir_name = os.path.dirname(file_path)
                        file_name = os.path.basename(file_path)
                        new_file_name = re.compile("disabled", re.IGNORECASE).sub("", file_name)
                        new_path = os.path.join(dir_name, new_file_name)
                        if not safe_rename_file(file_path, new_path):
                            print(f"Failed to re-enable {file_path}")

                # Stop descending further down this path
                dirs[:] = []
                print(f" -> Finished processing {root}, skipping its subdirectories.")

def get_user_order(ini_files):
    choice = input()
    if not choice:
        return ini_files

    while choice:
        try:
            order = [int(x) for x in choice.strip().split()]
            if len(set(order)) != len(order) or max(order) >= len(ini_files) or min(order) < 0:
                print("\nERROR: Invalid order. Please enter unique numbers within the valid range.")
                choice = input()
                continue

            return [ini_files[i] for i in order]
        except ValueError:
            print("\nERROR: Invalid input. Please enter numbers separated by spaces.")
            choice = input()
    return ini_files

def main():
    parser = argparse.ArgumentParser(description="Generates a merged mod from several mod folders using a namespace approach.")
    parser.add_argument("-r", "--root", type=str, default=".", help="Location to use to create mod")
    parser.add_argument("-s", "--store", action="store_true", help="Use to keep the original .ini files enabled after completion")
    parser.add_argument("-e", "--enable", action="store_true", help="Re-enable disabled .ini files")
    parser.add_argument("-n", "--name", type=str, default="merged.ini", help="Name of final .ini file")
    parser.add_argument("-k", "--key", type=str, default="", help="Key to press to switch mods")
    parser.add_argument("-b", "--back_key", type=str, default="", help="Key to press to switch back to previous mod")
    parser.add_argument("-a", "--active", action="store_true", default=True, help="Only active character gets swapped when swapping)")

    args = parser.parse_args()

    print("\n3Dmigoto Mods Merger Script (Namespace Edition)\n")

    if args.enable:
        print("Re-enabling all .ini files...")
        enable_ini(args.root)
        print("Re-enabling complete.")

    ini_files = collect_ini(args.root, args.name)
    if not ini_files:
        print("Found no .ini files to process. If you meant to re-enable files, use the -e flag.")
        return

    print(f"Found {len(ini_files)} .ini file(s) to process:")
    for i, f in enumerate(ini_files):
        print(f"\t{i}: {f}")

    print("\nPlease enter the order you want the script to merge the mods (e.g., 1 0 2). Press ENTER for default order:")
    ordered_files = get_user_order(ini_files)

    print("\nProcessing files in the selected order...")

    # Pre-read all files into memory as (path, content) tuples to avoid repeated IO
    file_data = []
    for ini_path in ordered_files:
        print(f"Reading {ini_path}...")
        content = safe_read_file(ini_path)
        if not content:
            print(f"Failed to read {ini_path}, exiting...")
            return
        file_data.append((ini_path, content))
        print(f" -> Loaded {ini_path} into memory")

    # Extract default character name from first file
    default_character_name = extract_character_name(ordered_files[0]) if ordered_files else ""

    # Ask for character name
    print(f"\nPlease enter the character name for the output files (default: '{default_character_name}'):")
    print("Leave empty to use default, or enter a custom name:")
    character_name = input().strip()
    if not character_name:
        character_name = default_character_name

    print(f"Using character name: '{character_name}'")

    if not args.key:
        print("\nPlease enter the key that will be used to cycle mods (e.g. K or VK_RIGHT):")
        key = input()
        while not key or not (len(key) == 1 or key.lower().startswith("vk_")):
            print("\nKey not recognized, must be a single letter or virtual key code.")
            key = input()
        args.key = key

    if not args.back_key:
        print("Please enter the key that will be used to go back to the previous mod (or press ENTER to skip):")
        back_key = input()
        if back_key and (len(back_key) == 1 or back_key.lower().startswith("vk_")):
            args.back_key = back_key
        else:
            args.back_key = ""

    create_master_ini(file_data, args, character_name)

    # Write namespace ini files with hash removed
    print("\nWriting namespace .ini files...")
    namespace_files = []
    for i, (original_path, original_content) in enumerate(file_data):
        namespace = str(i)
        namespace_file = write_namespace_ini(original_content, namespace, original_path, character_name)
        if namespace_file:
            namespace_files.append(namespace_file)

    if not args.store:
        print("\nDisabling original .ini files...")
        for original_path, _ in file_data:  # Use tuple unpacking to get path
            disabled_name = os.path.join(os.path.dirname(original_path), "DISABLED" + os.path.basename(original_path))
            if safe_rename_file(original_path, disabled_name):
                print(f" -> Disabled {original_path}")
            else:
                print(f"Failed to disable {original_path}")

    print("\nAll operations completed successfully.")

if __name__ == "__main__":
    main()