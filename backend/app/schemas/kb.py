"""Pydantic schemas for the Second Brain Knowledge Core (Phase 1)."""

from __future__ import annotations

import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Sources (Idea 2)
# ---------------------------------------------------------------------------

class KbSourceCreate(BaseModel):
    name: str
    source_type: str = "local_dir"
    root_path: str
    enabled: bool = True
    # Phase 9 (Idea 89): git | drive | clip | local | none
    sync_type: str = "none"
    # ``local`` adapter: external vault dir mirrored into the source root.
    sync_source_path: str | None = None


class KbSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    root_path: str | None = None
    enabled: bool | None = None
    sync_type: str | None = None
    sync_source_path: str | None = None


class KbSourceResponse(BaseModel):
    id: int
    user_id: int
    name: str
    source_type: str
    root_path: str | None
    enabled: bool
    last_scanned_at: datetime | None
    files_seen: int
    files_added: int
    files_changed: int
    files_removed: int
    created_at: datetime | None
    document_count: int = 0
    # Phase 9 (Idea 89): external sync adapter + per-source cursor.
    sync_type: str = "none"
    sync_cursor: dict | None = Field(default=None, validation_alias="sync_cursor_json")
    # ``local`` adapter external vault dir (Copy Recent Notes source).
    sync_source_path: str | None = None

    @field_validator("sync_cursor", mode="before")
    @classmethod
    def _sync_cursor(cls, v):
        return _parse_json(v)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Documents (Ideas 5, 7, 8, 9)
# ---------------------------------------------------------------------------

def _parse_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return None
    return v


class KbDocumentResponse(BaseModel):
    id: int
    user_id: int
    source_id: int | None
    path_rel: str | None
    title: str | None
    doc_type: str
    content_hash: str | None
    char_count: int
    frontmatter: dict | None = Field(default=None, validation_alias="frontmatter_json")
    outline: list | None = Field(default=None, validation_alias="outline_json")
    metadata: dict | None = Field(default=None, validation_alias="metadata_json")
    ocr_used: bool
    needs_ocr: bool
    status: str
    doc_date: date | None
    # Phase 2 metadata fields (Idea 13)
    author: str | None = None
    source_url: str | None = None
    language: str | None = None
    reading_time_seconds: int | None = None
    # Phase 2 dirty flags (Idea 20) — exposed so the frontend can show
    # "needs reindex" state and so tooling can report stale documents.
    embedding_dirty: bool = True
    graph_dirty: bool = True
    tags_dirty: bool = True
    # Phase 4 note-quality cache (Idea 39, phrase 84).
    quality_score: int | None = None
    quality_detail: dict | None = Field(default=None, validation_alias="quality_detail")
    # Phase 9 (Idea 86): summary staleness flag for the nightly summary job.
    summary_dirty: bool = False
    created_at: datetime | None
    updated_at: datetime | None
    indexed_at: datetime | None
    chunk_count: int = 0

    @field_validator("quality_detail", mode="before")
    @classmethod
    def _quality_detail(cls, v):
        return _parse_json(v)

    @field_validator("frontmatter", "metadata", mode="before")
    @classmethod
    def _obj(cls, v):
        return _parse_json(v)

    @field_validator("outline", mode="before")
    @classmethod
    def _list(cls, v):
        return _parse_json(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class KbDocumentListResponse(BaseModel):
    items: list[KbDocumentResponse]
    total: int
    page: int
    page_size: int


class KbChunkResponse(BaseModel):
    id: int
    document_id: int
    seq: int
    content: str
    char_start: int
    char_end: int
    heading_path: str | None
    token_estimate: int

    model_config = ConfigDict(from_attributes=True)


class KbUploadResult(BaseModel):
    document: KbDocumentResponse | None = None
    deduped: bool = False
    duplicate_of_id: int | None = None


# ---------------------------------------------------------------------------
# Versions (Idea 9)
# ---------------------------------------------------------------------------

class KbVersionResponse(BaseModel):
    id: int
    document_id: int
    version_seq: int
    content_hash: str | None
    snapshot_text: str | None
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class KbDiffResponse(BaseModel):
    from_version: int
    to_version: int
    changed: bool
    diff: str


class KbRestoreResponse(BaseModel):
    document: KbDocumentResponse
    new_version_seq: int


# ---------------------------------------------------------------------------
# Jobs (Idea 10)
# ---------------------------------------------------------------------------

class KbJobResponse(BaseModel):
    id: int
    user_id: int
    job_type: str
    status: str
    total_items: int
    processed_items: int
    error: str | None
    ref_type: str | None
    ref_id: int | None
    created_at: datetime | None
    finished_at: datetime | None
    # Scan/ingest summary so async jobs can surface stats via polling.
    summary: dict | None = Field(default=None, validation_alias="summary_json")

    @field_validator("summary", mode="before")
    @classmethod
    def _summary(cls, v):
        return _parse_json(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class KbScanResult(BaseModel):
    job: KbJobResponse
    # Populated when the job ran synchronously (hermetic/small runs).
    summary: dict | None = None


# ---------------------------------------------------------------------------
# Papers (Idea 5)
# ---------------------------------------------------------------------------

class KbPaperImport(BaseModel):
    arxiv_id: str
    source_id: int | None = None


class KbPaperImportResult(BaseModel):
    document: KbDocumentResponse
    metadata_fetched: bool


# ---------------------------------------------------------------------------
# Phase 2 — Embeddings, Indexing & Knowledge Graph
# ---------------------------------------------------------------------------

# ---- Embeddings (Idea 11) ----
class KbEmbeddingResponse(BaseModel):
    id: int
    chunk_id: int
    model: str
    dim: int
    content_hash: str | None
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ---- Stats (Idea 12) ----
class KbStatsResponse(BaseModel):
    document_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    embedded_documents: int = 0
    tag_count: int = 0
    concept_count: int = 0
    edge_count: int = 0
    duplicate_count: int = 0
    total_tokens: int = 0
    # Per-user daily budget meters (cost guards, Idea 15 / Idea 19).
    embeddings_today: int = 0
    embeddings_limit: int = 0
    inferences_today: int = 0
    inference_limit: int = 0
    # Stale flags exposed for the re-index tooling (Idea 20).
    dirty_documents: int = 0
    # Audit defect #67: the vault's activity window (first/last indexed note),
    # used to derive the analytics range from real data.
    oldest_document_date: str | None = None
    newest_document_date: str | None = None


# ---- Metadata enrichment (Idea 13) ----
class KbMetadataUpdate(BaseModel):
    author: str | None = None
    source_url: str | None = None
    language: str | None = None
    reading_time_seconds: int | None = Field(default=None, ge=0)
    # Metadata dict is merged into the stored metadata_json (null clears it).
    metadata: dict | None = None
    # Which fields came from a trusted source (llm | rule | manual | unknown).
    provenance: dict | None = None


class KbMetadataProposal(BaseModel):
    author: str | None = None
    source_url: str | None = None
    language: str | None = None
    reading_time_seconds: int | None = None
    confidence: float = 0.0
    reason: str | None = None


# ---- Auto-tagging (Idea 14) ----
class KbTagSuggestion(BaseModel):
    tag_id: int
    name: str
    provenance: str  # rule | ai | manual
    confidence: float = 0.0


class KbDocumentTagsResponse(BaseModel):
    document_id: int
    # Suggestion list (rule + ai). Manual/applied tags are excluded here —
    # they surface in ``applied`` below.
    tags: list[KbTagSuggestion]
    # Tags already linked to the document (rule + manual) — the "applied"
    # chips in the tag editor.
    applied: list[KbTagSuggestion] = Field(default_factory=list)


class KbApplyTags(BaseModel):
    document_id: int
    # tag_ids from the suggestion list to promote to manual (authoritative).
    tag_ids: list[int] = Field(default_factory=list)


class KbRejectTags(BaseModel):
    document_id: int
    tag_ids: list[int] = Field(default_factory=list)


class KbTagSummary(BaseModel):
    id: int
    name: str
    count: int
    last_used: datetime | None


# ---- Concepts (Idea 17) ----
class KbConceptResponse(BaseModel):
    id: int
    canonical_name: str
    definition: str | None = None
    aliases: list[str] | None = None
    document_count: int = 0
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("aliases", mode="before")
    @classmethod
    def _aliases(cls, v):
        if isinstance(v, str):
            parsed = _parse_json(v)
            return parsed or []
        return v or []


# ---- Knowledge graph (Idea 16/18) ----
class KbGraphNode(BaseModel):
    id: str  # "doc:<id>" or "concept:<id>"
    kind: str  # document | concept
    label: str
    doc_type: str | None = None
    status: str | None = None
    degree: int = 0


class KbGraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0
    provenance: str = "auto"


class KbGraphResponse(BaseModel):
    nodes: list[KbGraphNode]
    edges: list[KbGraphEdge]
    truncated: bool = False
    total_nodes: int = 0
    total_edges: int = 0


# ---- Related documents (Idea 19) ----
class KbRelatedResponse(BaseModel):
    document_id: int
    related: list[dict]  # [{id, title, relation, weight}]
    method: str  # embedding | shared_concept | rule


# ---- Near-duplicates (Idea 9/Phase-2 G9) ----
class KbDuplicateItem(BaseModel):
    document_id: int
    duplicate_of_id: int
    similarity: float
    method: str  # embedding | minhash
    created_at: datetime | None


class KbMergeRequest(BaseModel):
    keep_id: int  # canonical document to keep
    merge_ids: list[int] = Field(default_factory=list)  # duplicates to merge/archive


# ---------------------------------------------------------------------------
# Phase 3 — Search & Retrieval (Ideas 21–25)
# ---------------------------------------------------------------------------

class KbSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    mode: str | None = "hybrid"  # keyword | semantic | hybrid
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class KbSearchItem(BaseModel):
    chunk_id: int
    document_id: int
    seq: int
    title: str
    snippet: str = ""
    score: float = 0.0
    mode: str = "hybrid"
    source_path: str | None = None
    heading_path: str | None = None
    doc_type: str = ""
    doc_date: str | None = None
    char_start: int = 0
    char_end: int = 0
    sources: list[str] | None = None


class KbSearchResponse(BaseModel):
    items: list[KbSearchItem]
    total: int
    page: int
    page_size: int
    mode: str
    original_query: str
    expanded_query: str


# ---- Capture XP (Idea 69, defect #79 fix) ----

class KbCaptureXpRequest(BaseModel):
    amount: int = Field(..., ge=0, le=10000)
    kind: str | None = None
    trigger_key: str | None = None


class KbCaptureXpResponse(BaseModel):
    xp_awarded: int
