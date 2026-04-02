import json
import csv
import re
from collections import defaultdict, Counter

# --- CONFIGURATION ---
MIN_SUBS = 3 

# --- HELPERS ---
def normalize_set_key(text):
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def clean_csv_value(text):
    if not text: return ""
    text = re.sub(r'\s*\(.*?\)', '', text)
    return text.strip()

def clean_split(text):
    if not text: return []
    return [clean_csv_value(s) for s in text.split(',') if s.strip()]

def extract_base_character_name(full_name):
    """
    Extract base character name from CharacterName_Role format.
    Example: 'Heizou_DPS' -> 'Heizou'
    """
    if '_' in full_name:
        return full_name.split('_')[0]
    return full_name

STAT_MAP = {
    'ATK%': 'atk_', 'HP%': 'hp_', 'DEF%': 'def_', 
    'ER%': 'enerRech_', 'Energy Recharge': 'enerRech_',
    'EM': 'eleMas', 'Elemental Mastery': 'eleMas',
    'CRIT Rate%': 'critRate_', 'Crit Rate': 'critRate_',
    'CRIT DMG%': 'critDMG_', 'Crit DMG': 'critDMG_',
    'Physical DMG': 'physical_dmg_', 'Anemo DMG': 'anemo_dmg_', 
    'Geo DMG': 'geo_dmg_', 'Electro DMG': 'electro_dmg_', 
    'Hydro DMG': 'hydro_dmg_', 'Pyro DMG': 'pyro_dmg_', 
    'Cryo DMG': 'cryo_dmg_', 'Dendro DMG': 'dendro_dmg_',
    'Heal': 'heal_', 'Healing Bonus': 'heal_'
}

def map_stat(s):
    if s in STAT_MAP: return STAT_MAP[s]
    s_clean = s.strip()
    if s_clean in STAT_MAP: return STAT_MAP[s_clean]
    if s_clean.endswith('_') or s_clean == 'eleMas': return s_clean
    return normalize_set_key(s_clean)

# --- MAIN LOGIC ---
def scan_inventory(csv_file, json_file, strict_mode=False):
    logs = []
    
    # 1. Load CSV Requirements
    chars = {}
    csv_base_char_names_normalized = set()  # Store normalized base names
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Full name includes role: e.g., "Heizou_DPS"
                full_name = row['Character Name'].strip()
                if not full_name: continue
                
                # Extract base character name for comparison
                base_name = extract_base_character_name(full_name)
                csv_base_char_names_normalized.add(normalize_set_key(base_name))

                raw_sets = clean_split(row['Top Artifact Sets'])
                valid_sets = [normalize_set_key(s) for s in raw_sets]
                
                desired_raw = clean_split(row['Substat Priority'])
                desired_subs = [map_stat(s) for s in desired_raw]
                
                # Store with FULL name as key to support multiple builds per character
                chars[full_name] = {
                    "base_name": base_name,  # Store base name for reference
                    "valid_sets": valid_sets,
                    "raw_sets": raw_sets, 
                    "sands_main": [map_stat(s) for s in clean_split(row['Common Sands'])],
                    "goblet_main": [map_stat(s) for s in clean_split(row['Common Goblet'])],
                    "circlet_main": [map_stat(s) for s in clean_split(row['Common Circlet'])],
                    "desired_subs": desired_subs,
                    "display_subs": desired_raw
                }
    except Exception as e:
        return [f"Error reading CSV: {e}"], []

    # 2. Load JSON Inventory
    inventory = []
    json_equipped_chars = set()
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            inventory = data.get('artifacts', [])
            for art in inventory:
                if 'location' in art and art['location']:
                    json_equipped_chars.add(art['location'])
    except Exception as e:
        return [f"Error reading JSON: {e}"], []

    mode_str = "STRICT (On-Set Only)" if strict_mode else "LOOSE (Off-Piece Allowed)"
    logs.append(f"Scanning {len(inventory)} artifacts in {mode_str} mode...")

    # 3. Scan Artifacts
    char_builds = defaultdict(lambda: defaultdict(list))

    for art in inventory:
        slot = art.get('slotKey')
        main = art.get('mainStatKey')
        set_key = normalize_set_key(art.get('setKey'))
        art_subs = [s['key'] for s in art.get('substats', [])]
        level = art.get('level', 0)

        # Now iterate through ALL character builds (including multiple builds per character)
        for char_name, reqs in chars.items():
            matches = [s for s in reqs['desired_subs'] if s in art_subs]
            score = len(matches)
            if score < MIN_SUBS: continue

            art_entry = {
                'level': level, 
                'set': art.get('setKey'), 
                'main': main, 
                'score': score
            }

            is_set_match = set_key in reqs['valid_sets']

            if strict_mode:
                if not is_set_match: continue
                if slot in ['flower', 'plume']:
                    char_builds[char_name][slot].append(art_entry)
                elif slot == 'sands' and main in reqs['sands_main']:
                    char_builds[char_name][slot].append(art_entry)
                elif slot == 'goblet' and main in reqs['goblet_main']:
                    char_builds[char_name][slot].append(art_entry)
                elif slot == 'circlet' and main in reqs['circlet_main']:
                    char_builds[char_name][slot].append(art_entry)
            else:
                # LOOSE Mode
                if slot in ['flower', 'plume']:
                    if is_set_match: char_builds[char_name][slot].append(art_entry)
                elif slot == 'sands':
                    if main in reqs['sands_main']: char_builds[char_name][slot].append(art_entry)
                elif slot == 'goblet':
                    if main in reqs['goblet_main']: char_builds[char_name][slot].append(art_entry)
                elif slot == 'circlet':
                    if main in reqs['circlet_main']: char_builds[char_name][slot].append(art_entry)

    # ==========================================
    # 4. GENERATE SUMMARIES
    # ==========================================

    # --- SUMMARY A: INCOMPLETE CHARACTERS ---
    incomplete_chars = []
    
    for char_name, reqs in chars.items():
        filled_slots = char_builds[char_name].keys()
        filled_count = len(filled_slots)
        
        # Identify Incomplete Characters
        if filled_count < 5:
            # Calculate exactly which slots are missing for THIS character
            missing = []
            for slot in ['flower', 'plume', 'sands', 'goblet', 'circlet']:
                if slot not in filled_slots:
                    missing.append(slot)
            
            incomplete_chars.append({
                'name': char_name,
                'filled': filled_count,
                'missing_slots': missing,
                'sets': reqs['raw_sets']
            })
    
    # Sort by number of filled slots (descending) - closest to complete first
    incomplete_chars.sort(key=lambda x: x['filled'], reverse=True)
    
    logs.append("\n" + "="*60)
    logs.append("SUMMARY: INCOMPLETE CHARACTER BUILDS")
    logs.append(f"Total Incomplete: {len(incomplete_chars)}")
    logs.append("="*60)
    
    for char_data in incomplete_chars:
        missing_str = ", ".join(char_data['missing_slots'])
        sets_str = ", ".join(char_data['sets'])
        logs.append(f"[{char_data['filled']}/5] {char_data['name']:<30}")
        logs.append(f"       Missing: {missing_str}")
        logs.append(f"       Sets: {sets_str}")
        logs.append("")

    # --- SUMMARY B: FARMING PRIORITY (REVISED) ---
    # Structure: set_name -> { 'count': int, 'missing_slots': Counter }
    set_stats = defaultdict(lambda: {'count': 0, 'missing': Counter()})
    
    for char_name, reqs in chars.items():
        filled_slots = char_builds[char_name].keys()
        
        # Identify Incomplete Characters
        if len(filled_slots) < 5:
            # Calculate exactly which slots are missing for THIS character
            missing = []
            for slot in ['flower', 'plume', 'sands', 'goblet', 'circlet']:
                if slot not in filled_slots:
                    missing.append(slot)
            
            # Add demand to all their valid sets
            for s_raw in reqs['raw_sets']:
                set_stats[s_raw]['count'] += 1
                for m_slot in missing:
                    set_stats[s_raw]['missing'][m_slot] += 1
    
    logs.append("\n" + "="*60)
    logs.append("SUMMARY B: FARMING PRIORITY")
    logs.append("Sets needed by incomplete characters & missing slots")
    logs.append("="*60)
    
    # Sort by number of characters needing the set
    sorted_sets = sorted(set_stats.items(), key=lambda x: x[1]['count'], reverse=True)

    for set_name, data in sorted_sets:
        count = data['count']
        if count == 0: continue
        
        # Format the missing slots (e.g., "sands x2, goblet x1")
        missing_str_parts = []
        # Sort slots to be consistent (Flower -> Plume -> Sands...)
        slot_order = ['flower', 'plume', 'sands', 'goblet', 'circlet']
        for s in slot_order:
            if data['missing'][s] > 0:
                missing_str_parts.append(f"{s} x{data['missing'][s]}")
        
        missing_display = ", ".join(missing_str_parts)
        logs.append(f"[{count} Chars] {set_name:<30} | Missing: {missing_display}")

    # --- SUMMARY C: MISSING CONFIG ---
    # Compare JSON equipped characters against CSV base names
    missing_config = []
    for char in json_equipped_chars:
        # Normalize the JSON character name and check against CSV base names
        if normalize_set_key(char) not in csv_base_char_names_normalized:
            missing_config.append(char)
    
    if missing_config:
        logs.append("\n" + "!"*60)
        logs.append("SUMMARY C: MISSING CONFIG WARNING")
        logs.append("!"*60)
        for m in sorted(missing_config):
            logs.append(f"  - {m}")

    # ==========================================
    # 5. GENERATE DETAILED RESULTS
    # ==========================================
    results = []
    ranked_chars = sorted(char_builds.items(), key=lambda x: len(x[1]), reverse=True)
    
    for char_name, slots in ranked_chars:
        filled_slots = len(slots.keys())
        if filled_slots < 3: continue 

        char_report = {
            "name": char_name,  # This now includes the role (e.g., "Heizou_DPS")
            "ready": f"{filled_slots}/5",
            "subs": ", ".join(chars[char_name]['display_subs']),
            "artifacts": []
        }

        for slot in ['flower', 'plume', 'sands', 'goblet', 'circlet']:
            pieces = slots.get(slot, [])
            pieces.sort(key=lambda x: (x['score'], x['level']), reverse=True)
            
            if pieces:
                top = pieces[0]
                set_display = top['set']
                if not strict_mode and slot not in ['flower', 'plume']:
                     if normalize_set_key(top['set']) not in chars[char_name]['valid_sets']:
                         set_display += " (Off-Set)"

                char_report["artifacts"].append(
                    f"[{slot.upper()}] {set_display} (Matches: {top['score']})"
                )
            else:
                 char_report["artifacts"].append(f"[{slot.upper()}] -- MISSING --")
        
        results.append(char_report)

    return logs, results