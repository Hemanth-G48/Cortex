# Similar GitHub Repos — Second Brain × AI Study Planner × Student OS

**Purpose:** Reference list of GitHub repositories that overlap with this project — a
**Student Life OS** that combines a Second Brain (Obsidian vault integration), AI-powered
subject management (syllabus parsing, topic graphs, roadmaps), study planning (spaced
repetition, exams, pomodoro), a RAG AI tutor, and gamification (XP, quests, streaks).

**Compiled:** 2026-08-05 (expanded), via GitHub search API + web research. Small/low-star
repos are included on purpose. ★ = stars verified via the GitHub API; otherwise count not
captured. These are **references, not dependencies** — nothing here is required to build
the phase plans.

---

## 1. AI Second Brain / RAG Knowledge Assistants

| Repo | Why it's relevant |
|---|---|
| **khoj-ai/khoj** — ★ 36.2k — [github.com/khoj-ai/khoj](https://github.com/khoj-ai/khoj) | Self-hostable "AI second brain": RAG over your docs + web, custom agents, scheduled automations. The big-name reference for the whole Second Brain AI layer (Phases 1–3, 10). |
| **AgriciDaniel/claude-obsidian** — ★ 10.4k — [github.com/AgriciDaniel/claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) | Claude-driven self-organizing Obsidian vault; source-cited answers (claim/provenance ledgers), LYT/PARA/Zettelkasten filing. Overlaps Ideas 1–4, 16–17, 93. |
| **eugeniughelbur/obsidian-second-brain** — ★ 3.8k — [github.com/eugeniughelbur/obsidian-second-brain](https://github.com/eugeniughelbur/obsidian-second-brain) | Persistent memory for Claude Code + other CLI agents stored as plain markdown in the Obsidian vault. |
| **agenticnotetaking/arscontexta** — ★ 3.5k — [github.com/agenticnotetaking/arscontexta](https://github.com/agenticnotetaking/arscontexta) | Generates individualized knowledge systems from conversations; agent-driven note organization. |
| **gnekt/My-Brain-Is-Full-Crew** — ★ 3.3k — [github.com/gnekt/My-Brain-Is-Full-Crew](https://github.com/gnekt/My-Brain-Is-Full-Crew) | CrewAI multi-agent second brain (built by a PhD with memory/focus struggles). |
| **decodingai-magazine/second-brain-ai-assistant-course** — ★ 3.0k — [github.com/decodingai-magazine/second-brain-ai-assistant-course](https://github.com/decodingai-magazine/second-brain-ai-assistant-course) | Course code for building second-brain AI assistants (LLMs, agents, RAG, fine-tuning, LLMOps). |
| **Gentleman-Programming/engram** — ★ 5.9k — [github.com/Gentleman-Programming/engram](https://github.com/Gentleman-Programming/engram) | Persistent memory system for AI coding agents: Go binary, SQLite + FTS5, MCP server, HTTP API. Overlaps Ideas 79, 92. |
| **moltis-org/moltis** — ★ 2.8k — [github.com/moltis-org/moltis](https://github.com/moltis-org/moltis) | Secure persistent personal agent server in Rust: one binary, sandboxed execution, multi-provider LLMs. |
| **agentset-ai/agentset** — ★ 2.0k — [github.com/agentset-ai/agentset](https://github.com/agentset-ai/agentset) | Open-source RAG platform: built-in citations, deep research, 22+ file formats, partitions, MCP server. Close to Ideas 22–25, 93. |
| **ghostwright/phantom** — ★ 1.5k — [github.com/ghostwright/phantom](https://github.com/ghostwright/phantom) | AI co-worker with its own computer: self-evolving, persistent memory, MCP server. |
| **Dataojitori/nocturne_memory** — ★ 1.3k — [github.com/Dataojitori/nocturne_memory](https://github.com/Dataojitori/nocturne_memory) | Lightweight, rollbackable, visual long-term memory server for MCP agents — explicitly "say goodbye to Vector RAG". Interesting counterpoint to the vector approach (Ideas 12, 92). |
| **alioshr/memory-bank-mcp** — ★ 0.9k — [github.com/alioshr/memory-bank-mcp](https://github.com/alioshr/memory-bank-mcp) | MCP server for remote memory bank management (Cline Memory Bank pattern). |
| **gcorman/CortX** — [github.com/gcorman/CortX](https://github.com/gcorman/CortX) | Local-first desktop second brain: SQLite FTS5 + embeddings hybrid search, multi-hop graph expansion, graph viz, propose-then-execute with git versioning. Close to Ideas 21–23, 94. |
| **nashsu/llm_wiki** — [github.com/nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | Incremental "LLM wiki": LanceDB vector search + 4-signal graph relevance, Louvain community detection, gap/island analysis, multi-format ingestion. Overlaps Ideas 22–28, 92. |
| **basicmachines-co/basic-memory** — [github.com/basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory) | MCP-native memory layer over plain markdown: entities/observations, `[[wikilinks]]` graph, hybrid search with cross-encoder rerank. Overlaps Ideas 15–17, 79, 93. |
| **Jallermax/knowledge-nexus** — [github.com/Jallermax/knowledge-nexus](https://github.com/Jallermax/knowledge-nexus) | GraphRAG engine: content embeddings + Neo4j semantic knowledge graph (entities, topics, relations). Overlaps Ideas 15–16, 94. |
| **DeusData/codebase-memory-mcp** — ★ 37.6k — [github.com/DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | Code-intelligence MCP server indexing codebases into a persistent knowledge graph. Code-focused, but a strong reference for knowledge-graph indexing mechanics (Ideas 16, 94). |

## 2. Obsidian-Based Learning & Knowledge Systems

| Repo | Why it's relevant |
|---|---|
| **ctrlaltwill/LearnKit** — [github.com/ctrlaltwill/LearnKit](https://github.com/ctrlaltwill/LearnKit) | Obsidian plugin: FSRS spaced repetition, multi-type flashcards, test modes, and an AI **Companion** that generates flashcards/quizzes from your own notes. Extremely close to Ideas 34, 52, 63. |
| **OPTIMETA/PAIDEIA** — ★ 0.1k — [github.com/OPTIMETA/PAIDEIA](https://github.com/OPTIMETA/PAIDEIA) | Claude Code plugin that forms exam readiness locally — "stop renting your own learning". Close to Ideas 53, 61. |
| **ballred/obsidian-claude-pkm** — ★ 1.7k — [github.com/ballred/obsidian-claude-pkm](https://github.com/ballred/obsidian-claude-pkm) | Complete starter kit for an Obsidian + Claude Code personal knowledge management system. |
| **uan-iel/obsidian-museum-desk** — ★ 0.04k — [github.com/uan-iel/obsidian-museum-desk](https://github.com/uan-iel/obsidian-museum-desk) | Museum-inspired Obsidian command-desk plugin for study, writing, tasks, mood, and health tracking. |
| **infinition/obsidian-flash-quizz** — ★ 0.01k — [github.com/infinition/obsidian-flash-quizz](https://github.com/infinition/obsidian-flash-quizz) | Flash & Quizz Obsidian plugin: turns JSON data into interactive learning cards. |
| **algometrix/second_brain_builder** — ★ 0.01k — [github.com/algometrix/second_brain_builder](https://github.com/algometrix/second_brain_builder) | AI-powered Obsidian plugin that turns any topic into a folder of interlinked study notes with an index hub + memory map. |
| **DylanTartarini1996/dyresearch** — ★ 0.01k — [github.com/DylanTartarini1996/dyresearch](https://github.com/DylanTartarini1996/dyresearch) | Agentic system for studying/learning/researching topics, integrated with Obsidian via a plugin sidecar. |
| **Timeverse/My-Brain-System** — [github.com/Timeverse/My-Brain-System](https://github.com/Timeverse/My-Brain-System) | Obsidian + Claude Code: auto-ingests PDFs/URLs, self-evolving MECE taxonomy, bi-directional wikilinks, adversarial "Thinking Lab". |
| **bevibing/tutor-skills** — [github.com/bevibing/tutor-skills](https://github.com/bevibing/tutor-skills) | Claude Code skills that ingest docs/PDFs into an interlinked Obsidian StudyVault (MOCs) + concept-level diagnostic quiz loop. Close to Ideas 4, 33, 62. |
| **Ar9av/obsidian-wiki** — [github.com/Ar9av/obsidian-wiki](https://github.com/Ar9av/obsidian-wiki) | Framework for local AI agents to build/maintain an Obsidian second brain; duplicate-RAG avoidance, graph linting, multi-source ingestion. Overlaps Ideas 8, 19, 78. |
| **mohsinkhadim59/youtube-obsidian-mcp** — [github.com/mohsinkhadim59/youtube-obsidian-mcp](https://github.com/mohsinkhadim59/youtube-obsidian-mcp) | MCP server: YouTube transcripts → timestamped, structured markdown study notes with key terms and review questions. |

## 3. AI Study Planners & Syllabus Parsers

| Repo | Why it's relevant |
|---|---|
| **vxk8058/syllabus-agent** — [github.com/vxk8058/syllabus-agent](https://github.com/vxk8058/syllabus-agent) | GPT-4 + CrewAI: parses syllabus PDFs into topics/subtopics and generates time-efficient study plans with curated YouTube tutorials. Overlaps Ideas 42, 47. |
| **SAHIL-creator-Dev/study-planner-agent** — [github.com/SAHIL-creator-Dev/study-planner-agent](https://github.com/SAHIL-creator-Dev/study-planner-agent) | Django + Gemini: exam schedules/syllabi → prioritized study plans, daily focus checklists, MCQ quiz generator, on-demand AI tutor chat. Overlaps Ideas 42, 53, 63. |
| **PixelCode01/syllabo** — [github.com/PixelCode01/syllabo](https://github.com/PixelCode01/syllabo) | AI learning companion: syllabus/goals → topic hierarchy, top resources, spaced-repetition scheduling, adaptive quizzes. Overlaps Ideas 42–44, 52, 63, 67. |
| **ajay160380/ai-tutor** (EduAI) — [github.com/ajay160380/ai-tutor](https://github.com/ajay160380/ai-tutor) | Personalized virtual tutor: smart syllabus tracking, real-time progress analytics, weak-point practice tests, 24/7 context-aware chatbot. Overlaps Ideas 58, 61, 66. |
| **MansiPatil21/Syllabify** — [github.com/MansiPatil21/Syllabify](https://github.com/MansiPatil21/Syllabify) | React + FastAPI + AWS: transforms syllabus PDFs into semester-long roadmaps with daily schedules and curated learning links. Overlaps Ideas 42, 47. |
| **KartikLabhshetwar/mind-mentor** — ★ 0.1k — [github.com/KartikLabhshetwar/mind-mentor](https://github.com/KartikLabhshetwar/mind-mentor) | AI-powered study assistant for how students learn and prepare. |
| **mhss1/AIStudyAssistant** — ★ 0.1k — [github.com/mhss1/AIStudyAssistant](https://github.com/mhss1/AIStudyAssistant) | AI chatbot + lecture summarizer + essay writer + questions generator. Close to Ideas 61, 63, 66. |
| **karthikkasirajan/studybuddy-ai** — ★ 0.05k — [github.com/karthikkasirajan/studybuddy-ai](https://github.com/karthikkasirajan/studybuddy-ai) | AI study assistant that transforms PDF notes into quizzes, flashcards, and summaries (Streamlit). Close to Ideas 31, 33, 34. |
| **Yuvazyli/StudentAI-Assistant** — ★ 0.05k — [github.com/Yuvazyli/StudentAI-Assistant](https://github.com/Yuvazyli/StudentAI-Assistant) | ML-powered study assistant for college students. |
| **shafisma/StudyWise** — ★ 0.05k — [github.com/shafisma/StudyWise](https://github.com/shafisma/StudyWise) | AI study assistant that turns any text, topic, or video into structured study material. |
| **A-R007/Multi-Agent-Study-Assistant** — ★ 0.05k — [github.com/A-R007/Multi-Agent-Study-Assistant](https://github.com/A-R007/Multi-Agent-Study-Assistant) | AI learning platform with 6 specialized agents; adaptive roadmaps + personalized education. Close to Idea 91. |
| **tejgor/memora** — ★ 0.05k — [github.com/tejgor/memora](https://github.com/tejgor/memora) | Open-source AI study assistant. |

## 4. Student Productivity Apps

| Repo | Why it's relevant |
|---|---|
| **noodle-run/noodle** — [github.com/noodle-run/noodle](https://github.com/noodle-run/noodle) | Open-source all-in-one student planner ("Rethinking Student Productivity"): notes, assignments, syllabus, grades, calendar. The closest existing "Student OS" product to this app. |
| **MarsWang42/OrbitOS** — ★ 0.9k — [github.com/MarsWang42/OrbitOS](https://github.com/MarsWang42/OrbitOS) | AI-powered personal productivity system where knowledge management and daily task planning are intelligent. Close to the whole app concept. |
| **ramya0715/Student_Study_Planner** — [github.com/ramya0715/Student_Study_Planner](https://github.com/ramya0715/Student_Study_Planner) | A student study planner repo (sparse — no description; included per "even if little content" request). |

## 5. Gamified Habit / Quest Trackers

| Repo | Why it's relevant |
|---|---|
| **4RGUS/habit_quest** — [github.com/4RGUS/habit_quest](https://github.com/4RGUS/habit_quest) | HabitQuest: RPG XP tiers (Seedling → Ancient Oak), milestone badges, fire streaks, 60-day calendar heatmap. Close to this app's habit/XP/vault heatmap features. |
| **dohsimpson/HabitTrove** — [github.com/dohsimpson/HabitTrove](https://github.com/dohsimpson/HabitTrove) | Coin economy + personal wishlist rewards, calendar heatmaps, streak stats, PWA, Docker. |
| **hussaino03/QuestLog** — [github.com/hussaino03/QuestLog](https://github.com/hussaino03/QuestLog) | Quest-based task/project management with XP + leveling (harder tasks = more XP), public leaderboards, AI productivity insights, Todoist/TickTick import. Close to the quest centre + XP features. |
| **Karthik998byte/Habit-Quest** — [github.com/Karthik998byte/Habit-Quest](https://github.com/Karthik998byte/Habit-Quest) | Lightweight Flask + SQLite RPG habit tracker: XP scaling, streaks, levels, leaderboards. |

## 6. Spaced Repetition & Flashcards

| Repo | Why it's relevant |
|---|---|
| **ankitects/anki** — ★ 29.5k — [github.com/ankitects/anki](https://github.com/ankitects/anki) | The gold-standard open-source spaced-repetition flashcard program. The reference for Ideas 34, 52. |
| **open-spaced-repetition/fsrs4anki** — ★ 4.0k — [github.com/open-spaced-repetition/fsrs4anki](https://github.com/open-spaced-repetition/fsrs4anki) | FSRS (Free Spaced Repetition Scheduler) for Anki — modern replacement for SM-2. The algorithm worth studying for Idea 52. |
| **open-spaced-repetition/free-spaced-repetition-scheduler** — ★ 0.7k — [github.com/open-spaced-repetition/free-spaced-repetition-scheduler](https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler) | The FSRS algorithm (DSR model) itself; official ports: [fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs), [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs), [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs), plus an [awesome-fsrs](https://github.com/open-spaced-repetition/awesome-fsrs) index. |
| **st3v3nmw/obsidian-spaced-repetition** — ★ 2.5k — [github.com/st3v3nmw/obsidian-spaced-repetition](https://github.com/st3v3nmw/obsidian-spaced-repetition) | Fight the forgetting curve by reviewing flashcards & entire notes inside Obsidian. |
| **olmps/memo** — ★ 1.9k — [github.com/olmps/memo](https://github.com/olmps/memo) | Open-source, programming-oriented spaced repetition software (SRS) written in Flutter. |
| **andymatuschak/orbit** — ★ 1.8k — [github.com/andymatuschak/orbit](https://github.com/andymatuschak/orbit) | Experimental SRS platform for memory augmentation and programmable attention. |
| **eudoxia0/hashcards** — ★ 1.2k — [github.com/eudoxia0/hashcards](https://github.com/eudoxia0/hashcards) | Plain text-based spaced repetition system. |
| **mochi-co/mochi-desktop** — [github.com/mochi-co/mochi-desktop ⚠️ (repo no longer on GitHub — 404; clone skipped)](https://github.com/mochi-co/mochi-desktop ⚠️ (repo no longer on GitHub — 404; clone skipped)) | Markdown-powered, offline-first flashcard app (multi-sided cards, backlinks, FSRS option). |
| **true-recall** — [github.com/true-recall](https://github.com/true-recall) (Obsidian plugin) | Next-gen Obsidian SRS: local SQLite, Anki import/export, rich analytics, FSRS-6 via ts-fsrs. |
| **gyoomei/mimocard** — [github.com/gyoomei/mimocard](https://github.com/gyoomei/mimocard) | Zero-dependency single-HTML AI flashcard generator: URL → Q&A cards → SM-2 reviews → Anki export. |
| **KeyulJain/yt-flashcard-ai** — [github.com/KeyulJain/yt-flashcard-ai](https://github.com/KeyulJain/yt-flashcard-ai) | Browser extension that turns YouTube transcripts into spaced-repetition flashcards (OpenAI). |
| **bmmunga/recalla** — [github.com/bmmunga/recalla](https://github.com/bmmunga/recalla) | AI flashcard generator: upload PDFs/text → auto-generated study sessions (Next.js + Supabase). |
| **org-fc/org-fc** — [github.com/l3kn/org-fc (corrected URL — repo moved)](https://github.com/l3kn/org-fc (corrected URL — repo moved)) | Flashcard templates + spaced repetition for Emacs Org-mode (experimental FSRS-6 hooks). |

## 7. Personal Knowledge Management / Wikis

| Repo | Why it's relevant |
|---|---|
| **siyuan-note/siyuan** — ★ 45.6k — [github.com/siyuan-note/siyuan](https://github.com/siyuan-note/siyuan) | Privacy-first, self-hosted PKM (TypeScript/Go) with block-level references and built-in FSRS spaced repetition. A full platform reference. |
| **foambubble/foam** — ★ 17.3k — [github.com/foambubble/foam](https://github.com/foambubble/foam) | PKM + sharing system for VSCode: markdown, `[[wikilinks]]`, graph — Obsidian-style notes outside Obsidian. |
| **reorproject/reor** — ★ 8.6k — [github.com/reorproject/reor](https://github.com/reorproject/reor) | Private & local AI PKM app: markdown notes + local LLM RAG + graph. Close to Phases 1–3. |
| **dendronhq/dendron** — ★ 7.5k — [github.com/dendronhq/dendron](https://github.com/dendronhq/dendron) | Hierarchical PKM tool ("grows as you do") — VSCode-based, markdown-native. |
| **LeslieLeung/glean** — ★ 0.8k — [github.com/LeslieLeung/glean](https://github.com/LeslieLeung/glean) | Self-hosted RSS reader + PKM tool. |

## 8. MCP Memory Servers & Agent Memory

| Repo | Why it's relevant |
|---|---|
| **Gentleman-Programming/engram** — ★ 5.9k — [github.com/Gentleman-Programming/engram](https://github.com/Gentleman-Programming/engram) | Persistent memory for AI agents: SQLite + FTS5, MCP server, HTTP API (listed in §1 too — the canonical small memory server). Overlaps Ideas 79, 92. |
| **Dataojitori/nocturne_memory** — ★ 1.3k — [github.com/Dataojitori/nocturne_memory](https://github.com/Dataojitori/nocturne_memory) | Long-term memory server for MCP agents with rollback + visualization; argues against vector RAG for memory. |
| **alioshr/memory-bank-mcp** — ★ 0.9k — [github.com/alioshr/memory-bank-mcp](https://github.com/alioshr/memory-bank-mcp) | Remote memory-bank MCP server (Cline Memory Bank pattern). |
| **Mibayy/token-savior** — ★ 1.1k — [github.com/Mibayy/token-savior](https://github.com/Mibayy/token-savior) | MCP server optimizing context/token usage — relevant to the memory-in-prompt design (Idea 92). |

## 9. Discovery Topics (browse more)

- [github.com/topics/second-brain](https://github.com/topics/second-brain)
- [github.com/topics/obsidian](https://github.com/topics/obsidian)
- [github.com/topics/spaced-repetition](https://github.com/topics/spaced-repetition)
- [github.com/topics/anki](https://github.com/topics/anki)
- [github.com/topics/personal-knowledge-management](https://github.com/topics/personal-knowledge-management)
- [github.com/topics/gamified-productivity](https://github.com/topics/gamified-productivity)
- [github.com/topics/student-dashboard](https://github.com/topics/student-dashboard)
- [github.com/topics/study-planner](https://github.com/topics/study-planner)
- [github.com/topics/rag](https://github.com/topics/rag)
- [github.com/topics/mcp](https://github.com/topics/mcp)

---

## Notes

- **Closest overall references:** `khoj-ai/khoj` (Second Brain AI at scale), `noodle-run/noodle`
  + `MarsWang42/OrbitOS` (student OS products), `ctrlaltwill/LearnKit` + `st3v3nmw/obsidian-spaced-repetition`
  (in-vault SRS + AI flashcards), `PixelCode01/syllabo` (syllabus → roadmap + adaptive study),
  and `reorproject/reor` (local AI PKM).
- **Algorithm worth adopting:** FSRS (`free-spaced-repetition-scheduler` + language ports) is the
  modern replacement for SM-2 — the phase plan's Idea 52 scheduler should consider it.
- **Architecture patterns worth borrowing:** CortX's FTS5+embeddings hybrid search and
  propose-then-execute review flows; llm_wiki's graph-relevance ranking and gap analysis;
  claude-obsidian's provenance/claim ledgers (citation discipline); engram's SQLite+FTS5 memory
  layout (Ideas 79/92).
- Many of the smaller repos are single-purpose (one feature) — good for studying one subsystem
  (syllabus parsing, quiz generation, heatmaps, SRS scheduling) without the noise of a full platform.
- Star counts are shown only where verified via the GitHub API at compile time; counts change
  over time. These are **references, not dependencies** — implementing the phase plans requires
  none of them.
