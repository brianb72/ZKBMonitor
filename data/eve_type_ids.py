'''
Centeral location for important type ids
'''

WATCH_REGIONS = [
    10000015,   # Venal
    10000035,   # Deklein
    10000055,   # Branch
    10000045,   # Tenal
    10000066,   # Perrigen Falls
    10000010,   # Tribute
    10000040,   # Oasa
    10000053,   # Cobalt Edge
    10000046,   # Fade
    10000023,   # Pure Blind
    10000013,   # Malpais
]

HOME_SYSTEM_ID = 30001329
REGION_VENAL = 10000015

# Supers
id_titan = [671, 3764, 11567, 23773, 42126, 42241, 45649]
id_supercarrier = [3514, 3628, 22852, 23913, 23917, 23919, 42125]

# Caps
id_carrier = [23757, 23911, 23915, 24483, 42132]
id_dreadnought = [19720, 19722, 19724, 19726, 34339, 34341, 34343, 34345, 42124, 42243, 45647]
id_fax = [37604, 37605, 37606, 37607, 42133, 42242, 45645]
id_jumpfreighter = [28844, 28846, 28848, 28850]
id_freighter = [20183, 20185, 20187, 20189, 34328]

# Battleships
id_blackop = [22428, 22430, 22436, 22440, 44996]
id_marauder = [28659, 28661, 28665, 28710]

#          Rorq
id_misc = [28352]
id_cruisers = [620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 2006, 17634, 17709,
               17713, 17715, 17718, 17720, 17722, 17843, 17922, 29336, 29337, 29340, 29344, 33470, 33818]

id_supers = id_titan + id_supercarrier
id_caps = id_carrier + id_dreadnought + id_fax + id_jumpfreighter + id_freighter + id_misc
id_otherbig = id_blackop + id_marauder + id_misc

id_full_list = id_supers + id_caps + id_otherbig
