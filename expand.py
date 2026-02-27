#!/usr/bin/env python3
import argparse
import fnmatch
import os
import re
import platform
import shlex
import sys

#    'compiler.ar.flags'
#    'compiler.c.elf.flags'
#    'compiler.c.flags'
#    'compiler.cpp.extra_flags'
#    'compiler.cpp.flags'
#    'compiler.libraries.ldflags'
#    'compiler.optimization_flags'
#    'serial.port'
#    'serial.port.file'

ARDUINO_VARS=set([ 
    'archive_file',
    'archive_file_path',
    'build.arch',
    'build.board',
    'build.board.platform.path',
    'build.core.path',
    'build.core.platform.path',
    'build.extra_flags',
    'build.fqbn',
    'build.library_discovery_phase',
    'build.path',
    'build.project_name',
    'build.source.path',
    'build.system.path',
    'build.variant.path',
    'config.path',
    'directories.data',
    'directories.user',
    'extra.time.dst',
    'extra.time.local',
    'extra.time.utc',
    'extra.time.zone',
    '_id',
    'ide_version',
    'includes',
    'object_file',
    'object_files',
    'preprocessed_file_path',
    'program.verbose',
    'program.verify',
    'runtime.tools.*.path',
    'runtime.hardware.path',
    'runtime.ide.path',
    'runtime.ide.version',
    'runtime.os',
    'runtime.platform.path',
    'runtime.tools.*.path',
    'runtime.use_core_platform_path_for_runtime_platform_path',
    'sketch_path',
    'software',
    'source_file',
    'upload.field.*',
    'upload.maximum_data_size',
    'upload.maximum_size',
    'upload.params.quiet',
    'upload.params.verbose',
    'upload.port.*',
    'upload.verbose',
    'upload.verify',
])

class ArduinoPlatformExpander:
    def __init__(self, platform_path, boards_path):
        self.platform_data = self._parse_file(platform_path)
        self.boards_data = self._parse_file(boards_path)
        
        # Standard system variables normally provided by the IDE/CLI
        self.system_vars = {
        }

    def _detect_os(self):
        sys_platform = platform.system().lower()
        if sys_platform == "windows":
            return "windows"
        elif sys_platform == "darwin":
            return "macosx"
        else:
            return "linux"

    def _parse_file(self, filepath):
        """
        Parses a .txt file (key=value) into a dictionary.
        Ignores comments (#) and empty lines.
        """
        data = {}
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found.")
            return data
            
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key.strip()] = value.strip()
        return data

    def _apply_os_overrides(self, data, os):
        """
        Looks for keys ending in .linux, .windows, .macosx and overrides the base key.
        """
        if not os:
            os = self._detect_os()
        suffix = "." + os
        
        overrides = {}
        for key, value in data.items():
            if key.endswith(suffix):
                base_key = key[:-len(suffix)]
                overrides[base_key] = value
        
        data.update(overrides)
        return data

    def list_boards(self):
        """Returns a list of available board identifiers."""
        boards = set()
        for key in self.boards_data:
            if "." in key:
                boards.add(key.split('.')[0])
        return sorted(list(boards))

    def list_menus(self, board_id):
        """Returns available menu options for a specific board."""
        menus = {}
        prefix = f"{board_id}.menu."
        for key, value in self.boards_data.items():
            if key.startswith(prefix):
                # Format: board.menu.menu_id.election_id=Label
                parts = key[len(prefix):].split('.')
                if len(parts) >= 2:
                    menu_id = parts[0]
                    selection_id = parts[1]
                    # We usually want the label, which is the value of this specific key
                    # if the key ends there.
                    if len(parts) == 2: 
                        if menu_id not in menus: menus[menu_id] = []
                        menus[menu_id].append((selection_id, value))
        return menus

    def expand_vars(self, board_id, menu_selections=None, os=None):
        """
        Main logic to expand variables for a specific board configuration.
        
        1. Load global platform.txt variables.
        2. Merge system variables.
        3. Load board-specific variables (stripping board_id).
        4. Load menu-specific variables (stripping menu prefixes).
        5. Apply OS overrides.
        6. Recursively resolve {variables}.
        """
        if menu_selections is None:
            menu_selections = {}

        # 1. Start with platform global definitions
        context = self.platform_data.copy()
        
        # 2. Add System variables
        context.update(self.system_vars)

        # 3. Merge Board specific properties
        # Format: board_id.property=value -> property=value
        board_prefix = f"{board_id}."
        for key, value in self.boards_data.items():
            if key.startswith(board_prefix):
                # We strip the board prefix to make it a global property in this context
                # e.g. 'uno.build.mcu' becomes 'build.mcu'
                clean_key = key[len(board_prefix):]
                
                # Check if this is a menu definition (we ignore definitions of menus themselves here, 
                # we only want the properties that result from a menu selection)
                if not clean_key.startswith("menu."):
                    context[clean_key] = value

        # 4. Merge Menu selections
        # Format: board_id.menu.menu_id.selection_id.property=value -> property=value
        for menu_id, selection_id in menu_selections.items():
            menu_prefix = f"{board_id}.menu.{menu_id}.{selection_id}."
            for key, value in self.boards_data.items():
                if key.startswith(menu_prefix):
                    clean_key = key[len(menu_prefix):]
                    context[clean_key] = value

        # 5. Apply OS Overrides (e.g., tools.x.path.windows overrides tools.x.path)
        context = self._apply_os_overrides(context, os)

        # 6. Recursive Variable Expansion
        return self._recursive_expansion(context)

    def _recursive_expansion(self, context):
        """
        Resolves {key} references until no changes occur.
        """
        # Regex to find {variable}
        var_pattern = re.compile(r'\{([\w\.\-_]+)\}')
       
        used_context = set()
        while True:
            changes_made = False
            missing_vars = set()
            for key, value in context.items():
                if value is None: continue
                
                # Find all {vars} in the current value
                matches = var_pattern.findall(value)
                
                if not matches:
                    continue
                
                new_value = value
                for match in matches:
                    if match in context:
                        used_context.add(match)
                        # Replace {match} with its value from context
                        # We use a safe replacement to avoid regex injection issues
                        replace_val = context[match]
                        new_value = new_value.replace(f"{{{match}}}", replace_val)
                        changes_made = True
                    else:
                        missing_vars.add(match)
                
                if changes_made:
                    context[key] = new_value
            
            if not changes_made:
                break
       
        return context, used_context, missing_vars

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    
    # parse arguments
    parser = argparse.ArgumentParser(description="Expand Arduino platform and board configurations.")
    parser.add_argument("board", help="Board identifier to expand.")
    parser.add_argument("selections", nargs="*", help="Selection for menu options.")
    parser.add_argument("--os", choices=["windows", "linux", "macosx"], help="Override OS (windows, linux, macosx).")
    parser.add_argument("--unused", "-u", action="store_true", help="Show variables that were defined but not used in the final expansion.")
    parser.add_argument("--verbose", "-v", action="store_true", help="List each argument of each variable")
    args = parser.parse_args()

    # Initialize
    expander = ArduinoPlatformExpander("platform.txt", "boards.txt")
    
    if args.board not in expander.list_boards():
        print(f"Error: Board '{args.board}' not found.")
        print("Available Boards:", expander.list_boards())
        sys.exit(1)
    
    board_menus = expander.list_menus(args.board)
    menu_selections = {}
    for selection in args.selections:
        if '=' not in selection:
            print(f"Invalid selection format: {selection}. Expected format is menu_id=selection_id.")
            sys.exit(1)

        menu_id, selection_id = selection.split('=', 1)
        if menu_id not in board_menus:
            print(f"Error: Menu '{menu_id}' not found for board '{args.board}'.")
            print(f"Menus for {args.board}:", board_menus)
            sys.exit(1)
        if selection_id not in [ m[0] for m in board_menus[menu_id] ]:
            print(f"Error: Selection '{selection_id}' not found for menu '{menu_id}' on board '{args.board}'.")
            print(f"Available selections for {menu_id}:", [ m[0] for m in board_menus[menu_id] ])
            sys.exit(1)

        menu_selections[menu_id] = selection_id

    # Expand
    exp_vars, used_vars, missing_vars = expander.expand_vars(args.board, menu_selections, os=args.os)

    print(f"#\n# {args.board} {menu_selections}\n#\n")

    if args.unused:
        unused_vars = set(exp_vars.keys()) - used_vars
    
        print(f"# Unused variables:\n#")
        for k in sorted(unused_vars):
            print(f"# {k}={exp_vars[k]}")
        print()
    
    print(f"# Unset variables:\n#")
    for k in sorted(missing_vars):
        for pattern in ARDUINO_VARS:
            if fnmatch.fnmatch(k, pattern):
                break
        else:
            print(f"# {k}")
    print()

    if args.verbose:
        for k in sorted(exp_vars):
            lexer = shlex.shlex(exp_vars[k], posix=False)
            lexer.whitespace_split = True
            for tok in lexer:
                print(f"{k} {tok}")
    else:
        for k in sorted(exp_vars):
            print(f"{k}={exp_vars[k]}")
