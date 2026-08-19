"""Auto-detect course subjects from Second Brain documents.

Analyzes document titles and content to identify academic subjects,
then tags them with `course:<subject>` tags for the course derivation pipeline.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models import KbDocument, KbDocumentTag, KbTag
from app.services.kb import utcnow

# Common academic subject patterns (case-insensitive)
SUBJECT_PATTERNS = [
    # Computer Science
    r"\b(?:operating\s+systems?|os)\b",
    r"\b(?:data\s+structures?|dsa?)\b",
    r"\b(?:algorithms?)\b",
    r"\b(?:machine\s+learning|ml)\b",
    r"\b(?:deep\s+learning|dl)\b",
    r"\b(?:artificial\s+intelligence|ai)\b",
    r"\b(?:computer\s+networks?|cn)\b",
    r"\b(?:database\s+systems?|dbms?)\b",
    r"\b(?:compiler\s+design)\b",
    r"\b(?:computer\s+organization|coa)\b",
    r"\b(?:digital\s+logic|dl)\b",
    r"\b(?:theory\s+of\s+computation|toc)\b",
    r"\b(?:discrete\s+math(?:ematics)?)\b",
    r"\b(?:programming|coding)\b",
    r"\b(?:software\s+engineering|se)\b",
    r"\b(?:web\s+development)\b",
    r"\b(?:cyber\s*security|info\s*sec)\b",
    r"\b(?:cloud\s+computing)\b",
    r"\b(?:big\s+data)\b",
    r"\b(?:natural\s+language\s+processing|nlp)\b",
    r"\b(?:computer\s+vision|cv)\b",
    r"\b(?:data\s+science)\b",
    r"\b(?:blockchain)\b",
    r"\b(?:iot|internet\s+of\s+things)\b",
    
    # Mathematics
    r"\b(?:calculus|calc)\b",
    r"\b(?:linear\s+algebra|la)\b",
    r"\b(?:probability)\b",
    r"\b(?:statistics|stats)\b",
    r"\b(?:differential\s+equations?|ode)\b",
    r"\b(?:numerical\s+methods?)\b",
    r"\b(?:graph\s+theory)\b",
    r"\b(?:combinatorics)\b",
    r"\b(?:number\s+theory)\b",
    
    # Physics
    r"\b(?:quantum\s+mechanics?|qm)\b",
    r"\b(?:thermodynamics?|thermo)\b",
    r"\b(?:electromagnetism|em)\b",
    r"\b(?:mechanics?|classical\s+mechanics?)\b",
    r"\b(?:optics?)\b",
    r"\b(?:modern\s+physics?)\b",
    
    # Electronics
    r"\b(?:digital\s+electronics?)\b",
    r"\b(?:analog\s+electronics?)\b",
    r"\b(?:signals?\s+and\s+systems?|s&s)\b",
    r"\b(?:vlsi)\b",
    r"\b(?:embedded\s+systems?)\b",
    r"\b(?:control\s+systems?)\b",
    r"\b(?:microprocessors?)\b",
    r"\b(?:microcontrollers?)\b",
    
    # Business/Economics
    r"\b(?:economics?|microeconomics|macroeconomics)\b",
    r"\b(?:finance)\b",
    r"\b(?:accounting)\b",
    r"\b(?:marketing)\b",
    r"\b(?:management)\b",
    r"\b(?:business)\b",
    
    # Languages
    r"\b(?:english)\b",
    r"\b(?:hindi)\b",
    r"\b(?:french)\b",
    r"\b(?:german)\b",
    r"\b(?:spanish)\b",
    
    # Other
    r"\b(?:chemistry|chem)\b",
    r"\b(?:biology|bio)\b",
    r"\b(?:environmental\s+science|evs)\b",
    r"\b(?:ethics)\b",
    r"\b(?:psychology)\b",
    r"\b(?:sociology)\b",
]

# Subject name normalization
SUBJECT_ALIASES = {
    "os": "Operating Systems",
    "operating system": "Operating Systems",
    "operating systems": "Operating Systems",
    "dsa": "Data Structures and Algorithms",
    "data structure": "Data Structures and Algorithms",
    "data structures": "Data Structures and Algorithms",
    "data structures and algorithms": "Data Structures and Algorithms",
    "algorithm": "Algorithms",
    "algorithms": "Algorithms",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "cn": "Computer Networks",
    "computer network": "Computer Networks",
    "computer networks": "Computer Networks",
    "dbms": "Database Management Systems",
    "database": "Database Management Systems",
    "database systems": "Database Management Systems",
    "toc": "Theory of Computation",
    "theory of computation": "Theory of Computation",
    "se": "Software Engineering",
    "software engineering": "Software Engineering",
    "la": "Linear Algebra",
    "linear algebra": "Linear Algebra",
    "calc": "Calculus",
    "calculus": "Calculus",
    "stats": "Statistics",
    "statistics": "Statistics",
    "qm": "Quantum Mechanics",
    "quantum mechanics": "Quantum Mechanics",
    "thermo": "Thermodynamics",
    "thermodynamics": "Thermodynamics",
    "em": "Electromagnetism",
    "electromagnetism": "Electromagnetism",
    "nlp": "Natural Language Processing",
    "natural language processing": "Natural Language Processing",
    "cv": "Computer Vision",
    "computer vision": "Computer Vision",
    "coa": "Computer Organization and Architecture",
    "computer organization": "Computer Organization and Architecture",
    "vlsi": "VLSI Design",
    "iot": "Internet of Things",
    "internet of things": "Internet of Things",
    "chem": "Chemistry",
    "chemistry": "Chemistry",
    "bio": "Biology",
    "biology": "Biology",
}


def _normalize_subject(name: str) -> str:
    """Normalize subject name to a consistent format."""
    name_lower = name.lower().strip()
    # Check aliases first
    if name_lower in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[name_lower]
    # Title case the result
    return name.title()


def _extract_subject_from_title(title: str) -> list[str]:
    """Extract potential subject names from a document title."""
    subjects = []
    title_lower = (title or "").lower()
    
    for pattern in SUBJECT_PATTERNS:
        matches = re.finditer(pattern, title_lower, re.IGNORECASE)
        for match in matches:
            matched_text = match.group(0).strip()
            normalized = _normalize_subject(matched_text)
            if normalized and normalized not in subjects:
                subjects.append(normalized)
    
    return subjects


def _extract_subject_from_content(content: str, max_chars: int = 5000) -> list[str]:
    """Extract potential subject names from document content (first N chars)."""
    subjects = []
    # Only analyze first portion of content for efficiency
    text = (content or "")[:max_chars].lower()
    
    # Count pattern occurrences
    pattern_counts: Counter[str] = Counter()
    
    for pattern in SUBJECT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            normalized = _normalize_subject(match)
            if normalized:
                pattern_counts[normalized] += len(matches)
    
    # Return subjects that appear at least twice (to reduce false positives)
    for subject, count in pattern_counts.most_common(20):
        if count >= 2:
            subjects.append(subject)
    
    return subjects


def detect_subjects_from_document(doc: KbDocument) -> list[str]:
    """Detect course subjects from a single document."""
    subjects = []
    
    # Check title first (higher weight)
    title_subjects = _extract_subject_from_title(doc.title or "")
    subjects.extend(title_subjects)
    
    # Check extracted_text or frontmatter_json for content (lower weight, but still useful)
    content_text = doc.extracted_text or ""
    # Also check frontmatter if available
    if doc.frontmatter_json:
        try:
            import json
            frontmatter = json.loads(doc.frontmatter_json)
            if isinstance(frontmatter, dict):
                # Combine title, tags, and description from frontmatter
                fm_text = " ".join([
                    frontmatter.get("title", ""),
                    frontmatter.get("description", ""),
                    " ".join(frontmatter.get("tags", [])) if isinstance(frontmatter.get("tags"), list) else "",
                ])
                content_text = f"{content_text} {fm_text}"
        except (json.JSONDecodeError, TypeError):
            pass
    
    content_subjects = _extract_subject_from_content(content_text)
    for subj in content_subjects:
        if subj not in subjects:
            subjects.append(subj)
    
    return subjects


def auto_tag_documents(
    db: Session,
    user_id: int,
    *,
    dry_run: bool = False,
    limit: int = 0,
) -> dict[str, Any]:
    """Auto-detect and tag documents with course: tags.
    
    Args:
        db: Database session
        user_id: User ID
        dry_run: If True, only analyze without creating tags
        limit: Max documents to process (0 = all)
    
    Returns:
        Summary of detection results
    """
    # Get all documents
    query = db.query(KbDocument).filter(KbDocument.user_id == user_id)
    if limit > 0:
        query = query.limit(limit)
    
    docs = query.all()
    total_docs = len(docs)
    
    # Track results
    tagged_count = 0
    skipped_count = 0
    subject_counts: Counter[str] = Counter()
    already_tagged: set[int] = set()
    
    # Get existing course tags
    existing_course_tags = {
        tag.name: tag.id
        for tag in db.query(KbTag).filter(
            KbTag.user_id == user_id,
            KbTag.name.like("course:%")
        ).all()
    }
    
    # Get documents already tagged with course: tags
    for doc_tag in (
        db.query(KbDocumentTag.document_id)
        .join(KbTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(
            KbTag.user_id == user_id,
            KbTag.name.like("course:%")
        )
        .all()
    ):
        already_tagged.add(doc_tag.document_id)
    
    for doc in docs:
        # Skip if already tagged with course: tags
        if doc.id in already_tagged:
            skipped_count += 1
            continue
        
        # Detect subjects
        subjects = detect_subjects_from_document(doc)
        
        if not subjects:
            continue
        
        # Use the most likely subject (first one from title has priority)
        primary_subject = subjects[0]
        subject_counts[primary_subject] += 1
        
        if not dry_run:
            # Create or get the course tag
            tag_name = f"course:{primary_subject}"
            
            if tag_name not in existing_course_tags:
                # Create new tag
                tag = KbTag(
                    user_id=user_id,
                    name=tag_name,
                    kind="auto",
                )
                db.add(tag)
                db.flush()
                existing_course_tags[tag_name] = tag.id
            
            tag_id = existing_course_tags[tag_name]
            
            # Check if document already has this tag
            existing_doc_tag = (
                db.query(KbDocumentTag)
                .filter(
                    KbDocumentTag.document_id == doc.id,
                    KbDocumentTag.tag_id == tag_id,
                )
                .first()
            )
            
            if not existing_doc_tag:
                # Add the tag
                doc_tag = KbDocumentTag(
                    user_id=user_id,
                    document_id=doc.id,
                    tag_id=tag_id,
                    provenance="rule",
                )
                db.add(doc_tag)
                tagged_count += 1
        
        # Mark document as dirty for reindexing
        if not dry_run and subjects:
            doc.embedding_dirty = True
    
    if not dry_run:
        db.commit()
    
    return {
        "total_documents": total_docs,
        "tagged": tagged_count,
        "skipped_already_tagged": skipped_count,
        "subjects_detected": len(subject_counts),
        "top_subjects": subject_counts.most_common(20),
        "dry_run": dry_run,
    }


def get_detection_preview(
    db: Session,
    user_id: int,
    sample_size: int = 100,
) -> dict[str, Any]:
    """Preview what subjects would be detected from documents.
    
    Returns a sample of documents and their detected subjects without
    creating any tags.
    """
    # Get a sample of documents
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id)
        .order_by(KbDocument.id)
        .limit(sample_size)
        .all()
    )
    
    # Detect subjects
    subject_counts: Counter[str] = Counter()
    samples = []
    
    for doc in docs:
        subjects = detect_subjects_from_document(doc)
        if subjects:
            subject_counts[subjects[0]] += 1
            samples.append({
                "id": doc.id,
                "title": doc.title[:80] if doc.title else "(no title)",
                "subjects": subjects[:3],  # Top 3
            })
    
    return {
        "sample_size": len(docs),
        "documents_with_subjects": len(samples),
        "subjects_detected": len(subject_counts),
        "top_subjects": subject_counts.most_common(20),
        "samples": samples[:20],  # Show up to 20 examples
    }
