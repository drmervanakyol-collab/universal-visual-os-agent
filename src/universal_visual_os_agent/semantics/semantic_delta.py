"""Observe-only semantic state delta comparison."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, time
from enum import Enum, StrEnum
from typing import Mapping, Self

from universal_visual_os_agent.geometry.models import NormalizedBBox
from universal_visual_os_agent.semantics.layout import SemanticNode
from universal_visual_os_agent.semantics.state import (
    SemanticCandidate,
    SemanticLayoutRegion,
    SemanticRegionBlock,
    SemanticStateSnapshot,
    SemanticTextBlock,
    SemanticTextRegion,
    SemanticTextStatus,
)


class SemanticDeltaChangeType(StrEnum):
    """Kinds of semantic changes emitted by the comparator."""

    added = "added"
    removed = "removed"
    changed = "changed"


class SemanticDeltaCategory(StrEnum):
    """Stable semantic-delta categories for downstream consumers."""

    layout_tree_node = "layout_tree_node"
    region_block = "region_block"
    layout_region = "layout_region"
    text_region = "text_region"
    text_block = "text_block"
    candidate = "candidate"
    snapshot_metadata = "snapshot_metadata"


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticDeltaChange:
    """A deterministic observe-only change record."""

    category: SemanticDeltaCategory
    change_type: SemanticDeltaChangeType
    item_id: str
    summary: str
    changed_fields: tuple[str, ...] = ()
    before_state: Mapping[str, object] = field(default_factory=dict)
    after_state: Mapping[str, object] = field(default_factory=dict)
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty.")
        if not self.summary:
            raise ValueError("summary must not be empty.")
        if self.change_type is SemanticDeltaChangeType.changed and not self.changed_fields:
            raise ValueError("Changed semantic delta records must include changed_fields.")
        if self.change_type is not SemanticDeltaChangeType.changed and self.changed_fields:
            raise ValueError("Only changed semantic delta records may include changed_fields.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Semantic delta records must remain observe-only and non-actionable.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticDeltaSummary:
    """Summary counts for a semantic delta."""

    total_change_count: int
    added_change_count: int
    removed_change_count: int
    changed_change_count: int
    candidate_score_change_count: int = 0
    category_counts: Mapping[str, int] = field(default_factory=dict)
    before_counts: Mapping[str, int] = field(default_factory=dict)
    after_counts: Mapping[str, int] = field(default_factory=dict)
    changed_categories: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_change_count < 0:
            raise ValueError("total_change_count must not be negative.")
        if self.added_change_count < 0:
            raise ValueError("added_change_count must not be negative.")
        if self.removed_change_count < 0:
            raise ValueError("removed_change_count must not be negative.")
        if self.changed_change_count < 0:
            raise ValueError("changed_change_count must not be negative.")
        if self.candidate_score_change_count < 0:
            raise ValueError("candidate_score_change_count must not be negative.")
        if (
            self.total_change_count
            != self.added_change_count + self.removed_change_count + self.changed_change_count
        ):
            raise ValueError("total_change_count must match the sum of the change-type counts.")


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticDelta:
    """Structured observe-only delta between two semantic snapshots."""

    before_snapshot_id: str
    after_snapshot_id: str
    layout_tree_node_changes: tuple[SemanticDeltaChange, ...] = ()
    region_block_changes: tuple[SemanticDeltaChange, ...] = ()
    layout_region_changes: tuple[SemanticDeltaChange, ...] = ()
    text_region_changes: tuple[SemanticDeltaChange, ...] = ()
    text_block_changes: tuple[SemanticDeltaChange, ...] = ()
    candidate_changes: tuple[SemanticDeltaChange, ...] = ()
    snapshot_metadata_changes: tuple[SemanticDeltaChange, ...] = ()
    summary: SemanticDeltaSummary = field(
        default_factory=lambda: SemanticDeltaSummary(
            total_change_count=0,
            added_change_count=0,
            removed_change_count=0,
            changed_change_count=0,
        )
    )
    signal_status: str = "available"
    observe_only: bool = True
    read_only: bool = True
    non_actionable: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.before_snapshot_id:
            raise ValueError("before_snapshot_id must not be empty.")
        if not self.after_snapshot_id:
            raise ValueError("after_snapshot_id must not be empty.")
        if self.signal_status not in {"available", "partial"}:
            raise ValueError("signal_status must be 'available' or 'partial'.")
        if not self.observe_only or not self.read_only or not self.non_actionable:
            raise ValueError("Semantic delta must remain observe-only and non-actionable.")
        if self.summary.total_change_count != len(self.all_changes):
            raise ValueError("summary.total_change_count must match the total number of change records.")

    @property
    def all_changes(self) -> tuple[SemanticDeltaChange, ...]:
        """Return every change in stable category order."""

        return (
            self.layout_tree_node_changes
            + self.region_block_changes
            + self.layout_region_changes
            + self.text_region_changes
            + self.text_block_changes
            + self.candidate_changes
            + self.snapshot_metadata_changes
        )

    @property
    def candidate_score_changes(self) -> tuple[SemanticDeltaChange, ...]:
        """Return candidate changes that modified confidence/score."""

        return tuple(
            change
            for change in self.candidate_changes
            if "confidence" in change.changed_fields
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class SemanticDeltaResult:
    """Structured result for observe-only semantic-state comparison."""

    comparator_name: str
    success: bool
    delta: SemanticDelta | None = None
    error_code: str | None = None
    error_message: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.comparator_name:
            raise ValueError("comparator_name must not be empty.")
        if self.success and self.delta is None:
            raise ValueError("Successful semantic delta comparison must include delta.")
        if not self.success and self.error_code is None:
            raise ValueError("Failed semantic delta comparison must include error_code.")
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("Successful semantic delta comparison must not include error details.")
        if not self.success and self.delta is not None:
            raise ValueError("Failed semantic delta comparison must not include delta.")

    @classmethod
    def ok(
        cls,
        *,
        comparator_name: str,
        delta: SemanticDelta,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            comparator_name=comparator_name,
            success=True,
            delta=delta,
            details={} if details is None else details,
        )

    @classmethod
    def failure(
        cls,
        *,
        comparator_name: str,
        error_code: str,
        error_message: str,
        details: Mapping[str, object] | None = None,
    ) -> Self:
        return cls(
            comparator_name=comparator_name,
            success=False,
            error_code=error_code,
            error_message=error_message,
            details={} if details is None else details,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class _DeltaArtifacts:
    layout_tree_node_changes: tuple[SemanticDeltaChange, ...]
    region_block_changes: tuple[SemanticDeltaChange, ...]
    layout_region_changes: tuple[SemanticDeltaChange, ...]
    text_region_changes: tuple[SemanticDeltaChange, ...]
    text_block_changes: tuple[SemanticDeltaChange, ...]
    candidate_changes: tuple[SemanticDeltaChange, ...]
    snapshot_metadata_changes: tuple[SemanticDeltaChange, ...]
    missing_before_layout_tree: bool = False
    missing_after_layout_tree: bool = False
    incomplete_layout_region_ids: tuple[str, ...] = ()
    incomplete_text_region_ids: tuple[str, ...] = ()
    incomplete_text_block_ids: tuple[str, ...] = ()
    incomplete_candidate_ids: tuple[str, ...] = ()

    @property
    def signal_status(self) -> str:
        if (
            self.missing_before_layout_tree
            or self.missing_after_layout_tree
            or self.incomplete_layout_region_ids
            or self.incomplete_text_region_ids
            or self.incomplete_text_block_ids
            or self.incomplete_candidate_ids
        ):
            return "partial"
        return "available"

    @property
    def all_changes(self) -> tuple[SemanticDeltaChange, ...]:
        return (
            self.layout_tree_node_changes
            + self.region_block_changes
            + self.layout_region_changes
            + self.text_region_changes
            + self.text_block_changes
            + self.candidate_changes
            + self.snapshot_metadata_changes
        )


class ObserveOnlySemanticDeltaComparator:
    """Compare two semantic snapshots into a deterministic observe-only delta."""

    comparator_name = "ObserveOnlySemanticDeltaComparator"

    def compare(
        self,
        before: SemanticStateSnapshot | None,
        after: SemanticStateSnapshot | None,
    ) -> SemanticDeltaResult:
        if before is None:
            return SemanticDeltaResult.failure(
                comparator_name=self.comparator_name,
                error_code="before_snapshot_unavailable",
                error_message="Semantic delta comparison requires a before snapshot.",
            )
        if after is None:
            return SemanticDeltaResult.failure(
                comparator_name=self.comparator_name,
                error_code="after_snapshot_unavailable",
                error_message="Semantic delta comparison requires an after snapshot.",
            )

        try:
            artifacts = self._build_delta(before, after)
            summary = _build_summary(artifacts, before=before, after=after)
            delta = SemanticDelta(
                before_snapshot_id=before.snapshot_id,
                after_snapshot_id=after.snapshot_id,
                layout_tree_node_changes=artifacts.layout_tree_node_changes,
                region_block_changes=artifacts.region_block_changes,
                layout_region_changes=artifacts.layout_region_changes,
                text_region_changes=artifacts.text_region_changes,
                text_block_changes=artifacts.text_block_changes,
                candidate_changes=artifacts.candidate_changes,
                snapshot_metadata_changes=artifacts.snapshot_metadata_changes,
                summary=summary,
                signal_status=artifacts.signal_status,
                metadata={
                    "observe_only": True,
                    "analysis_only": True,
                    "read_only": True,
                    "non_actionable": True,
                    "sort_order": "category_then_item_id",
                    "missing_before_layout_tree": artifacts.missing_before_layout_tree,
                    "missing_after_layout_tree": artifacts.missing_after_layout_tree,
                    "incomplete_layout_region_ids": artifacts.incomplete_layout_region_ids,
                    "incomplete_text_region_ids": artifacts.incomplete_text_region_ids,
                    "incomplete_text_block_ids": artifacts.incomplete_text_block_ids,
                    "incomplete_candidate_ids": artifacts.incomplete_candidate_ids,
                    "candidate_score_change_ids": tuple(
                        change.item_id
                        for change in artifacts.candidate_changes
                        if "confidence" in change.changed_fields
                    ),
                    "changed_metadata_keys": tuple(
                        change.item_id for change in artifacts.snapshot_metadata_changes
                    ),
                    "changed_category_counts": dict(summary.category_counts),
                    "before_counts": dict(summary.before_counts),
                    "after_counts": dict(summary.after_counts),
                },
            )
        except Exception as exc:  # noqa: BLE001 - comparator must remain failure-safe
            return SemanticDeltaResult.failure(
                comparator_name=self.comparator_name,
                error_code="semantic_delta_exception",
                error_message=str(exc),
                details={"exception_type": type(exc).__name__},
            )

        return SemanticDeltaResult.ok(
            comparator_name=self.comparator_name,
            delta=delta,
            details={
                "total_change_count": summary.total_change_count,
                "signal_status": artifacts.signal_status,
                "candidate_score_change_count": summary.candidate_score_change_count,
            },
        )

    def _build_delta(
        self,
        before: SemanticStateSnapshot,
        after: SemanticStateSnapshot,
    ) -> _DeltaArtifacts:
        if before.layout_tree is not None and after.layout_tree is not None:
            layout_tree_node_changes = _compare_nodes(before.layout_tree.walk(), after.layout_tree.walk())
        else:
            layout_tree_node_changes = ()

        return _DeltaArtifacts(
            layout_tree_node_changes=layout_tree_node_changes,
            region_block_changes=_compare_items(
                SemanticDeltaCategory.region_block,
                before.region_blocks,
                after.region_blocks,
                id_getter=lambda block: block.block_id,
                descriptor_getter=_region_block_state,
                label_getter=lambda block: block.label,
            ),
            layout_region_changes=_compare_items(
                SemanticDeltaCategory.layout_region,
                before.layout_regions,
                after.layout_regions,
                id_getter=lambda region: region.region_id,
                descriptor_getter=_layout_region_state,
                label_getter=lambda region: region.label,
            ),
            text_region_changes=_compare_items(
                SemanticDeltaCategory.text_region,
                before.text_regions,
                after.text_regions,
                id_getter=lambda region: region.region_id,
                descriptor_getter=_text_region_state,
                label_getter=lambda region: region.label,
            ),
            text_block_changes=_compare_items(
                SemanticDeltaCategory.text_block,
                before.text_blocks,
                after.text_blocks,
                id_getter=lambda block: block.text_block_id,
                descriptor_getter=_text_block_state,
                label_getter=lambda block: block.label,
            ),
            candidate_changes=_compare_items(
                SemanticDeltaCategory.candidate,
                before.candidates,
                after.candidates,
                id_getter=lambda candidate: candidate.candidate_id,
                descriptor_getter=_candidate_state,
                label_getter=lambda candidate: candidate.label,
            ),
            snapshot_metadata_changes=_compare_snapshot_metadata(before.metadata, after.metadata),
            missing_before_layout_tree=before.layout_tree is None,
            missing_after_layout_tree=after.layout_tree is None,
            incomplete_layout_region_ids=_incomplete_layout_region_ids(before, after),
            incomplete_text_region_ids=_incomplete_text_region_ids(before, after),
            incomplete_text_block_ids=_incomplete_text_block_ids(before, after),
            incomplete_candidate_ids=_incomplete_candidate_ids(before, after),
        )


def _build_summary(
    artifacts: _DeltaArtifacts,
    *,
    before: SemanticStateSnapshot,
    after: SemanticStateSnapshot,
) -> SemanticDeltaSummary:
    all_changes = artifacts.all_changes
    change_type_counts = Counter(change.change_type.value for change in all_changes)
    category_counts = Counter(change.category.value for change in all_changes)
    candidate_score_change_count = sum(
        "confidence" in change.changed_fields for change in artifacts.candidate_changes
    )
    return SemanticDeltaSummary(
        total_change_count=len(all_changes),
        added_change_count=change_type_counts.get(SemanticDeltaChangeType.added.value, 0),
        removed_change_count=change_type_counts.get(SemanticDeltaChangeType.removed.value, 0),
        changed_change_count=change_type_counts.get(SemanticDeltaChangeType.changed.value, 0),
        candidate_score_change_count=candidate_score_change_count,
        category_counts=dict(sorted(category_counts.items())),
        before_counts=_snapshot_counts(before),
        after_counts=_snapshot_counts(after),
        changed_categories=tuple(sorted(category_counts)),
    )


def _compare_nodes(
    before_nodes: tuple[SemanticNode, ...],
    after_nodes: tuple[SemanticNode, ...],
) -> tuple[SemanticDeltaChange, ...]:
    return _compare_items(
        SemanticDeltaCategory.layout_tree_node,
        before_nodes,
        after_nodes,
        id_getter=lambda node: node.node_id,
        descriptor_getter=_layout_tree_node_state,
        label_getter=lambda node: node.name or node.role,
    )


def _compare_items[T](
    category: SemanticDeltaCategory,
    before_items: tuple[T, ...],
    after_items: tuple[T, ...],
    *,
    id_getter,
    descriptor_getter,
    label_getter,
) -> tuple[SemanticDeltaChange, ...]:
    before_by_id = {id_getter(item): item for item in before_items}
    after_by_id = {id_getter(item): item for item in after_items}
    changes: list[SemanticDeltaChange] = []
    for item_id in sorted(set(before_by_id) | set(after_by_id)):
        before_item = before_by_id.get(item_id)
        after_item = after_by_id.get(item_id)
        before_label = None if before_item is None else label_getter(before_item)
        after_label = None if after_item is None else label_getter(after_item)

        if before_item is None and after_item is not None:
            after_state = descriptor_getter(after_item)
            changes.append(
                SemanticDeltaChange(
                    category=category,
                    change_type=SemanticDeltaChangeType.added,
                    item_id=item_id,
                    summary=f"{_category_label(category)} '{after_label or item_id}' was added.",
                    after_state=after_state,
                    metadata={
                        "before_label": before_label,
                        "after_label": after_label,
                    },
                )
            )
            continue

        if before_item is not None and after_item is None:
            before_state = descriptor_getter(before_item)
            changes.append(
                SemanticDeltaChange(
                    category=category,
                    change_type=SemanticDeltaChangeType.removed,
                    item_id=item_id,
                    summary=f"{_category_label(category)} '{before_label or item_id}' was removed.",
                    before_state=before_state,
                    metadata={
                        "before_label": before_label,
                        "after_label": after_label,
                    },
                )
            )
            continue

        if before_item is None or after_item is None:
            continue

        before_state = descriptor_getter(before_item)
        after_state = descriptor_getter(after_item)
        changed_fields = _changed_fields(before_state, after_state)
        if not changed_fields:
            continue
        change_metadata: dict[str, object] = {
            "before_label": before_label,
            "after_label": after_label,
        }
        if category is SemanticDeltaCategory.candidate and "confidence" in changed_fields:
            before_confidence = before_state.get("confidence")
            after_confidence = after_state.get("confidence")
            if isinstance(before_confidence, float) and isinstance(after_confidence, float):
                change_metadata["score_delta"] = round(after_confidence - before_confidence, 4)
        changes.append(
            SemanticDeltaChange(
                category=category,
                change_type=SemanticDeltaChangeType.changed,
                item_id=item_id,
                summary=f"{_category_label(category)} '{after_label or before_label or item_id}' changed.",
                changed_fields=changed_fields,
                before_state=before_state,
                after_state=after_state,
                metadata=change_metadata,
            )
        )
    return tuple(changes)


def _compare_snapshot_metadata(
    before_metadata: Mapping[str, object],
    after_metadata: Mapping[str, object],
) -> tuple[SemanticDeltaChange, ...]:
    changes: list[SemanticDeltaChange] = []
    for key in sorted(set(before_metadata) | set(after_metadata)):
        before_exists = key in before_metadata
        after_exists = key in after_metadata
        before_value = _freeze_value(before_metadata.get(key)) if before_exists else None
        after_value = _freeze_value(after_metadata.get(key)) if after_exists else None
        if before_exists and after_exists and before_value == after_value:
            continue
        if not before_exists and after_exists:
            changes.append(
                SemanticDeltaChange(
                    category=SemanticDeltaCategory.snapshot_metadata,
                    change_type=SemanticDeltaChangeType.added,
                    item_id=key,
                    summary=f"Snapshot metadata key '{key}' was added.",
                    after_state={"value": after_value},
                )
            )
            continue
        if before_exists and not after_exists:
            changes.append(
                SemanticDeltaChange(
                    category=SemanticDeltaCategory.snapshot_metadata,
                    change_type=SemanticDeltaChangeType.removed,
                    item_id=key,
                    summary=f"Snapshot metadata key '{key}' was removed.",
                    before_state={"value": before_value},
                )
            )
            continue
        changes.append(
            SemanticDeltaChange(
                category=SemanticDeltaCategory.snapshot_metadata,
                change_type=SemanticDeltaChangeType.changed,
                item_id=key,
                summary=f"Snapshot metadata key '{key}' changed.",
                changed_fields=("value",),
                before_state={"value": before_value},
                after_state={"value": after_value},
            )
        )
    return tuple(changes)


def _region_block_state(block: SemanticRegionBlock) -> Mapping[str, object]:
    return _dataclass_state(block, id_field="block_id")


def _layout_region_state(region: SemanticLayoutRegion) -> Mapping[str, object]:
    return _dataclass_state(region, id_field="region_id")


def _text_region_state(region: SemanticTextRegion) -> Mapping[str, object]:
    return _dataclass_state(region, id_field="region_id")


def _text_block_state(block: SemanticTextBlock) -> Mapping[str, object]:
    return _dataclass_state(block, id_field="text_block_id")


def _candidate_state(candidate: SemanticCandidate) -> Mapping[str, object]:
    return {
        **_dataclass_state(candidate, id_field="candidate_id"),
        "actionable": candidate.actionable,
    }


def _layout_tree_node_state(node: SemanticNode) -> Mapping[str, object]:
    return {
        "role": node.role,
        "name": node.name,
        "bounds": _freeze_value(node.bounds),
        "visible": node.visible,
        "enabled": node.enabled,
        "child_node_ids": tuple(child.node_id for child in node.children),
        "attributes": _freeze_value(node.attributes),
    }


def _dataclass_state(item: object, *, id_field: str) -> Mapping[str, object]:
    state: dict[str, object] = {}
    for dataclass_field in fields(item):
        if dataclass_field.name == id_field:
            continue
        state[dataclass_field.name] = _freeze_value(getattr(item, dataclass_field.name))
    return state


def _freeze_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            dataclass_field.name: _freeze_value(getattr(value, dataclass_field.name))
            for dataclass_field in fields(value)
        }
    if isinstance(value, NormalizedBBox):
        return {
            "left": value.left,
            "top": value.top,
            "width": value.width,
            "height": value.height,
        }
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Mapping):
        frozen_mapping: dict[str, object] = {}
        for key in sorted(value, key=str):
            frozen_mapping[str(key)] = _freeze_value(value[key])
        return frozen_mapping
    if isinstance(value, tuple | list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _changed_fields(
    before_state: Mapping[str, object],
    after_state: Mapping[str, object],
) -> tuple[str, ...]:
    ordered_fields = tuple(before_state) + tuple(
        key for key in after_state if key not in before_state
    )
    return tuple(
        field_name
        for field_name in ordered_fields
        if before_state.get(field_name) != after_state.get(field_name)
    )


def _category_label(category: SemanticDeltaCategory) -> str:
    return category.value.replace("_", " ")


def _snapshot_counts(snapshot: SemanticStateSnapshot) -> Mapping[str, int]:
    layout_tree_node_count = 0
    if snapshot.layout_tree is not None:
        layout_tree_node_count = len(snapshot.layout_tree.walk())
    return {
        SemanticDeltaCategory.layout_tree_node.value: layout_tree_node_count,
        SemanticDeltaCategory.region_block.value: len(snapshot.region_blocks),
        SemanticDeltaCategory.layout_region.value: len(snapshot.layout_regions),
        SemanticDeltaCategory.text_region.value: len(snapshot.text_regions),
        SemanticDeltaCategory.text_block.value: len(snapshot.text_blocks),
        SemanticDeltaCategory.candidate.value: len(snapshot.candidates),
        SemanticDeltaCategory.snapshot_metadata.value: len(snapshot.metadata),
    }


def _incomplete_layout_region_ids(
    before: SemanticStateSnapshot,
    after: SemanticStateSnapshot,
) -> tuple[str, ...]:
    incomplete_ids = {
        region.region_id
        for region in before.layout_regions + after.layout_regions
        if region.semantic_role is None
    }
    return tuple(sorted(incomplete_ids))


def _incomplete_text_region_ids(
    before: SemanticStateSnapshot,
    after: SemanticStateSnapshot,
) -> tuple[str, ...]:
    incomplete_ids = {
        region.region_id
        for region in before.text_regions + after.text_regions
        if region.status is SemanticTextStatus.extracted and not _has_text(region.extracted_text)
    }
    return tuple(sorted(incomplete_ids))


def _incomplete_text_block_ids(
    before: SemanticStateSnapshot,
    after: SemanticStateSnapshot,
) -> tuple[str, ...]:
    incomplete_ids = {
        block.text_block_id
        for block in before.text_blocks + after.text_blocks
        if not _has_text(block.extracted_text)
    }
    return tuple(sorted(incomplete_ids))


def _incomplete_candidate_ids(
    before: SemanticStateSnapshot,
    after: SemanticStateSnapshot,
) -> tuple[str, ...]:
    incomplete_ids = {
        candidate.candidate_id
        for candidate in before.candidates + after.candidates
        if candidate.metadata.get("semantic_origin") == "candidate_generation"
        and (
            candidate.candidate_class is None
            or candidate.confidence is None
            or candidate.source_type is None
            or candidate.selection_risk_level is None
            or not candidate.source_of_truth_priority
            or not candidate.provenance
            or not isinstance(candidate.metadata.get("source_layout_region_id"), str)
            or not candidate.metadata.get("source_layout_region_id")
        )
    }
    return tuple(sorted(incomplete_ids))


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())
