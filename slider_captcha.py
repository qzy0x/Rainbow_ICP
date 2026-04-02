"""工信部备案滑块验证码：大图缺口定位，算法与 yzm.go 一致。"""
from __future__ import annotations

import base64
from typing import Optional, Tuple

import cv2
import numpy as np

SLIDER_X_BIAS = -1
_STRIP = 3


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def decode_base64_image(raw: str) -> np.ndarray:
    raw = raw.strip()
    for p in ("data:image/png;base64,", "data:image/jpeg;base64,"):
        if raw.startswith(p):
            raw = raw[len(p) :]
    data = base64.b64decode(raw)
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("invalid image data")
    return img


def rect_sum(ii: np.ndarray, x: int, y: int, rw: int, rh: int) -> float:
    h1, w1 = ii.shape
    x1 = clamp(x, 0, w1 - 1)
    y1 = clamp(y, 0, h1 - 1)
    x2 = clamp(x + rw, 0, w1 - 1)
    y2 = clamp(y + rh, 0, h1 - 1)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return float(ii[y2, x2] - ii[y1, x2] - ii[y2, x1] + ii[y1, x1])


def rect_mean(ii: np.ndarray, x: int, y: int, rw: int, rh: int) -> float:
    area = rw * rh
    if area <= 0:
        return 0.0
    return rect_sum(ii, x, y, rw, rh) / float(area)


def build_integral_gray_sat(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    bgr = img.astype(np.float64)
    b, g, r = bgr[:, :, 0], bgr[:, :, 1], bgr[:, :, 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    sat = (np.abs(r - g) + np.abs(r - b) + np.abs(g - b)) / 3.0
    gray_pad = np.pad(gray, ((1, 0), (1, 0)), mode="constant", constant_values=0)
    gray_sq_pad = np.pad(gray * gray, ((1, 0), (1, 0)), mode="constant", constant_values=0)
    sat_pad = np.pad(sat, ((1, 0), (1, 0)), mode="constant", constant_values=0)
    ig = gray_pad.cumsum(axis=0).cumsum(axis=1)
    ig2 = gray_sq_pad.cumsum(axis=0).cumsum(axis=1)
    isa = sat_pad.cumsum(axis=0).cumsum(axis=1)
    return ig, ig2, isa


def region_stats(img: np.ndarray, x: int, y: int, rw: int, rh: int) -> Tuple[float, float, float]:
    h, w = img.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w, x + rw), min(h, y + rh)
    if x2 <= x1 or y2 <= y1:
        return 0.0, 0.0, 0.0
    patch = img[y1:y2, x1:x2].astype(np.float64)
    b, g, r = patch[:, :, 0], patch[:, :, 1], patch[:, :, 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    sat = (np.abs(r - g) + np.abs(r - b) + np.abs(g - b)) / 3.0
    area = float((y2 - y1) * (x2 - x1))
    mean = float(gray.sum() / area)
    variance = float((gray * gray).sum() / area) - mean * mean
    saturation = float(sat.sum() / area)
    return mean, variance, saturation


def refine_blank_region(
    img: np.ndarray, seed_x: int, seed_y: int, box_w: int, box_h: int
) -> Optional[Tuple[int, int, int, int]]:
    h, w = img.shape[:2]
    best_score = float("-inf")
    best: Optional[Tuple[int, int, int, int]] = None

    y_min = max(0, seed_y - 4)
    y_max = min(h - box_h, seed_y + 4)
    x_min = max(0, seed_x - 4)
    x_max = min(w - box_w, seed_x + 4)
    if y_min > y_max or x_min > x_max:
        return None

    for yy in range(y_min, y_max + 1):
        for xx in range(x_min, x_max + 1):
            mean, variance, saturation = region_stats(img, xx, yy, box_w, box_h)
            if mean < 120 or mean > 245:
                continue
            if saturation > 20:
                continue
            score = -(variance * 1.2) - (saturation * 4)
            if score > best_score:
                best_score = score
                best = (xx, yy, box_w, box_h)
    return best


def locate_blank_region(
    img: np.ndarray, box_w: int, box_h: int
) -> Tuple[Tuple[int, int, int, int], float]:
    h, w = img.shape[:2]
    if box_w <= 0 or box_h <= 0 or box_w > w or box_h > h:
        return (0, 0, 0, 0), float("-inf")

    ig, ig2, isa = build_integral_gray_sat(img)
    best_score = float("-inf")
    best_xy: Optional[Tuple[int, int, int, int]] = None

    y_lo, y_hi = _STRIP, h - box_h - _STRIP
    x_lo, x_hi = _STRIP, w - box_w - _STRIP
    if y_lo > y_hi or x_lo > x_hi:
        return (0, 0, 0, 0), best_score

    for yy in range(y_lo, y_hi + 1):
        for xx in range(x_lo, x_hi + 1):
            inside_mean = rect_mean(ig, xx, yy, box_w, box_h)
            inside_var = rect_mean(ig2, xx, yy, box_w, box_h) - inside_mean * inside_mean
            inside_sat = rect_mean(isa, xx, yy, box_w, box_h)
            if inside_mean < 120 or inside_mean > 245:
                continue
            if inside_sat > 18:
                continue
            left_mean = rect_mean(ig, xx - _STRIP, yy, _STRIP, box_h)
            right_mean = rect_mean(ig, xx + box_w, yy, _STRIP, box_h)
            top_mean = rect_mean(ig, xx, yy - _STRIP, box_w, _STRIP)
            bottom_mean = rect_mean(ig, xx, yy + box_h, box_w, _STRIP)
            border_contrast = (
                abs(inside_mean - left_mean)
                + abs(inside_mean - right_mean)
                + abs(inside_mean - top_mean)
                + abs(inside_mean - bottom_mean)
            )
            score = border_contrast * 4 - inside_var * 0.45 - inside_sat * 3
            if score > best_score:
                best_score = score
                best_xy = (xx, yy, box_w, box_h)

    if best_xy is None:
        return (0, 0, 0, 0), best_score

    bx, by, bw, bh = best_xy
    refined = refine_blank_region(img, bx, by, bw, bh)
    if refined is not None:
        return refined, best_score
    return best_xy, best_score


def solve_captcha_x(big_b64: str, small_b64: str) -> int:
    big = decode_base64_image(big_b64)
    small = decode_base64_image(small_b64)
    sh, sw = small.shape[:2]
    rect, score = locate_blank_region(big, sw, sh)
    x0, _y0, rw, rh = rect
    if score == float("-inf") or (rw == 0 and rh == 0):
        raise RuntimeError("failed to locate blank region")
    return max(0, x0 + SLIDER_X_BIAS)
