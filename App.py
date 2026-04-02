import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import csv
import json
import re
import csv_comparator  # The new module
from collections import Counter, defaultdict

# Local Modules
import conversion_utils
import stat_utils           # Required for build analysis
import Inventory_Scanner    # The merged scanner
import Sanity_Checker       # The dynamic checker

# --- CONFIGURATION ---
CONFIG_FILE = ".artifact_tool_config.json"
DEFAULT_CSV_FILE = "artifacts usage.csv"
DEFAULT_JS_FILE = "Generated Master Filter.js"
SETS_ENUM_FILE = "sets_enum.ts"
WHITELIST_FILE = "whitelist.txt"

# --- EVALUATOR CONSTANTS ---
# Median values to calculate how many rolls occurred
AVG_ROLLS = {
    "critRate_": 3.3, "critDMG_": 6.6, "atk_": 4.96, "hp_": 4.96, "def_": 6.2,
    "eleMas": 19.8, "enerRech_": 5.5, "atk": 16.5, "hp": 254.0, "def": 19.8
}

# Maximum theoretical values to calculate RV%
MAX_ROLLS = {
    "critRate_": 3.89, "critDMG_": 7.77, "atk_": 5.83, "hp_": 5.83, "def_": 7.29,
    "eleMas": 23.31, "enerRech_": 6.48, "atk": 19.45, "hp": 298.75, "def": 23.15
}

# --- EXTRACTION LOGIC (Restored) ---

def normalize_character_name(name):
    name_lower = name.lower().replace(' ', '')
    traveler_match = re.match(r'^(aether|lumine)(anemo|geo|electro|dendro|hydro|pyro)?$', name_lower)
    if traveler_match:
        element = traveler_match.group(2)
        if element: return f"MC ({element.capitalize()})"
        return "MC"
    return name

def parse_teams_data(file_path):
    teams = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file: content = file.read()
    except Exception as e: raise Exception(f"Could not read file: {e}")

    # Regex to find team blocks in Simpact/GCsim output
    team_blocks = re.findall(r'=+ VALID TEAM .+?=+(.*?)(?=\n\n|\Z)', content, re.DOTALL)
    for block in team_blocks:
        if not re.search(r'Mean DPS: [\d,]+', block): continue
        char_lines = re.findall(r'  - Name: (.+)', block)
        characters = []
        for line in char_lines:
            match = re.search(r'^(.*?)\s*\|\s*Stats:\s*(\[.*\])$', line)
            if not match: continue
            main_part, stats_part_str = match.groups()
            try: stats_array = json.loads(stats_part_str)
            except json.JSONDecodeError: continue
            sets_match = re.search(r' \| Sets: (.+)', main_part)
            if not sets_match: continue
            char_name = main_part.split(' | ')[0].strip()
            raw_sets = sets_match.group(1).strip()
            
            # Parse sets (e.g., "Emblem of Severed Fate (x4)" or "Gladiator (x2), Shimenawa (x2)")
            artifacts = [s.split(' (x')[0].strip().replace(' ', '') for s in raw_sets.split('), ') if ' (x' in s]
            if not artifacts and ' (x' in raw_sets: artifacts = [raw_sets.split(' (x')[0].strip().replace(' ', '')]
            
            characters.append({'name': char_name, 'artifacts': artifacts, 'stats': stats_array})
        teams.append({'characters': characters})
    return teams

def analyze_all_character_builds(teams_data, allowed_characters=None):
    all_char_data = defaultdict(lambda: {
        'instance_count': 0, 'artifact_counter': Counter(),
        'sands_counter': Counter(), 'goblet_counter': Counter(), 'circlet_counter': Counter(),
        'substat_roll_totals': defaultdict(float)
    })
    for team in teams_data:
        for character in team['characters']:
            raw_char_name = character['name']
            if allowed_characters is not None:
                if raw_char_name.lower() not in allowed_characters: continue
            normalized_char_name = normalize_character_name(raw_char_name)
            data = all_char_data[normalized_char_name]
            data['instance_count'] += 1
            
            set_combo = "+".join(sorted(character['artifacts'])) if character['artifacts'] else "NoSets"
            data['artifact_counter'][set_combo] += 1
            
            # Use stat_utils to determine main stats from the stat array
            main_stats, substats = stat_utils.deduce_build(character['stats'])
            if main_stats:
                data['sands_counter'][main_stats['Sands']] += 1
                data['goblet_counter'][main_stats['Goblet']] += 1
                data['circlet_counter'][main_stats['Circlet']] += 1
            if substats:
                for stat, value in substats.items():
                    idx = stat_utils.STAT_NAME_TO_INDEX.get(stat)
                    if idx and stat_utils.AVG_SUB_VALUES[idx]:
                        data['substat_roll_totals'][stat] += value / stat_utils.AVG_SUB_VALUES[idx]
    return all_char_data

def format_aggregated_artifacts(counter, total_count, style):
    if total_count == 0: return ""
    top_sets_formatted = []
    cumulative_count = 0
    for item, count in counter.most_common():
        cumulative_count += count
        display_name = item.replace('+', ', ')
        if style == 'verbose':
            percentage = (count / total_count) * 100
            top_sets_formatted.append(f"{display_name} ({count}/{total_count} | {percentage:.1f}%)")
        else: top_sets_formatted.append(display_name)
        if (cumulative_count / total_count) >= 0.70: break
    return ", ".join(top_sets_formatted)

def generate_spreadsheet_data(all_char_data, style):
    rows = []
    if not all_char_data: return [], []
    
    def translate(stat_name): return stat_utils.INTERNAL_TO_TS_STAT.get(stat_name, stat_name)
    
    def format_list(counter, total_count, style, needs_translation=False):
        if style == 'verbose':
            if needs_translation: return [f"{translate(item)} ({count}/{total_count} | {(count/total_count)*100:.1f}%)" for item, count in counter.most_common()]
            else: return [f"{item} ({count}/{total_count} | {(count/total_count)*100:.1f}%)" for item, count in counter.most_common()]
        else:
            items = [item for item, count in counter.most_common()]
            return [translate(item) for item in items] if needs_translation else items

    headers = ['Character Name', 'Top Artifact Sets', 'Common Sands', 'Common Goblet', 'Common Circlet', 'Substat Priority']
    
    for char_name in sorted(all_char_data.keys()):
        data = all_char_data[char_name]
        count = data['instance_count']
        row = {'Character Name': char_name}
        row['Top Artifact Sets'] = format_aggregated_artifacts(data['artifact_counter'], count, style)
        row['Common Sands'] = ", ".join(format_list(data['sands_counter'], sum(data['sands_counter'].values()), style, needs_translation=True))
        row['Common Goblet'] = ", ".join(format_list(data['goblet_counter'], sum(data['goblet_counter'].values()), style, needs_translation=True))
        row['Common Circlet'] = ", ".join(format_list(data['circlet_counter'], sum(data['circlet_counter'].values()), style, needs_translation=True))
        
        avg_rolls = {stat: total / count for stat, total in data['substat_roll_totals'].items()}
        sorted_substats = sorted(avg_rolls.items(), key=lambda item: item[1], reverse=True)
        
        if style == 'verbose': substat_list = [f"{translate(stat)} ({rolls:.1f})" for stat, rolls in sorted_substats[:4]]
        else: substat_list = [translate(stat) for stat, rolls in sorted_substats[:4]]
        
        row['Substat Priority'] = ", ".join(substat_list)
        rows.append(row)
    return headers, rows
    
def evaluate_roll_value(csv_file, json_file):
    logs = []
    builds = defaultdict(dict)
    
    # --- TRANSLATION LAYER: GOOD Format -> CSV Format ---
    NAME_MAPPING = {
        "KamisatoAyaka": "Ayaka",
        "KamisatoAyato": "Ayato",
        "KujouSara": "Sara",
        "KukiShinobu": "Kuki",
        "RaidenShogun": "Raiden",
        "SangonomiyaKokomi": "Kokomi",
        "ShikanoinHeizou": "Heizou",
        "YumemizukiMizuki": "Mizuki",
        "KaedeharaKazuha": "Kazuha",
        "YaeMiko": "Yaemiko",
        "AratakiItto": "Itto",
        "LanYan": "Lanyan",
        "YunJin": "Yunjin",
        "Traveler": "MC"
    }
    
    # 1. Parse CSV Logic
    try:
        with open(csv_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                char_data = row['Character Name'].split('_')
                char_name = char_data[0].strip()
                role = char_data[1].strip() if len(char_data) > 1 else "Standard"
                useful_stats = [stat.strip() for stat in row['Substat Priority'].split(',')]
                builds[char_name][role] = useful_stats
    except Exception as e:
        return [f"Error reading CSV: {e}"]

    # 2. Parse JSON Data
    try:
        with open(json_file, mode='r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return [f"Error reading JSON: {e}"]
        
    equipped_artifacts = defaultdict(list)
    for artifact in data.get('artifacts', []):
        location = artifact.get('location', '')
        if location:
            equipped_artifacts[location].append(artifact)

    # --- INITIALIZE CATEGORY BUCKETS ---
    categories = {
        "🟢 STOP FARMING (25+ Rolls - Diminishing Returns Hit)": [],
        "🟡 OPTIMAL (20-24 Rolls - Comfortable Abyss Clear)": [],
        "🔴 INCOMPLETE (<20 Rolls - Keep Grinding)": [],
        "⚪ UNMAPPED (Skipped or Missing CSV Data)": []
    }

    # 3. Evaluate Characters
    for raw_char, artifacts in equipped_artifacts.items():
        normalized_char = NAME_MAPPING.get(raw_char, raw_char)
        
        matched_csv_keys = []
        for csv_key in builds.keys():
            if csv_key == normalized_char or (normalized_char == "MC" and csv_key.startswith("MC")):
                matched_csv_keys.append(csv_key)

        # Handle unmapped characters
        if not matched_csv_keys:
            categories["⚪ UNMAPPED (Skipped or Missing CSV Data)"].append(
                f"  [!] {raw_char.upper()} ({len(artifacts)}/5 equipped) - No build logic found."
            )
            continue
        
        # Evaluate mapped characters and sort into buckets
        for matched_key in matched_csv_keys:
            for role, useful_stats in builds[matched_key].items():
                total_useful_rolls = 0
                total_rv_percentage = 0.0
                
                for artifact in artifacts:
                    for substat in artifact.get('substats', []):
                        key = substat.get('key')
                        val = substat.get('value', 0)
                        
                        if key in useful_stats and val > 0 and key in AVG_ROLLS:
                            roll_count = round(val / AVG_ROLLS[key])
                            total_useful_rolls += roll_count
                            rv = (val / MAX_ROLLS[key]) * 100
                            total_rv_percentage += rv
                
                display_role = f"{matched_key} - {role}" if normalized_char == "MC" else role
                
                # Format the result block
                result_block = (
                    f"  Character: {raw_char.upper()} ({len(artifacts)}/5 equipped)\n"
                    f"  Role: {display_role}\n"
                    f"  ↳ Substats Counted: {', '.join(useful_stats)}\n"
                    f"  ↳ Total Useful Rolls: {total_useful_rolls}\n"
                    f"  ↳ Total Roll Value:   {total_rv_percentage/100:.2f}x (Equiv. to {total_rv_percentage/100:.1f} Max Rolls)\n"
                    f"  {'-' * 45}"
                )

                # Sort into the correct bucket
                if total_useful_rolls >= 25:
                    categories["🟢 STOP FARMING (25+ Rolls - Diminishing Returns Hit)"].append(result_block)
                elif total_useful_rolls >= 20:
                    categories["🟡 OPTIMAL (20-24 Rolls - Comfortable Abyss Clear)"].append(result_block)
                else:
                    categories["🔴 INCOMPLETE (<20 Rolls - Keep Grinding)"].append(result_block)

    # 4. Construct Final Output Logs
    logs.append("="*65)
    logs.append(" GENSHIN STRATEGIC BUILD EVALUATOR - PRIORITY TRIAGE")
    logs.append("="*65 + "\n")

    # Print each category block
    for cat_name, items in categories.items():
        logs.append(cat_name)
        logs.append("=" * len(cat_name))
        
        if not items:
            logs.append("  None\n")
        else:
            for item in items:
                logs.append(item)
            logs.append("") # Extra space after category

    return logs

# --- MAIN APP CLASS ---

class UnifiedArtifactTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Genshin Artifact Manager")
        self.geometry("950x750")
        
        self.input_file_var = tk.StringVar()
        self.json_file_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.style_var = tk.StringVar(value="verbose") # Added for style selection
        
        self.sets_data = {}
        self._load_sets_data() # Load sets for Manual Builder
        self._load_settings()
        self._create_widgets()

    def _load_sets_data(self):
        try:
            self.sets_data, _ = conversion_utils.parse_sets_enum(SETS_ENUM_FILE)
        except Exception:
            self.sets_data = {}

    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # TAB 1: Extract
        extract_frame = ttk.Frame(notebook, padding="15")
        notebook.add(extract_frame, text="1. Database Creator")
        self._build_extract_tab(extract_frame)

        # TAB 2: Manual Builder (Restored)
        manual_frame = ttk.Frame(notebook, padding="15")
        notebook.add(manual_frame, text="2. Manual Builder")
        self._build_manual_tab(manual_frame)

        # TAB 3: Generate JS
        gen_frame = ttk.Frame(notebook, padding="15")
        notebook.add(gen_frame, text="3. Filter Generator")
        self._build_generator_tab(gen_frame)

        # TAB 4: Inventory Scanner
        scan_frame = ttk.Frame(notebook, padding="15")
        notebook.add(scan_frame, text="4. Inventory Scanner")
        self._build_scanner_tab(scan_frame)
        
        # TAB 5: Sanity Checker
        check_frame = ttk.Frame(notebook, padding="15")
        notebook.add(check_frame, text="5. Sanity Checker")
        self._build_sanity_tab(check_frame)
        
        # TAB 6: CSV Comparator
        compare_frame = ttk.Frame(notebook, padding="15")
        notebook.add(compare_frame, text="6. CSV Compare")
        self._build_compare_tab(compare_frame)
        
        # TAB 7: Roll Value Evaluator
        eval_frame = ttk.Frame(notebook, padding="15")
        notebook.add(eval_frame, text="7. Roll Evaluator")
        self._build_evaluator_tab(eval_frame)

        # Status Bar
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, side=tk.BOTTOM)

    # --- TABS ---

    def _build_extract_tab(self, parent):
        ttk.Label(parent, text="Extract data from Simpact/GCsim Text Files", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # File Selection
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=10)
        ttk.Entry(frame, textvariable=self.input_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame, text="Browse", command=lambda: self._browse(self.input_file_var, [("Text", "*.txt")])).pack(side=tk.RIGHT)
        
        # Style Selection (Restored)
        style_frame = ttk.Frame(parent)
        style_frame.pack(fill=tk.X, pady=5)
        ttk.Label(style_frame, text="CSV Output Style:").pack(side=tk.LEFT)
        ttk.Radiobutton(style_frame, text="Verbose (Includes %)", variable=self.style_var, value="verbose").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(style_frame, text="Minimal (Clean names)", variable=self.style_var, value="minimal").pack(side=tk.LEFT)

        ttk.Button(parent, text="Extract to CSV", command=self._run_extract).pack(pady=10)

    def _build_manual_tab(self, parent):
        # Character Name
        ttk.Label(parent, text="Character Name:").pack(anchor=tk.W)
        self.manual_char_entry = ttk.Entry(parent)
        self.manual_char_entry.pack(fill=tk.X, pady=(0, 10))

        # Artifact Set
        ttk.Label(parent, text="Artifact Set:").pack(anchor=tk.W)
        self.manual_set_combo = ttk.Combobox(parent, values=sorted(self.sets_data.keys()), state="readonly")
        self.manual_set_combo.pack(fill=tk.X, pady=(0, 10))

        # Main Stats
        ms_frame = ttk.LabelFrame(parent, text="Main Stats", padding="10")
        ms_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Helper to create checkboxes
        def create_cb_group(p, title, options):
            f = ttk.LabelFrame(p, text=title)
            f.pack(fill=tk.X, pady=5)
            vars_d = {}
            for i, opt in enumerate(options):
                v = tk.BooleanVar()
                vars_d[opt] = v
                ttk.Checkbutton(f, text=opt, variable=v).grid(row=i//4, column=i%4, sticky=tk.W, padx=5)
            return vars_d

        self.sands_vars = create_cb_group(ms_frame, "Sands", stat_utils.POSSIBLE_MAINS["Sands"])
        self.goblet_vars = create_cb_group(ms_frame, "Goblet", stat_utils.POSSIBLE_MAINS["Goblet"])
        self.circlet_vars = create_cb_group(ms_frame, "Circlet", stat_utils.POSSIBLE_MAINS["Circlet"])

        # Substats
        sub_frame = ttk.LabelFrame(parent, text="Desired Substats", padding="10")
        sub_frame.pack(fill=tk.X, pady=(0, 10))
        substats_ui = ['ATK%', 'HP%', 'DEF%', 'Energy Recharge', 'Elemental Mastery', 'Crit Rate', 'Crit DMG']
        self.substat_vars = {}
        for i, stat in enumerate(substats_ui):
            var = tk.BooleanVar()
            self.substat_vars[stat] = var
            ttk.Checkbutton(sub_frame, text=stat, variable=var).grid(row=i//3, column=i%3, sticky=tk.W, padx=5)

        ttk.Button(parent, text="Add Build to CSV", command=self._add_build_to_csv).pack(fill=tk.X, pady=10)

    def _build_generator_tab(self, parent):
        ttk.Label(parent, text="Convert CSV to 'Generated Master Filter.js'", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Button(parent, text="Generate JS", command=self._run_gen).pack(pady=20)

    def _build_scanner_tab(self, parent):
        ttk.Label(parent, text="Scan GOOD.json for builds", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Entry(frame, textvariable=self.json_file_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(frame, text="Browse JSON", command=lambda: self._browse(self.json_file_var, [("JSON", "*.json")])).pack(side=tk.RIGHT)

        ctrl_frame = ttk.Frame(parent)
        ctrl_frame.pack(fill=tk.X, pady=10)
        self.strict_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text="Strict Mode (On-Set Pieces ONLY)", variable=self.strict_var).pack(side=tk.LEFT)
        ttk.Button(ctrl_frame, text="Run Scan", command=self._run_scan).pack(side=tk.RIGHT)

        self.scan_log = scrolledtext.ScrolledText(parent, height=20)
        self.scan_log.pack(fill=tk.BOTH, expand=True)

    def _build_sanity_tab(self, parent):
        ttk.Label(parent, text="Verify JSON locks against CSV Rules", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Button(parent, text="Run Integrity Check", command=self._run_sanity).pack(pady=10)
        
        self.sanity_log = scrolledtext.ScrolledText(parent, height=20)
        self.sanity_log.pack(fill=tk.BOTH, expand=True)

    def _build_compare_tab(self, parent):
        ttk.Label(parent, text="Compare two CSV versions to see Meta shifts", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        # File Selection
        fs_frame = ttk.Frame(parent)
        fs_frame.pack(fill=tk.X, pady=10)

        self.csv_old_var = tk.StringVar()
        ttk.Label(fs_frame, text="Old CSV:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(fs_frame, textvariable=self.csv_old_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(fs_frame, text="Browse", command=lambda: self._browse(self.csv_old_var, [("CSV", "*.csv")])).grid(row=0, column=2)

        self.csv_new_var = tk.StringVar()
        ttk.Label(fs_frame, text="New CSV:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(fs_frame, textvariable=self.csv_new_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(fs_frame, text="Browse", command=lambda: self._browse(self.csv_new_var, [("CSV", "*.csv")])).grid(row=1, column=2, pady=5)

        # Options
        opt_frame = ttk.Frame(parent)
        opt_frame.pack(fill=tk.X, pady=5)
        self.ignore_rank_var = tk.BooleanVar(value=True) # Default to True to reduce noise!
        ttk.Checkbutton(opt_frame, text="Ignore Priority Swaps (e.g. 'Atk, EM' vs 'EM, Atk')", variable=self.ignore_rank_var).pack(side=tk.LEFT)

        # Action
        ttk.Button(parent, text="Compare Files", command=self._run_compare).pack(pady=10)

        # Log
        self.compare_log = scrolledtext.ScrolledText(parent, height=20)
        self.compare_log.pack(fill=tk.BOTH, expand=True)
        
    def _build_evaluator_tab(self, parent):
        ttk.Label(parent, text="Evaluate equipped artifacts against Diminishing Returns thresholds.", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # We reuse self.json_file_var so you don't have to browse twice!
        info_label = ttk.Label(parent, text="Uses the GOOD.json selected in Tab 4 and matches it against your CSV priorities.")
        info_label.pack(anchor=tk.W, pady=(5, 10))

        ttk.Button(parent, text="Calculate Roll Values", command=self._run_evaluator).pack(pady=5)
        
        self.eval_log = scrolledtext.ScrolledText(parent, height=20)
        self.eval_log.pack(fill=tk.BOTH, expand=True)
        
    # --- ACTIONS ---

    def _run_extract(self):
        input_file = self.input_file_var.get()
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Error", "Invalid input file.")
            return
        
        self.status_var.set("Extracting...")
        self.update()
        
        try:
            teams_data = parse_teams_data(input_file)
            if not teams_data:
                messagebox.showwarning("Warning", "No teams found.")
                return
            
            # Whitelist check
            allowed_characters = None
            if os.path.exists(WHITELIST_FILE):
                with open(WHITELIST_FILE, 'r') as f:
                    allowed_characters = {line.strip().lower() for line in f if line.strip()}
                if allowed_characters and ('aether' in allowed_characters or 'lumine' in allowed_characters):
                     for e in ['anemo', 'geo', 'electro', 'dendro', 'hydro', 'pyro']:
                        allowed_characters.add(f'aether{e}'); allowed_characters.add(f'lumine{e}')

            all_char_data = analyze_all_character_builds(teams_data, allowed_characters)
            headers, rows = generate_spreadsheet_data(all_char_data, self.style_var.get())
            
            with open(DEFAULT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            
            self._save_settings()
            self.status_var.set(f"Extracted to {DEFAULT_CSV_FILE}")
            messagebox.showinfo("Success", "Extraction Complete.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error during extraction.")

    def _add_build_to_csv(self):
        char_name = self.manual_char_entry.get().strip()
        set_name = self.manual_set_combo.get()
        
        if not char_name or not set_name:
            messagebox.showerror("Error", "Character Name and Artifact Set are required.")
            return

        # Collect Main Stats
        sands = [k for k, v in self.sands_vars.items() if v.get()]
        goblets = [k for k, v in self.goblet_vars.items() if v.get()]
        circlets = [k for k, v in self.circlet_vars.items() if v.get()]
        
        # Mapping UI names to CSV internal names (matching extraction logic)
        ui_to_csv_map = {
            'ATK%': 'ATK%', 'HP%': 'HP%', 'DEF%': 'DEF%', 
            'Energy Recharge': 'ER%', 'Elemental Mastery': 'EM', 
            'Crit Rate': 'CRIT Rate%', 'Crit DMG': 'CRIT DMG%'
        }
        substats = [ui_to_csv_map[k] for k, v in self.substat_vars.items() if v.get()]

        if not substats:
            messagebox.showerror("Error", "Select at least one substat.")
            return

        file_exists = os.path.exists(DEFAULT_CSV_FILE)
        headers = ['Character Name', 'Top Artifact Sets', 'Common Sands', 'Common Goblet', 'Common Circlet', 'Substat Priority']
        
        try:
            with open(DEFAULT_CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists: writer.writeheader()
                
                writer.writerow({
                    'Character Name': char_name,
                    'Top Artifact Sets': set_name,
                    'Common Sands': ", ".join(sands),
                    'Common Goblet': ", ".join(goblets),
                    'Common Circlet': ", ".join(circlets),
                    'Substat Priority': ", ".join(substats)
                })
            
            self.status_var.set(f"Added {char_name} to CSV.")
            messagebox.showinfo("Success", f"Added build for {char_name}")
            
            # Reset UI
            self.manual_char_entry.delete(0, tk.END)
            self.manual_set_combo.set('')
            for d in [self.sands_vars, self.goblet_vars, self.circlet_vars, self.substat_vars]:
                for v in d.values(): v.set(False)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _run_gen(self):
        try:
            c1, c2 = conversion_utils.generate_js_from_csv(DEFAULT_CSV_FILE, DEFAULT_JS_FILE, SETS_ENUM_FILE)
            messagebox.showinfo("Success", f"Generated JS with {c1} Sets and {c2} Builds.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _run_scan(self):
        json_path = self.json_file_var.get()
        if not os.path.exists(json_path): return
        
        self.scan_log.delete(1.0, tk.END)
        self.status_var.set("Scanning...")
        self.update()

        logs, results = Inventory_Scanner.scan_inventory(
            DEFAULT_CSV_FILE, json_path, strict_mode=self.strict_var.get()
        )

        for l in logs: self.scan_log.insert(tk.END, l + "\n")
        self.scan_log.insert(tk.END, "\n" + "="*40 + "\n")
        
        for r in results:
            self.scan_log.insert(tk.END, f"CHAR: {r['name']} ({r['ready']})\n")
            for art in r['artifacts']:
                self.scan_log.insert(tk.END, f"  {art}\n")
            self.scan_log.insert(tk.END, "\n")
        
        self.status_var.set("Done.")

    def _run_sanity(self):
        json_path = self.json_file_var.get()
        if not os.path.exists(json_path): return
        
        self.sanity_log.delete(1.0, tk.END)
        self.status_var.set("Verifying...")
        self.update()

        logs = Sanity_Checker.run_check(DEFAULT_CSV_FILE, json_path)
        for l in logs: self.sanity_log.insert(tk.END, l + "\n")
        
        self.status_var.set("Done.")

    def _run_compare(self):
        f1 = self.csv_old_var.get()
        f2 = self.csv_new_var.get()

        if not os.path.exists(f1) or not os.path.exists(f2):
            messagebox.showerror("Error", "Please select two valid CSV files.")
            return

        self.compare_log.delete(1.0, tk.END)
        self.status_var.set("Comparing...")
        self.update()

        # Pass the checkbox value
        results = csv_comparator.compare_csvs(f1, f2, ignore_rank_swaps=self.ignore_rank_var.get())
        
        for line in results:
            self.compare_log.insert(tk.END, line + "\n")
            
            # Coloring
            if line.startswith("MODIFIED"):
                self.compare_log.tag_add("mod", "end-2l", "end-1c")
                self.compare_log.tag_config("mod", foreground="blue") # Changed to Blue
            elif "[+]" in line:
                self.compare_log.tag_add("add", "end-2l", "end-1c")
                self.compare_log.tag_config("add", foreground="green")
            elif "[-]" in line:
                self.compare_log.tag_add("rem", "end-2l", "end-1c")
                self.compare_log.tag_config("rem", foreground="red")

        self.status_var.set("Comparison Done.")
        
    def _run_evaluator(self):
        json_path = self.json_file_var.get()
        if not os.path.exists(json_path):
            messagebox.showerror("Error", "Please select a valid GOOD.json file in Tab 4 first.")
            return
            
        csv_path = DEFAULT_CSV_FILE
        if not os.path.exists(csv_path):
            messagebox.showerror("Error", f"Could not find {csv_path}. Please extract data first.")
            return
            
        self.eval_log.delete(1.0, tk.END)
        self.status_var.set("Evaluating Roll Values...")
        self.update()

        # Run the calculation
        logs = evaluate_roll_value(csv_path, json_path)
        
        for line in logs:
            self.eval_log.insert(tk.END, line + "\n")
            
        self.status_var.set("Evaluation Complete.")

    # --- UTILS ---
    def _browse(self, var, file_types):
        f = filedialog.askopenfilename(filetypes=file_types)
        if f: 
            var.set(f)
            self._save_settings()

    def _load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.input_file_var.set(data.get("input", ""))
                    self.json_file_var.set(data.get("json", ""))
                    self.style_var.set(data.get("last_style", "verbose"))
            except: pass

    def _save_settings(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({
                    "input": self.input_file_var.get(),
                    "json": self.json_file_var.get(),
                    "last_style": self.style_var.get()
                }, f)
        except: pass

if __name__ == "__main__":
    app = UnifiedArtifactTool()
    app.mainloop()