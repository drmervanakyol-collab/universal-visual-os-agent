"""RapidOCR backend integration for observe-only text extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor
from typing import Any, Callable, Protocol, cast

import numpy

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.perception import FrameImagePayload, FramePixelFormat
from universal_visual_os_agent.semantics.ocr import (
    TextExtractionRegionRequest,
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionResponseStatus,
)
from universal_visual_os_agent.semantics.state import (
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)


class _RapidOcrEngine(Protocol):
    """Callable interface for the RapidOCR engine."""

    def __call__(
        self,
        img_content: object,
        use_det: bool | None = None,
        use_cls: bool | None = None,
        use_rec: bool | None = None,
        return_word_box: bool | None = None,
        return_single_char_box: bool | None = None,
        text_score: float | None = None,
        box_thresh: float | None = None,
        unclip_ratio: float | None = None,
    ) -> object:
        """Run OCR over the provided image content."""


@dataclass(slots=True, frozen=True, kw_only=True)
class _CropRect:
    left_px: int
    top_px: int
    right_px: int
    bottom_px: int

    @property
    def width_px(self) -> int:
        return self.right_px - self.left_px

    @property
    def height_px(self) -> int:
        return self.bottom_px - self.top_px


@dataclass(slots=True, kw_only=True)
class RapidOcrTextExtractionBackend:
    """Run observe-only OCR using the Python-native RapidOCR backend."""

    backend_name: str = "rapidocr_onnxruntime"
    text_score: float = 0.5
    engine_factory: Callable[[], _RapidOcrEngine] | None = None
    _engine: _RapidOcrEngine | None = field(init=False, default=None, repr=False)

    def run(self, request: TextExtractionRequest) -> TextExtractionResponse:
        """Execute OCR over each prepared region and return a structured response."""

        try:
            image = self._payload_to_bgr_array(request.payload)
        except Exception as exc:  # noqa: BLE001 - backend must fail safely
            return TextExtractionResponse(
                status=TextExtractionResponseStatus.failed,
                backend_name=self.backend_name,
                error_code="ocr_input_unavailable",
                error_message=str(exc),
                details={"frame_id": request.frame_id, "exception_type": type(exc).__name__},
            )

        try:
            engine = self._get_engine()
        except Exception as exc:  # noqa: BLE001 - backend must fail safely
            return TextExtractionResponse(
                status=TextExtractionResponseStatus.failed,
                backend_name=self.backend_name,
                error_code="ocr_backend_unavailable",
                error_message=str(exc),
                details={"frame_id": request.frame_id, "exception_type": type(exc).__name__},
            )

        text_regions: list[SemanticTextRegion] = []
        text_blocks: list[SemanticTextBlock] = []
        extracted_region_count = 0
        empty_region_count = 0

        for region in request.regions:
            crop_rect = _crop_rect_from_bounds(region.bounds, request.payload.width, request.payload.height)
            if crop_rect is None:
                text_regions.append(_build_empty_region(region, backend_name=self.backend_name))
                empty_region_count += 1
                continue

            crop = image[crop_rect.top_px : crop_rect.bottom_px, crop_rect.left_px : crop_rect.right_px]
            try:
                raw_output = engine(crop, text_score=self.text_score)
            except Exception as exc:  # noqa: BLE001 - backend must fail safely
                return TextExtractionResponse(
                    status=TextExtractionResponseStatus.failed,
                    backend_name=self.backend_name,
                    error_code="ocr_backend_runtime_error",
                    error_message=str(exc),
                    details={
                        "frame_id": request.frame_id,
                        "region_id": region.region_id,
                        "exception_type": type(exc).__name__,
                    },
                )

            try:
                region_result, region_blocks = self._map_region_output(
                    request=request,
                    region=region,
                    crop_rect=crop_rect,
                    raw_output=raw_output,
                )
            except ValueError as exc:
                return TextExtractionResponse(
                    status=TextExtractionResponseStatus.failed,
                    backend_name=self.backend_name,
                    error_code="ocr_backend_malformed_output",
                    error_message=str(exc),
                    details={"frame_id": request.frame_id, "region_id": region.region_id},
                )

            if region_result.status is SemanticTextStatus.extracted:
                extracted_region_count += 1
            else:
                empty_region_count += 1
            text_regions.append(region_result)
            text_blocks.extend(region_blocks)

        return TextExtractionResponse(
            status=TextExtractionResponseStatus.completed,
            backend_name=self.backend_name,
            text_regions=tuple(text_regions),
            text_blocks=tuple(text_blocks),
            details={
                "frame_id": request.frame_id,
                "region_count": len(request.regions),
                "extracted_region_count": extracted_region_count,
                "empty_region_count": empty_region_count,
                "text_block_count": len(text_blocks),
                "observe_only": True,
            },
        )

    def _get_engine(self) -> _RapidOcrEngine:
        if self._engine is not None:
            return self._engine
        engine = self.engine_factory() if self.engine_factory is not None else self._build_default_engine()
        self._engine = engine
        return engine

    def _build_default_engine(self) -> _RapidOcrEngine:
        from rapidocr import RapidOCR

        return cast(_RapidOcrEngine, RapidOCR())

    def _payload_to_bgr_array(self, payload: FrameImagePayload) -> numpy.ndarray[Any, Any]:
        if payload.pixel_format is not FramePixelFormat.bgra_8888:
            raise ValueError(
                f"Unsupported payload pixel format for OCR: {payload.pixel_format.value!r}."
            )
        if payload.row_stride_bytes % payload.pixel_format.bytes_per_pixel != 0:
            raise ValueError("Payload row stride is not aligned to pixel width.")

        row_stride_pixels = payload.row_stride_bytes // payload.pixel_format.bytes_per_pixel
        bgra = numpy.frombuffer(payload.image_bytes, dtype=numpy.uint8).reshape(
            payload.height,
            row_stride_pixels,
            payload.pixel_format.bytes_per_pixel,
        )
        return numpy.ascontiguousarray(bgra[:, : payload.width, :3])

    def _map_region_output(
        self,
        *,
        request: TextExtractionRequest,
        region: TextExtractionRegionRequest,
        crop_rect: _CropRect,
        raw_output: object,
    ) -> tuple[SemanticTextRegion, tuple[SemanticTextBlock, ...]]:
        boxes = _coerce_sequence(getattr(raw_output, "boxes", None))
        texts = _coerce_sequence(getattr(raw_output, "txts", None))
        scores = _coerce_sequence(getattr(raw_output, "scores", None))
        if not (len(boxes) == len(texts) == len(scores)):
            raise ValueError("RapidOCR output lengths for boxes, txts, and scores do not match.")

        if not texts:
            return _build_empty_region(region, backend_name=self.backend_name), ()

        text_blocks: list[SemanticTextBlock] = []
        recognized_text: list[str] = []
        score_values: list[float] = []

        for index, (box, text, score) in enumerate(zip(boxes, texts, scores, strict=True), start=1):
            if not isinstance(text, str):
                raise ValueError("RapidOCR returned a non-string text entry.")
            normalized_text = text.strip()
            if not normalized_text:
                continue

            score_value = float(score)
            block_bounds = _normalized_bbox_from_box(
                box=box,
                crop_rect=crop_rect,
                image_width=request.payload.width,
                image_height=request.payload.height,
            )
            text_blocks.append(
                SemanticTextBlock(
                    text_block_id=f"{region.region_id}:line:{index}",
                    region_id=region.region_id,
                    label=f"{region.label} Line {index}",
                    bounds=block_bounds,
                    enabled=False,
                    extracted_text=normalized_text,
                    confidence=score_value,
                    metadata={
                        **dict(region.metadata),
                        "text_source": "rapidocr",
                        "ocr_backend_name": self.backend_name,
                        "line_index": index - 1,
                        "observe_only": True,
                        "analysis_only": True,
                    },
                )
            )
            recognized_text.append(normalized_text)
            score_values.append(score_value)

        if not recognized_text:
            return _build_empty_region(region, backend_name=self.backend_name), ()

        region_text = "\n".join(recognized_text)
        average_score = sum(score_values) / len(score_values)
        region_result = SemanticTextRegion(
            region_id=region.region_id,
            label=region.label,
            bounds=region.bounds,
            node_id=region.node_id,
            block_id=region.block_id,
            role=region.role,
            status=SemanticTextStatus.extracted,
            enabled=False,
            extracted_text=region_text,
            confidence=average_score,
            metadata={
                **dict(region.metadata),
                "text_source": "rapidocr",
                "ocr_backend_name": self.backend_name,
                "ocr_line_count": len(text_blocks),
                "observe_only": True,
                "analysis_only": True,
            },
        )
        return region_result, tuple(text_blocks)


def _build_empty_region(
    region: TextExtractionRegionRequest,
    *,
    backend_name: str,
) -> SemanticTextRegion:
    return SemanticTextRegion(
        region_id=region.region_id,
        label=region.label,
        bounds=region.bounds,
        node_id=region.node_id,
        block_id=region.block_id,
        role=region.role,
        status=SemanticTextStatus.unavailable,
        enabled=False,
        extracted_text=None,
        confidence=None,
        metadata={
            **dict(region.metadata),
            "text_source": "rapidocr",
            "ocr_backend_name": backend_name,
            "ocr_empty": True,
            "observe_only": True,
            "analysis_only": True,
        },
    )


def _crop_rect_from_bounds(
    bounds: NormalizedBBox,
    image_width: int,
    image_height: int,
) -> _CropRect | None:
    left_px = max(0, min(image_width, floor(bounds.left * image_width)))
    top_px = max(0, min(image_height, floor(bounds.top * image_height)))
    right_px = max(left_px, min(image_width, ceil((bounds.left + bounds.width) * image_width)))
    bottom_px = max(top_px, min(image_height, ceil((bounds.top + bounds.height) * image_height)))

    if right_px <= left_px or bottom_px <= top_px:
        return None
    return _CropRect(
        left_px=left_px,
        top_px=top_px,
        right_px=right_px,
        bottom_px=bottom_px,
    )


def _normalized_bbox_from_box(
    *,
    box: object,
    crop_rect: _CropRect,
    image_width: int,
    image_height: int,
) -> NormalizedBBox:
    try:
        points = tuple(tuple(float(value) for value in point) for point in cast(object, box))
    except TypeError as exc:
        raise ValueError("RapidOCR returned a non-iterable box.") from exc
    if not points:
        raise ValueError("RapidOCR returned an empty box.")

    x_values = tuple(point[0] for point in points)
    y_values = tuple(point[1] for point in points)
    left_px = _clamp_float(crop_rect.left_px + min(x_values), 0.0, float(image_width))
    top_px = _clamp_float(crop_rect.top_px + min(y_values), 0.0, float(image_height))
    right_px = _clamp_float(crop_rect.left_px + max(x_values), 0.0, float(image_width))
    bottom_px = _clamp_float(crop_rect.top_px + max(y_values), 0.0, float(image_height))

    if right_px <= left_px:
        right_px = min(float(image_width), left_px + (1.0 / image_width))
    if bottom_px <= top_px:
        bottom_px = min(float(image_height), top_px + (1.0 / image_height))

    return NormalizedBBox(
        left=left_px / image_width,
        top=top_px / image_height,
        width=(right_px - left_px) / image_width,
        height=(bottom_px - top_px) / image_height,
    )


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _coerce_sequence(value: object) -> tuple[object, ...]:
    if value is None:
        return ()
    return tuple(cast(object, value))
