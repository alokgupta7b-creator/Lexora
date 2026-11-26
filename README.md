# Lexora: Research Paper AI Risk Analyzer, Rephraser & Humanizer

Lexora is a full-stack research writing assistant for analyzing stylistic risk and readability, rephrasing text while preserving citations, and reviewing publication readiness.

---

## 🚀 Key Features

* **Doc Parser**: Automatically uploads and segmentates PDF, DOCX, and TXT papers into standard sections: Abstract, Introduction, Methodology, Results, and Conclusions.
* **Explainable Stylistic Risk Engine**: Rather than claiming AI detection certainty, the system runs 14+ linguistic checks (Type-Token Ratio, passive verbs count, transition overuses, cliché patterns) and gives explainable reasons for every flagged sentence.
* **Interactive Style Highlighter**: Sentence-by-sentence color audits (Green, Yellow, Orange, Red) representing risk, complete with sidebar inspect widgets and direct humanizer hotkeys.
* **Preserving Paraphraser**: Rephrases scientific paragraphs in 8 styles (Journal style, Technical, Concise, etc.) while preserving LaTeX math formulas (`$...$`) and academic citation matrices (`[1]`, `Smith et al., 2020`).
* **Pacing Humanizer**: Automatically injects structural length variances (burstiness) and strips stilted ChatGPT/Claude transitional headers.
* **Plagiarism-Safe Similarity HUD**: Evaluates Jaccard overlap ratios between original and rewritten blocks to ensure plagiarism safety.
* **Publication Readiness Audit**: Generates combined grammar, structure, readability, and style indexes to output a readiness grade out of 100.
* **Report compiler**: Generates elegant printable PDF, Word (DOCX), or Text (TXT) audits for researchers.

---

## 🛠 Tech Stack

* **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts, Lucide Icons.
* **Backend**: FastAPI, Python 3.12, PyMuPDF (fitz), python-docx, ReportLab.
* **Database**: PostgreSQL (SQLAlchemy backend engine).
* **Caching**: Redis.
* **DevOps**: Docker, Docker Compose, environment configurations.

---

## 📂 Folder Layout

```
ai-detection-for-research/
├── backend/
│   ├── app/
│   │   ├── config.py              # Settings, directories, S3/API configuration
│   │   ├── main.py                # FastAPI entry point, middlewares, routers mounting
│   │   ├── auth/
│   │   │   └── security.py        # Password hashes, JWT tokens, OAuth SSO logic
│   │   ├── db/
│   │   │   ├── session.py         # DB connection pools, engines
│   │   │   └── models.py          # Tables: Users, Docs, Analyses, Reports, Logs
│   │   ├── schemas/
│   │   │   └── schemas.py         # Pydantic data schemas
│   │   ├── services/
│   │   │   ├── doc_parser.py      # PDF/Docx parser, academic regex separators
│   │   │   ├── readability.py     # Formulas: Flesch Ease, FK Grade, Fog, SMOG
│   │   │   ├── analyzer.py        # AI Risk analyzer, lexical diversities, passive voices
│   │   │   ├── rephraser.py       # Synonym rewrites, citations preservation tokens
│   │   │   ├── humanizer.py       # Burstiness injections, cliche filters, before/after HUD
│   │   │   └── reporter.py        # ReportLab PDF compile, Docx paragraphs builder
│   │   └── routes/
│   │       ├── auth.py            # Endpoints: /register, /login, /google sso
│   │       ├── documents.py       # Endpoints: /upload, /analyze, /rephrase, /report
│   │       └── admin.py           # Endpoints: /users, /system-stats telemetry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── layout.tsx             # HTML wrappers, SEO meta keywords
│   │   ├── globals.css            # Dark mode tokens, glassmorphisms, pulse glows
│   │   ├── page.tsx               # Root redirects (checks token)
│   │   ├── login/
│   │   │   └── page.tsx           # Premium SSO and standard auth cards
│   │   ├── dashboard/
│   │   │   └── page.tsx           # Workspace listings, histories, Recharts
│   │   ├── analyze/
│   │   │   └── page.tsx           # Audit panel, section pickers
│   │   ├── rephrase/
│   │   │   └── page.tsx           # parphrase workbenches, copying HUD
│   │   └── admin/
│   │       └── page.tsx           # Server resources, user suspensions
│   ├── components/
│   │   ├── navbar.tsx             # Dynamic navigation, logouts, theme togglers
│   │   ├── sidebar.tsx            # Dashboard panel lists
│   │   ├── file-upload.tsx        # Stateful drop uploader, sizes check
│   │   └── sentence-highlighter.tsx # Highlighting blocks, sidebar detail widgets
│   ├── package.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 📈 Linguistic Risk Algorithms

Lexora analyzes structural markers to profile AI writing characteristics:

1. **Lexical Diversity (Type-Token Ratio)**:
   $$\text{TTR} = \frac{\text{Unique Words}}{\text{Total Words}}$$
   LLMs display significantly lower TTR values because they consistently optimize for high-probability tokens.
2. **Burstiness (Length variance Coefficient)**:
   $$\text{Burstiness} = \frac{\sigma_{\text{lengths}}}{\mu_{\text{lengths}}}$$
   Human paragraphs exhibit large variance (combining short, punchy statements with complex clauses). LLMs output highly uniform sentence lengths.
3. **Passive Voice Frequency**:
   Regex pattern checking for auxiliary verbs followed by a past participle (e.g., `is demonstrated`, `was utilized`). Overuse increases AI risk indicators.
4. **Generic LLM Cliché Density**:
   Matches 40+ precompiled LLM cliché words and expressions (such as `tapestry`, `delve`, `testament`, `it is important to note`, `rapidly evolving`).

---

## 🚀 Getting Started

### Option A: Launch with Docker Compose (Recommended)

Make sure Docker is installed. Copy `.env.example` to `.env`, then set unique
values for `SECRET_KEY` and `POSTGRES_PASSWORD`. Generate the signing key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start the services with:

```bash
docker compose up --build
```

This single command will spin up:
1. **PostgreSQL** on port `5432`
2. **Redis** caching on port `6379`
3. **FastAPI backend** on port `8000` (complete with API interactive docs on `http://localhost:8000/docs`)
4. **Next.js 15 frontend** on `http://localhost:3000`

---

### Option B: Local Manual Setup (For Development)

#### 1. Setup Backend
Open a terminal in the `backend/` directory:

```bash
# Create and activate python environment
python -m venv venv
venv\Scripts\activate      # Windows

# Install libraries
pip install -r requirements.txt

# Run main development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Setup Frontend
Open a terminal in the `frontend/` directory:

```bash
# Install node packages
npm install

# Launch Next.js dev server
npm run dev
```
Open `http://localhost:3000` to interact with the application dashboard.

---

## 🧪 Interactive API Documents

Once the backend is online, navigate to:
* **Swagger Interactive HUD**: `http://localhost:8000/docs`
* **Redoc documentation**: `http://localhost:8000/redoc`

### Core endpoints list:
* `POST /api/v1/auth/register` - Registers a new credentials account
* `POST /api/v1/auth/login` - Authenticates session and retrieves JWT token
* `POST /api/v1/auth/google` - Simulates OAuth Single Sign-on
* `POST /api/v1/upload` - Uploads research documents and extracts sections
* `POST /api/v1/analyze/{doc_id}` - Audits complete AI risk profiles
* `POST /api/v1/rephrase` - Restructures text, preserving formulas
* `POST /api/v1/humanize` - Varies sentence pacing and removes AI signatures
* `POST /api/v1/report/{doc_id}` - Exports printable PDF/Word assessments

---

## 📄 License & Integrity Guidelines

Lexora is designed to serve as a writing optimization assistant. We recommend that users always maintain complete control over their final research text and utilize the tool to optimize academic clarity and syntactic variety rather than bypass ethical boundaries.
