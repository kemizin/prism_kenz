from time import perf_counter


PIPELINE_STAGES = (
    "capture",
    "color",
    "beauty",
    "segmentation",
    "alpha_resize",
    "background_prepare",
    "alpha_prepare",
    "compose_math",
    "compose_total",
    "compose",
    "preview",
    "virtual_camera_send",
    "total",
)


class PipelineProfiler:
    def __init__(self, log_interval_seconds=2.0, show_logs=True):
        self.log_interval_seconds = max(0.1, float(log_interval_seconds))
        self.show_logs = bool(show_logs)
        self._last_log_at = perf_counter()
        self._sums = {stage: 0.0 for stage in PIPELINE_STAGES}
        self._ema = {stage: 0.0 for stage in PIPELINE_STAGES}
        self._frame_count = 0
        self._has_ema = False

    def record_frame(self, timings):
        for stage in PIPELINE_STAGES:
            value = max(0.0, float(timings.get(stage, 0.0)))
            self._sums[stage] += value

            if self._has_ema:
                self._ema[stage] = self._ema[stage] * 0.90 + value * 0.10
            else:
                self._ema[stage] = value

        self._has_ema = True
        self._frame_count += 1

    def snapshot(self):
        total_ms = self._ema["total"]
        return {
            "fps": 1000.0 / total_ms if total_ms > 0 else 0.0,
            "timings": self._ema.copy(),
        }

    def maybe_log(self):
        now = perf_counter()
        if now - self._last_log_at < self.log_interval_seconds:
            return

        if self.show_logs and self._frame_count > 0:
            averages = {
                stage: self._sums[stage] / self._frame_count
                for stage in PIPELINE_STAGES
            }
            total_ms = averages["total"]
            fps = 1000.0 / total_ms if total_ms > 0 else 0.0
            stages = " | ".join(
                f"{stage}: {averages[stage]:.1f} ms"
                for stage in PIPELINE_STAGES
                if stage != "total"
            )
            print(
                f"[Performance] FPS: {fps:.1f} | {stages} | "
                f"total: {total_ms:.1f} ms"
            )

        self._sums = {stage: 0.0 for stage in PIPELINE_STAGES}
        self._frame_count = 0
        self._last_log_at = now
