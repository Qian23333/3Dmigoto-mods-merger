# Author: Qian23333
# Version: v0.1.0
# Special Thanks:
#   SilentNightSound#7430 (for the original script framework)
#   Takoyaki#0697 (for demonstrating principle and creating the first proof of concept)
#   HazrateGolabi#1364 (for implementing the code to limit toggles to the on-screen character)

import os
import re
import argparse

def extract_character_name(ini_path):
    """
    Extract character name from the first TextureOverride section.
    Returns the first capitalized word after TextureOverride.
    """
    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line.lower().startswith('[textureoverride'):
                    # Extract the suffix after TextureOverride
                    suffix = stripped_line[len('[TextureOverride'):-1]
                    # Find first capitalized word using regex
                    match = re.search(r'[A-Z][a-z]*(?=[A-Z]|$)', suffix)
                    if match:
                        return match.group(0)
                    break
    except Exception as e:
        print(f"Error extracting character name from {ini_path}: {e}")
    return ""

def process_ini_file(ini_path, character_name, namespace):
    """
    Processes a single ini file by injecting a 'namespace = ...' directive
    and converting [TextureOverride...] sections to [CommandList...].
    Returns the processed content and original content for later use.
    """
    print(f"Processing {ini_path} with namespace '{namespace}'...")

    processed_lines = [f"namespace = {character_name}\\{namespace}\n"]
    original_lines = []

    try:
        with open(ini_path, 'r', encoding='utf-8') as f:
            for line in f:
                original_lines.append(line)
                stripped_line = line.strip()
                if stripped_line.lower().startswith('[textureoverride'):
                    suffix = stripped_line[len('[TextureOverride'):-1]
                    processed_lines.append(f"[CommandList{suffix}]\n")
                else:
                    processed_lines.append(line)

        print(f" -> Processed {ini_path} in memory")
        return ''.join(processed_lines), ''.join(original_lines)

    except Exception as e:
        print(f"Error processing {ini_path}: {e}")
        return None, None

def write_namespace_ini(original_content, namespace, original_path, character_name):
    lines_without_hash = []
    for line in original_content.split('\n'):
        stripped = line.strip().lower()
        if not ((stripped.startswith('hash') or stripped.startswith('match_first_index')) and '=' in stripped):
            lines_without_hash.append(line)

    lines_without_override = [f'namespace = {character_name}\\{namespace}\n\n']
    for line in lines_without_hash:
        if line.lower().startswith('[textureoverride'):
            prefix_len = len('[TextureOverride')
            line = f'[CommandList{line[prefix_len:-1]}.{namespace}]'
        lines_without_override.append(line)

    output_dir = os.path.dirname(original_path)
    filename = f"{character_name}.{namespace}"
    output_path = os.path.join(output_dir, f"{filename}.ini")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines_without_override))
        print(f" -> Saved namespace file to {output_path}")
        return output_path

    except Exception as e:
        print(f"Error writing namespace file: {e}")
        return None

def create_master_ini(processed_contents, original_paths, args, character_name):
    """
    Creates the master ini file by grouping command lists by (hash, index).
    Uses processed_contents (list of processed file contents) and original_paths for reference.
    """
    print("\nCreating master .ini file...")

    command_groups = {}
    order_map = {str(i): i for i in range(len(original_paths))}

    for i, processed_content in enumerate(processed_contents):
        namespace = str(i)

        current_section_data = {}
        for line in processed_content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith(';') or stripped.startswith('namespace'):
                continue

            if stripped.startswith('[') and stripped.endswith(']'):
                if current_section_data.get('hash'):
                    key = (current_section_data['hash'], current_section_data.get('match_first_index', '-1'))
                    if key not in command_groups:
                        command_groups[key] = []
                    command_groups[key].append(current_section_data)

                cmd_name = stripped[1:-1]
                suffix = cmd_name[len('CommandList'):] if cmd_name.lower().startswith('commandlist') else ''
                current_section_data = {'namespace': namespace, 'suffix': suffix}

            elif '=' in stripped:
                key, val = stripped.split('=', 1)
                key, val = key.strip(), val.strip()
                if key.lower() in ['hash', 'match_first_index']:
                    current_section_data[key.lower()] = val

        if current_section_data.get('hash'):
            key = (current_section_data['hash'], current_section_data.get('match_first_index', '-1'))
            if key not in command_groups:
                command_groups[key] = []
            command_groups[key].append(current_section_data)

    ini_content = []
    ini_content.append(f"; Merged Mod: {', '.join(original_paths)}\n\n")

    swap_count = len(original_paths)
    ini_content.append("[Constants]")
    ini_content.append(f"global persist $swapvar = 0")
    if args.active:
        ini_content.append(f"global $active = 0")
    ini_content.append("\n[KeySwap]")
    if args.active:
        ini_content.append(f"condition = $active == 1")
    ini_content.append(f"key = {args.key}")
    if args.back_key:
        ini_content.append(f"back_key = {args.back_key}")
    ini_content.append(f"type = cycle")
    ini_content.append(f"$swapvar = {','.join([str(x) for x in range(swap_count)])}")
    ini_content.append("\n")
    if args.active:
        ini_content.append("[Present]")
        ini_content.append("post $active = 0\n\n")

    ini_content.append("; Master Overrides\n")
    for (hash_val, index), commands in command_groups.items():
        sorted_commands = sorted(commands, key=lambda x: order_map.get(x['namespace'], 999))

        suffix = sorted_commands[0]['suffix']
        ini_content.append(f"[TextureOverride{suffix}]")
        ini_content.append(f"hash = {hash_val}")
        if index != '-1':
            ini_content.append(f"match_first_index = {index}")

        for i, command_data in enumerate(sorted_commands):
            mod_index = order_map.get(command_data['namespace'])
            if mod_index is not None:
                condition = "if" if i == 0 else "else if"
                run_target = f"CommandList\\{character_name}\\{command_data['namespace']}\\{command_data['suffix']}.{command_data['namespace']}"
                ini_content.append(f"{condition} $swapvar == {mod_index}")
                ini_content.append(f"\trun = {run_target}")

        if commands:
            ini_content.append("endif")

        if args.active and "position" in suffix.lower():
             ini_content.append("$active = 1")
        ini_content.append("\n")

    ini_content.append("; .ini generated by 3Dmigoto mods merger script\n")
    ini_content.append("; If you have any issues or find any bugs, please open a ticket at https://github.com/Qian23333/3Dmigoto-mods-merger\n")

    with open(args.name, "w", encoding="utf-8") as f:
        f.write("\n".join(ini_content))

    print(f"Master file '{args.name}' created successfully.")

def collect_ini(path, ignore):
    ini_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if root == path and ignore.lower() in file.lower():
                continue
            if "disabled" in root.lower() or "disabled" in file.lower():
                continue
            if os.path.splitext(file)[1] == ".ini":
                ini_files.append(os.path.join(root, file))
    return ini_files

def enable_ini(path):
    for root, _, files in os.walk(path):
        for file in files:
            if os.path.splitext(file)[1] == ".ini" and ("disabled" in root.lower() or "disabled" in file.lower()):
                print(f"\tRe-enabling {os.path.join(root, file)}")
                new_path = re.compile("disabled", re.IGNORECASE).sub("", os.path.join(root, file))
                os.rename(os.path.join(root, file), new_path)

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
    processed_contents = []
    original_contents = []

    # Extract default character name from first file
    default_character_name = extract_character_name(ordered_files[0]) if ordered_files else ""

    # Ask for character name
    print(f"\nPlease enter the character name for the output files (default: '{default_character_name}'):")
    print("Leave empty to use default, or enter a custom name:")
    character_name = input().strip()
    if not character_name:
        character_name = default_character_name

    print(f"Using character name: '{character_name}'")

    for i, ini_path in enumerate(ordered_files):
        namespace = str(i) # Use the order index as the namespace
        processed_content, original_content = process_ini_file(ini_path, character_name, namespace)
        if processed_content and original_content:
            processed_contents.append(processed_content)
            original_contents.append(original_content)

    if not processed_contents:
        print("No files were processed successfully. Exiting.")
        return

    if not args.key:
        print("\nPlease enter the key that will be used to cycle mods (e.g., K):")
        key = input()
        while not key or len(key) != 1:
            print("\nKey not recognized, must be a single letter.")
            key = input()
        args.key = key.lower()

    if not args.back_key:
        print("Please enter the key that will be used to go back to the previous mod (or press ENTER to skip):")
        back_key = input()
        if back_key and len(back_key) == 1:
            args.back_key = back_key.lower()
        else:
            args.back_key = ""

    create_master_ini(processed_contents, ordered_files, args, character_name)

    # Write namespace ini files with hash removed
    print("\nWriting namespace .ini files...")
    namespace_files = []
    for i, (original_content, original_path) in enumerate(zip(original_contents, ordered_files)):
        namespace = str(i)
        namespace_file = write_namespace_ini(original_content, namespace, original_path, character_name)
        if namespace_file:
            namespace_files.append(namespace_file)

    if not args.store:
        print("\nDisabling original .ini files...")
        for file in ordered_files: # Disable the original files in the correct order
            try:
                os.rename(file, os.path.join(os.path.dirname(file), "DISABLED" + os.path.basename(file)))
                print(f" -> Disabled {file}")
            except OSError as e:
                print(f"Error disabling {file}: {e}")

    print("\nAll operations completed successfully.")

if __name__ == "__main__":
    main()