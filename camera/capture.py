from threading import Condition, Thread

import cv2

from config import (
    CAMERA_INDEX,
    WIDTH,
    HEIGHT,
    FPS,
    MIRROR_CAMERA,
    USE_THREADED_CAPTURE,
)


class CameraCapture:
    def __init__(self):
        self.cap = self._open_camera()
        self.threaded = bool(USE_THREADED_CAPTURE)
        self._condition = Condition()
        self._latest_frame = None
        self._latest_sequence = 0
        self._last_read_sequence = 0
        self._stopped = False
        self._failed = False
        self._thread = None

        if self.threaded:
            self._thread = Thread(
                target=self._capture_loop,
                name="camera-capture",
                daemon=True,
            )
            self._thread.start()
            print("[Camera] Captura em thread ativada (latest frame).")

    def _open_camera(self):
        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, FPS)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            cap.release()
            raise RuntimeError("Nao consegui abrir a camera.")

        return cap

    def _capture_loop(self):
        while not self._stopped:
            success, frame = self.cap.read()

            with self._condition:
                if not success:
                    self._failed = True
                    self._condition.notify_all()
                    return

                self._latest_frame = frame
                self._latest_sequence += 1
                self._condition.notify_all()

    def read(self):
        if self.threaded:
            with self._condition:
                has_new_frame = self._condition.wait_for(
                    lambda: (
                        self._latest_sequence > self._last_read_sequence
                        or self._failed
                        or self._stopped
                    ),
                    timeout=2.0,
                )

                if (
                    not has_new_frame
                    or self._failed
                    or self._latest_frame is None
                ):
                    return None

                frame = self._latest_frame
                self._last_read_sequence = self._latest_sequence
        else:
            success, frame = self.cap.read()

            if not success:
                return None

        if MIRROR_CAMERA:
            frame = cv2.flip(frame, 1)

        return frame

    def release(self):
        self._stopped = True

        with self._condition:
            self._condition.notify_all()

        self.cap.release()

        if self._thread is not None:
            self._thread.join(timeout=3.0)
