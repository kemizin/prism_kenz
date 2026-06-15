import cv2

from config import BEAUTY_ENABLED, BEAUTY_STRENGTH, BEAUTY_MODE


def apply_beauty_filter(frame, strength=None, enabled=None):
    if enabled is None:
        enabled = BEAUTY_ENABLED

    if strength is None:
        strength = BEAUTY_STRENGTH

    strength = max(0.0, min(1.0, float(strength)))
    mode = str(BEAUTY_MODE).lower()

    if not enabled or strength <= 0 or mode == "off":
        return frame

    if mode == "fast":
        smooth = cv2.GaussianBlur(frame, (5, 5), 0)
    elif mode == "quality":
        smooth = cv2.bilateralFilter(
            frame,
            d=9,
            sigmaColor=75,
            sigmaSpace=75,
        )
    else:
        return frame

    return cv2.addWeighted(
        frame,
        1 - strength,
        smooth,
        strength,
        0,
    )
