import csv
from collections import defaultdict

def load_csv_as_dict(filepath):
    """Loads CSV into a dict: {'CharName': {row_data}}"""
    data = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('Character Name', '').strip()
                if key:
                    data[key] = row
    except Exception as e:
        return None, str(e)
    return data, None

def analyze_diff(col_name, val1, val2):
    """
    Compares two CSV values. 
    Returns a list of strings describing the difference, or None if no difference.
    """
    v1_clean = val1.strip()
    v2_clean = val2.strip()

    if v1_clean == v2_clean:
        return None

    # Treat these columns as Lists of Items
    list1 = [x.strip() for x in v1_clean.split(',') if x.strip()]
    list2 = [x.strip() for x in v2_clean.split(',') if x.strip()]

    # If parsing failed or empty (e.g. empty cells), fallback to direct string compare
    if not list1 and not list2: return None
    if not list1 or not list2:
        return [f"    {col_name}:", f"      OLD: {v1_clean}", f"      NEW: {v2_clean}"]

    set1 = set(list1)
    set2 = set(list2)

    diffs = []

    # 1. CHECK FOR NEW/REMOVED ITEMS (The Important Stuff)
    added = sorted(list(set2 - set1))
    removed = sorted(list(set1 - set2))

    if added or removed:
        diffs.append(f"    {col_name}:")
        if added:   diffs.append(f"      [+] ADDED:   {', '.join(added)}")
        if removed: diffs.append(f"      [-] REMOVED: {', '.join(removed)}")
        return diffs

    # 2. CHECK FOR RANK SWAPS (The Minor Stuff)
    # If sets are equal, but lists are not, it's just a reordering
    if list1 != list2:
        # We can detect exactly what swapped, but usually just knowing it swapped is enough
        return [f"    {col_name}: [RANK SWAP] (Priority changed, same items)"]

    return None

def compare_csvs(old_file, new_file, ignore_rank_swaps=False):
    old_data, err1 = load_csv_as_dict(old_file)
    new_data, err2 = load_csv_as_dict(new_file)

    if err1: return [f"Error loading Old CSV: {err1}"]
    if err2: return [f"Error loading New CSV: {err2}"]

    logs = []
    
    old_keys = set(old_data.keys())
    new_keys = set(new_data.keys())

    # 1. New Characters
    added = sorted(list(new_keys - old_keys))
    if added:
        logs.append(f"--- NEW CHARACTERS ({len(added)}) ---")
        for char in added: logs.append(f"+ {char}")
        logs.append("")

    # 2. Removed Characters
    removed = sorted(list(old_keys - new_keys))
    if removed:
        logs.append(f"--- REMOVED CHARACTERS ({len(removed)}) ---")
        for char in removed: logs.append(f"- {char}")
        logs.append("")

    # 3. Changed Characters
    common = sorted(list(old_keys & new_keys))
    changes_found = False
    
    columns_to_watch = [
        'Top Artifact Sets', 
        'Common Sands', 'Common Goblet', 'Common Circlet', 
        'Substat Priority'
    ]

    diff_logs = []

    for char in common:
        old_row = old_data[char]
        new_row = new_data[char]
        char_changes = []

        for col in columns_to_watch:
            # Use the smart analyzer
            res = analyze_diff(col, old_row.get(col, ""), new_row.get(col, ""))
            if res:
                # If we are ignoring rank swaps, skip if the only change is [RANK SWAP]
                if ignore_rank_swaps and any("[RANK SWAP]" in line for line in res):
                    continue
                char_changes.extend(res)

        if char_changes:
            diff_logs.append(f"MODIFIED: {char}")
            diff_logs.extend(char_changes)
            diff_logs.append("")
            changes_found = True

    if changes_found:
        logs.append(f"--- MODIFIED CHARACTERS ---")
        logs.extend(diff_logs)
    elif not added and not removed:
        logs.append("Files are identical (content-wise).")

    return logs