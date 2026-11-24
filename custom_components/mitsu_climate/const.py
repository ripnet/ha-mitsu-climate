from __future__ import annotations

DOMAIN = "mitsu_climate"

# Config keys
CONF_SOURCE_ENTITY = "source_entity"
CONF_NAME = "name"
CONF_REVERSE_POLICY = "reverse_policy"  # "lowest" or "highest"

# (Celsius, Fahrenheit) pairs from the thermostat's internal table.
# C values are 0.5-step from -18 to 60; F values are integers.
LOOKUP_TABLE: list[tuple[float, int]] = [
    (-18.0, 0),  (-17.5, 1),  (-17.0, 1),  (-16.5, 2),  (-16.0, 3),
    (-15.5, 4),  (-15.0, 5),  (-14.5, 6),  (-14.0, 7),  (-13.5, 8),
    (-13.0, 9),  (-12.5, 10), (-12.0, 10), (-11.5, 11), (-11.0, 12),
    (-10.5, 13), (-10.0, 14), (-9.5, 15),  (-9.0, 16),  (-8.5, 17),
    (-8.0, 18),  (-7.5, 19),  (-7.0, 19),  (-6.5, 20),  (-6.0, 21),
    (-5.5, 22),  (-5.0, 23),  (-4.5, 24),  (-4.0, 25),  (-3.5, 26),
    (-3.0, 27),  (-2.5, 28),  (-2.0, 28),  (-1.5, 29),  (-1.0, 30),
    (-0.5, 31),  (0.0, 32),   (0.5, 33),   (1.0, 34),   (1.5, 35),
    (2.0, 36),   (2.5, 37),   (3.0, 37),   (3.5, 38),   (4.0, 39),
    (4.5, 40),   (5.0, 41),   (5.5, 42),   (6.0, 43),   (6.5, 44),
    (7.0, 45),   (7.5, 46),   (8.0, 46),   (8.5, 47),   (9.0, 48),
    (9.5, 49),   (10.0, 50),  (10.5, 51),  (11.0, 52),  (11.5, 53),
    (12.0, 53),  (12.5, 54),  (13.0, 55),  (13.5, 56),  (14.0, 57),
    (14.5, 58),  (15.0, 59),  (15.5, 60),  (16.0, 61),  (16.5, 62),
    (17.0, 63),  (17.5, 64),  (18.0, 65),  (18.5, 66),  (19.0, 67),
    (19.5, 67),  (20.0, 68),  (20.5, 68),  (21.0, 69),  (21.5, 70),
    (22.0, 71),  (22.5, 72),  (23.0, 73),  (23.5, 74),  (24.0, 75),
    (24.5, 76),  (25.0, 77),  (25.5, 78),  (26.0, 79),  (26.5, 80),
    (27.0, 81),  (27.5, 82),  (28.0, 83),  (28.5, 84),  (29.0, 85),
    (29.5, 86),  (30.0, 87),  (30.5, 88),  (31.0, 88),  (31.5, 89),
    (32.0, 89),  (32.5, 90),  (33.0, 91),  (33.5, 92),  (34.0, 93),
    (34.5, 94),  (35.0, 95),  (35.5, 96),  (36.0, 97),  (36.5, 98),
    (37.0, 99),  (37.5, 100), (38.0, 100), (38.5, 101), (39.0, 102),
    (39.5, 103), (40.0, 104), (40.5, 105), (41.0, 106), (41.5, 107),
    (42.0, 108), (42.5, 109), (43.0, 109), (43.5, 110), (44.0, 111),
    (44.5, 112), (45.0, 113), (45.5, 114), (46.0, 115), (46.5, 116),
    (47.0, 117), (47.5, 118), (48.0, 118), (48.5, 119), (49.0, 120),
    (49.5, 121), (50.0, 122), (50.5, 123), (51.0, 124), (51.5, 125),
    (52.0, 126), (52.5, 127), (53.0, 127), (53.5, 128), (54.0, 129),
    (54.5, 130), (55.0, 131), (55.5, 132), (56.0, 133), (56.5, 134),
    (57.0, 135), (57.5, 136), (58.0, 136), (58.5, 137), (59.0, 138),
    (59.5, 139), (60.0, 140),
]


def c_to_f(celsius: float) -> int | None:
    """Convert C to F using the thermostat's lookup table.

    Snaps the input to the nearest 0.5°C entry, then returns the
    corresponding integer F value. Returns None if the input is
    outside the table's C range (treat as unknown/invalid).
    """
    min_c = LOOKUP_TABLE[0][0]
    max_c = LOOKUP_TABLE[-1][0]
    if celsius is None or celsius < min_c or celsius > max_c:
        return None
    closest = min(LOOKUP_TABLE, key=lambda pair: abs(pair[0] - celsius))
    return closest[1]


def f_to_c(fahrenheit: int, policy: str = "lowest") -> float:
    """Convert F back to C. Multiple C values may map to the same F.

    policy='lowest'  -> return the lowest C that maps to this F
    policy='highest' -> return the highest C that maps to this F
    """
    matches = [c for c, f in LOOKUP_TABLE if f == fahrenheit]
    if matches:
        return min(matches) if policy == "lowest" else max(matches)

    # F outside the table: clamp to the range and recurse
    min_f = min(f for _, f in LOOKUP_TABLE)
    max_f = max(f for _, f in LOOKUP_TABLE)
    clamped = max(min_f, min(max_f, fahrenheit))
    return f_to_c(clamped, policy)


# Precomputed bounds for the entity
MIN_F = min(f for _, f in LOOKUP_TABLE)  # 0
MAX_F = max(f for _, f in LOOKUP_TABLE)  # 140