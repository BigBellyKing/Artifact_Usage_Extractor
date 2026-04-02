import json
import csv
import re
from collections import defaultdict

# --- CONFIG ---
CONFIG = {
    "DESIRED_SUBSTAT_COUNT_4_LINE": 3,
    "DESIRED_SUBSTAT_COUNT_3_LINE": 3,
}

# --- SORTING ORDER ---
SLOT_ORDER = {
    'flower': 0,
    'plume': 1,
    'sands': 2,
    'goblet': 3,
    'circlet': 4
}

# --- HELPERS ---
def normalize_set_key(text):
    """
    For Set Names ONLY.
    Aggressively removes spaces/symbols and lowercases to match 'noblesseoblige'.
    """
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def clean_csv_value(text):
    """
    Removes the verbose percentage data from CSV values.
    Example: "ATK% (50.5%)" -> "ATK%"
    """
    if not text: return ""
    text = re.sub(r'\s*\(.*?\)', '', text) # Remove (...)
    return text.strip()

def clean_split(text):
    if not text: return []
    return [clean_csv_value(s) for s in text.split(',') if s.strip()]

# --- STAT MAPPING ---
STAT_MAP = {
    # Readable Names
    'ATK%': 'atk_', 
    'HP%': 'hp_', 
    'DEF%': 'def_', 
    'ER%': 'enerRech_', 'Energy Recharge': 'enerRech_',
    'EM': 'eleMas', 'Elemental Mastery': 'eleMas',
    'CRIT Rate%': 'critRate_', 'Crit Rate': 'critRate_',
    'CRIT DMG%': 'critDMG_', 'Crit DMG': 'critDMG_',
    'Physical DMG': 'physical_dmg_', 
    'Anemo DMG': 'anemo_dmg_', 
    'Geo DMG': 'geo_dmg_', 
    'Electro DMG': 'electro_dmg_', 
    'Hydro DMG': 'hydro_dmg_', 
    'Pyro DMG': 'pyro_dmg_', 
    'Cryo DMG': 'cryo_dmg_', 
    'Dendro DMG': 'dendro_dmg_',

    # Internal Keys
    'atk_': 'atk_', 'hp_': 'hp_', 'def_': 'def_',
    'enerRech_': 'enerRech_', 'enerrech_': 'enerRech_',
    'eleMas': 'eleMas', 'elemas': 'eleMas',
    'critRate_': 'critRate_', 'critrate_': 'critRate_',
    'critDMG_': 'critDMG_', 'critdmg_': 'critDMG_',
    'heal_': 'heal_'
}

def map_stat(s):
    """Maps a CSV string to the strict JSON key."""
    if s in STAT_MAP: return STAT_MAP[s]
    s_clean = s.strip()
    if s_clean in STAT_MAP: return STAT_MAP[s_clean]
    if s_clean.endswith('_') or s_clean in ['eleMas', 'heal_']: return s_clean
    return s_clean

# --- DYNAMIC LOGIC LOADER ---
def load_logic_from_csv(csv_path):
    fp_builds = {}          # Flower/Plume (Strict Set)
    gsc_builds = []         # General Sands/Goblet/Circlet (Loose Set)
    strict_builds = defaultdict(list) # NEW: Fully Strict S/G/C for specific sets (like Instructor)

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                char = row['Character Name']
                sets = [normalize_set_key(s) for s in clean_split(row['Top Artifact Sets'])]
                
                sands = [map_stat(s) for s in clean_split(row['Common Sands'])]
                gob = [map_stat(s) for s in clean_split(row['Common Goblet'])]
                circ = [map_stat(s) for s in clean_split(row['Common Circlet'])]
                subs = [map_stat(s) for s in clean_split(row['Substat Priority'])]

                if not subs: continue

                build_obj = {'sands': sands, 'gob': gob, 'circ': circ, 'subs': subs, 'chars': [char]}

                # 1. Populate Strict Lists (e.g. Instructor) and Flower/Plume
                for s_key in sets:
                    # Flower/Plume Logic (Always strictly keyed by set)
                    if s_key not in fp_builds: fp_builds[s_key] = []
                    existing_fp = next((b for b in fp_builds[s_key] if b['subs'] == subs), None)
                    if existing_fp: existing_fp['chars'].append(char)
                    else: fp_builds[s_key].append({'subs': subs, 'chars': [char]})

                    # Special Strict S/G/C Logic for Instructor
                    if s_key == 'instructor':
                        # Check if this exact build exists in strict list to avoid dupes
                        existing_strict = next((b for b in strict_builds[s_key] 
                                                if b['sands']==sands and b['gob']==gob and b['circ']==circ and b['subs']==subs), None)
                        if existing_strict: existing_strict['chars'].append(char)
                        else: strict_builds[s_key].append({'sands':sands, 'gob':gob, 'circ':circ, 'subs':subs, 'chars':[char]})

                # 2. Populate General Logic (Standard 5-stars logic)
                # We add everyone to GSC to allow off-pieces, EXCEPT we don't rely on this list for Instructor artifacts later.
                existing_gsc = next((b for b in gsc_builds if b['sands']==sands and b['gob']==gob and b['circ']==circ and b['subs']==subs), None)
                if existing_gsc: existing_gsc['chars'].append(char)
                else: gsc_builds.append({'sands':sands, 'gob':gob, 'circ':circ, 'subs':subs, 'chars':[char]})
        
        return fp_builds, gsc_builds, strict_builds

    except Exception as e:
        return None, None, None

# --- CORE CHECKER ---
def check_artifact(art, fp_builds, gsc_builds, strict_builds):
    substat_keys = set(s['key'] for s in art.get('substats', []))
    set_key = normalize_set_key(art['setKey'])
    rarity = art.get('rarity', 0)
    slot = art['slotKey']
    main = art['mainStatKey']
    line_count = len(substat_keys)

    # --- INSTRUCTOR LOGIC (Strict) ---
    if set_key == 'instructor':
        # 1. Rarity: Allow 4-star and 5-star (though Instructor is 4-star max)
        if rarity < 4: return False, None

        # 2. Custom Match Threshold for Instructor
        # 2 lines -> 1 match
        # 3 lines -> 2 matches (also applies to 4 lines)
        threshold = 1 if line_count == 2 else 2

        # 3. Strict Build Lookup
        # We DO NOT use gsc_builds (generic) for Instructor. We only use strict_builds.
        
        # 3a. Flower/Plume (Use fp_builds as it is already strict by set)
        if slot in ['flower', 'plume']:
            builds = fp_builds.get(set_key, [])
            for build in builds:
                match_count = sum(1 for s in substat_keys if s in build['subs'])
                if match_count >= threshold:
                    return True, f"Instructor Set Match ({', '.join(build['chars'])})"
        
        # 3b. Sands/Goblet/Circlet (Use strict_builds only)
        else:
            builds = strict_builds.get(set_key, [])
            for build in builds:
                valid_main = False
                if slot == 'sands' and main in build['sands']: valid_main = True
                elif slot == 'goblet' and main in build['gob']: valid_main = True
                elif slot == 'circlet' and main in build['circ']: valid_main = True
                
                if valid_main:
                    match_count = sum(1 for s in substat_keys if s in build['subs'])
                    if match_count >= threshold:
                        return True, f"Instructor Strict Match ({', '.join(build['chars'])})"
        
        return False, None

    # --- STANDARD LOGIC (Everything else) ---
    else:
        # 1. Double Crit Global Check (Optional, but usually good for non-support)
        if 'critRate_' in substat_keys and 'critDMG_' in substat_keys:
            return True, "Universal (Double Crit)"

        # 2. Rarity: Must be 5-star
        if rarity < 5: return False, None

        # 3. Standard Threshold
        threshold = CONFIG["DESIRED_SUBSTAT_COUNT_4_LINE"] if line_count == 4 else CONFIG["DESIRED_SUBSTAT_COUNT_3_LINE"]

        # 4a. Flower/Plume (Strict Set Match)
        if slot in ['flower', 'plume']:
            builds = fp_builds.get(set_key)
            if builds:
                for build in builds:
                    match_count = sum(1 for s in substat_keys if s in build['subs'])
                    if match_count >= threshold:
                        return True, f"Set Match ({', '.join(build['chars'])})"
        
        # 4b. Others (General Match - allows off-pieces)
        else:
            for build in gsc_builds:
                valid_main = False
                if slot == 'sands' and main in build['sands']: valid_main = True
                elif slot == 'goblet' and main in build['gob']: valid_main = True
                elif slot == 'circlet' and main in build['circ']: valid_main = True
                
                if valid_main:
                    match_count = sum(1 for s in substat_keys if s in build['subs'])
                    if match_count >= threshold:
                        return True, f"General Match ({', '.join(build['chars'])})"

    return False, None

# --- REPORT GENERATOR ---
def run_check(csv_path, json_path):
    fp_data, gsc_data, strict_data = load_logic_from_csv(csv_path)
    if fp_data is None: return ["Error: Could not read CSV file."]

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            artifacts = data.get('artifacts', [])
    except Exception as e:
        return [f"Error: Could not read JSON file: {e}"]

    total = len(artifacts)
    matches = 0
    false_positives = 0
    false_negatives = 0
    mismatches_by_set = defaultdict(list)

    logs = []
    logs.append(f"--- Loaded Rules from CSV & Scanning {total} Artifacts ---")

    for i, art in enumerate(artifacts):
        should_lock, reason = check_artifact(art, fp_data, gsc_data, strict_data)
        is_locked = art.get('lock', False)

        if should_lock == is_locked:
            matches += 1
        else:
            set_key = art.get('setKey', 'UnknownSet')
            
            if should_lock:
                cat = "FALSE POSITIVE"
                desc = f"Logic Locks for: {reason}"
                false_positives += 1
            else:
                cat = "FALSE NEGATIVE"
                desc = "Logic Unlocks, JSON Locks"
                false_negatives += 1
            
            mismatches_by_set[set_key].append({
                "index": i,
                "category": cat,
                "description": desc,
                "slot": art['slotKey'],
                "main": art['mainStatKey'],
                "subs": [s['key'] for s in art['substats']]
            })

    if not mismatches_by_set:
        logs.append("\nPERFECT MATCH! No discrepancies found.")
    else:
        for set_key in sorted(mismatches_by_set.keys()):
            logs.append("\n" + "="*60)
            logs.append(f"SET: {set_key}")
            logs.append("="*60)
            
            items = mismatches_by_set[set_key]
            fp_items = [x for x in items if x['category'] == "FALSE POSITIVE"]
            fn_items = [x for x in items if x['category'] == "FALSE NEGATIVE"]

            def sort_by_slot(x):
                return SLOT_ORDER.get(x['slot'], 99)

            fp_items.sort(key=sort_by_slot)
            fn_items.sort(key=sort_by_slot)

            if fp_items:
                logs.append(f"\n   >>> FALSE POSITIVES (Script says LOCK, JSON says Unlock) <<<")
                for error in fp_items:
                    logs.append(f"   (Index {error['index']}) {error['description']}")
                    logs.append(f"      Slot: {error['slot']:<10} Main: {error['main']}")
                    logs.append(f"      Subs: {error['subs']}")
                    logs.append("   " + "-" * 30)

            if fn_items:
                logs.append(f"\n   >>> FALSE NEGATIVES (Script says UNLOCK, JSON says Lock) <<<")
                for error in fn_items:
                    logs.append(f"   (Index {error['index']}) {error['description']}")
                    logs.append(f"      Slot: {error['slot']:<10} Main: {error['main']}")
                    logs.append(f"      Subs: {error['subs']}")
                    logs.append("   " + "-" * 30)

    logs.append("\n\n" + "#"*30)
    logs.append("       SUMMARY STATISTICS       ")
    logs.append("#"*30)
    logs.append(f"Total Artifacts: {total}")
    logs.append(f"Matches:         {matches}")
    logs.append(f"Accuracy:        {(matches/total)*100:.2f}%")
    logs.append(f"Mismatches:      {total - matches}")
    logs.append(f"  - False Positives (Suggests Locking): {false_positives}")
    logs.append(f"  - False Negatives (Suggests Unlocking): {false_negatives}")

    return logs