import copy

# --- STAT CONSTANTS ---

STAT_NAME_TO_INDEX = {
    'DEF%': 1, 'Flat DEF': 2, 'Flat HP': 3, 'HP%': 4, 'Flat ATK': 5,
    'ATK%': 6, 'ER%': 7, 'EM': 8, 'CRIT Rate%': 9, 'CRIT DMG%': 10
}

# Average substat roll values (85% of max roll)
AVG_SUB_VALUES = [None] * 26
AVG_SUB_VALUES[3] = 298.75 * 0.85  # hp
AVG_SUB_VALUES[4] = 0.0583 * 0.85  # hp_pcnt
AVG_SUB_VALUES[2] = 23.15 * 0.85   # defd
AVG_SUB_VALUES[1] = 0.0729 * 0.85  # defd_pcnt
AVG_SUB_VALUES[5] = 19.45 * 0.85   # atk
AVG_SUB_VALUES[6] = 0.0583 * 0.85  # atk_pcnt
AVG_SUB_VALUES[8] = 23.31 * 0.85   # em
AVG_SUB_VALUES[9] = 0.0389 * 0.85  # cr
AVG_SUB_VALUES[10] = 0.0777 * 0.85 # cd
AVG_SUB_VALUES[7] = 0.0648 * 0.85  # er

MAIN_STATS = {
    'HP': 4780, 'ATK': 311, 'HP%': 0.466, 'ATK%': 0.466, 'DEF%': 0.583, 'ER%': 0.518, 'EM': 187,
    'Anemo DMG%': 0.466, 'Geo DMG%': 0.466, 'Cryo DMG%': 0.466, 'Hydro DMG%': 0.466,
    'Pyro DMG%': 0.466, 'Electro DMG%': 0.466, 'Physical DMG%': 0.583, 'Dendro DMG%': 0.466,
    'CRIT Rate%': 0.311, 'CRIT DMG%': 0.622, 'Healing Bonus%': 0.359,
}

INDEX_TO_STAT = {
    1: 'DEF%', 2: 'Flat DEF', 3: 'Flat HP', 4: 'HP%', 5: 'Flat ATK', 6: 'ATK%', 7: 'ER%',
    8: 'EM', 9: 'CRIT Rate%', 10: 'CRIT DMG%', 11: 'Healing Bonus%', 12: 'Pyro DMG%',
    13: 'Hydro DMG%', 14: 'Cryo DMG%', 15: 'Electro DMG%', 16: 'Anemo DMG%', 17: 'Geo DMG%',
    18: 'Dendro DMG%', 19: 'Physical DMG%',
}

POSSIBLE_MAINS = {
    "Sands": ['ATK%', 'HP%', 'DEF%', 'ER%', 'EM'],
    "Goblet": ['ATK%', 'HP%', 'DEF%', 'EM', 'Anemo DMG%', 'Geo DMG%', 'Cryo DMG%', 'Hydro DMG%',
               'Pyro DMG%', 'Electro DMG%', 'Physical DMG%', 'Dendro DMG%'],
    "Circlet": ['ATK%', 'HP%', 'DEF%', 'EM', 'CRIT Rate%', 'CRIT DMG%', 'Healing Bonus%']
}

INTERNAL_TO_TS_STAT = {
    'HP%': 'hp_', 'Flat HP': 'hp', 'ATK%': 'atk_', 'Flat ATK': 'atk', 'DEF%': 'def_',
    'Flat DEF': 'def', 'ER%': 'enerRech_', 'EM': 'eleMas', 'CRIT Rate%': 'critRate_',
    'CRIT DMG%': 'critDMG_', 'Healing Bonus%': 'heal_', 'Physical DMG%': 'physical_dmg_',
    'Anemo DMG%': 'anemo_dmg_', 'Geo DMG%': 'geo_dmg_', 'Electro DMG%': 'electro_dmg_',
    'Hydro DMG%': 'hydro_dmg_', 'Pyro DMG%': 'pyro_dmg_', 'Cryo DMG%': 'cryo_dmg_',
    'Dendro DMG%': 'dendro_dmg_', 'HP': 'hp', 'ATK': 'atk',
}

# --- FUNCTIONS ---

def array_to_dict(stats_array):
    """Converts a stats array (from JSON) into a dictionary using INDEX_TO_STAT."""
    stats_dict = {}
    for i, value in enumerate(stats_array):
        if i in INDEX_TO_STAT:
            stats_dict[INDEX_TO_STAT[i]] = value
    return stats_dict

def deduce_build(stats_array):
    """
    Deduces the main stats and substats from a character's total stats array.
    Returns:
        main_stats (dict): {'Sands': ..., 'Goblet': ..., 'Circlet': ...}
        substats (dict): {stat_name: value}
    """
    total_stats = array_to_dict(stats_array)
    
    # Iterate through all possible main stat combinations
    for sand in POSSIBLE_MAINS["Sands"]:
        for goblet in POSSIBLE_MAINS["Goblet"]:
            for circlet in POSSIBLE_MAINS["Circlet"]:
                substats = copy.deepcopy(total_stats)
                try:
                    # Subtract base stats (Flower HP, Plume ATK)
                    substats.setdefault('Flat HP', 0); substats['Flat HP'] -= MAIN_STATS['HP']
                    substats.setdefault('Flat ATK', 0); substats['Flat ATK'] -= MAIN_STATS['ATK']
                    
                    # Subtract candidate main stats
                    substats.setdefault(sand, 0); substats[sand] -= MAIN_STATS[sand]
                    substats.setdefault(goblet, 0); substats[goblet] -= MAIN_STATS[goblet]
                    substats.setdefault(circlet, 0); substats[circlet] -= MAIN_STATS[circlet]
                except KeyError:
                    continue
                
                # Check if the remaining stats (substats) are valid (non-negative within tolerance)
                if all(v >= -1e-6 for v in substats.values()):
                    main_stats = {'Sands': sand, 'Goblet': goblet, 'Circlet': circlet}
                    # Filter out zero values
                    final_substats = {k: v for k, v in substats.items() if v > 1e-6}
                    return main_stats, final_substats
    return None, None
