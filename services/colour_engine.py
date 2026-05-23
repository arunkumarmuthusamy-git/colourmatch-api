"""
AI Colour Matching App — Colour Science Engine
CIE L*a*b* conversion, CIEDE2000 Delta-E, lighting correction
"""
import math
import numpy as np
from typing import Tuple, List, Optional


def srgb_to_linear(c: float) -> float:
    """Convert sRGB channel [0-255] to linear RGB [0-1]."""
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_xyz(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB (0-255) to CIE XYZ using D65 illuminant."""
    rl, gl, bl = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
    y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
    z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041
    return x * 100, y * 100, z * 100


def xyz_to_lab(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Convert CIE XYZ to CIE L*a*b* (D65 illuminant)."""
    xn, yn, zn = 95.047, 100.000, 108.883  # D65 reference white
    def f(t):
        return t ** (1/3) if t > 0.008856 else (7.787 * t) + (16/116)
    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB (0-255) to CIE L*a*b*."""
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)


def lab_to_xyz(L: float, a: float, b: float) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to CIE XYZ."""
    xn, yn, zn = 95.047, 100.000, 108.883
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    def f_inv(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16/116) / 7.787
    return f_inv(fx) * xn, f_inv(fy) * yn, f_inv(fz) * zn


def lab_to_rgb(L: float, a: float, b: float) -> Tuple[int, int, int]:
    """Convert CIE L*a*b* to sRGB (0-255)."""
    x, y, z = lab_to_xyz(L, a, b)
    x, y, z = x / 100, y / 100, z / 100
    r = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    bl = x * 0.0556434 + y * -0.2040259 + z * 1.0572252
    def to_srgb(c):
        c = max(0, min(1, c))
        return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1/2.4)) - 0.055
    return (int(round(to_srgb(r) * 255)), int(round(to_srgb(g) * 255)), int(round(to_srgb(bl) * 255)))


def lab_to_hex(L: float, a: float, b: float) -> str:
    """Convert L*a*b* to hex colour string."""
    r, g, b_val = lab_to_rgb(L, a, b)
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b_val)):02x}"


def ciede2000(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
    """
    Calculate CIEDE2000 colour difference (Delta E).
    Implementation per CIE technical report.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Step 1: Calculate C' and h'
    C1 = math.sqrt(a1**2 + b1**2)
    C2 = math.sqrt(a2**2 + b2**2)
    C_avg = (C1 + C2) / 2.0
    C_avg_7 = C_avg**7
    G = 0.5 * (1 - math.sqrt(C_avg_7 / (C_avg_7 + 25**7)))

    a1p = a1 * (1 + G)
    a2p = a2 * (1 + G)
    C1p = math.sqrt(a1p**2 + b1**2)
    C2p = math.sqrt(a2p**2 + b2**2)

    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    # Step 2: Calculate dL', dC', dH'
    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p * C2p == 0:
        dhp = 0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360

    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))

    # Step 3: Calculate CIEDE2000
    Lp_avg = (L1 + L2) / 2.0
    Cp_avg = (C1p + C2p) / 2.0

    if C1p * C2p == 0:
        hp_avg = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hp_avg = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        hp_avg = (h1p + h2p + 360) / 2.0
    else:
        hp_avg = (h1p + h2p - 360) / 2.0

    T = (1 - 0.17 * math.cos(math.radians(hp_avg - 30))
         + 0.24 * math.cos(math.radians(2 * hp_avg))
         + 0.32 * math.cos(math.radians(3 * hp_avg + 6))
         - 0.20 * math.cos(math.radians(4 * hp_avg - 63)))

    SL = 1 + 0.015 * (Lp_avg - 50)**2 / math.sqrt(20 + (Lp_avg - 50)**2)
    SC = 1 + 0.045 * Cp_avg
    SH = 1 + 0.015 * Cp_avg * T

    Cp_avg_7 = Cp_avg**7
    RT = (-math.sin(2 * math.radians(30 * math.exp(-((hp_avg - 275) / 25)**2)))
          * 2 * math.sqrt(Cp_avg_7 / (Cp_avg_7 + 25**7)))

    dE = math.sqrt((dLp / SL)**2 + (dCp / SC)**2 + (dHp / SH)**2 + RT * (dCp / SC) * (dHp / SH))
    return round(dE, 4)


def delta_e_to_match_percent(delta_e: float) -> float:
    """Convert Delta-E to a human-friendly match percentage (0-100%)."""
    if delta_e <= 0:
        return 100.0
    elif delta_e >= 20:
        return 0.0
    return round(max(0, 100 * math.exp(-0.15 * delta_e)), 1)


def get_interpretation(match_percent: float) -> str:
    """Classify match quality based on percentage."""
    if match_percent >= 85:
        return "excellent_match"
    elif match_percent >= 70:
        return "good_match"
    elif match_percent >= 50:
        return "marginal_match"
    elif match_percent >= 20:
        return "poor_match"
    return "no_match"


def get_recommendation(delta_l: float, delta_a: float, delta_b: float, interpretation: str) -> str:
    """Generate a plain-English recommendation based on colour differences."""
    if interpretation == "excellent_match":
        return "Excellent colour match. This sample is within acceptable tolerance for production."

    parts = []
    if abs(delta_l) > 1.0:
        parts.append("darker" if delta_l < 0 else "lighter")
    if abs(delta_a) > 1.0:
        parts.append("more green" if delta_a < 0 else "more red")
    if abs(delta_b) > 1.0:
        parts.append("more blue" if delta_b < 0 else "more yellow")

    if not parts:
        return "Minor colour deviation detected. Review under standard lighting."

    direction = ", ".join(parts)
    if interpretation == "good_match":
        return f"Good match with slight deviation: sample appears {direction}. Acceptable for most applications."
    elif interpretation == "marginal_match":
        return f"Marginal match: sample is noticeably {direction}. Consider re-dyeing or adjusting recipe."
    else:
        return f"Poor match: sample is significantly {direction}. Re-dyeing recommended with adjusted parameters."


# Lighting correction matrices (simplified)
LIGHTING_CORRECTIONS = {
    "indoor": {
        "L_offset": 2.5,   # Indoor tends to appear darker
        "a_offset": -0.8,  # Slight green shift under fluorescent
        "b_offset": 1.2,   # Warm yellow shift under tungsten
    },
    "outdoor": {
        "L_offset": -1.0,  # Outdoor tends to appear brighter
        "a_offset": 0.3,
        "b_offset": -0.5,  # Slight blue shift in daylight
    },
}


def apply_lighting_correction(L: float, a: float, b: float, condition: str) -> Tuple[float, float, float]:
    """Apply lighting correction to raw L*a*b* values."""
    corr = LIGHTING_CORRECTIONS.get(condition, LIGHTING_CORRECTIONS["indoor"])
    return (
        max(0, min(100, L + corr["L_offset"])),
        max(-128, min(127, a + corr["a_offset"])),
        max(-128, min(127, b + corr["b_offset"])),
    )


def extract_dominant_colour_from_roi(image_array: np.ndarray, roi: Optional[dict] = None) -> Tuple[int, int, int]:
    """
    Extract dominant colour from image region using mean of central pixels.
    image_array: numpy array (H, W, 3) in RGB
    roi: optional {x, y, width, height}
    """
    if roi and all(k in roi for k in ("x", "y", "width", "height")):
        x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
        crop = image_array[y:y+h, x:x+w]
    else:
        h, w = image_array.shape[:2]
        cx, cy = w // 2, h // 2
        size = min(w, h) // 4
        crop = image_array[cy-size:cy+size, cx-size:cx+size]

    if crop.size == 0:
        crop = image_array

    avg = crop.mean(axis=(0, 1))
    return int(round(avg[0])), int(round(avg[1])), int(round(avg[2]))


# Basic Pantone TCX lookup (subset — top 50 most used in garments)
PANTONE_DB = [
    ("19-4052 TCX", "Classic Blue", 15.42, 3.58, -31.85),
    ("17-5104 TCX", "Ultimate Gray", 53.59, -1.52, -0.73),
    ("13-0647 TCX", "Illuminating", 87.44, -2.66, 72.47),
    ("18-1662 TCX", "Flame Scarlet", 42.09, 55.23, 36.86),
    ("19-0303 TCX", "Jet Black", 15.24, 0.41, -0.82),
    ("11-0601 TCX", "Bright White", 95.05, -0.85, 2.56),
    ("19-3952 TCX", "Royal Blue", 23.32, 17.47, -44.26),
    ("18-1764 TCX", "Lollipop", 37.06, 52.76, 20.29),
    ("15-1247 TCX", "Apricot", 67.92, 22.89, 37.62),
    ("14-0756 TCX", "Empire Yellow", 80.31, 0.47, 72.89),
    ("17-1463 TCX", "Tangerine Tango", 49.86, 47.43, 45.81),
    ("15-5519 TCX", "Turquoise", 63.44, -28.91, -8.63),
    ("18-3838 TCX", "Ultra Violet", 33.59, 26.74, -35.05),
    ("16-1546 TCX", "Living Coral", 63.33, 35.35, 24.05),
    ("19-4150 TCX", "Snorkel Blue", 25.68, 4.87, -34.15),
    ("17-1564 TCX", "Fiesta", 47.59, 51.95, 44.41),
    ("15-0343 TCX", "Greenery", 67.72, -22.78, 47.67),
    ("17-4041 TCX", "Cerulean", 47.13, -7.92, -31.23),
    ("19-1557 TCX", "Chili Pepper", 29.36, 41.08, 23.74),
    ("14-4811 TCX", "Aqua Sky", 72.32, -15.64, -10.95),
    ("16-1720 TCX", "Strawberry Ice", 62.61, 29.48, 7.71),
    ("18-3943 TCX", "Blue Iris", 36.01, 18.44, -32.83),
    ("18-2120 TCX", "Honeysuckle", 48.95, 43.96, 1.27),
    ("19-1664 TCX", "True Red", 33.17, 50.18, 30.14),
    ("15-1040 TCX", "Custard", 75.73, 4.48, 41.95),
    ("13-1520 TCX", "Rose Quartz", 78.62, 11.84, 2.67),
    ("15-3919 TCX", "Serenity", 70.19, 1.97, -15.78),
    ("18-1438 TCX", "Marsala", 39.96, 24.53, 15.38),
    ("15-0146 TCX", "Kale", 46.23, -22.39, 20.91),
    ("17-1462 TCX", "Flame", 53.07, 43.13, 45.50),
]


def find_nearest_pantones(L: float, a: float, b: float, n: int = 3) -> List[Tuple[str, str, float]]:
    """Find the N nearest Pantone TCX colours using CIEDE2000."""
    distances = []
    for code, name, pL, pa, pb in PANTONE_DB:
        de = ciede2000((L, a, b), (pL, pa, pb))
        distances.append((code, name, de))
    distances.sort(key=lambda x: x[2])
    return distances[:n]
