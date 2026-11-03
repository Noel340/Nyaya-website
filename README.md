# NyayaGuide — AI-Powered Indian Legal Awareness Platform

> **"Know Your Rights. Understand Your Law."**
> A source-grounded, privacy-first legal awareness and rights guidance assistant designed for citizens of India.

NyayaGuide helps ordinary people in India describe what happened to them using everyday words or speech input, understand potentially applicable constitutional articles and statutory sections in simple English, discover which category of lawyer to contact, and access verified legal-aid resources (such as NALSA and official dispute portals).

---

## 🏛️ Brand Identity & Design

Inspired by the 75th year of the Constitution of India, national symbols, and the Nandalal Bose illuminated manuscript borders:
- **Colour Palette**:
  - Saffron: `#FF9933` (tasteful accent)
  - Indian Green: `#138808` (statutory status & verified indicators)
  - Navy: `#14213D` (authority, structure & typography)
  - Warm Ivory: `#FFF9F0` (parchment background)
  - Muted Gold: `#C7A45D` (filigree & ornamental borders)
- **Respectful National Motifs**: Custom SVG 24-spoke Ashoka Chakra and dignified national emblem integration.
- **Accessibility & Responsiveness**: Mobile-first design, high-contrast text, keyboard navigability, and print/PDF formatting.

---

## 🚀 Key Features

1. **Everyday Language & Voice Input**:
   - Speak or type grievances in natural everyday language.
   - Built-in browser **Web Speech API** supporting English (`en-IN`), Hindi (`hi-IN`), Malayalam (`ml-IN`), Tamil (`ta-IN`), Telugu (`te-IN`), Bengali (`bn-IN`), Marathi (`mr-IN`), and Gujarati (`gu-IN`).
   - Animated visual listening waveform indicator with clear stop, retry, and clear controls.
   - Audio is processed client-side and never saved or recorded on backend servers.

2. **Criminal Law Reform & Transition Handling**:
   - Accounts for the **Bharatiya Nyaya Sanhita, 2023 (BNS)**, **Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)**, and **Bharatiya Sakshya Adhiniyam, 2023 (BSA)** which came into force on **1 July 2024**.
   - Preserves historical provisions of the Indian Penal Code (IPC 1860) and CrPC (1973) with cross-statutory mappings and date-aware incident filtering.

3. **Grounded Retrieval-Augmented Generation (RAG)**:
   - Queries are indexed and retrieved using **SQLite FTS5 full-text search**, topic heuristics, and statutory hierarchy.
   - **Zero Hallucination Shield**: Every cited section ID is strictly validated against local database primary keys. Nonexistent sections are blocked.
   - Works **100% offline** with a built-in deterministic grounded legal reasoning engine. Supports Google Gemini / LLM API when configured.

4. **Transparent Results Experience**:
   - Distinguishes Supreme Constitutional Articles from Statutory Acts.
   - Details required conditions to establish and important exceptions/limitations.
   - Direct clickable links to official India Code repositories (`indiacode.nic.in` & `legislative.gov.in`).
   - "Find the Right Type of Lawyer" practice area matching (e.g. Cybercrime, Consumer, Labour, MACT, Property) with Bar Council guidance.
   - Verified statutory legal-aid directory (NALSA 15100, Cybercrime Helpline 1930, National Consumer Helpline 1915).
   - "Print / Save PDF" and "Copy Summary" export utilities.

5. **Open Legal Data Pipeline & Truthful Coverage**:
   - Ingestion scripts (`legal/ingest.py`, `legal/extract_pdf.py`, `legal/normalize.py`, `legal/sync_sources.py`).
   - CLI & web dataset export in machine-readable JSON and CSV.
   - Truthful coverage dashboard detailing Central and all 28 State / 8 Union Territory indexing statuses.

---

## 🛠️ Technology Stack

- **Backend Framework**: Python Flask (Application Factory architecture).
- **Database**: SQLite with **FTS5** virtual tables (prepared for PostgreSQL migration).
- **Templating**: Jinja2.
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (no heavy node dependencies).
- **Speech-to-Text**: Browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
- **AI / LLM**: Configurable REST interface (Google Gemini API / OpenAI compatible) with reliable database-driven fallback.
- **Data Ingestion**: `pypdf`, `beautifulsoup4`, `requests`.
- **Testing**: `pytest`.

---

## 📦 Directory Structure

```text
indian constitution project/
├── app.py                     # Main Flask application & routes factory
├── config.py                  # Environment & deployment configurations
├── requirements.txt           # Dependencies
├── .env.example               # Template environment variables
├── .gitignore                 # Git ignore rules
├── README.md                  # Comprehensive setup & architecture documentation
├── instance/
│   └── nyayaguide.db          # SQLite relational database with FTS5 search
├── data/
│   ├── indian constitution pdf.pdf  # Authentic 402-page diglot Constitution PDF
│   ├── preamble.pdf           # Gazette of India extraordinary amendment
│   ├── seed/                  # Verified statutory seed datasets (JSON)
│   │   ├── sources.json
│   │   ├── jurisdictions.json
│   │   ├── topics.json
│   │   ├── acts.json
│   │   ├── provisions.json
│   │   ├── provision_topics.json
│   │   ├── relations.json
│   │   ├── lawyer_categories.json
│   │   └── legal_aid.json
│   └── exports/               # Exported provisions (JSON, CSV, coverage report)
├── legal/
│   ├── __init__.py
│   ├── init_db.py             # Schema definition & FTS5 creation
│   ├── ingest.py              # Ingestion pipeline & audit logger
│   ├── extract_pdf.py         # PDF parser & article extractor
│   ├── normalize.py           # Citation standardizer & FTS query sanitizer
│   ├── validate.py            # Anti-hallucination & domain verifier
│   ├── search.py              # FTS5 full-text & criminal transition search
│   ├── retrieval.py           # Topic detection & RAG pre-processor
│   ├── answer.py              # Grounded explanation engine & LLM dispatcher
│   ├── sync_sources.py        # Official portal audit & manifest generator
│   └── export_dataset.py      # CLI dataset exporter (JSON/CSV)
├── services/
│   ├── legal_service.py       # Core legal querying service
│   ├── lawyer_service.py      # Practice area matcher & legal aid lookup
│   └── ai_service.py          # AI integration wrapper
├── templates/
│   ├── base.html              # Layout with Constitution motif & navigation
│   ├── index.html             # Homepage with Hero, Situation input & Voice toolbar
│   ├── results.html           # Dedicated results, plain English, lawyer match & export
│   ├── browse_laws.html       # Law catalog with category & jurisdiction filters
│   ├── law_detail.html        # Detailed Act & provisions view
│   ├── legal_resources.html   # NALSA, SLSAs, Bar Councils & Helplines directory
│   ├── download_data.html     # Dataset downloads & truthful coverage dashboard
│   ├── about.html             # Mission, technical architecture & ethics
│   ├── disclaimer.html        # Legal disclaimer & emergency guidance
│   ├── 404.html               # Custom 404 error page
│   └── 500.html               # Custom 500 error page
├── static/
│   ├── css/
│   │   └── style.css          # Dribbble-inspired custom stylesheet
│   ├── js/
│   │   ├── main.js            # Prompt chips, validation, copy & print handlers
│   │   └── speech.js          # Web Speech API controller
│   └── images/
│       ├── ashoka_chakra.svg  # Custom vector 24-spoke Ashoka Chakra
│       └── constitution_book.webp # Ornate Constitution book artwork
└── tests/
    ├── __init__.py
    ├── test_routes.py         # HTTP endpoints & view tests
    ├── test_search.py         # FTS5, citation lookups & topic heuristics
    ├── test_citations.py      # Anti-hallucination & domain validation
    └── test_data_validation.py# Criminal transition (BNS vs IPC) & exports
```

---

## 💻 Setup & Run Instructions (Windows Laptop)

### 1. Prerequisites
- **Python**: Version 3.10 or higher (Tested with Python 3.15).
- **Git**: (Optional, for version control).
- Modern web browser (Google Chrome, Microsoft Edge, or Safari recommended for Web Speech recognition).

### 2. Create Virtual Environment & Install Dependencies
Open **PowerShell** or **Command Prompt** in the project directory:

```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

*(Optional)* If you wish to use Google Gemini for AI-generated grounded explanations, add your API key to `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```
> **Note**: NyayaGuide includes a complete built-in deterministic grounded legal explanation engine. If `GEMINI_API_KEY` is omitted, the platform runs 100% locally and offline without errors!

### 4. Initialize Database & Run Ingestion

```powershell
# Initialize SQLite database tables and FTS5 search index
python -m legal.init_db

# Ingest verified Central Acts, provisions, topics, legal aid & lawyer profiles
python -m legal.ingest
```

### 5. Export Datasets (JSON & CSV)

```powershell
# Generates nyayaguide_provisions.json and nyayaguide_provisions.csv in data/exports/
python -m legal.export_dataset
```

### 6. Run the Flask Web Application

```powershell
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🧪 Running the Automated Test Suite

Run the full pytest suite:

```powershell
python -m pytest tests/ -v
```

All 19 test cases verify:
- ✅ Route loading & HTTP responses (`/`, `/find-sections`, `/browse-laws`, `/download-data`, `/health`).
- ✅ Situation validation & redirect logic.
- ✅ Full-Text Search (SQLite FTS5) with BM25 ranking.
- ✅ Direct citation detection (`Article 21`, `Section 138`, `Section 318`).
- ✅ Topic detection heuristics.
- ✅ Rejection of fabricated or unknown section IDs.
- ✅ Validation of official government domains (`indiacode.nic.in`, `legislative.gov.in`, `nalsa.gov.in`).
- ✅ BNS 2023 vs IPC 1860 criminal transition date boundary (1 July 2024).
- ✅ Machine-readable dataset export generation (JSON & CSV).

---

## 🔍 Representative Scenarios Tested

Try clicking the example chips on the homepage or typing:

1. **Consumer Fraud**:
   > *"An online seller took my money but did not deliver the product."*
   - **Retrieved**: Consumer Protection Act 2019 (Section 2(47) Unfair Trade Practice & Section 35 District Commission complaint) and Bharatiya Nyaya Sanhita 2023 (Section 318 Cheating).
   - **Recommended Lawyer**: Consumer Dispute & Redressal Advocate.
   - **Official Channel**: National Consumer Helpline (1915 / consumerhelpline.gov.in) & e-Daakhil.

2. **Digital Privacy & Harassment**:
   > *"Someone is using my photographs without permission."*
   - **Retrieved**: IT Act 2000 (Section 66E Violation of privacy), BNS 2023 (Section 79 Insulting modesty / privacy intrusion, Section 78 Stalking), and Constitution of India (Article 21 Right to Privacy).
   - **Recommended Lawyer**: Cybercrime & Digital Evidence Lawyer.
   - **Official Channel**: National Cybercrime Helpline (1930 / cybercrime.gov.in).

3. **Unpaid Wages**:
   > *"My employer has not paid my salary."*
   - **Retrieved**: Code on Wages 2019 (Section 17 Payment of wages deadline within 2 days of resignation/termination) and Constitution of India (Article 23).
   - **Recommended Lawyer**: Labour & Employment Law Advocate.

4. **Police Summons / Legal Notice**:
   > *"I want to understand my rights if I receive a legal notice."*
   - **Retrieved**: BNSS 2023 (Section 35 Notice of appearance before police officer) and Constitution of India (Article 22 Protection against arrest & right to consult counsel).
   - **Recommended Lawyer**: Criminal Defence & Prosecution Advocate.

5. **Tenancy Dispute**:
   > *"I am facing a rental deposit dispute."*
   - **Retrieved**: Transfer of Property Act 1882 (Section 108 Rights and liabilities of lessor/lessee) and BNS Section 316 (Criminal breach of trust).
   - **Recommended Lawyer**: Property & Tenancy Advocate.

---

## ⚖️ Legal Limitations & Responsible AI Disclaimer

- **Educational Purpose**: NyayaGuide is created to enhance legal literacy among Indian citizens. It does not provide formal legal advice, issue binding opinions, or create an advocate-client relationship.
- **Truthful Coverage**: Coverage of state-specific legislation is currently underway. Central statutes and core fundamental rights are fully seeded.
- **Emergency Situations**: For imminent physical danger or active financial cyber fraud, citizens should contact **112** (Police Emergency), **1930** (Cybercrime), or **15100** (NALSA Toll-Free).

---

## 📜 License & Acknowledgments

- Developed with deep reverence for the **Constitution of India (1950)**.
- Authentic legislative texts referenced from the **Ministry of Law and Justice, Government of India** and **India Code Information System**.
