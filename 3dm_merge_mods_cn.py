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
            print(f"写入文件 {file_path} 失败 (已经尝试 {attempt + 1}/{max_retries} 次): {e}")
            if attempt < max_retries - 1:
                input("按下 ENTER 重试, 或者 Ctrl+C 取消...")
            else:
                print(f"写入文件 {file_path} 失败，已重试 {max_retries} 次")
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
            print(f"重命名文件 {old_path} 失败 (已经尝试 {attempt + 1}/{max_retries} 次): {e}")
            if attempt < max_retries - 1:
                input("按下 ENTER 重试, 或者 Ctrl+C 取消...")
            else:
                print(f"重命名文件 {old_path} 失败，已重试 {max_retries} 次")
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
        skip_keys = ['hash', 'match_first_index', 'filter_index', 'match_priority', 'allow_duplicate_hash']
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
        print(f" -> 已保存命名空间文件到 {output_path}")
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
        print(f"正在处理 {ini_path}，命名空间为 '{namespace}'...")

        processed_content = process_ini_content(original_content, character_name, namespace, remove_hash=False)
        print(f" -> 已在内存中处理 {ini_path}")

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
        if ('ShaderOverride').lower() in original_section_name.lower():
            ini_content.append("allow_duplicate_hash = overrule")

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
        print(f"主文件 '{args.name}' 创建成功。")

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
                print(f"在 {root} 找到 .ini 文件，正在处理该目录...")
                for file in ini_files_in_dir:
                    file_path = os.path.join(root, file)
                    if "disabled" in file.lower():
                        print(f"\t正在重新启用 {file_path}")
                        dir_name = os.path.dirname(file_path)
                        file_name = os.path.basename(file_path)
                        new_file_name = re.compile("disabled", re.IGNORECASE).sub("", file_name)
                        new_path = os.path.join(dir_name, new_file_name)
                        if not safe_rename_file(file_path, new_path):
                            print(f"重新启用 {file_path} 失败")

                # Stop descending further down this path
                dirs[:] = []
                print(f" -> 已处理完 {root}，跳过其子目录。")

def get_user_order(ini_files):
    choice = input()
    if not choice:
        return ini_files

    while choice:
        try:
            order = [int(x) for x in choice.strip().split()]
            if len(set(order)) != len(order) or max(order) >= len(ini_files) or min(order) < 0:
                print("\n错误：顺序无效。请输入唯一且在有效范围内的数字。")
                choice = input()
                continue

            return [ini_files[i] for i in order]
        except ValueError:
            print("\n错误：输入无效。请用空格分隔输入数字。")
            choice = input()
    return ini_files

def main():
    parser = argparse.ArgumentParser(description="使用命名空间方式合并多个 mod 文件夹生成一个mod。")
    parser.add_argument("-r", "--root", type=str, default=".", help="用于创建 mod 的目录")
    parser.add_argument("-s", "--store", action="store_true", help="完成后保留原始 .ini 文件为启用状态")
    parser.add_argument("-e", "--enable", action="store_true", help="重新启用被禁用的 .ini 文件")
    parser.add_argument("-n", "--name", type=str, default="merged.ini", help="最终生成的 .ini 文件名")
    parser.add_argument("-k", "--key", type=str, default="", help="切换 mod 时使用的按键")
    parser.add_argument("-b", "--back_key", type=str, default="", help="切换回上一个 mod 时使用的按键")
    parser.add_argument("-a", "--active", action="store_true", default=True, help="仅在激活角色时切换 mod")

    args = parser.parse_args()

    print("\n3Dmigoto Mods Merger 脚本（命名空间版）\n")

    if args.enable:
        print("正在重新启用所有 .ini 文件...")
        enable_ini(args.root)
        print("重新启用完成。")

    ini_files = collect_ini(args.root, args.name)
    if not ini_files:
        print("未找到需要处理的 .ini 文件。如果你想重新启用文件，请使用 -e 参数。")
        return

    print(f"共找到 {len(ini_files)} 个 .ini 文件:")
    for i, f in enumerate(ini_files):
        print(f"\t{i}: {f}")

    print("\n请输入你希望合并 mod 的顺序（如：1 0 2），直接回车使用默认顺序:")
    ordered_files = get_user_order(ini_files)

    print("\n按所选顺序处理文件...")

    # Pre-read all files into memory as (path, content) tuples to avoid repeated IO
    file_data = []
    for ini_path in ordered_files:
        print(f"正在读取 {ini_path}...")
        content = safe_read_file(ini_path)
        if not content:
            print(f"读取 {ini_path} 失败，正在退出...")
            return
        file_data.append((ini_path, content))
        print(f" -> 已加载 {ini_path} 到内存")

    # Extract default character name from first file
    default_character_name = extract_character_name(ordered_files[0]) if ordered_files else ""

    # Ask for character name
    print(f"\n请输入输出文件的角色名（默认: '{default_character_name}'）：")
    print("留空使用默认，或输入自定义名称:")
    character_name = input().strip()
    if not character_name:
        character_name = default_character_name

    print(f"使用角色名: '{character_name}'")

    if not args.key:
        print("\n请输入用于切换 mod 的按键（如 K 或 VK_RIGHT）：")
        key = input()
        while not key or not (len(key) == 1 or key.lower().startswith("vk_")):
            print("\n按键无效，必须为单个字母或虚拟键码。")
            key = input()
        args.key = key

    if not args.back_key:
        print("请输入用于返回上一个 mod 的按键（或直接回车跳过）：")
        back_key = input()
        if back_key and (len(back_key) == 1 or back_key.lower().startswith("vk_")):
            args.back_key = back_key
        else:
            args.back_key = ""

    create_master_ini(file_data, args, character_name)

    # Write namespace ini files with hash removed
    print("\n正在写入命名空间 .ini 文件...")
    namespace_files = []
    for i, (original_path, original_content) in enumerate(file_data):
        namespace = str(i)
        namespace_file = write_namespace_ini(original_content, namespace, original_path, character_name)
        if namespace_file:
            namespace_files.append(namespace_file)

    if not args.store:
        print("\n正在禁用原始 .ini 文件...")
        for original_path, _ in file_data:  # Use tuple unpacking to get path
            disabled_name = os.path.join(os.path.dirname(original_path), "DISABLED" + os.path.basename(original_path))
            if safe_rename_file(original_path, disabled_name):
                print(f" -> 已禁用 {original_path}")
            else:
                print(f"禁用 {original_path} 失败")

    print("\n所有操作已成功完成。")

if __name__ == "__main__":
    main()