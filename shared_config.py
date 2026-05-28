# shared_config.py

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

# --- TRANSLATION LAYER: GOOD Format -> CSV Format ---
GOOD_NAME_MAPPING = {
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

# --- ARTIFACT UI & LOGIC CONSTANTS ---
SLOT_ORDER = {
    'flower': 0,
    'plume': 1,
    'sands': 2,
    'goblet': 3,
    'circlet': 4
}

POSSIBLE_MAINS = {
    "Sands": ['ATK%', 'HP%', 'DEF%', 'ER%', 'EM'],
    "Goblet": ['ATK%', 'HP%', 'DEF%', 'EM', 'Anemo DMG%', 'Geo DMG%', 'Cryo DMG%', 'Hydro DMG%',
               'Pyro DMG%', 'Electro DMG%', 'Physical DMG%', 'Dendro DMG%'],
    "Circlet": ['ATK%', 'HP%', 'DEF%', 'EM', 'CRIT Rate%', 'CRIT DMG%', 'Healing Bonus%']
}

# --- SUBSTAT UI TO INTERNAL KEY MAPPING ---
SUBSTAT_UI_MAPPING = {
    'ATK%': 'atk_', 
    'HP%': 'hp_', 
    'DEF%': 'def_', 
    'Energy Recharge': 'enerRech_', 
    'Elemental Mastery': 'eleMas', 
    'Crit Rate': 'critRate_', 
    'Crit DMG': 'critDMG_'
}

# --- VALID ARTIFACT SETS ---
VALID_SETS = [
    "Adventurer", "ArchaicPetra", "Berserker", "BlizzardStrayer", "BloodstainedChivalry",
    "BraveHeart", "CrimsonWitchOfFlames", "DeepwoodMemories", "DefendersWill", 
    "DesertPavilionChronicle", "EchoesOfAnOffering", "EmblemOfSeveredFate", 
    "FlowerOfParadiseLost", "Gambler", "GildedDreams", "GladiatorsFinale", 
    "HeartOfDepth", "HuskOfOpulentDreams", "Instructor", "Lavawalker", "LuckyDog", 
    "MaidenBeloved", "MartialArtist", "NoblesseOblige", "OceanHuedClam", "PaleFlame", 
    "PrayersForDestiny", "PrayersForIllumination", "PrayersForWisdom", "PrayersToSpringtime", 
    "ResolutionOfSojourner", "RetracingBolide", "Scholar", "ShimenawasReminiscence", 
    "TenacityOfTheMillelith", "TheExile", "ThunderingFury", "Thundersoother", "TinyMiracle", 
    "TravelingDoctor", "VermillionHereafter", "ViridescentVenerer", "WanderersTroupe", 
    "NymphsDream", "VourukashasGlow", "GoldenTroupe", "MarechausseeHunter", 
    "NighttimeWhispersInTheEchoingWoods", "SongOfDaysPast", "FinaleOfTheDeepGalleries", 
    "FragmentOfHarmonicWhimsy", "LongNightsOath", "ObsidianCodex", 
    "ScrollOfTheHeroOfCinderCity", "UnfinishedReverie", "NightOfTheSkysUnveiling", 
    "SilkenMoonsSerenade", "ADayCarvedFromRisingWinds", "AubadeOfMorningstarAndMoon", 
    "CelestialGift", "DisenchantmentInDeepShadow"
]