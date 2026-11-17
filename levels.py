# ==========================================
# ORBIT BREAKER - LEVELS
# ==========================================
# Each level is a grid of 25 columns x 18 rows (40px tiles).
# Rows are listed top to bottom. Short maps are padded with empty
# rows at the top, short rows are padded with spaces on the right.
#
#   #  solid block            P  player start
#   ^  spike (floor)          E  exit portal (opens when all orbs are taken)
#   v  spike (ceiling)        o  energy orb
#   C  checkpoint             c  crumbling platform
#   J  spring pad             g  gravity ring (flips gravity)
#   w  walker drone           f  flying drone (up/down)
#   F  flying drone (left/right)
#
# "movers" are moving platforms: c/r = start tile, w = width in tiles,
# dx/dy = travel in tiles, speed = pixels per frame.

LEVELS = [
    # ------------------------------------------------------------ 1
    {
        "name": "THE FIRST ORBIT",
        "hint": "SPACE to jump. Collect every orb, then enter the portal.",
        "map": [
            "                     o E ",
            "                     ####",
            "                o ^      ",
            "               #####     ",
            "           o C           ",
            "         #####           ",
            "     o                   ",
            "   #####                 ",
            " P        ^^             ",
            "#########################",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 2
    {
        "name": "THE BROKEN MOON",
        "hint": "Hold SPACE for a high jump, tap it for a short hop.",
        "map": [
            "                o E      ",
            "                #####    ",
            "           o             ",
            "         #####           ",
            "    o C                  ",
            "  #####                  ",
            "         o ^             ",
            "        #####            ",
            "              ^ o        ",
            "              #####      ",
            "                     o   ",
            "        o      o    #### ",
            " P                 ^     ",
            "#######   ####   ########",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 3
    {
        "name": "SOLAR WINDS",
        "hint": "Moving platforms carry you. Pick your moment to hop on.",
        "map": [
            "             o           ",
            "     E o                 ",
            "   ######           oC ^ ",
            "                    #####",
            "                         ",
            "                  o      ",
            "                         ",
            "                         ",
            "             o C         ",
            "        o   ####         ",
            " P                       ",
            "#####^^^^^^^^^^^^^^^#####",
        ],
        "movers": [
            {"c": 6, "r": 16, "w": 2, "dx": 4, "dy": 0, "speed": 1.6},
            {"c": 17, "r": 15, "w": 2, "dx": 0, "dy": -6, "speed": 1.3},
            {"c": 11, "r": 7, "w": 2, "dx": 4, "dy": 0, "speed": 1.5},
        ],
    },
    # ------------------------------------------------------------ 4
    {
        "name": "DRONE FIELD",
        "hint": "Land on drones from above, or smash them with a SHIFT dash.",
        "map": [
            "                  o w    ",
            "                #####    ",
            "           o             ",
            "         #####           ",
            "    o                    ",
            "  #####         f        ",
            "                     o   ",
            " P      w  o  w    ^ C E ",
            "#########################",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 5
    {
        "name": "CRUMBLING STATION",
        "hint": "Crumbling platforms fall soon after you land. Keep moving!",
        "map": [
            "  E                      ",
            " ####  o                 ",
            "      ccc                ",
            "            o            ",
            "           ccc           ",
            "                 o       ",
            "                ccc      ",
            "                      o C",
            "                 o   ####",
            "            o   ccc      ",
            "       o   ccc           ",
            " P    ccc                ",
            "####^^^^^^^^^^^^^^^^^####",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 6
    {
        "name": "GRAVITY WELL",
        "hint": "Purple rings flip gravity. Walk on the ceiling!",
        "map": [
            "#########################",
            "#########################",
            "         oC v  v og      ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            "        o            o   ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            "                         ",
            " P o  g ^^^^^^^^^^  o  E ",
            "#########################",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 7
    {
        "name": "ION STORM",
        "hint": "Green springs launch you sky-high. Steer in mid-air!",
        "map": [
            "  o o o o                ",
            " ########                ",
            "                         ",
            "                      oE ",
            "                      ###",
            "                  o f    ",
            "           J  C    ####  ",
            "           #####         ",
            "                         ",
            "         o               ",
            "                         ",
            "                         ",
            "         J               ",
            " P      ###              ",
            "######^^^^^^^^^^^^^######",
        ],
        "movers": [],
    },
    # ------------------------------------------------------------ 8
    {
        "name": "THE FINAL FRONTIER",
        "hint": "Everything you have learned, all at once. Good luck, pilot.",
        "map": [
            "#########################",
            "#########################",
            "    g  o v   v  o        ",
            "                         ",
            "                         ",
            "                      o  ",
            "     o                   ",
            "                   C  g  ",
            "                   ####  ",
            "    E                    ",
            " #######                 ",
            "                o        ",
            "                         ",
            "         f   o           ",
            "            w            ",
            "       o   ####          ",
            " P    ccc                ",
            "#####^^^^^^^^^^^^^^^^^^^^",
        ],
        "movers": [
            {"c": 16, "r": 15, "w": 2, "dx": 0, "dy": -7, "speed": 1.4},
        ],
    },
]