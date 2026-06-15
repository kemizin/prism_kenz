from time import perf_counter

import cv2
import numpy as np

from effects.background import AlphaCompositor


HEIGHT = 720
WIDTH = 1280
ITERATIONS = 40


def benchmark(function):
    for _ in range(5):
        function()

    started_at = perf_counter()
    for _ in range(ITERATIONS):
        function()

    return (perf_counter() - started_at) * 1000.0 / ITERATIONS


def main():
    rng = np.random.default_rng(7)
    frame = rng.integers(0, 256, (HEIGHT, WIDTH, 3), dtype=np.uint8)
    background = rng.integers(0, 256, (HEIGHT, WIDTH, 3), dtype=np.uint8)
    alpha = rng.random((HEIGHT, WIDTH, 1), dtype=np.float32)

    def compose_float32():
        return (
            frame.astype(np.float32) * alpha
            + background.astype(np.float32) * (1.0 - alpha)
        ).astype(np.uint8)

    compositor = AlphaCompositor()
    changing_alpha_compositor = AlphaCompositor()
    inverse_alpha = 1.0 - alpha
    alpha_index = 0

    def compose_optimized():
        return compositor.compose(frame, background, alpha)[0]

    def compose_optimized_changing_alpha():
        nonlocal alpha_index
        alpha_index += 1
        current_alpha = alpha if alpha_index % 2 else inverse_alpha
        return changing_alpha_compositor.compose(
            frame,
            background,
            current_alpha,
        )[0]

    old_ms = benchmark(compose_float32)
    new_ms = benchmark(compose_optimized)
    changing_alpha_ms = benchmark(compose_optimized_changing_alpha)
    reference = compose_float32()
    output = compose_optimized().copy()
    max_difference = np.abs(
        reference.astype(np.int16) - output.astype(np.int16)
    ).max()

    print(f"float32 anterior: {old_ms:.2f} ms")
    print(f"cv2.blendLinear com buffers/cache: {new_ms:.2f} ms")
    print(f"cv2.blendLinear com alpha novo: {changing_alpha_ms:.2f} ms")
    print(f"speedup: {old_ms / new_ms:.2f}x")
    print(f"diferenca maxima por canal: {max_difference}")


if __name__ == "__main__":
    main()
