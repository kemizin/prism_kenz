from contextlib import nullcontext
from time import perf_counter

import cv2
import numpy as np
import torch

from config import (
    SEGMENTATION_BACKEND,
    RVM_MODEL,
    RVM_DEVICE,
    RVM_DOWNSAMPLE_RATIO,
    RVM_INFERENCE_WIDTH,
    RVM_INFERENCE_HEIGHT,
    RVM_PROCESS_EVERY_N_FRAMES,
    RVM_TORCH_THREADS,
    USE_FP16,
    MASK_BLUR_KERNEL,
)


class PersonSegmenter:
    def __init__(self):
        self.backend = SEGMENTATION_BACKEND.lower()

        if self.backend == "rvm":
            self._init_rvm()
        else:
            raise ValueError(f"Backend de segmentacao nao suportado: {self.backend}")

    def _init_rvm(self):
        if RVM_TORCH_THREADS and RVM_TORCH_THREADS > 0:
            torch.set_num_threads(int(RVM_TORCH_THREADS))

        requested_device = str(RVM_DEVICE).lower()
        cuda_available = torch.cuda.is_available()

        print("[RVM] Diagnostico do PyTorch")
        print(f"[RVM] PyTorch: {torch.__version__}")
        print(f"[RVM] torch.version.cuda: {torch.version.cuda}")
        print(f"[RVM] torch.cuda.is_available(): {cuda_available}")

        if cuda_available:
            print(f"[RVM] GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("[RVM] GPU: sem CUDA disponivel")

        if requested_device == "auto":
            self.device = torch.device("cuda" if cuda_available else "cpu")
        elif requested_device.startswith("cuda") and not cuda_available:
            print(
                f"[RVM] AVISO: RVM_DEVICE='{RVM_DEVICE}', mas CUDA nao esta "
                "disponivel. Usando CPU."
            )
            self.device = torch.device("cpu")
        else:
            self.device = torch.device(RVM_DEVICE)

        print(f"[RVM] Carregando modelo '{RVM_MODEL}' em: {self.device}")
        self.model = torch.hub.load(
            "PeterL1n/RobustVideoMatting",
            RVM_MODEL,
            pretrained=True,
            trust_repo=True,
        )
        self.model = self.model.eval().to(self.device)
        self.device = next(self.model.parameters()).device
        self.use_fp16 = bool(USE_FP16 and self.device.type == "cuda")

        if self.device.type == "cuda":
            torch.backends.cudnn.benchmark = True

        print(f"[RVM] Device real do modelo: {self.device}")
        print(
            f"[RVM] Resolucao de inferencia: "
            f"{RVM_INFERENCE_WIDTH}x{RVM_INFERENCE_HEIGHT}, "
            f"downsample_ratio={RVM_DOWNSAMPLE_RATIO}"
        )
        print(
            f"[RVM] FP16 autocast: {self.use_fp16} | "
            f"processa a cada {max(1, int(RVM_PROCESS_EVERY_N_FRAMES))} frame(s)"
        )

        self.rec = [None, None, None, None]
        self._rec_input_size = None
        self._cached_alpha = None
        self._cached_alpha_size = None
        self._frame_index = 0
        self.last_segmentation_ms = 0.0
        self.last_alpha_resize_ms = 0.0
        self.last_inference_ms = 0.0
        self.last_mask_reused = False
        self._first_inference_completed = False

    def get_person_mask(self, frame):
        if self.backend != "rvm":
            return None

        original_size = (frame.shape[1], frame.shape[0])
        process_every = max(1, int(RVM_PROCESS_EVERY_N_FRAMES))
        should_process = (
            self._cached_alpha is None
            or self._cached_alpha_size != original_size
            or self._frame_index % process_every == 0
        )
        self._frame_index += 1

        if not should_process:
            self.last_segmentation_ms = 0.0
            self.last_alpha_resize_ms = 0.0
            self.last_inference_ms = 0.0
            self.last_mask_reused = True
            return self._cached_alpha

        alpha = self._get_rvm_alpha(frame)
        self._cached_alpha = alpha
        self._cached_alpha_size = original_size
        self.last_mask_reused = False
        return alpha

    def _autocast_context(self):
        if self.use_fp16:
            return torch.autocast("cuda", dtype=torch.float16)
        return nullcontext()

    def _get_rvm_alpha(self, frame):
        segmentation_started_at = perf_counter()
        original_height, original_width = frame.shape[:2]
        inference_width = int(RVM_INFERENCE_WIDTH)
        inference_height = int(RVM_INFERENCE_HEIGHT)

        if inference_width <= 0 or inference_height <= 0:
            inference_width = original_width
            inference_height = original_height

        inference_size = (inference_width, inference_height)

        if (original_width, original_height) != inference_size:
            inference_frame = cv2.resize(
                frame,
                inference_size,
                interpolation=cv2.INTER_AREA,
            )
        else:
            inference_frame = frame

        if self._rec_input_size != inference_size:
            self.rec = [None, None, None, None]
            self._rec_input_size = inference_size

        rgb_frame = cv2.cvtColor(inference_frame, cv2.COLOR_BGR2RGB)
        src = torch.from_numpy(rgb_frame)
        src = src.permute(2, 0, 1).unsqueeze(0)
        src = src.to(self.device, dtype=torch.float32).div_(255.0)

        if not self._first_inference_completed:
            print("[RVM] Iniciando primeira inferencia...")

        try:
            with torch.inference_mode():
                with self._autocast_context():
                    _, pha, *self.rec = self.model(
                        src,
                        *self.rec,
                        downsample_ratio=RVM_DOWNSAMPLE_RATIO,
                    )
        except (RuntimeError, TypeError) as exc:
            if not self.use_fp16:
                raise

            print(f"[RVM] FP16 falhou ({exc}). Tentando novamente em FP32.")
            self.use_fp16 = False
            self.rec = [None, None, None, None]

            with torch.inference_mode():
                _, pha, *self.rec = self.model(
                    src,
                    *self.rec,
                    downsample_ratio=RVM_DOWNSAMPLE_RATIO,
                )

        alpha = pha[0, 0].float().cpu().numpy()
        self.last_segmentation_ms = (
            perf_counter() - segmentation_started_at
        ) * 1000.0

        resize_started_at = perf_counter()
        if alpha.shape != (original_height, original_width):
            alpha = cv2.resize(
                alpha,
                (original_width, original_height),
                interpolation=cv2.INTER_LINEAR,
            )

        np.clip(alpha, 0.0, 1.0, out=alpha)

        if MASK_BLUR_KERNEL > 1:
            kernel = int(MASK_BLUR_KERNEL)
            if kernel % 2 == 0:
                kernel += 1
            alpha = cv2.GaussianBlur(alpha, (kernel, kernel), 0)

        self.last_alpha_resize_ms = (
            perf_counter() - resize_started_at
        ) * 1000.0
        self.last_inference_ms = (
            self.last_segmentation_ms + self.last_alpha_resize_ms
        )

        if not self._first_inference_completed:
            self._first_inference_completed = True
            print(
                f"[RVM] Primeira inferencia concluida: "
                f"{self.last_inference_ms:.1f} ms"
            )

        return alpha

    def reset(self):
        if self.backend == "rvm":
            self.rec = [None, None, None, None]
            self._rec_input_size = None
            self._cached_alpha = None
            self._cached_alpha_size = None
            self._frame_index = 0

    def close(self):
        self.reset()
