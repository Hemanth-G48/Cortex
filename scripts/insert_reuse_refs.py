#!/usr/bin/env python3
"""Insert a 'Reference repos' section into each SECOND_BRAIN_PHASE*_100_PHRASE_PLAN.md.

The section is inserted immediately before '## Group 1 —' and links each idea to
reusable components in the cloned reference repos (from REPOS_REUSE_ANALYSIS.md).
"""
import re
import sys
from pathlib import Path

ROOT = Path("/home/hemanth/productivity_app")

# (idea_number, idea_title, repo_list) for each phase — repo list derived from REPOS_REUSE_ANALYSIS.md
PHASES = {
    1: {
        "title": "Second Brain Foundation & Ingestion",
        "ideas": [
            (1, "Knowledge Core data model", "basic-memory (entity/relation SQLAlchemy schema) · siyuan (block/attribute model) · dendron (note hierarchy) · engram (SQLite store)"),
            (2, "Knowledge source registry", "glean (RSS sources) · khoj (content-type configs) · obsidian-wiki (session_sources.py)"),
            (3, "Folder watcher & file scanning", "obsidian-wiki (sync.py) · glean · claude-obsidian (vault_ops.py) · obsidian-second-brain (adapters/)"),
            (4, "Markdown parser — frontmatter & wikilinks", "basic-memory (markdown/) · foam (foam-core) · dendron (engine-server) · llm_wiki (commands/fs.ts) · claude-obsidian (obsidian-markdown skill)"),
            (5, "PDF & research-paper ingestion", "khoj (processor/content/pdf) · syllabus-agent (PyPDF2 extract) · memora (processing.py) · PAIDEIA (vision_ocr.py) · recalla (flashcards/pdf route)"),
            (6, "OCR for scanned documents", "PAIDEIA (vision_ocr.py + tesseract checks in doctor.py)"),
            (7, "Semantic (heading-aware) chunking", "khoj (processor/content) · reor (ChunkSizeSettings.tsx) · decodingai (chunk_embed_load.py) · glean"),
            (8, "Content-hash deduplication", "hashcards (content-addressable cards) · engram (content hash) · basic-memory (mtime/size columns)"),
            (9, "Version history & diff", "orbit (store-fs/store-web) · engram (store) · llm_wiki (file-history-panel.tsx)"),
            (10, "Ingestion job queue & status", "glean (worker) · khoj (background jobs) · decodingai (pipelines/)"),
        ],
    },
    2: {
        "title": "Embeddings, Indexing & Knowledge Graph",
        "ideas": [
            (11, "Embeddings service", "glean (embedding_factory.py + provider classes) · reor (lib/llm) · khoj (bi-encoder config) · decodingai"),
            (12, "Persistent vector store", "glean (milvus_client.py) · reor (local vector DB) · khoj (pgvector) · dyresearch (pgvector/lancedb)"),
            (13, "Metadata extraction & enrichment", "llm_wiki (frontmatter-panel.tsx) · claude-obsidian · khoj"),
            (14, "Auto-tagging", "khoj (tag/group processors) · basic-memory (picoschema/) · llm_wiki"),
            (15, "Concept extraction & canonicalization", "obsidian-wiki (ast_extractor.py, graph_analysis.py) · knowledge-nexus (entity_extraction_agent.py) · llm_wiki"),
            (16, "Knowledge graph nodes & edges", "basic-memory (models + index/) · nocturne_memory (db/graph.py) · obsidian-wiki (session_graph.py) · knowledge-nexus (Neo4j)"),
            (17, "Relationship & backlink inference", "foam (foam-core backlinks) · dendron · llm_wiki (page-links-panel.tsx)"),
            (18, "Graph visualization & explorer", "llm_wiki (graph-view.tsx + layout worker) · dendron (dendron-viz) · obsidian-wiki (session_viz.py) · mind-mentor (insights/knowledge-graph page) · basic-memory"),
            (19, "Duplicate & near-duplicate detection (chunk level)", "hashcards · engram"),
            (20, "Backfill & re-index tooling", "PAIDEIA (reindex.py) · obsidian-wiki (batch.py, sync.py) · decodingai (pipelines)"),
        ],
    },
    3: {
        "title": "Search & Retrieval",
        "ideas": [
            (21, "Full-text search with FTS5", "siyuan (kernel/search + sql/) · engram (SQLite FTS) · basic-memory (search index)"),
            (22, "Semantic search API", "khoj (search_type/) · reor (SearchComponent.tsx) · glean"),
            (23, "Hybrid retrieval with RRF fusion", "khoj (search_type/hybrid) · reor"),
            (24, "Query expansion & spelling tolerance", "khoj · dyresearch"),
            (25, "Citation-aware result cards", "claude-obsidian (ledgers.py, contracts.py) · khoj"),
            (26, "Retrieval evaluation harness", "khoj (tests) · decodingai (eval/dataset steps)"),
            (27, "Knowledge health analysis", "claude-obsidian (lint_engine.py) · PAIDEIA (doctor.py) · obsidian-wiki (lint.py, trust.py)"),
            (28, "Missing knowledge detection", "llm_wiki (gap analysis) · obsidian-wiki (graph_analysis.py)"),
            (29, "Search feedback & learning", "QuestLog (ai.controller.js caching + feedback) · khoj"),
            (30, "Global unified search box", "siyuan · reor (SearchComponent) · khoj (web search UI)"),
        ],
    },
    4: {
        "title": "Note Intelligence & Content Generation",
        "ideas": [
            (31, "AI summaries of notes & papers", "memora (generatorGPT.py) · StudyWise (notes page) · khoj (summarize) · EduAI (chat app)"),
            (32, "AI explanations (ELI5, analogies, derivations)", "StudyWise (eli5 page) · mind-mentor"),
            (33, "AI quizzes generated from notes", "EduAI (practice app) · StudyWise (quiz) · studybuddy-ai · memora · Multi-Agent-Study-Assistant (quiz gen) · infinition (quiz modals)"),
            (34, "Flashcards generated from notes", "LearnKit (engine/scheduler) · obsidian-spaced-repetition · hashcards · mimocard · memo · recalla · yt-flashcard-ai · studybuddy-ai · org-fc"),
            (35, "Daily notes integration", "obsidian-second-brain (obsidian-daily command) · My-Brain-System · OrbitOS · obsidian-claude-pkm"),
            (36, "Citation management", "claude-obsidian (contracts.py/ledgers.py) · obsidian-wiki"),
            (37, "Concept linking UI", "llm_wiki (page-links-panel.tsx) · mind-mentor (knowledge graph) · obsidian-wiki"),
            (38, "Mind-map generation", "second_brain_builder (mermaid output) · StudyWise (concept-map) · mind-mentor · obsidian-second-brain (obsidian-architect)"),
            (39, "Note quality scoring", "claude-obsidian (lint_engine.py) · PAIDEIA (doctor.py) · obsidian-wiki (lint.py)"),
            (40, "Brain dump → structured notes", "CortX (cortx_extractor.py + agent) · second_brain_builder (generation modals) · claude-obsidian (capture.py) · obsidian-second-brain (obsidian-capture)"),
        ],
    },
    5: {
        "title": "Subject Management Core",
        "ideas": [
            (41, "Automatic subject creation", "syllabo · study-planner-agent (models.py Subject)"),
            (42, "Syllabus parsing", "syllabus-agent (utils.py extract_topics_from_text) · syllabo · PAIDEIA · study-planner-agent · Syllabify · EduAI (syllabus app)"),
            (43, "Semester & calendar detection", "syllabo · Student_Study_Planner · EduAI"),
            (44, "Topic extraction & normalization", "syllabus-agent · PAIDEIA · syllabo · StudyWise"),
            (45, "Unit & lecture segmentation", "PAIDEIA · syllabo · EduAI"),
            (46, "Topic dependency graph", "PAIDEIA (learning graph) · mind-mentor (knowledge graph) · knowledge-nexus (Neo4j) · obsidian-wiki"),
            (47, "Learning roadmap generation", "Multi-Agent-Study-Assistant (roadmaps) · study-planner-agent (generate_plan) · syllabo · StudyWise · PAIDEIA · OrbitOS"),
            (48, "Difficulty estimation", "syllabo (difficulty_analyzer.py) · studybuddy-ai · syllabus-agent"),
            (49, "Time estimation", "syllabus-agent (build_study_plan) · study-planner-agent · syllabo"),
            (50, "Learning-outcome extraction", "syllabo · PAIDEIA · syllabus-agent"),
        ],
    },
    6: {
        "title": "Study Planning & Execution",
        "ideas": [
            (51, "Personalized study plans (AI-driven)", "study-planner-agent (generate_plan) · mind-mentor (study-plan) · Multi-Agent-Study-Assistant · syllabo · StudyWise"),
            (52, "Revision scheduling (spaced repetition)", "py-fsrs · ts-fsrs · fsrs-rs · obsidian-spaced-repetition (FSRS+SM-2) · LearnKit (fsrs.ts/lkrs.ts) · infinition (SM-2) · org-fc (SM-2 + FSRS) · hashcards · memo · orbit · fsrs4anki · anki (rslib scheduler)"),
            (53, "Exam preparation mode", "StudyWise (exam page) · EduAI (practice) · syllabo · Student_Study_Planner"),
            (54, "Assignment intelligence", "QuestLog (tasks) · noodle (modules) · EduAI"),
            (55, "Lab tracking", "QuestLog (collaboration) · EduAI"),
            (56, "Attendance monitoring", "EduAI · habit_quest (streak patterns)"),
            (57, "Subject progress analytics", "QuestLog (analytics.controller.js) · StudyWise (progress) · mind-mentor (insights) · HabitTrove · syllabo"),
            (58, "Weak & strong topic detection", "QuestLog (AI insights) · StudyWise · syllabo · PAIDEIA"),
            (59, "Recommended study order", "syllabo (content_recommender.py) · Multi-Agent-Study-Assistant · StudyWise"),
            (60, "Micro-session & focus integration", "mind-mentor (timer) · habit_quest · HabitTrove"),
        ],
    },
    7: {
        "title": "AI Tutor & Assessment",
        "ideas": [
            (61, "RAG-grounded AI tutor", "khoj (chat + search) · reor (Chat) · mind-mentor (chat) · EduAI (chat) · memora (RetrievalQA_mod.py) · dyresearch · Multi-Agent-Study-Assistant · claude-obsidian (grounded answers) · tutor-skills · obsidian-wiki"),
            (62, "AI doubt solving", "EduAI (chat) · mind-mentor · StudyWise"),
            (63, "AI-generated practice questions", "EduAI (practice) · StudyWise (quiz) · studybuddy-ai · syllabo (adaptive_quiz_engine.py) · memora"),
            (64, "Mock tests & exam simulations", "StudyWise (exam) · EduAI · LearnKit (exam-tests-sqlite.ts) · syllabo"),
            (65, "Interview preparation", "Multi-Agent-Study-Assistant · dyresearch (research agents)"),
            (66, "Answer grading & feedback (advanced)", "EduAI (practice grading) · StudyWise (quiz scoring)"),
            (67, "Adaptive question difficulty", "syllabo (adaptive_quiz_engine.py) · StudyWise"),
            (68, "Explain-my-mistake analysis", "PAIDEIA (wrong-answer tracking) · QuestLog (analytics) · syllabo"),
            (69, "Knowledge capture & revision XP", "habit_quest · QuestLog (XP) · Habit-Quest · HabitTrove · LearnKit (exam-tests)"),
            (70, "Skill mapping", "PAIDEIA (subject learning graph) · mind-mentor (knowledge graph) · syllabo"),
        ],
    },
    8: {
        "title": "Personalization & Learning Memory",
        "ideas": [
            (71, "Learning preference profile", "mind-mentor (profile/settings) · Multi-Agent-Study-Assistant (profiling) · dyresearch (config_manager.py) · glean (preference.py schema)"),
            (72, "Knowledge-gap detection (concept level)", "llm_wiki (gap analysis) · Multi-Agent-Study-Assistant (gap analysis) · obsidian-wiki (graph_analysis.py)"),
            (73, "Personalized explanations", "mind-mentor · EduAI · StudyWise"),
            (74, "Remember previously learned concepts", "engram (memory store) · nocturne_memory · basic-memory · claude-obsidian"),
            (75, "Recommend what to study next", "QuestLog (AI recommendations) · syllabo (content_recommender.py) · StudyWise"),
            (76, "Connect new concepts to existing notes", "llm_wiki (graph) · claude-obsidian (connect skill) · obsidian-second-brain (obsidian-connect) · obsidian-wiki"),
            (77, "Suggest missing notes", "llm_wiki · obsidian-wiki (graph_analysis) · My-Brain-Is-Full-Crew"),
            (78, "Detect outdated notes", "claude-obsidian (lint_engine.py) · obsidian-wiki (lint.py, trust.py)"),
            (79, "Long-term learning memory store", "engram (internal/store) · nocturne_memory (db/) · basic-memory (repository/) · memory-bank-mcp · token-savior"),
            (80, "Adaptive learning paths", "Multi-Agent-Study-Assistant · syllabo · StudyWise"),
        ],
    },
    9: {
        "title": "Automation",
        "ideas": [
            (81, "Auto-categorize new notes", "CortX (agent structuring) · obsidian-second-brain (obsidian-board) · My-Brain-Is-Full-Crew (sorter agent) · claude-obsidian (wiki-fold skill)"),
            (82, "Auto-tag documents (scheduled)", "My-Brain-Is-Full-Crew (sorter/scribe) · khoj (grouping)"),
            (83, "Auto-link related notes (scheduled)", "llm_wiki · claude-obsidian · obsidian-second-brain (obsidian-connect) · My-Brain-Is-Full-Crew (connector)"),
            (84, "Auto-detect duplicates (scheduled)", "hashcards · engram"),
            (85, "Auto-create flashcards from new notes", "LearnKit · mimocard · yt-flashcard-ai · StudyWise · studybuddy-ai"),
            (86, "Auto-create summaries (scheduled)", "memora · StudyWise · khoj"),
            (87, "Auto-generate mind maps (scheduled)", "second_brain_builder · StudyWise (concept-map) · mind-mentor"),
            (88, "Auto-update study plans on new materials", "study-planner-agent · syllabo · OrbitOS"),
            (89, "Auto-sync external repositories", "glean (RSS) · khoj (github_to_entries.py) · llm_wiki (file-sync.ts) · obsidian-wiki (sync.py)"),
            (90, "Auto-create revision tasks", "obsidian-spaced-repetition · LearnKit · py-fsrs (due cards)"),
        ],
    },
    10: {
        "title": "Advanced AI, Analytics & Platform",
        "ideas": [
            (91, "Multi-agent architecture", "Multi-Agent-Study-Assistant (study_agents.py) · My-Brain-Is-Full-Crew (8 agents) · dyresearch (ADK agents) · obsidian-second-brain (46 commands) · mind-mentor (mind-mentor-agents) · phantom · arscontexta"),
            (92, "Long-term memory system", "engram · nocturne_memory · basic-memory · token-savior · memory-bank-mcp"),
            (93, "Full RAG pipeline hardening", "khoj · decodingai · reor · obsidian-wiki (graphrag.py)"),
            (94, "Knowledge-graph + vector fusion", "knowledge-nexus (Neo4j GraphRAG) · llm_wiki · obsidian-wiki (graphrag.py) · basic-memory"),
            (95, "Context-aware responses", "QuestLog (AI controller w/ user stats) · mind-mentor · EduAI"),
            (96, "Research assistant", "dyresearch · knowledge-nexus (notion/pocket providers) · decodingai · claude-obsidian (autoresearch skill)"),
            (97, "Intelligent recommendation engine", "syllabo (content_recommender.py) · QuestLog · StudyWise"),
            (98, "Goal planning & reflection", "obsidian-claude-pkm (3-year vision → daily) · OrbitOS · My-Brain-System · obsidian-second-brain (obsidian-challenge)"),
            (99, "Predictive analytics & trajectory forecasting", "QuestLog (analytics) · syllabo (prediction) · StudyWise"),
            (100, "Self-improving assistant + observability", "claude-obsidian (ledgers.py) · token-savior · QuestLog (analytics) · decodingai (Opik integration)"),
        ],
    },
}

WARNING = (
    "> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines "
    "(khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. "
    "Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, "
    "infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, "
    "HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, "
    "mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, "
    "My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, "
    "dendron. Repos without a license file are STUDY only."
)


def build_section(phase_no: int) -> str:
    p = PHASES[phase_no]
    lines = [
        "",
        "---",
        "",
        f"## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))",
        "",
        f"Every idea in Phase {phase_no} ({p['title']}) has reusable components in the cloned reference "
        "repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — "
        "full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.",
        "",
    ]
    for num, title, repos in p["ideas"]:
        lines.append(f"- **Idea {num} — {title}:** {repos}")
    lines += [
        "",
        WARNING,
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    inserted = []
    for phase_no in sorted(PHASES):
        fname = f"SECOND_BRAIN_PHASE{phase_no}_100_PHRASE_PLAN.md"
        path = ROOT / fname
        if not path.exists():
            print(f"MISSING {fname}", file=sys.stderr)
            continue
        text = path.read_text()
        marker = "## Group 1 —"
        idx = text.find(marker)
        if idx == -1:
            print(f"NO GROUP-1 MARKER in {fname}", file=sys.stderr)
            continue
        section = build_section(phase_no)
        new_text = text[:idx] + section + "\n" + text[idx:]
        path.write_text(new_text)
        inserted.append(fname)
    print("Inserted into:", ", ".join(inserted))


if __name__ == "__main__":
    main()
