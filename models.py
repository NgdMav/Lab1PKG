# models.py
from typing import Tuple, List
import colorsys
import math

# Все rgb внутри функций использует нормализованные значения в диапазоне [0.0, 1.0]
# RGB (UI) отображается/вводится в диапазоне 0..255
# HLS: H in degrees 0..360, L,S in percent 0..100
# CMYK: channels in percent 0..100

# ----------------- RGB <-> HLS -----------------
def srgb_to_hls(rgb: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """rgb: normalized [0..1] -> (H°, L%, S%)"""
    r, g, b = rgb
    h, l, s = colorsys.rgb_to_hls(r, g, b)  # colorsys: H 0..1, L 0..1, S 0..1
    return (h * 360.0, l * 100.0, s * 100.0)

def hls_to_srgb(hls: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """(H°, L%, S%) -> normalized rgb [0..1]"""
    h_deg, l_pct, s_pct = hls
    h = (h_deg % 360.0) / 360.0
    l = max(0.0, min(100.0, l_pct)) / 100.0
    s = max(0.0, min(100.0, s_pct)) / 100.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r, g, b)

# ----------------- RGB <-> CMYK -----------------
def srgb_to_cmyk(rgb: Tuple[float, float, float]) -> Tuple[float, float, float, float]:
    """rgb normalized -> (C%, M%, Y%, K%)"""
    r, g, b = rgb
    # Protect against tiny floating errors
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))

    k = 1.0 - max(r, g, b)
    if k >= 1.0 - 1e-12:
        return (0.0, 0.0, 0.0, 100.0)
    c = (1.0 - r - k) / (1.0 - k)
    m = (1.0 - g - k) / (1.0 - k)
    y = (1.0 - b - k) / (1.0 - k)
    return (c * 100.0, m * 100.0, y * 100.0, k * 100.0)

def cmyk_to_srgb(cmyk: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
    """(C%,M%,Y%,K%) -> rgb normalized [0..1]"""
    c, m, y, k = cmyk
    c = max(0.0, min(100.0, c)) / 100.0
    m = max(0.0, min(100.0, m)) / 100.0
    y = max(0.0, min(100.0, y)) / 100.0
    k = max(0.0, min(100.0, k)) / 100.0
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    # clamp just in case
    return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))

# ----------------- HEX utilities -----------------
def srgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = rgb
    r_i = int(round(max(0.0, min(1.0, r)) * 255.0))
    g_i = int(round(max(0.0, min(1.0, g)) * 255.0))
    b_i = int(round(max(0.0, min(1.0, b)) * 255.0))
    return "#{:02X}{:02X}{:02X}".format(r_i, g_i, b_i)

def hex_to_srgb(hex_str: str) -> Tuple[float, float, float]:
    s = hex_str.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) != 6:
        raise ValueError("HEX must be 6 hex digits")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    return (r, g, b)

# ----------------- small helpers -----------------
def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x

def rgb_norm_to_ui(rgb: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """normalized [0..1] -> 0..255 ints"""
    return (int(round(clamp01(rgb[0]) * 255.0)),
            int(round(clamp01(rgb[1]) * 255.0)),
            int(round(clamp01(rgb[2]) * 255.0)))

def rgb_ui_to_norm(rgb_ui: Tuple[int, int, int]) -> Tuple[float, float, float]:
    r, g, b = rgb_ui
    return (max(0, min(255, r)) / 255.0,
            max(0, min(255, g)) / 255.0,
            max(0, min(255, b)) / 255.0)

# ----------------- Convenience convert-from/to for panels -----------------
def convert_from_srgb(panel_name: str, rgb_norm: Tuple[float, float, float]) -> List[float]:
    """Return list of values suitable for UI controls for the given panel."""
    if panel_name == "RGB":
        r, g, b = rgb_norm_to_ui(rgb_norm)
        return [r, g, b]
    elif panel_name == "CMYK":
        c, m, y, k = srgb_to_cmyk(rgb_norm)
        return [round(c, 2), round(m, 2), round(y, 2), round(k, 2)]
    elif panel_name == "HLS":
        h, l, s = srgb_to_hls(rgb_norm)
        return [round(h, 2), round(l, 2), round(s, 2)]
    else:
        raise ValueError("Unknown panel: " + panel_name)

def convert_to_srgb(panel_name: str, values: List[float]) -> Tuple[Tuple[float, float, float], bool]:
    """
    Given UI values from a panel, return (rgb_norm, clipped_flag).
    clipped_flag indicates whether some values were outside [0..1] and clipped (only relevant for conversions that can produce out-of-gamut).
    """
    clipped = False
    if panel_name == "RGB":
        r = max(0, min(255, int(round(values[0])))) / 255.0
        g = max(0, min(255, int(round(values[1])))) / 255.0
        b = max(0, min(255, int(round(values[2])))) / 255.0
        return ((r, g, b), clipped)
    elif panel_name == "CMYK":
        # values: C, M, Y, K percent
        c = values[0]
        m = values[1]
        y = values[2]
        k = values[3]
        rgb = cmyk_to_srgb((c, m, y, k))
        return (rgb, clipped)
    elif panel_name == "HLS":
        # values: H°, L%, S%
        h = values[0]
        l = values[1]
        s = values[2]
        rgb = hls_to_srgb((h, l, s))
        # hls_to_srgb returns normalized; theoretically in-range, but clamp
        r, g, b = rgb
        cr, cg, cb = clamp01(r), clamp01(g), clamp01(b)
        if (cr != r) or (cg != g) or (cb != b):
            clipped = True
        return ((cr, cg, cb), clipped)
    else:
        raise ValueError("Unknown panel: " + panel_name)
