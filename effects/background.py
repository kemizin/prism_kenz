from time import perf_counter

import cv2
import numpy as np

from config import (
    BACKGROUND_ENABLED,
    BACKGROUND_MODE,
    BACKGROUND_IMAGE_PATH,
    BACKGROUND_BLUR_KERNEL,
    BLUR_WORK_WIDTH,
    BLUR_WORK_HEIGHT,
    SEGMENTATION_THRESHOLD,
    SEGMENTATION_BACKEND,
    MASK_FEATHER_KERNEL,
    RVM_ALPHA_SHIFT,
)
from effects.segmentation import PersonSegmenter


_segmenter = None
_cached_background_image = None
_cached_background_key = None
_missing_bg_warning_shown = False
_background_was_active = False
_cached_alpha_source = None
_cached_composition_alpha = None
_cached_composition_alpha_key = None
_last_background_timings = {
    "segmentation": 0.0,
    "alpha_resize": 0.0,
    "background_prepare": 0.0,
    "alpha_prepare": 0.0,
    "compose_math": 0.0,
    "compose_total": 0.0,
    "compose": 0.0,
}
_last_compose_timings = {
    "alpha_prepare": 0.0,
    "compose_math": 0.0,
    "compose_total": 0.0,
}


class AlphaCompositor:
    """Fast OpenCV alpha compositor with reusable alpha/output buffers."""

    def __init__(self):
        self._shape = None
        self._alpha_source = None
        self._alpha_2d = None
        self._inv_alpha = None
        self._output_u8 = None

    def _ensure_buffers(self, frame):
        if self._shape == frame.shape:
            return

        height, width = frame.shape[:2]
        self._shape = frame.shape
        self._alpha_source = None
        self._alpha_2d = None
        self._inv_alpha = np.empty((height, width), dtype=np.float32)
        self._output_u8 = np.empty(frame.shape, dtype=np.uint8)

    def _prepare_alpha(self, alpha):
        if alpha is self._alpha_source:
            return self._alpha_2d

        alpha_2d = alpha[:, :, 0] if alpha.ndim == 3 else alpha
        if alpha_2d.dtype != np.float32 or not alpha_2d.flags.c_contiguous:
            alpha_2d = np.ascontiguousarray(alpha_2d, dtype=np.float32)

        np.subtract(1.0, alpha_2d, out=self._inv_alpha)
        self._alpha_source = alpha
        self._alpha_2d = alpha_2d
        return self._alpha_2d

    def compose(self, frame, background, alpha):
        self._ensure_buffers(frame)

        alpha_started_at = perf_counter()
        alpha_2d = self._prepare_alpha(alpha)
        alpha_prepare_ms = (perf_counter() - alpha_started_at) * 1000.0

        math_started_at = perf_counter()
        cv2.blendLinear(
            frame,
            background,
            alpha_2d,
            self._inv_alpha,
            dst=self._output_u8,
        )

        compose_math_ms = (perf_counter() - math_started_at) * 1000.0
        return self._output_u8, alpha_prepare_ms, compose_math_ms


_compositor = AlphaCompositor()


def get_segmenter():
    global _segmenter

    if _segmenter is None:
        _segmenter = PersonSegmenter()

    return _segmenter


def get_last_background_timings():
    return _last_background_timings.copy()


def _clear_background_timings():
    for stage in _last_background_timings:
        _last_background_timings[stage] = 0.0


def _deactivate_background():
    global _background_was_active

    if _background_was_active and _segmenter is not None:
        _segmenter.reset()

    _background_was_active = False


def get_background_image(width, height):
    global _cached_background_image
    global _cached_background_key
    global _missing_bg_warning_shown

    cache_key = (BACKGROUND_IMAGE_PATH, width, height)

    if _cached_background_image is not None and _cached_background_key == cache_key:
        return _cached_background_image

    image = cv2.imread(BACKGROUND_IMAGE_PATH)

    if image is None:
        if not _missing_bg_warning_shown:
            print(f"Nao consegui carregar o fundo: {BACKGROUND_IMAGE_PATH}")
            _missing_bg_warning_shown = True
        return None

    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    _cached_background_image = image
    _cached_background_key = cache_key
    return _cached_background_image


def apply_background(
    frame,
    mode=None,
    threshold=None,
    blur_kernel=None,
    enabled=None,
):
    global _background_was_active

    _clear_background_timings()

    if enabled is None:
        enabled = BACKGROUND_ENABLED
    if mode is None:
        mode = BACKGROUND_MODE
    if threshold is None:
        threshold = SEGMENTATION_THRESHOLD
    if blur_kernel is None:
        blur_kernel = BACKGROUND_BLUR_KERNEL

    if not enabled or mode == "none":
        _deactivate_background()
        return frame

    if mode not in ("blur", "image"):
        _deactivate_background()
        return frame

    segmenter = get_segmenter()
    if not _background_was_active:
        segmenter.reset()
    _background_was_active = True

    mask = segmenter.get_person_mask(frame)
    _last_background_timings["segmentation"] = segmenter.last_segmentation_ms
    _last_background_timings["alpha_resize"] = segmenter.last_alpha_resize_ms

    if mask is None:
        return frame

    height, width = frame.shape[:2]
    started_at = perf_counter()

    if mode == "blur":
        background = make_blur_background(frame, blur_kernel)
    else:
        background = get_background_image(width, height)
        if background is None:
            background = make_blur_background(frame, blur_kernel)

    _last_background_timings["background_prepare"] = (
        perf_counter() - started_at
    ) * 1000.0

    output = compose_person_with_background(
        frame=frame,
        background=background,
        mask=mask,
        threshold=threshold,
    )
    _last_background_timings.update(_last_compose_timings)
    _last_background_timings["compose"] = _last_compose_timings["compose_total"]
    return output


def make_blur_background(frame, blur_kernel):
    height, width = frame.shape[:2]
    work_width = max(1, int(BLUR_WORK_WIDTH))
    work_height = max(1, int(BLUR_WORK_HEIGHT))
    kernel = max(1, int(blur_kernel))

    if kernel % 2 == 0:
        kernel += 1

    if (width, height) != (work_width, work_height):
        work_frame = cv2.resize(
            frame,
            (work_width, work_height),
            interpolation=cv2.INTER_AREA,
        )
    else:
        work_frame = frame

    blurred = cv2.GaussianBlur(work_frame, (kernel, kernel), 0)

    if blurred.shape[:2] != (height, width):
        blurred = cv2.resize(
            blurred,
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )

    return blurred


def build_alpha_mask(mask, threshold):
    global _cached_alpha_source
    global _cached_composition_alpha
    global _cached_composition_alpha_key

    backend = SEGMENTATION_BACKEND.lower()

    if backend == "rvm":
        alpha_shift = float(RVM_ALPHA_SHIFT)
        feather = max(1, int(MASK_FEATHER_KERNEL))
        if feather % 2 == 0:
            feather += 1

        cache_key = (alpha_shift, feather)
        if (
            mask is _cached_alpha_source
            and cache_key == _cached_composition_alpha_key
        ):
            return _cached_composition_alpha

        alpha = mask.astype(np.float32, copy=False)

        if alpha_shift != 0.0:
            alpha = alpha.copy()
            alpha += alpha_shift
            np.clip(alpha, 0.0, 1.0, out=alpha)

        if feather > 1:
            alpha = cv2.GaussianBlur(alpha, (feather, feather), 0)

        _cached_alpha_source = mask
        _cached_composition_alpha_key = cache_key
        _cached_composition_alpha = alpha[..., None]
        return _cached_composition_alpha

    threshold = max(0.01, min(0.99, float(threshold)))
    alpha = (mask - threshold) / (1.0 - threshold)
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha = cv2.GaussianBlur(alpha, (9, 9), 0)
    return alpha[..., None]


def compose_person_with_background(frame, background, mask, threshold):
    compose_started_at = perf_counter()

    alpha_started_at = perf_counter()
    alpha = build_alpha_mask(mask, threshold)
    build_alpha_ms = (perf_counter() - alpha_started_at) * 1000.0

    output, alpha_convert_ms, compose_math_ms = _compositor.compose(
        frame,
        background,
        alpha,
    )

    _last_compose_timings["alpha_prepare"] = build_alpha_ms + alpha_convert_ms
    _last_compose_timings["compose_math"] = compose_math_ms
    _last_compose_timings["compose_total"] = (
        perf_counter() - compose_started_at
    ) * 1000.0
    return output
