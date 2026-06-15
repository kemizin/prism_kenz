import cv2

from config import (
    WINDOW_NAME,
    BEAUTY_STRENGTH,
    SEGMENTATION_THRESHOLD,
    BACKGROUND_BLUR_KERNEL,
    BACKGROUND_MODE,
    SHOW_FPS_OVERLAY,
)


CONTROL_WINDOW_NAME = "Prism Kenz Controls"


class PreviewWindow:
    def __init__(self):
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.namedWindow(CONTROL_WINDOW_NAME, cv2.WINDOW_NORMAL)

        cv2.createTrackbar(
            "Beauty",
            CONTROL_WINDOW_NAME,
            int(BEAUTY_STRENGTH * 100),
            100,
            self._nothing,
        )

        cv2.createTrackbar(
            "Cut",
            CONTROL_WINDOW_NAME,
            int(SEGMENTATION_THRESHOLD * 100),
            100,
            self._nothing,
        )

        cv2.createTrackbar(
            "BG Blur",
            CONTROL_WINDOW_NAME,
            BACKGROUND_BLUR_KERNEL,
            99,
            self._nothing,
        )

        cv2.createTrackbar(
            "Mode",
            CONTROL_WINDOW_NAME,
            self._mode_to_int(BACKGROUND_MODE),
            2,
            self._nothing,
        )

    def _nothing(self, value):
        pass

    def _mode_to_int(self, mode):
        modes = {
            "none": 0,
            "blur": 1,
            "image": 2,
        }

        return modes.get(mode, 1)

    def _int_to_mode(self, value):
        modes = {
            0: "none",
            1: "blur",
            2: "image",
        }

        return modes.get(value, "blur")

    def get_settings(self):
        beauty = cv2.getTrackbarPos("Beauty", CONTROL_WINDOW_NAME) / 100
        cut = cv2.getTrackbarPos("Cut", CONTROL_WINDOW_NAME) / 100

        blur = cv2.getTrackbarPos("BG Blur", CONTROL_WINDOW_NAME)

        if blur < 1:
            blur = 1

        if blur % 2 == 0:
            blur += 1

        mode_value = cv2.getTrackbarPos("Mode", CONTROL_WINDOW_NAME)
        mode = self._int_to_mode(mode_value)

        return {
            "beauty_strength": beauty,
            "segmentation_threshold": cut,
            "background_blur_kernel": blur,
            "background_mode": mode,
        }

    def show(self, frame, settings=None):
        if settings is not None and SHOW_FPS_OVERLAY:
            preview = frame.copy()
            timings = settings.get("performance_timings", {})
            text = (
                f"Mode: {settings['background_mode']} | "
                f"Beauty: {settings['beauty_strength']:.2f} | "
                f"Cut: {settings['segmentation_threshold']:.2f} | "
                f"Blur: {settings['background_blur_kernel']} | "
                f"FPS: {settings.get('pipeline_fps', 0.0):.1f}"
            )

            cv2.putText(
                preview,
                text,
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.putText(
                preview,
                (
                    "Q sair | N none | B blur | I image | "
                    f"Seg: {timings.get('segmentation', 0.0):.1f} ms | "
                    f"Compose: {timings.get('compose', 0.0):.1f} ms | "
                    f"Total: {timings.get('total', 0.0):.1f} ms"
                ),
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        else:
            preview = frame

        cv2.imshow(WINDOW_NAME, preview)

    def should_close(self):
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            return True

        if key == ord("n"):
            cv2.setTrackbarPos("Mode", CONTROL_WINDOW_NAME, 0)

        if key == ord("b"):
            cv2.setTrackbarPos("Mode", CONTROL_WINDOW_NAME, 1)

        if key == ord("i"):
            cv2.setTrackbarPos("Mode", CONTROL_WINDOW_NAME, 2)

        return False

    def close(self):
        cv2.destroyAllWindows()
