import cv2
import numpy as np

from config import (
    VIRTUAL_CAMERA_ENABLED,
    VIRTUAL_CAMERA_FPS,
    VIRTUAL_CAMERA_BACKEND,
    VIRTUAL_CAMERA_FMT,
)


class VirtualCameraOutput:
    def __init__(self):
        self.enabled = bool(VIRTUAL_CAMERA_ENABLED)
        self.camera = None
        self.pyvirtualcam = None
        self.pixel_format = None
        self._convert_bgr_to_rgb = False
        self._rgb_buffer = None
        self._frame_size = None
        self._failure_shown = False

        if not self.enabled:
            print("[VirtualCamera] Desativada pela configuracao.")
            return

        try:
            import pyvirtualcam
            from pyvirtualcam.camera import BACKENDS

            self.pyvirtualcam = pyvirtualcam

            if (
                VIRTUAL_CAMERA_BACKEND is not None
                and VIRTUAL_CAMERA_BACKEND not in BACKENDS
            ):
                available = ", ".join(BACKENDS) or "nenhum"
                self._disable_with_warning(
                    f"Backend '{VIRTUAL_CAMERA_BACKEND}' desconhecido. "
                    f"Disponiveis: {available}."
                )
        except Exception as exc:
            self._disable_with_warning(
                f"Nao foi possivel importar pyvirtualcam: {exc}"
            )

    def _resolve_pixel_format(self, format_name):
        format_name = str(format_name).upper()

        if format_name not in ("BGR", "RGB"):
            raise ValueError(
                f"Formato virtual desconhecido: {format_name}. "
                "Use BGR ou RGB."
            )

        pixel_format = getattr(self.pyvirtualcam.PixelFormat, format_name, None)

        if pixel_format is None:
            raise ValueError(
                f"Formato virtual desconhecido: {format_name}. "
                "Use BGR ou RGB."
            )

        return pixel_format

    def _open(self, frame):
        height, width = frame.shape[:2]
        requested_format = str(VIRTUAL_CAMERA_FMT).upper()

        try:
            pixel_format = self._resolve_pixel_format(requested_format)
            camera = self.pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=float(VIRTUAL_CAMERA_FPS),
                fmt=pixel_format,
                backend=VIRTUAL_CAMERA_BACKEND,
                print_fps=False,
            )
            self._convert_bgr_to_rgb = requested_format == "RGB"
        except Exception as first_error:
            if requested_format != "BGR":
                raise

            try:
                pixel_format = self.pyvirtualcam.PixelFormat.RGB
                camera = self.pyvirtualcam.Camera(
                    width=width,
                    height=height,
                    fps=float(VIRTUAL_CAMERA_FPS),
                    fmt=pixel_format,
                    backend=VIRTUAL_CAMERA_BACKEND,
                    print_fps=False,
                )
                self._convert_bgr_to_rgb = True
                print(
                    "[VirtualCamera] BGR nao foi aceito pelo backend; "
                    "usando fallback RGB."
                )
            except Exception as fallback_error:
                raise RuntimeError(
                    f"BGR falhou: {first_error}\n"
                    f"Fallback RGB falhou: {fallback_error}"
                ) from fallback_error

        self.camera = camera
        self.pixel_format = pixel_format
        self._frame_size = (width, height)
        self._rgb_buffer = (
            np.empty_like(frame) if self._convert_bgr_to_rgb else None
        )

        print("[VirtualCamera] Camera virtual iniciada.")
        print(f"[VirtualCamera] Dispositivo: {self.camera.device}")
        print(f"[VirtualCamera] Backend: {self.camera.backend}")
        print(f"[VirtualCamera] Resolucao: {width}x{height}")
        print(f"[VirtualCamera] FPS: {float(VIRTUAL_CAMERA_FPS):g}")
        print(f"[VirtualCamera] Formato de entrada: {self.pixel_format.name}")

    def _prepare_frame(self, frame):
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)

        if self._convert_bgr_to_rgb:
            if self._rgb_buffer is None or self._rgb_buffer.shape != frame.shape:
                self._rgb_buffer = np.empty_like(frame)

            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB, dst=self._rgb_buffer)
            return self._rgb_buffer

        if not frame.flags.c_contiguous:
            return np.ascontiguousarray(frame)

        return frame

    def _disable_with_warning(self, message):
        self.enabled = False

        if self.camera is not None:
            try:
                self.camera.close()
            except Exception:
                pass
            self.camera = None

        if not self._failure_shown:
            print(f"[VirtualCamera] AVISO: {message}")
            print(
                "[VirtualCamera] Preview continuara funcionando. "
                "Instale/ative OBS Virtual Camera ou Unity Capture no Windows."
            )
            self._failure_shown = True

    def send(self, frame):
        if not self.enabled or self.pyvirtualcam is None:
            return

        try:
            height, width = frame.shape[:2]
            frame_size = (width, height)

            if self.camera is None:
                self._open(frame)
            elif frame_size != self._frame_size:
                self.camera.close()
                self.camera = None
                self._open(frame)

            self.camera.send(self._prepare_frame(frame))
        except Exception as exc:
            self._disable_with_warning(f"Falha ao enviar frame: {exc}")

    def close(self):
        self.enabled = False

        if self.camera is not None:
            try:
                self.camera.close()
            except Exception as exc:
                if not self._failure_shown:
                    print(f"[VirtualCamera] AVISO ao fechar: {exc}")
            finally:
                self.camera = None

        self._rgb_buffer = None
        self._frame_size = None
