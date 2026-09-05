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

| Model | Purpose |
|---|---|
| `llama3.2` | Local language model |
| `nomic-embed-text` | Text embeddings for semantic search |

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