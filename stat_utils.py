import copy

# --- STAT CONSTANTS ---

POSSIBLE_MAINS = {
    "Sands": ['ATK%', 'HP%', 'DEF%', 'ER%', 'EM'],
    "Goblet": ['ATK%', 'HP%', 'DEF%', 'EM', 'Anemo DMG%', 'Geo DMG%', 'Cryo DMG%', 'Hydro DMG%',
               'Pyro DMG%', 'Electro DMG%', 'Physical DMG%', 'Dendro DMG%'],
    "Circlet": ['ATK%', 'HP%', 'DEF%', 'EM', 'CRIT Rate%', 'CRIT DMG%', 'Healing Bonus%']
}