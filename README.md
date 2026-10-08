# Personal AI Operating System

A local-first Personal AI system built with Python, Ollama, ChromaDB, semantic memory, and Retrieval-Augmented Generation (RAG).

The goal of this project is to build an AI assistant that can remember useful information, understand documents, retrieve relevant knowledge, and gradually evolve into a complete AI operating system.

---

## Current Features

- Long-term semantic memory
- User profile management
- Local LLM using Ollama
- Local embeddings using `nomic-embed-text`
- ChromaDB vector storage
- Semantic memory retrieval
- Memory classification and management
- PDF, DOCX, and TXT parsing
- Page-aware document processing
- Sentence-aware document chunking
- Document embeddings
- Retrieval-Augmented Generation (RAG)
- Source filename and page references
- Multi-document indexing
- Duplicate document detection
- File change detection using hashes
- Recursive folder indexing
- Automatic file monitoring using Watchdog
- Automatic re-indexing when a document changes
- Automatic vector removal when a document is deleted

---

## Architecture

```text
Documents / Approved Folders
            |
            v
       File Watcher
            |
            v
          Parser
            |
            v
         Chunking
            |
            v
        Embeddings
            |
            v
         ChromaDB
            |
            v
        Retriever
            |
            v
        Ollama LLM
            |
            v
     Context-Aware Answer
```

Personal memory is stored separately from document knowledge using different ChromaDB collections.

---

## Tech Stack

**Language**
- Python

**Local AI**
- Ollama
- Llama 3.2

**Embeddings**
- Nomic Embed Text

**Vector Database**
- ChromaDB

**Document Processing**
- PyPDF
- python-docx

**File Monitoring**
- Watchdog

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ojhaprabhat1247/personal-ai.git
cd personal-ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama

Install Ollama on your system before running the AI.

### 5. Download the required models

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

---

## Required Ollama Models

The chat model defaults to `llama3.2`. Set `PERSONAL_AI_MODEL` before starting
the backend or CLI to use another installed Ollama chat model. This configures
the local provider resource; the four privacy policies remain routing policies.

| Model | Purpose |
|---|---|
| `llama3.2` | Local language model |
| `nomic-embed-text` | Text embeddings for semantic search |

---

## Chat Prototype

From the repository root, run the backend with the project's Python environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir app --host 127.0.0.1 --port 8000
```

Run `npm install` and `npm run dev` from `frontend` for the React UI. The frontend
uses `http://127.0.0.1:8000` by default; `VITE_API_BASE_URL` can override it.
The CLI remains available through `python app/main.py` from the repository root.

Both `POST /chat` and `POST /chat/stream` accept `message` and optional
`privacy_mode` (`auto`, `privacy_first`, `local_only`, `max_quality`). `/chat`
retains its JSON response. `/chat/stream` sends SSE frames over a POST fetch:

- `delta`: `{ "text": "..." }`
- `done`: `{ "privacy_mode": "auto", "sensitive": false, "sensitivity_reasons": [] }`
- `error`: `{ "code": "generation_failed", "message": "..." }`

A stream succeeds only on `done`. Partial output is not saved as a completed
turn, and fallback never appends a second provider's answer after visible text.
Provider streams use the existing Ollama-shaped chunks, including a terminal
`done: true` marker; future adapters should preserve that contract.

This remains one shared conversation history per backend process. Turns are
serialized; refreshing the browser clears its visible transcript but does not
clear persisted history. **New Chat** calls `POST /chat/reset`, which resets only
the active conversation and its saved history, retaining the base instructions.
It preserves profile, long-term semantic memory, indexed documents, Chroma data,
and approved-folder settings. The UI resets only after the backend confirms
success; a failed reset retains the transcript and shows an error. All browser
tabs connected to this single-process prototype share the same backend history.
Run one backend worker; independent CLI/backend processes do not synchronize
their in-memory histories.

Disconnect cleanup can wait for an outstanding synchronous operation. Local
chat-model reads time out after 120 seconds without data. Response quality and
language/length compliance remain model-dependent even with a fresh chat.

Focused checks (fake providers/storage; no real memory or Chroma writes):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_chat.py -v
cd frontend
npm test
npm run lint
npm run build
```

---

## Document Intelligence

The document pipeline currently supports:

```text
PDF
DOCX
TXT
```

Documents are parsed, divided into meaningful chunks, converted into embeddings, and stored inside ChromaDB.

The RAG pipeline retrieves relevant chunks before generating an answer, allowing the assistant to answer questions using indexed documents.

Where available, answers can also include the source filename and page number.

---

## Automatic Document Indexing

The file watcher monitors supported documents recursively.

When a supported file is:

```text
Created  -> Index document
Modified -> Re-index changed document
Deleted  -> Remove document vectors
```

SHA-256 file hashes are used to avoid unnecessary duplicate indexing.

---

## Local-First Design

The current system uses a local ChromaDB persistent database and local Ollama models.

```text
data/chroma/
```

contains the local vector database used by the application.

Local database files and personal data should not be committed to the repository.

---

## Roadmap

Planned development includes:

- Excel document support
- Image understanding
- OCR for scanned documents
- Resume analysis
- Invoice analysis
- Contract analysis
- Research-paper analysis
- Multi-document comparison
- Configurable approved system folders
- Improved file synchronization
- Report generation
- Email drafting from documents
- Tool calling
- AI agent workflows
- FastAPI backend
- React frontend
- Authentication
- Multi-user architecture
- Docker
- Cloud deployment
- Automated testing
- CI/CD
- Logging and monitoring

---

## Project Goal

The long-term goal is to develop a Personal AI Operating System capable of combining:

```text
Memory
+
Personal Profile
+
Document Intelligence
+
Semantic Search
+
RAG
+
AI Agents
+
Tools
+
Automation
```

while maintaining a local-first and privacy-aware architecture.

---

## Author

**Prabhat Ranjan**

AI & Software Development | Building a Personal AI Operating System
