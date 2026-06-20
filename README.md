# Document Q&A Bot (RAG)

This project is a Streamlit Retrieval-Augmented Generation (RAG) bot. It
indexes local PDF, DOCX, TXT, and Markdown files, retrieves semantically relevant
passages for a question, and asks Google Gemini to produce a
grounded answer with filename and page/section citations.

## Tech stack

- Python 3.11+
- pypdf 6.13.3 — page-level PDF extraction
- python-docx 1.2.0 — DOCX extraction
- langchain-text-splitters 0.3.8 — recursive semantic chunking
- scikit-learn 1.9.0 — deterministic local n-gram hashing embeddings
- ChromaDB 1.5.9 — persistent cosine-similarity vector store
- python-dotenv 1.2.2 — environment configuration
- Streamlit 1.52.2 — interactive web interface
- Google Gen AI SDK 2.9.0 — Gemini answer generation

## Architecture

```text
data files -> extraction + metadata -> overlapping chunks -> embeddings -> ChromaDB
                                                                        |
user question -> query embedding -> top-k similarity search ------------+
                                          |
                              grounded prompt + citations -> Gemini -> answer
```

The indexing and query paths are deliberately separate. `src/ingest.py` reads,
chunks, batch-embeds, and persists documents in `db/`; `src/query.py` opens that
existing store for retrieval and generation. `app.py` provides the Streamlit
interface, `src/main.py` retains an optional CLI, and `src/config.py` centralizes
settings.

## Chunking strategy

The indexer uses recursive character splitting. It prefers paragraph, line,
sentence, and word boundaries before falling back to character boundaries.
Chunks default to 1,000 characters with 150 characters of overlap, which keeps
nearby context around boundaries without returning whole pages. Every chunk
retains its source filename, page or section, and chunk number.

## Embeddings and vector database

A 4,096-dimensional `HashingVectorizer` creates local word and phrase n-gram
embeddings. It has no fitted vocabulary, so indexing and queries always use the
same vector space without a model download. ChromaDB stores vectors on disk in
`db/` and uses cosine distance. All chunks are embedded in one batch. This
lightweight choice is reliable on Python 3.11+ but captures lexical similarity
less well than a neural embedding model.

## Project structure

```text
Intern_work/
|-- .env.example
|-- .gitignore
|-- app.py                # Streamlit web interface
|-- requirements.txt
|-- README.md
|-- data/                 # 4–5 knowledge-base documents belong here
|-- db/                   # generated persistent index; gitignored
`-- src/
    |-- __init__.py
    |-- config.py
    |-- ingest.py
    |-- query.py
    `-- main.py
```

## Setup

1. Clone the repository and enter its directory.
2. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create a Gemini API key in Google AI Studio.
5. Copy `.env.example` to `.env` and replace the placeholder `GEMINI_API_KEY`,
   or enter the key in the masked Streamlit sidebar field.
6. Put four or five meaningful source documents in `data/` (at least one PDF).
7. Start the Streamlit application:

   ```powershell
   streamlit run app.py
   ```

8. Open the displayed local URL and select **Rebuild document index** in the
   sidebar before asking questions.

The CLI remains available as an alternative:

   ```powershell
   python -m src.main index --rebuild
   python -m src.main chat
   ```

A one-off CLI query is also supported:

```powershell
python -m src.main ask "What are the main conclusions?" --top-k 4
```

Later runs reuse the persisted Chroma database and require no embedding download.

## Environment variables

Retrieval and embeddings run locally. Gemini generation requires an API key.
Supported settings are:

| Variable | Default | Purpose |
|---|---|---|
| `CHUNK_SIZE` | `1000` | Maximum chunk size in characters |
| `CHUNK_OVERLAP` | `150` | Context shared by adjacent chunks |
| `TOP_K` | `4` | Number of chunks retrieved |
| `EMBEDDING_DIMENSIONS` | `4096` | Size of local hashing embeddings |
| `GEMINI_API_KEY` | none | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini generation model |

Never commit `.env`; it is included in `.gitignore`.

## Example queries

- “What is the central argument of the first document?” — expect its main thesis.
- “Which recommendations appear across multiple documents?” — expect a synthesis.
- “What evidence supports the reported conclusion?” — expect cited evidence.
- “How do the documents differ in their proposed approaches?” — expect comparison.
- “What limitations do the authors identify?” — expect cited limitations.
- “Who won the 2030 World Cup?” — expect the not-found response when absent.

## Known limitations

- Scanned PDFs need OCR before this parser can extract their text.
- Hashing embeddings favor lexical overlap and can miss paraphrases that a neural
  embedding model would retrieve.
- Gemini generation requires internet access, a valid API key, and available API
  quota.
- Page citations are available for PDFs; DOCX/TXT/Markdown use section numbers.
- Updating or deleting source files requires `index --rebuild` to remove stale chunks.

## Included document collection

The `data/` directory contains four substantive documents totaling more than
5,000 extracted words: one PDF, one DOCX, and two TXT files. Each exceeds the
assignment's 500-word or two-page minimum.

The remaining submission work is external to the codebase: publish the project
with a clean multi-commit history and record a 3–8 minute live demonstration
showing indexing, five answerable questions, one unanswerable question,
retrieved chunks, and citations.
