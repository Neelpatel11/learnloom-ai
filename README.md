<div align="center">

<img src="docs/images/banner.svg" alt="LearnLoom AI" width="100%"/>

### Your notes in, cited answers out.

LearnLoom AI is a multi-agent study companion that reads the material *you* upload and answers from it,
with clickable sources. It works in English, Hindi and Gujarati.

![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Next.js 15](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs)
![PostgreSQL 16 + pgvector](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agents-1C3C3C)

[What you get](#what-you-get) ·
[Under the hood](#under-the-hood) ·
[Run it locally](#run-it-locally) ·
[The pipeline](#the-pipeline-step-by-step) ·
[Evaluation](#evaluation) ·
[Quality checks](#quality-checks) ·
[Limits](#current-limits)

</div>

<!--
  Screenshots go here once the app is running:

  <p align="center">
    <img src="docs/images/chat.png" width="49%" alt="Chat with cited answers"/>
    <img src="docs/images/planner.png" width="49%" alt="Study planner"/>
  </p>
-->

---

## Why LearnLoom?

General-purpose chatbots answer from the internet. Students need answers from **their own syllabus**.
LearnLoom takes whatever you study from (PDFs, Word documents, slide decks, plain text, even phone
photos of handwritten pages), breaks it into passages and builds a search index that only you can see.
On top of that index you can:

- 💬 **Ask anything** and get an answer that points to the exact page or section it came from.
- 📝 **Test yourself** with generated quizzes and spaced-repetition cards that come back when they are due.
- 🧭 **Work through assignments** with a coach that guides you step by step but never writes the work for you.
- 📅 **Plan your revision** around exams and deadlines, then push the plan to Google Calendar.
- 👥 **Study together** by sharing notes privately with classmates in study groups.

Privacy comes first. Every student's data is isolated **inside PostgreSQL itself** through row-level
security, not just by application checks. LearnLoom also uses a **bring-your-own-key** model (Anthropic,
Google Gemini, OpenAI or Groq), so there's no shared AI bill to worry about.

> **The engineering highlights:** four retrieval strategies benchmarked head-to-head on multilingual
> text (vector, hybrid with reciprocal rank fusion, vector + cross-encoder rerank, hybrid + rerank);
> a LangGraph multi-agent orchestrator that can pause for human approval; layered AI safety (PII
> masking, prompt-injection defence, guardrails); multi-tenancy enforced by row-level security; an
> in-app Evaluation Lab that scores retrieval and answers on a student's own files; and a 53-case
> agent test harness covering routing, tool use, task success, citations and safety.

### At a glance

Numbers from real runs (method and caveats are under [Evaluation](#evaluation)):

| Area | Result |
| --- | --- |
| Retrieval: vector only → vector + rerank (the chat default) | Recall@1 **53% → 76%**, Recall@3 77% → 91%, Recall@10 91% → 95%, MRR 0.68 → 0.86 (168 English questions, 153 answerable, K = 10, single run) |
| Hybrid search (vector + BM25) | Recall@1 61%, Recall@10 94%, MRR 0.75, ahead of vector-only. Feeding keyword hits into the reranker added nothing measurable |
| Latency (median search) | ~48 ms vector, ~214 ms hybrid, ~542 ms with rerank |
| Agents (51 of 53 cases ran) | Task success 47 / 51 (92%), routing 31 / 31, 9 / 9 harmful messages blocked, 0 / 12 safe messages wrongly blocked |
| Guardrails (offline) | 16 / 16 cases, median 14 ms |

## What you get

| Module | In short |
| --- | --- |
| **Accounts** | Email + password (with email confirmation and reset) or one-click Google sign-in. Sessions are kept in an HttpOnly cookie. |
| **Subjects & materials** | Upload → parse (with OCR for scans and photos in English, Hindi, Gujarati) → chunk → embed. Each stage is tracked and retryable. |
| **Chat Assistant** | Multi-agent chat with semantic search, cross-encoder reranking (keyword fallback), streamed answers with numbered citations, Mermaid diagrams and file attachments. |
| **Quizzes & practice** | MCQ, true/false and short answer. Objective auto-marking plus AI marking for short answers, explanations, and Leitner-style revision cards. |
| **Assignment Helper** | Step-by-step breakdowns, outlines built from your notes, and feedback on your draft, in a workspace with autosave and version history. It coaches; it never writes. |
| **Planner & calendar** | A deterministic (non-AI) planner that works from exams, deadlines, due cards and weak topics. Optional sync into a dedicated "LearnLoom AI" Google calendar. |
| **Study groups & library** | Private shelves joined by code, shared notes, discussions, sessions with RSVPs, plus reporting and moderation. |
| **Evaluation Lab** | Scores retrieval (Recall@K, Precision@K, MRR, Hit@K), citation validity, latency percentiles and AI-judged answer quality on your own material. |
| **Agent evaluation** | 53 scripted conversations that check routing, tool selection, real citations, and whether the safety rail stops attacks without blocking normal messages. Runs offline (guardrails only) or live. |
| **AI safety** | PII is masked before anything reaches a provider, plus prompt-injection defence, NeMo Guardrails, output sanitising and redacted logs. See [docs/security.md](docs/security.md). |
| **Admin** | Users, usage, reports and safety counters. Admins see counts and account metadata only, never content. |
| **Trilingual** | English, Hindi and Gujarati across the UI, the student guide, search and answers. |
| **Accessibility** | A dark "liquid glass" design system with full keyboard support and reduced-motion, high-contrast and forced-colours modes. |

## Under the hood

### Agents, tools and MCP in one picture

![LearnLoom AI architecture: guard rail, router, seven agents with their tools, retrieval, route functions, workers, the MCP calendar path, the approval pause and the output rail](docs/images/agents-tools-mcp-architecture.png)

Each message goes through an input rail first. A router then picks one or two of the seven agents,
and each agent can only call its own tools. Tools run as the logged-in student, so row-level security
always applies. Only three calendar tools ever touch the outside world. They wait for the student to
approve, then reach Google through a single MCP service using a 60-second, single-use signed token.
Every reply passes an output rail before display. The [tool reference](#tool-reference) lists every tool.

### Services

```mermaid
flowchart LR
    subgraph Browser
        W["Next.js 15 web app<br/>(React 19, Tailwind, i18n en/hi/gu)"]
    end

    subgraph Edge
        C["Caddy (production)<br/>automatic HTTPS"]
    end

    subgraph Backend
        A["FastAPI API<br/>30 routers, 200+ endpoints<br/>under /api/v1"]
        WK["Celery workers<br/>ingest, quizzes, grading, evaluation"]
        MCP["Calendar MCP server<br/>(sole Google Calendar client)"]
        M["Model service<br/>BGE-M3 embeddings + reranker"]
    end

    subgraph Data
        PG[("PostgreSQL 16<br/>pgvector, pg_trgm, RLS")]
        R[("Redis<br/>queue + rate limits")]
        S[("S3-compatible storage<br/>uploaded files")]
    end

    subgraph External
        LLM["AI providers (student's own key)<br/>Anthropic · Gemini · OpenAI · Groq"]
        G["Google OAuth + Calendar"]
    end

    W -->|"/api/* proxied"| C --> A
    A --> PG
    A --> R
    A --> S
    A -->|"embed, rerank"| M
    A -->|"httpx / LangChain"| LLM
    A -->|"signed 60 s tokens"| MCP --> G
    A -->|"enqueue"| R --> WK
    WK --> PG
    WK --> S
    WK --> M
    WK --> LLM
```

The browser only talks to the web app's own `/api` path, and Next.js forwards it to the API, so the
session cookie stays first-party. During development the model service runs directly on the host to
get GPU access; everything else lives in Docker Compose.

### Where things live

```
.
├── apps/web/              Next.js app (App Router, Tailwind, typed i18n catalogs, student-guide content)
├── services/
│   ├── api/               FastAPI app: routers, auth, rate limits, retrieval, LangGraph agents
│   ├── worker/            Celery: parsing, OCR, chunking, embedding, quizzes, grading, evaluation runs
│   ├── models/            Embedding + rerank HTTP service (BGE-M3, bge-reranker-v2-m3)
│   └── calendar_mcp/      MCP server that is the only holder of Google Calendar access
├── libs/
│   ├── core/              Settings, DB sessions with RLS, pure business logic (planner, quiz, metrics, safety)
│   └── agents/            Guardrails, model factory, tracing, checkpointing, agent evaluation
├── infra/
│   ├── migrations/        23 Alembic migrations written in SQL (tables, indexes, RLS policies)
│   ├── compose/           Postgres init scripts (dev and production roles)
│   ├── docker/            api / web / models Dockerfiles
│   └── caddy/             Production reverse-proxy configuration
├── packages/contracts/    openapi.json, the contract the web client is checked against
├── evals/                 Datasets (50 RAG questions in 3 languages, agent cases), corpus, offline checker
├── docs/                  Student guide (en/hi/gu), security overview, agents, runbooks, ADRs
├── scripts/               Model launcher, OpenAPI export, prod / backup / restore, load test, checks
├── compose.yaml           Development stack
├── compose.prod.yaml      Production stack (Caddy is the only public service)
└── DOC.md                 Deep technical documentation
```

### Stack choices

| Layer | Pick | Reasoning (the full version is in [DOC.md](DOC.md#19-why-these-technologies)) |
| --- | --- | --- |
| API | **FastAPI**, Pydantic v2, async SQLAlchemy 2 + asyncpg | Async I/O suits streamed chat, and typed models produce the OpenAPI contract for free. |
| Database | **PostgreSQL 16** + **pgvector** + pg_trgm | One engine for relational data, vectors, full-text search and row-level security. |
| Migrations | **Alembic**, plain SQL | RLS policies and extensions are SQL anyway, so there's no ORM layer hiding them. |
| Queue | **Celery** + **Redis** | Battle-tested retries and routing, with a dedicated `eval` queue at concurrency 1. |
| Embeddings | **BGE-M3** (1024-dim), self-hosted | Strong multilingual coverage including Hindi/Gujarati, no per-token cost, and data stays local. |
| Reranker | **bge-reranker-v2-m3** cross-encoder | A big precision jump over raw vector order on a small candidate set. |
| Agents | **LangGraph** + **LangChain** | Explicit graphs, checkpointing, and interrupts for human approval. |
| Safety | **NeMo Guardrails** + custom rules | Rails on input, tool calls, tool results and output. |
| Calendar | **MCP** server + Google Calendar API | Side effects isolated in one process behind short-lived signed tokens. |
| Tracing | **LangSmith** (opt-in, masked) | Debuggable runs without leaking personal data. |
| Quality | **Ragas** (optional) + custom metrics | Agent and RAG evaluation. |
| OCR | **Tesseract** (eng + hin + guj) | Free, local, and covers all three languages. |
| Web | **Next.js 15**, React 19, TypeScript, Tailwind 3.4 | App Router, streaming proxy, strict typing. |
| UI | `motion`, Mermaid, KaTeX | Animation plus diagrams and maths rendered from model output; the planner uses native HTML5 drag and drop. |
| Ops | Docker Compose, Caddy, GitHub Actions | Reproducible dev, automatic HTTPS in prod, CI on every push. |

## Run it locally

**Prerequisites:** Docker Desktop (WSL2 on Windows) and Python 3.12. A CUDA GPU speeds up the model
service a lot (it's tuned for a 4 GB RTX 3050), but CPU works too, just slower. You only need Node 22
and pnpm if you want to run the web app outside Docker.

### Step 1: bring up the stack

```bash
docker compose up --build
```

This launches Postgres (pgvector), Redis, Mailpit and RustFS storage, runs the migrations, and then
starts the API, two workers, the Calendar MCP server and the web app.

| Service | URL |
| --- | --- |
| Web app | <http://localhost:3000> |
| API docs (dev only) | <http://localhost:8000/api/docs> |
| Readiness check (`database: ok`) | <http://localhost:8000/api/v1/ready> |
| Mailpit (catches every outgoing email) | <http://localhost:8025> |
| Storage console | <http://localhost:9001> (user `learnloom`, password `learnloom-secret`) |

### Step 2: start the model service on the host (GPU)

Open PowerShell with your Python environment active. One-time setup:
`pip install torch --index-url https://download.pytorch.org/whl/cu126`, then `pip install -e ".[models]"`.

```powershell
.\scripts\start-models.ps1          # real models; first launch downloads BGE-M3 (a few GB)
.\scripts\start-models.ps1 -Fake    # dummy vectors, only for quick pipeline smoke tests
```

Confirm it's up at <http://localhost:8100/health>. Fake vectors are useless for real search, so after
switching to the real models, hit *Try again* on each material to re-embed it.

### Step 3: plug in an AI key

Create an account, go to **Settings**, paste a key for any supported provider and click **Test**.
Keys are encrypted with `SECRET_KEY` before storage and never sent back to the browser.

### Extras

```bash
# make yourself an admin in development
docker compose run --rm migrate python -m learnloom_core.adminctl grant you@example.org
```

For Google sign-in and Calendar sync, follow [docs/runbooks/google-oauth.md](docs/runbooks/google-oauth.md).

All configuration is via environment variables. [`.env.example`](.env.example) lists them with dev defaults.

## The pipeline, step by step

### 1. Ingesting a file

```mermaid
flowchart LR
    U["Upload<br/>(max 50 MB)"] --> ST[("Object storage")]
    U --> Q["Celery job"]
    Q --> P["Parse<br/>pypdf · pypdfium2 · python-pptx · python-docx"]
    P -->|"page has < 20 chars<br/>or is an image"| O["Tesseract OCR<br/>eng + hin + guj"]
    P --> CH["Chunk<br/>~800 chars, 120 overlap<br/>paragraph → sentence → hard split"]
    O --> CH
    CH --> L["Detect script<br/>en / hi / gu"]
    L --> E["Embed<br/>BGE-M3, batches of 16"]
    E --> DB[("chunks<br/>vector(1024) + tsvector")]
```

Every stage writes to `ingestion_jobs`, so when a material fails you can see exactly where, and retry
it from the UI.

### 2. Retrieving an answer

```mermaid
flowchart LR
    Qn["Question"] --> EM["Embed query<br/>BGE-M3"]
    EM --> V["Vector search, 30 candidates<br/>HNSW index, cosine distance"]
    V --> RR["Cross-encoder rerank<br/>bge-reranker-v2-m3<br/>keep top 6"]
    RR --> PR["Numbered, neutralised,<br/>PII-masked sources"]
    PR --> LLMn["LLM streams a cited answer"]
    EM -. "model service down" .-> F["Full-text search<br/>tsvector, 'simple' config"]
    F -.-> PR
```

Chat runs the **advanced** strategy shown above. In the Evaluation Lab you can pit four strategies
against each other on your own files: **baseline** (vector only), **hybrid** (vector + BM25 merged via
reciprocal rank fusion, `score = Σ 1 / (60 + rank)`), **advanced** (vector candidates + cross-encoder
rerank), and **advanced + hybrid** (merged vector + keyword candidates, then rerank). If the model
service goes down, chat falls back to keyword search and flags the reply as `degraded`.

### 3. A chat message from start to finish

```mermaid
sequenceDiagram
    autonumber
    participant S as Student
    participant API as FastAPI
    participant G as Guardrails (NeMo)
    participant R as Router
    participant AG as Agent (LangGraph)
    participant T as Tools
    participant L as AI provider
    S->>API: POST /conversations/{id}/messages
    API->>API: rate limit, mask personal data, scan for injection
    API->>G: input rail
    G-->>API: allow / refuse
    API->>R: plan (max 2 agents)
    R-->>AG: study / quiz / planner / ...
    loop until final answer (max 8 tool calls)
        AG->>L: prompt + sources
        L-->>AG: tokens or tool call
        AG->>T: run tool as the student (RLS applies)
        T-->>AG: result (tool rails check it)
    end
    AG-->>API: stream events
    API->>API: sanitise output, strip unknown citations
    API-->>S: SSE events: meta, route, step, token, sources, safety, final, done
```

Any tool that would change something outside LearnLoom (adding, moving or deleting a calendar event)
**pauses the graph** until the student approves. The paused state is persisted in Postgres.

### 4. The agent graph

```mermaid
flowchart TD
    START([start]) --> GI["guard_input<br/>NeMo input rail"]
    GI -->|blocked| END1([refusal])
    GI --> RT["router<br/>small talk shortcut,<br/>else JSON plan"]
    RT --> A1["agent subgraph"]
    A1 -->|"plan has a 2nd step"| A2["next agent"]
    A1 --> END2([end])
    A2 --> END2

    subgraph agent_subgraph["inside one agent"]
        direction LR
        PRE["prepare"] --> MOD["model"]
        MOD -->|tool calls| TL["tools + rails"]
        TL --> MOD
        MOD -->|done| FIN["finish"]
    end
```

There are seven agents: **study**, **quiz**, **materials**, **planner**, **assignment**, **calendar** and **direct**.

### Tool reference

Each agent's tools: what they do, whether they write data, whether they need approval, and which chat card they render.

| Agent | Tool | What it does | Writes data? | Approval? | Chat card |
| --- | --- | --- | --- | --- | --- |
| `study` | `search_materials` | Searches the student's uploaded notes (vector search, then rerank) and returns numbered passages to cite. One search runs automatically before answering; the model may run one or two sharper follow-up searches. | No | No | None (sources appear under the answer) |
| `quiz` | `create_quiz` | Creates a quiz on a subject or topic. With at least 3 matching passages it's built from the notes; otherwise from general knowledge (labelled as such). Returns immediately while a background job writes the questions. | Yes (quiz + job) | No | `quiz` (title, basis label, Start button) |
| `quiz` | `start_quiz` | Opens an attempt on a ready quiz. | Yes (attempt) | No | `quiz_attempt` (link to the attempt) |
| `quiz` | `list_quizzes` | Lists recent quizzes with last scores. | No | No | None |
| `quiz` | `start_revision` | Builds a revision quiz from today's due flashcards, optionally for one subject. | Yes (quiz) | No | `quiz` (basis "revision") |
| `materials` | `list_materials` | Lists uploaded files (name, subject, status), optionally per subject. | No | No | `materials` (file list with download links) |
| `materials` | `read_material` | Reads part of a file (its start, a page, or the parts relevant to a question). Passages become numbered sources. | No | No | `material` |
| `materials` | `get_material_overview` | Returns passages spread evenly across a whole file so summaries cover all of it. | No | No | `material` |
| `planner` | `list_exams` | Lists saved exams with days remaining. | No | No | None |
| `planner` | `add_exam` | Saves an exam with its date and optional subject. | Yes | No | `exam` (date, days left) |
| `planner` | `list_tasks` | Lists planned study tasks in a date range (default: next two weeks). | No | No | `plan` (tasks grouped by day) |
| `planner` | `add_task` | Adds a study task on a given day (5–480 minutes). | Yes | No | `plan` |
| `planner` | `update_task` | Moves a task, changes its duration, or marks it done / skipped / cancelled. | Yes | No | None |
| `planner` | `generate_plan` | Runs the deterministic planner from exams, dated assignments, due flashcards and weak subjects, and saves the tasks. | Yes (tasks) | No | `plan` |
| `assignment` | `list_assignments` | Lists assignments with status and due date. | No | No | None |
| `assignment` | `get_assignment` | Reads one assignment with its brief and draft. | No | No | `assignment` |
| `assignment` | `add_assignment` | Saves a new assignment (title, brief, subject, due date). | Yes | No | `assignment` |
| `assignment` | `update_assignment` | Edits title, brief, due date or status, or saves the student's own draft verbatim. | Yes | No | None |
| `assignment` | `get_help` | Starts a coaching breakdown, outline or draft feedback in the background. Never writes the assignment. | Yes (help run) | No | `assignment_run` (fills in when ready) |
| `calendar` | `calendar_status` | Checks whether Google Calendar is connected. | No | No | `calendar_connect` only if disconnected or reconnect needed |
| `calendar` | `list_events` | Lists events on the "LearnLoom AI" calendar in a range (max 93 days) via the MCP server. | No (reads Google) | No | `calendar_events` |
| `calendar` | `add_event` | Proposes a new event. Nothing reaches Google until approved. | Yes, in Google, after approval | **Yes** | `calendar_proposal` (Approve, Edit, Cancel) |
| `calendar` | `move_event` | Proposes changing an event's day, time, duration or title. | Yes, in Google, after approval | **Yes** | `calendar_proposal` ("Now / Will become") |
| `calendar` | `remove_event` | Proposes deleting an event. | Yes, in Google, after approval | **Yes** | `calendar_proposal` |
| `quiz`, `materials`, `planner`, `assignment` | `list_subjects` | Lists subjects and how many processed files each has. | No | No | None |
| `direct` | none | Plain conversation: greetings, thanks, "what can you do?", general questions. | No | No | None |

**In short:** only the three calendar write tools ask for approval, because they're the only ones that
act outside LearnLoom. Every other write (quizzes, exams, tasks, assignments) stays inside the student's
own account and goes through the same route functions as the web UI, so RLS and rate limits still apply.
On top of that, the `tool_call` rail blocks any write tool carrying a link, an image URL or an
instruction that isn't in the student's own message. The planner agent deliberately has **no delete
tool**, so delete requests are politely declined. **Cards** are small interactive blocks stored with the
message, so they survive a page reload. Cards for background work (quizzes, assignment help) poll every
2.5 s for up to five minutes.

### Data model

```mermaid
erDiagram
    users ||--o{ subjects : owns
    subjects ||--o{ materials : contains
    materials ||--o{ chunks : "split into"
    materials ||--o{ ingestion_jobs : tracks
    users ||--o{ conversations : has
    conversations ||--o{ messages : has
    conversations ||--o{ agent_runs : "runs"
    agent_runs ||--o{ agent_steps : records
    subjects ||--o{ quizzes : "practice on"
    quizzes ||--o{ quiz_questions : has
    quizzes ||--o{ quiz_attempts : "taken as"
    quiz_attempts ||--o{ quiz_answers : holds
    users ||--o{ revision_cards : "due on"
    users ||--o{ exams : sets
    users ||--o{ assignments : tracks
    users ||--o{ study_tasks : plans
    users ||--o{ eval_datasets : "evaluates with"
    eval_datasets ||--o{ eval_runs : "measured in"
```

Every per-student table is protected by row-level security tied to the logged-in user. See
[DOC.md](DOC.md#4-database-and-multi-tenancy) for the details.

## Deploying to production

Production runs from `compose.prod.yaml`: Caddy handles HTTPS, secrets come from `.env.production`,
only ports 80 and 443 are exposed, containers are hardened (`no-new-privileges`, capabilities dropped
where possible), and backups are built in.

```bash
cp .env.production.example .env.production      # fill it in
scripts/prod.sh check                            # rejects weak or dev-only values
scripts/prod.sh up -d --build
```

Recommended reading order: [docs/runbooks/production.md](docs/runbooks/production.md) →
[docs/runbooks/backup-restore.md](docs/runbooks/backup-restore.md) → [docs/security.md](docs/security.md).
To load-test: `python scripts/loadtest.py https://your-domain --users 20 --seconds 60`.

## Evaluation

The goal is to measure, not guess. Two harnesses ship with the repo, both driven by `scripts/run-evals.ps1`.

| Harness | What it measures | Requirements | Cost |
| --- | --- | --- | --- |
| **RAG Lab** (`/eval` page) | Recall@1/3/5/10/K, Precision@K, Hit@K, MRR, citation validity and accuracy, AI-judged correctness and faithfulness, p50/p95 latency and tokens, per language, across **baseline**, **hybrid**, **advanced** and **advanced + hybrid** | Running stack, model service, uploaded corpus | Retrieval runs are free; a generation run uses tokens |
| **Dataset check** (`evals/verify_dataset.py`) | Confirms every evidence phrase of the 50 questions (26 English, 12 Hindi, 12 Gujarati; multi-fact, cross-lingual, unanswerable and prompt-injection) exists in the corpus | Python only | Free, offline |
| **Guardrail eval** | Input rail on 16 messages: blocks what it should, lets safe ones through, and how fast | Python only | Free, offline |
| **Live agent eval** | 53 cases through the real app: routing, tool use, task success, citations, latency, tokens (plus Ragas faithfulness and topic adherence with a judge) | Running stack + a test account with an AI key | Uses that key |

### Try it

```powershell
pip install -e ".[dev]"                       # once; add ".[eval]" for Ragas scores
.\scripts\run-evals.ps1                       # help: what every mode does and costs
.\scripts\run-evals.ps1 -Mode Offline         # dataset check + guardrail test (free, no stack needed)
.\scripts\run-evals.ps1 -Mode Agents -Limit 5 # live smoke test (asks for a TEST account; stack must be up)
.\scripts\run-evals.ps1 -Mode Rag             # checks the stack, then walks you through the RAG Lab
.\scripts\run-evals.ps1 -Mode Reports         # newest reports in evals\reports
```

To fill in the model-graded scores, add a judge:

```powershell
.\scripts\run-evals.ps1 -Mode Agents -JudgeProvider anthropic -JudgeModel claude-haiku-4-5
```

The RAG comparison lives in the web app because it runs on uploaded files. Create a subject, upload
`evals/corpus` and `evals/corpus/synthetic`, and import `evals/datasets/rag_v1.jsonl` at `/eval` (or
the bigger `rag_v2.jsonl`: 218 questions, 168 in English, same corpus). Run all four search modes
(retrieval only, free), then advanced with the judge, and click **Compare runs**. Never compare a run
flagged *degraded* (meaning the model service was down). More in [evals/README.md](evals/README.md) and
[docs/runbooks/agent-evaluation.md](docs/runbooks/agent-evaluation.md). Reports are written to
`evals/reports/` as `.md` and `.json`.

### How the agent harness works

Since chat is a router plus seven tool-calling agents, "the answer looks fine" isn't good enough. The
harness (`libs/agents/learnloom_agents/evaluation/`, cases in `evals/agents/agent_v1.jsonl`) sends real
messages through the real chat endpoint and checks what the system actually **did**, not only what it
said. Each case declares only the rules it cares about:

```json
{"id": "study-calvin", "category": "study", "message": "How does the Calvin cycle fix carbon dioxide?",
 "expect": {"agents": ["study"], "tools": ["search_materials"], "cites": true, "grounded": true,
            "answer_any": ["RuBisCO", "stroma"]}}
```

The 53 cases included:

| Category | Cases | Checks |
| --- | --- | --- |
| `study` | 11 | Factual questions route to the study agent, search the notes, cite a real `[n]` source and contain the expected facts |
| `guardrail` | 18 | Prompt injection (English, Hindi, Gujarati), self-harm crisis, weapon requests, seven harmless look-alikes (idioms, a sociology question, security study) and two indirect injections hidden in uploaded notes. **16 run offline**; the two indirect ones need the live app |
| `planner` | 5 | Exam, task and plan tools fire with the right card, and delete requests are declined (no delete tool exists) |
| `direct`, `quiz`, `materials`, `assignment`, `calendar`, `routing` | 4, 4, 2, 2, 3, 1 | Greetings go to the direct agent without searching, quizzes produce a quiz card, calendar changes **wait for approval**, and a two-part request (quiz + plan) is split across two agents |
| `off_topic` | 3 | Recipe, cricket and phone-shopping requests get a polite decline (judge-scored, so `n/a` without a judge) |

Per-run scores:

| Score | Computed as | Needs a model? |
| --- | --- | --- |
| **Routing** | Exact agent set matches and the first agent matches; confusion matrix per agent | No |
| **Tools** | Tool recall (required tools called), forbidden tools never called, calls per run, tool failures | No |
| **Task success** | Every rule in the case holds (no error, cards, answer words, approval state), broken down by category and failure type | No |
| **Guardrails** | Recall on must-block messages, false-block rate on safe ones, precision, second opinions used | No |
| **Grounding** | Share of factual answers citing a source, and that every cited number is a real source the agent saw; Ragas *faithfulness* with a judge | Faithfulness only |
| **Topic adherence** | Ragas `AspectCritic`: off-topic requests declined politely rather than fulfilled | Yes |
| **Speed & cost** | Time to first token and to completion (p50/p95), tokens per run, median time per agent | No |

Two modes:

- **Offline** (`-Mode Guardrails`): the 16 guardrail cases run through the input rail only, with no
  server, model, key or network needed. It's quick and deterministic enough for every change. With no
  model available, a prompt-injection takeover phrase is *expected to pass the rules* offline (marked
  with `guard_offline`); whether the model's second opinion blocks it is only measured live.
- **Live** (`-Mode Agents`): every case through the running app, using a **dedicated test account**
  with an AI key. Seven cases modify data (planner, quizzes) and are skipped unless you pass
  `-AllowWrites`, and two need Google Calendar connected. The judge model is picked independently of
  the model under test, because self-grading inflates scores.

```powershell
.\scripts\eval-agents.ps1                                          # the whole thing: offline + live, 5 batches, prints the metrics
.\scripts\eval-agents.ps1 -Delay 10 -BatchPause 180                # gentler on a free AI plan (rate limits)
.\scripts\run-evals.ps1 -Mode Guardrails                           # 16 cases, free
.\scripts\run-evals.ps1 -Mode Agents -Category routing -Limit 3     # tiny live run
.\scripts\run-evals.ps1 -Mode Agents -AllowWrites `
    -JudgeProvider anthropic -JudgeModel claude-haiku-4-5           # full run with judged scores
```

Free-tier providers cap requests per minute, and a single case can make several model calls. So the
live run splits cases into batches (`--batches`, default 5 in `eval-agents.ps1`), waits `--batch-pause`
seconds between batches and `--delay` seconds after each case, and retries rate-limited cases once at
the end. Anything still refused is reported as *skipped*, not failed. `-Part n` runs a single batch
with its own report, which helps when spreading a small quota over several days.

To add a case, append a JSON line to `evals/agents/agent_v1.jsonl` using only the keys in
`KNOWN_EXPECT` (`agents`, `tools`, `forbid_tools`, `cards`, `answer_any`, `answer_all`,
`answer_none`, `guard`, `guard_offline`, `awaiting_approval`, `grounded`, `cites`, `on_topic`,
`max_ms`, `error`). Unknown keys are rejected at load time, so a typo can't slip through as a pass.

### Results

Every figure below comes from real runs on a single dev machine (Windows, Docker Compose, model service
on the host). Each is **one run** on a **small set**. Treat these numbers as directional, not as benchmarks.

#### Retrieval (RAG Lab, November 2026)

Retrieval only (no generation), on the English set `evals/datasets/rag_v2_en.jsonl`: 168 questions, 153
answerable and 15 deliberately unanswerable, across seven documents (MCP, agent harness, prompt and
context engineering, KNN, a multi-step agent deck, English tenses, and the 150,000-character Qwen3-VL
report). Same corpus, model service and questions for all four modes; **K = 10 passages kept** from 30
candidates; one run each. So Recall@K here means Recall@10.

| Mode | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Precision@10 | Hit@10 | MRR | Median search | p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline (vector only) | 53% | 77% | 82% | 91% | 11% | 92% | 0.68 | 48 ms | 65 ms |
| hybrid (vector + BM25, RRF) | 61% | 83% | 90% | 94% | 12% | 95% | 0.75 | 214 ms | 255 ms |
| **advanced** (vector → rerank; used by chat) | **76%** | **91%** | **93%** | **95%** | 12% | **96%** | **0.86** | 542 ms | 765 ms |
| advanced + hybrid (vector + BM25 → rerank) | 77% | 92% | 94% | 97% | 13% | 97% | 0.87 | 649 ms | 864 ms |

What we learned:

- **Reranking mostly fixes ordering rather than finding new passages.** Vector search already has the
  right passage in its top 10 for 91% of questions, but ranks it first only 53% of the time. Reranking
  takes Recall@1 from 53% to 76% (+23 pts) and Recall@3 from 77% to 91%, while Recall@10 only goes from
  91% to 95%. That's why chat reranks: LLMs pay the most attention to the first sources.
- **Hybrid helps once keyword ranking is done right.** Merging BM25 hits with vector hits beats vector
  alone on every metric (Recall@1 +8, Recall@3 +6, Recall@5 +8, Recall@10 +3, MRR +0.07), with the gap
  shrinking as K grows. It costs roughly 4.5× the search time.
- **Keyword candidates in the reranker didn't move the needle.** Advanced + hybrid lands within 0.6–1.6
  points of plain advanced everywhere (one question ≈ 0.65 points, so that's one to three questions)
  for ~110 ms extra per search. Chat sticks with the cheaper vector candidates.
- **A handful of questions are never found.** Even the best mode misses the evidence in its top 10 for
  ~3% of answerable questions (four or five). They haven't been investigated yet; it could be the
  retriever or the evidence phrase.
- **Low Precision@K is expected.** With 10 results and one or two evidence passages per question, even
  a perfect system tops out around 10–20%. Compare modes against each other, not against 100%.
- **Latency scales with the method**: roughly 50, 200, 540 and 650 ms median. Next to the seconds an
  LLM takes to respond, the reranker's cost is a fair price for accuracy.

Earlier runs, kept for history. First, the same 168 questions at **K = 6** (three modes; the last row is
advanced + hybrid, run before the Lab had a dedicated mode for it). Precision, Hit and MRR are computed
over the kept passages, so they aren't comparable with the K = 10 table:

| Mode | Recall@1 | Recall@3 | Recall@6 | Precision@6 | Hit@6 | MRR |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (vector only) | 53% | 77% | 85% | 17% | 86% | 0.67 |
| hybrid (BM25) | 61% | 83% | 92% | 19% | 93% | 0.75 |
| advanced + hybrid | 77% | 92% | 96% | 20% | 96% | 0.87 |

And the original, smaller English set (`rag_v1_en.jsonl`, 26 questions, 23 answerable, K = 6). There,
one question was worth ~4 points, which is why it was retired as the headline:

| Mode | Recall@1 | Recall@3 | Recall@K | Precision@K | Hit@K | MRR |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (vector only) | 54% | 89% | 89% | 21% | 91% | 0.73 |
| hybrid, keyword leg ranked by Postgres `ts_rank_cd` | 54% | 72% | 85% | 18% | 87% | 0.67 |
| hybrid, keyword leg ranked by BM25 | 59% | 85% | 93% | 23% | 96% | 0.74 |
| advanced (vector candidates, then rerank) | 80% | 98% | 98% | 25% | 100% | 0.90 |

With Postgres's built-in keyword ranking, hybrid actually looked *worse* than vector-only on the small
set; the larger set shows hybrid with BM25 clearly ahead. Search times fluctuate between runs (advanced
measured 976, 499, 628 and 542 ms across four runs), so only compare times within a single run.

Caveats: the headline table is English only. A Hindi and Gujarati set exists in `rag_v2.jsonl`, but its
wording was AI-generated and hasn't been reviewed by native speakers, so no Hindi/Gujarati numbers are
quoted. Each mode was run once, the questions were drafted by Claude against the same documents rather
than collected from real students, and answer quality (correctness, faithfulness) wasn't part of this
run. Re-run the Lab with a judge model to get those.

#### How retrieval got better, iteration by iteration

1. **Start simple.** Embed the question with BGE-M3 and take the nearest chunks by cosine distance
   (baseline). The right passage is in the top 3 about 77% of the time and in the top 10 about 91%, but
   ranked first only ~53%, and the LLM reads the top sources most closely.
2. **Try keyword + vector fusion** (hybrid, RRF). Using Postgres's `ts_rank_cd`, the small set showed no
   gain (Recall@3 72% vs 89%), so it wasn't adopted. Suspecting the keyword ranking itself, we added a
   proper BM25 ranker (IDF, length normalisation, common question words dropped when picking candidates).
   On the larger set, hybrid + BM25 beat vector-only everywhere (Recall@1 53% → 61%, Recall@10 91% → 94%,
   MRR 0.68 → 0.75). That's exactly what the Lab is for: test an idea, drop it, diagnose, re-test on
   evidence. Two things changed together (BM25 scoring and the stop-word filter), so their individual
   impact isn't isolated.
3. **Add a cross-encoder reranker** (advanced). Fetch 30 vector candidates, score each against the
   question with `bge-reranker-v2-m3`, keep the best. On the larger set: Recall@1 53% → 76%, Recall@3
   77% → 91%, MRR 0.68 → 0.86, Recall@10 91% → 95%.
4. **Feed keyword candidates to the reranker too** (advanced + hybrid): Recall@1 77% vs 76%, Recall@10
   97% vs 95%, for ~110 ms more. That's within noise, so chat keeps the simpler vector candidates.
5. **Keep a safety net.** If the model service is down, chat falls back to keyword search and labels the
   answer *degraded*; Lab runs made in that state are flagged and excluded from comparison.
6. **Harden retrieved text before it reaches the model.** Sources are numbered, neutralised against
   prompt injection and PII-masked, and the server verifies that every `[n]` the answer cites is a real source.

#### Agent evaluation (31 October 2026)

All 53 cases ran through the real chat API under a test account, in five batches to stay under the
provider's rate limit. Model under test: Groq `openai/gpt-oss-20b`, with no judge model. 51 cases ran;
2 were skipped because they need a connected Google Calendar. This baseline was taken before the fixes
listed further down.

| Metric | Result |
| --- | --- |
| Task success (every rule in the case holds) | **47 / 51 (92%)** |
| Routing, exact agent set | 31 / 31 |
| Required tool was called | 11 / 13 (missed `start_revision` in quiz-revise and `add_assignment` in assignment-add; both times the agent asked a clarifying question instead) |
| Forbidden tool used | 0 / 11 |
| Guardrails: must-block messages | 9 / 9 blocked (5 prompt injections, 3 crisis messages, 1 weapon request) |
| Guardrails: safe messages wrongly blocked | 0 / 12 |
| Factual answers citing a real source | 4 / 5 (study-mnemonic used the full-width mark `【1】`) |
| Time to finish, median / p95 | ~2.4 s / 21.6 s |
| Time to first token, median / p95 | ~2.1 s / 16.5 s |
| Tokens per run | ~3,000 |

Per category: study 9/11, quiz 3/4, materials 2/2, assignment 1/2, planner 5/5, direct 4/4, guardrail
18/18, calendar 1/1, routing 1/1, off_topic 3/3.

How to read these:

- **Off-topic "3/3" doesn't count.** Those rules are judge-scored and no judge was set, so they passed
  by default. In reality the recipe and phone-shopping answers were given in full, which is a **known
  weakness**: the direct agent happily helps with non-study requests.
- **`study-unanswerable` was marked failed, but the reply was a correct refusal.** The checker matched
  a narrow set of phrases and missed a curly apostrophe. It's been fixed since. The figure above is the
  original record, with two cases (materials-summary, guard-indirect) replaced by clean re-runs that
  both passed. Re-running study-unanswerable with the fixed checker should pass, giving 48 / 51.
- **The three genuine misses** were study-mnemonic (citation mark), quiz-revise and assignment-add
  (the agent asked instead of acting).
- **Guardrails:** all 9 must-block messages were stopped live, including the five prompt-injection
  phrasings that depend on the model's second opinion (10 second opinions were used), and all 12 safe
  messages got through. It's a small set, not proof that nothing can slip past.
- One run, one model, small sample, so a case or two can flip between runs. Speed depends on provider
  load and rate-limit waits.

Offline guardrail suite (no server, no model): **16 / 16 passed**. 4 must-block messages were blocked,
12 allowed, none wrongly stopped; median 14 ms, p95 436 ms. Reports are in [`evals/reports/`](evals/reports).

#### Bugs the evaluation caught

Running the harness surfaced real defects, and each one has been fixed. Their *effect* on the scores
above will be reported after a before/after rerun (`scripts/compare-eval-reports.ps1`).

| Caught by | Problem | Fix |
| --- | --- | --- |
| study-mnemonic | Model wrote citations as `【1】` instead of `[1]`, so the source wasn't recognised | `normalize_citation_marks` converts full-width marks to `[n]` before saving or display (code spans untouched) |
| study-unanswerable | A correct "the notes don't cover this" was scored wrong | Checker accepts more refusal phrasings and normalises curly quotes and dashes |
| Eval harness | Test subjects were never deleted (delete needs `confirm=true`), and duplicates broke later cases | Cleanup passes `confirm=true`; `eval-agents.ps1 -CleanLeftovers` clears old ones |
| Rate-limit / crash runs | A single 429 or an API restart lost the whole report | Batching, delays, a retry pass, per-case error handling and partial reports |
| Dashboard on a fresh account | "Something went wrong" (a component function passed from a server to a client component) | Pass an element instead of a component |

To measure the effect, rebuild (`docker compose up -d --build api web`), run
`.\scripts\eval-agents.ps1 -Delay 40 -BatchPause 120`, then
`.\scripts\compare-eval-reports.ps1 -Label "citation marks fix"`.

## Quality checks

Around 1,000 test functions cover the API, workers, pure-logic libraries, agents and guardrails. Tests
that need a migrated database skip themselves when it isn't available. API tests create disposable
users under `@learnloom-tests.dev` and clean them up afterwards, and `test_protected_routes.py` fails if
a new route forgets to require authentication.

```powershell
.\scripts\check.ps1            # lint + types + tests + OpenAPI check (Python side)
.\scripts\check.ps1 -Web       # also type-check and build the web app
```

Or run them manually (stack running, `pip install -e ".[dev]"` once):

```bash
cp .env.example .env
ruff check .
mypy -p learnloom_core -p learnloom_agents -p learnloom_api -p learnloom_worker -p learnloom_models
pytest
python scripts/export_openapi.py --check
cd apps/web && pnpm typecheck && pnpm build
```

CI (`.github/workflows/ci.yml`) runs the same checks against a real `pgvector/pgvector:pg16` service on
every pull request and every push to `main`.

If you change an API route or response shape, regenerate the contract with
`python scripts/export_openapi.py` and commit it. If you edit the student guide, run
`python scripts/build_guide_docs.py` to refresh the printable copies in `docs/`.

## Further reading

| Doc | What's inside |
| --- | --- |
| [DOC.md](DOC.md) | Every module, algorithm, formula and design decision, plus why each technology was chosen |
| [docs/security.md](docs/security.md) | What protects what, and the launch checklist |
| [docs/agents.md](docs/agents.md) | The agent layer |
| [evals/README.md](evals/README.md) | Evaluation datasets, corpus and how to run them |
| [docs/adr/](docs/adr) | Architecture decision records |
| [docs/runbooks/](docs/runbooks) | Production, backup/restore, admin, Google setup, agent evaluation |
| [Student guide](docs/student-guide.en.md) | ([हिन्दी](docs/student-guide.hi.md) · [ગુજરાતી](docs/student-guide.gu.md)) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to work on the project |

## Current limits

- Uploads are capped at 50 MB (`MAX_UPLOAD_MB`) and 100 scanned pages (`MAX_OCR_PAGES`). Images embedded
  in slides and Word files aren't OCR'd, and there's no per-student storage quota yet.
- Emails are English-only, and there's no account-deletion or email-change screen yet.
- Answers aren't fact-checked after generation; the Evaluation Lab measures how well they're grounded.
- Rate limiting uses the client IP from `X-Forwarded-For`. That's safe with the shipped production
  layout (Caddy overwrites the header) but spoofable if you expose the app another way.
- The production compose file, the model-service Dockerfile and the backup scripts have been checked
  statically (and their database parts against a real Postgres) but not yet run on a live server. Do a
  trial install and a practice restore first.
- The bundled storage (RustFS) is pre-1.0; in production you can use any hosted S3-compatible bucket.
- **The Hindi and Gujarati text is AI-written** (UI in `apps/web/src/i18n/messages`, guide in
  `apps/web/src/content/guide`). Get native speakers to review both before real students use them.

**Hardware tip (4 GB GPU, 16 GB RAM):** the model service loads BGE-M3 in half precision with batch
size 8 and 512-token inputs. The reranker loads lazily and falls back to CPU if the GPU runs out of
memory. Cap WSL2 memory at about 8 GB in Docker Desktop or `.wslconfig`.

## Contributing, credits & licence

Contributions are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md). Please report security issues privately to the maintainer rather than in a public issue.

Released under the [MIT licence](LICENSE).
