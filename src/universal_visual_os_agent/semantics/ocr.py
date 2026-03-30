"""OCR/text extraction scaffolding on top of the observe-only semantic pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Mapping, Self

from universal_visual_os_agent.geometry import NormalizedBBox
from universal_visual_os_agent.perception import FrameImagePayload
from universal_visual_os_agent.semantics.building import SemanticStateBuildResult
from universal_visual_os_agent.semantics.ocr_enrichment import apply_ocr_semantic_enrichment
from universal_visual_os_agent.semantics.preparation import (
    SemanticExtractionInput,
    SemanticExtractionPreparationResult,
)
from universal_visual_os_agent.semantics.state import (
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)

if TYPE_CHECKING:
    from universal_visual_os_agent.semantics.interfaces import TextExtractionBackend


@dataclass(slots=True, frozen=True, kw_only=True)
class TextExtractionRegionRequest:
    """One OCR-ready region request derived from semantic scaffold state."""

    region_id: str
    label: str
    bounds: NormalizedBBox
    node_id: str | None = None
    block_id: str | None = None
    role: str = "text_region"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.region_id:
            raise ValueError("region_id must not be empty.")
        if not self.label:
            raise ValueError("label must not be empty.")
        if not self.role:
            raise ValueError("role must not be empty.")


@dataclass(slots=True, frozen=True, kw_only=True)
class TextExtractionRequest:
    """Prepared OCR/text extraction request for a future backend."""

    frame_id: str
    snapshot_id: str
    captured_at: datetime
    payload: FrameImagePayload
    backend_name: str
    capture_target: str
    regions: tuple[TextExtractionRegionRequest, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id must not be empty.")
        if not self.snapshot_id:
            raise ValueError("snapshot_id must not be empty.")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")
        if not self.backend_name:
            raise ValueError("backend_name must not be empty.")
        if not self.capture_target:
            raise ValueError("capture_target must not be empty.")
        if not self.regions:
            raise ValueError("regions must not be empty.")


class TextExtractionResponseStatus(StrEnum):
    """Status values for future OCR backend responses."""

    pending = "pending"
    completed = "completed"
    failed = "failed"


@dataclass(slots=True, frozen=True, kw_only=True)
class TextExtractionResponse:
    """Structured OCR/text extraction response scaffold for future backends."""

    status: TextExtractionResponseStatus
    backend_name: str | None = None
    text_regions: tuple[SemanticTextRegion, ...] = ()
    text_blocks: tuple[SemanticTextBlock, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status is TextExtractionResponseStatus.failed and self.error_code is None:
            raise ValueError("Failed text extraction responses must include error_code.")
        if self.status is not TextExtractionResponseStatus.failed and self.error_code is not None:
            raise ValueError("Non-failed text extraction responses must not include error_code.")
        if self.error_message is not None and self.error_code is None:
            raise ValueError("error_message requires error_code.")


@dataclass(slots=True, frozen=True, kw_only=True)
class TextExtractionResult:
    """Structured result for observe-only OCR/text extraction scaffolding."""

    adapter_name: str
    success: bool
    request: TextExtractionRequest | None = None
    response: TextExtractionResponse | None = None
    text_regions: tuple[SemanticTextRegion, ...] = ()
    text_blocks: tuple[SemanticTextBlock, ...] = ()
    enriched_snapshot: SemanticStateSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.adapter_name:
            raise ValueError("adapter_name must not be empty.")
        if self.success and (self.request is None or self.response is None):
            raise ValueError("Successful extraction results must include request and response.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed extraction results must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful extraction results must not include error details.")
        if not self.success and self.enriched_snapshot is not None:
            raise ValueError("Failed extraction results must not include enriched_snapshot.")

    @classmethod
    def ok(
        cls,
        *,
        adapter_name: str,
        request: TextExtractionRequest,
        response: TextExtractionResponse,
        text_regions: tuple[SemanticTextRegion, ...],
        text_blocks: tuple[SemanticTextBlock, ...],
        enriched_snapshot: SemanticStateSnapshot,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a successful text extraction scaffolding result."""

        return cls(
            adapter_name=adapter_name,
            success=True,
            request=request,
            response=response,
            text_regions=text_regions,
            text_blocks=text_blocks,
            enriched_snapshot=enriched_snapshot,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        adapter_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a failed text extraction scaffolding result."""

        return cls(
            adapter_name=adapter_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


class PreparedSemanticTextExtractionAdapter:
    """Derive OCR-ready request scaffolding and text placeholders from semantic state."""

    adapter_name = "PreparedSemanticTextExtractionAdapter"

    def __init__(self, *, text_backend: TextExtractionBackend | None = None) -> None:
        self._text_backend = text_backend

    def extract(
        self,
        preparation_result: SemanticExtractionPreparationResult,
        state_result: SemanticStateBuildResult,
    ) -> TextExtractionResult:
        """Return OCR/text extraction scaffolding or a safe structured failure."""

        if not preparation_result.success:
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="preparation_failed",
                error_message=preparation_result.error_message or "Semantic preparation did not succeed.",
                details={
                    "preparation_error_code": preparation_result.error_code,
                    "preparation_adapter_name": preparation_result.adapter_name,
                },
            )

        if not state_result.success:
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="state_build_failed",
                error_message=state_result.error_message or "Semantic state building did not succeed.",
                details={
                    "state_error_code": state_result.error_code,
                    "state_builder_name": state_result.builder_name,
                },
            )

        extraction_input = preparation_result.extraction_input
        snapshot = state_result.snapshot
        if extraction_input is None:
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="extraction_input_unavailable",
                error_message="Semantic preparation did not provide extraction input.",
                details={"preparation_adapter_name": preparation_result.adapter_name},
            )
        if snapshot is None:
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="semantic_snapshot_unavailable",
                error_message="Semantic state building did not provide a snapshot.",
                details={"state_builder_name": state_result.builder_name},
            )
        if not isinstance(extraction_input.payload, FrameImagePayload):
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="payload_unavailable",
                error_message="Text extraction requires a prepared image payload.",
                details={"frame_id": extraction_input.frame_id},
            )
        if not snapshot.region_blocks:
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="text_regions_unavailable",
                error_message="Semantic state does not contain OCR-ready region blocks.",
                details={"snapshot_id": snapshot.snapshot_id},
            )

        try:
            request = self._build_request(extraction_input, snapshot)
            response = self._run_backend_or_placeholder(request)
            if response.status is TextExtractionResponseStatus.failed:
                return TextExtractionResult.failure(
                    adapter_name=self.adapter_name,
                    error_code=response.error_code or "ocr_backend_failed",
                    error_message=response.error_message or "OCR backend execution failed.",
                    details={
                        "frame_id": extraction_input.frame_id,
                        "ocr_backend_name": response.backend_name,
                        **dict(response.details),
                    },
                )
            text_regions = self._sanitize_text_regions(request, response)
            text_blocks = self._sanitize_text_blocks(text_regions, response)
            enriched_snapshot = apply_ocr_semantic_enrichment(
                snapshot,
                text_regions=text_regions,
                text_blocks=text_blocks,
                adapter_name=self.adapter_name,
                backend_name=response.backend_name,
                response_status=response.status.value,
            )
        except Exception as exc:  # noqa: BLE001 - adapter must remain failure-safe
            return TextExtractionResult.failure(
                adapter_name=self.adapter_name,
                error_code="text_extraction_exception",
                error_message=str(exc),
                details={
                    "frame_id": extraction_input.frame_id,
                    "exception_type": type(exc).__name__,
                },
            )

        return TextExtractionResult.ok(
            adapter_name=self.adapter_name,
            request=request,
            response=response,
            text_regions=text_regions,
            text_blocks=text_blocks,
            enriched_snapshot=enriched_snapshot,
            details={
                "frame_id": extraction_input.frame_id,
                "region_count": len(text_regions),
                "text_block_count": len(text_blocks),
                "snapshot_id": enriched_snapshot.snapshot_id,
                "ocr_backend_name": response.backend_name,
            },
        )

    def _build_request(
        self,
        extraction_input: SemanticExtractionInput,
        snapshot: SemanticStateSnapshot,
    ) -> TextExtractionRequest:
        request_regions = tuple(
            TextExtractionRegionRequest(
                region_id=f"{block.block_id}:ocr",
                label=block.label,
                bounds=block.bounds,
                node_id=block.node_id,
                block_id=block.block_id,
                role="text_region",
                metadata={
                    **dict(block.metadata),
                    "observe_only": True,
                    "analysis_only": True,
                    "ocr_scaffold": True,
                    "frame_id": extraction_input.frame_id,
                },
            )
            for block in snapshot.region_blocks
        )
        return TextExtractionRequest(
            frame_id=extraction_input.frame_id,
            snapshot_id=snapshot.snapshot_id,
            captured_at=extraction_input.captured_at,
            payload=extraction_input.payload,
            backend_name=extraction_input.backend_name,
            capture_target=extraction_input.capture_target,
            regions=request_regions,
            metadata={
                "capture_provider_name": extraction_input.capture_provider_name,
                "display_count": extraction_input.display_count,
                "observe_only": True,
                "ocr_backend_name": None,
            },
        )

    def _build_text_regions(
        self,
        request: TextExtractionRequest,
    ) -> tuple[SemanticTextRegion, ...]:
        return tuple(
            SemanticTextRegion(
                region_id=region.region_id,
                label=region.label,
                bounds=region.bounds,
                node_id=region.node_id,
                block_id=region.block_id,
                role=region.role,
                status=SemanticTextStatus.pending,
                enabled=False,
                extracted_text=None,
                confidence=None,
                metadata={
                    **dict(region.metadata),
                    "text_source": "placeholder",
                    "ocr_backend_name": None,
                    "observe_only": True,
                    "analysis_only": True,
                },
            )
            for region in request.regions
        )

    def _build_text_blocks(
        self,
        text_regions: tuple[SemanticTextRegion, ...],
    ) -> tuple[SemanticTextBlock, ...]:
        return tuple(
            SemanticTextBlock(
                text_block_id=f"{region.region_id}:block",
                region_id=region.region_id,
                label=f"{region.label} Block",
                bounds=region.bounds,
                enabled=False,
                extracted_text=None,
                confidence=None,
                metadata={
                    **dict(region.metadata),
                    "text_source": "placeholder",
                    "ocr_backend_name": None,
                    "observe_only": True,
                    "analysis_only": True,
                },
            )
            for region in text_regions
        )

    def _run_backend_or_placeholder(
        self,
        request: TextExtractionRequest,
    ) -> TextExtractionResponse:
        if self._text_backend is None:
            text_regions = self._build_text_regions(request)
            text_blocks = self._build_text_blocks(text_regions)
            return TextExtractionResponse(
                status=TextExtractionResponseStatus.pending,
                text_regions=text_regions,
                text_blocks=text_blocks,
                details={
                    "observe_only": True,
                    "ocr_backend_name": None,
                    "placeholder_response": True,
                },
            )
        try:
            return self._text_backend.run(request)
        except Exception as exc:  # noqa: BLE001 - backend exceptions must stay structured
            return TextExtractionResponse(
                status=TextExtractionResponseStatus.failed,
                backend_name=getattr(self._text_backend, "backend_name", None),
                error_code="text_extraction_backend_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

    def _sanitize_text_regions(
        self,
        request: TextExtractionRequest,
        response: TextExtractionResponse,
    ) -> tuple[SemanticTextRegion, ...]:
        if len(response.text_regions) != len(request.regions):
            raise ValueError("OCR backend returned an unexpected number of text regions.")
        request_region_ids = {region.region_id for region in request.regions}
        response_region_ids = {region.region_id for region in response.text_regions}
        if response_region_ids != request_region_ids:
            raise ValueError("OCR backend returned mismatched text region identifiers.")

        return tuple(
            replace(
                region,
                enabled=False,
                metadata={
                    **dict(region.metadata),
                    "ocr_backend_name": response.backend_name,
                    "observe_only": True,
                    "analysis_only": True,
                },
            )
            for region in response.text_regions
        )

    def _sanitize_text_blocks(
        self,
        text_regions: tuple[SemanticTextRegion, ...],
        response: TextExtractionResponse,
    ) -> tuple[SemanticTextBlock, ...]:
        valid_region_ids = {region.region_id for region in text_regions}
        text_blocks: list[SemanticTextBlock] = []
        for block in response.text_blocks:
            if block.region_id not in valid_region_ids:
                raise ValueError("OCR backend returned a text block for an unknown region.")
            text_blocks.append(
                replace(
                    block,
                    enabled=False,
                    metadata={
                        **dict(block.metadata),
                        "ocr_backend_name": response.backend_name,
                        "observe_only": True,
                        "analysis_only": True,
                    },
                )
            )
        return tuple(text_blocks)
