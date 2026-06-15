import faulthandler
from time import perf_counter

from camera.capture import CameraCapture
from camera.virtual_output import VirtualCameraOutput
from config import FPS_LOG_INTERVAL_SECONDS, SHOW_PERFORMANCE_LOGS
from effects.background import apply_background, get_last_background_timings
from effects.beauty import apply_beauty_filter
from effects.color import apply_color_correction
from performance import PipelineProfiler
from ui.app import PreviewWindow


faulthandler.enable()


def _elapsed_ms(started_at):
    return (perf_counter() - started_at) * 1000.0


def process_frame(frame, settings, timings=None):
    if timings is None:
        timings = {}

    started_at = perf_counter()
    frame = apply_color_correction(frame)
    timings["color"] = _elapsed_ms(started_at)

    started_at = perf_counter()
    frame = apply_beauty_filter(
        frame,
        strength=settings["beauty_strength"],
        enabled=settings["beauty_strength"] > 0,
    )
    timings["beauty"] = _elapsed_ms(started_at)

    frame = apply_background(
        frame,
        mode=settings["background_mode"],
        threshold=settings["segmentation_threshold"],
        blur_kernel=settings["background_blur_kernel"],
        enabled=settings["background_mode"] != "none",
    )
    timings.update(get_last_background_timings())
    return frame


def main():
    camera = CameraCapture()
    preview = PreviewWindow()
    virtual_camera = VirtualCameraOutput()
    profiler = PipelineProfiler(
        log_interval_seconds=FPS_LOG_INTERVAL_SECONDS,
        show_logs=SHOW_PERFORMANCE_LOGS,
    )

    try:
        while True:
            total_started_at = perf_counter()
            timings = {}

            started_at = perf_counter()
            frame = camera.read()
            timings["capture"] = _elapsed_ms(started_at)

            if frame is None:
                print("Frame vazio. Camera falhou.")
                break

            settings = preview.get_settings()
            output = process_frame(frame, settings, timings)

            snapshot = profiler.snapshot()
            settings["pipeline_fps"] = snapshot["fps"]
            settings["performance_timings"] = snapshot["timings"]
            settings["segmentation_ms"] = snapshot["timings"]["segmentation"]

            started_at = perf_counter()
            preview.show(output, settings)
            should_close = preview.should_close()
            timings["preview"] = _elapsed_ms(started_at)

            started_at = perf_counter()
            virtual_camera.send(output)
            timings["virtual_camera_send"] = _elapsed_ms(started_at)

            timings["total"] = _elapsed_ms(total_started_at)
            profiler.record_frame(timings)
            profiler.maybe_log()

            if should_close:
                break

    finally:
        camera.release()
        virtual_camera.close()
        preview.close()


if __name__ == "__main__":
    main()
