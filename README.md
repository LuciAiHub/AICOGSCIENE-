# AI Metacognitive Clinical Evaluator (DSM-5 RAG)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green?style=for-the-badge&logo=openai&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)

Acest proiect implementează un sistem de **Inteligență Artificială Metacognitivă** conceput pentru a evalua și valida informațiile clinice psihiatrice pe baza manualului **DSM-5** (Diagnostic and Statistical Manual of Mental Disorders).

> 📄 **Documentație Teoretică**: Pentru o analiză detaliată a conceptelor din spatele acestui sistem, consultă eseul aferent: [Metacognitie Psihiatru.docx](Metacognitie%20Psihiatru.docx).

Sistemul utilizează o arhitectură **Dual-Agent** pentru a demonstra diferența dintre un LLM standard și unul augmentat cu mecanisme de siguranță, verificare factuală (RAG) și auditare proprie (Self-Correction).

## 🧠 Arhitectura Sistemului

Aplicația compară în timp real doi agenți:

### 1. Agent A (Baseline) 🤖
- **Model**: GPT-4o-mini (Standard).
- **Comportament**: Răspunde direct la întrebările utilizatorului bazându-se doar pe datele de antrenament.
- **Riscuri**: Predispus la halucinații, omiterea criteriilor stricte sau confirmarea eronată a diagnosticelor.

### 2. Agent B (Metacognitive) 🛡️
- **Arhitectură**: RAG (Retrieval-Augmented Generation) + Chain-of-Thought + Auditor Layer.
- **Flux de Lucru**:
  1.  **RAG**: Caută paragrafe relevante în baza de date vectorială (Supabase) indexată cu DSM-5.
  2.  **Drafting**: Generează un răspuns preliminar folosind contextul recuperat și un proces de gândire "pas-cu-pas".
  3.  **Auditing (Metacogniție)**: Un "Auditor" intern verifică draftul împotriva contextului RAG pentru:
      - **Halucinații**: Inventează informații care nu există în text?
      - **Conformitate**: Respectă criteriile de timp/durată/simptome din DSM-5?
      - **Siguranță**: Blochează diagnosticele directe sau pseudo-știința.
- **Rezultat**: "APPROVE" (dacă e corect) sau "BLOCK" (dacă există riscuri/erori), împreună cu un Raport de Audit detaliat (JSON).

## 🚀 Funcționalități Cheie

- **Interfață Streamlit**: UI modern pentru compararea side-by-side a agenților.
- **Supabase Vector Store**: Stocare și căutare semantică a documentelor PDF (DSM-5).
- **Robustitate Pydantic**: Validare structurată a ieșirilor LLM, capabilă să gestioneze răspunsuri JSON complexe.
- **Logging Automat**: Salvarea fiecărui experiment (Query, Context, Audit) în fișiere text locale pentru analiză ulterioară.
- **Vizualizare Transparentă**: Afișarea prompt-urilor de sistem, a contextului RAG și a gândirii interne (Draft) pentru transparență totală.

## �️ Tehnologii Utilizate

- **Backend Logic**: Python, LangChain, OpenAI API (GPT-4o-mini).
- **Frontend**: Streamlit.
- **Database**: Supabase (PostgreSQL + pgvector).
- **Validation**: Pydantic.
- **Embeddings**: OpenAI `text-embedding-3-small`.

## 📦 Instalare și Configurare

### 1. Clonează Repozitoriul
```bash
git init
git remote add origin <URL-ul-tau-github>
git pull origin main
```

### 2. Configurare Mediu Virtual (Recomandat)
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instalare Dependențe
```bash
pip install -r requirements.txt
```
*(Asigură-te că ai `streamlit`, `openai`, `supabase`, `langchain`, `pydantic`, `python-dotenv` instalate)*

### 4. Configurare .env
Creează un fișier `.env` în rădăcina proiectului:
```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key-here"
SUPABASE_SERVICE_KEY="your-service-role-key-for-ingestion"
OPENAI_API_KEY="sk-..."
```

### 5. Ingestia Datelor (Dacă este necesar)
Dacă baza de date este goală, indexează PDF-ul DSM-5:
```bash
python ingest_dsm5.py
```

### 6. Rulare Aplicație
```bash
streamlit run app.py
```

## 📂 Structura Proiectului

- `app.py`: Aplicația principală Streamlit (Interfață & Logică Agenți).
- `run_agents.py`: Script CLI alternativ pentru rularea agenților în terminal.
- `ingest_dsm5.py`: Script pentru citirea PDF-ului și încărcarea vectorilor în Supabase.
- `vector.sql`: Schema bazei de date SQL/Vector.
- `experiment_log_*.txt`: Log-uri generate automat la fiecare rulare.

## 🛡️ Studii de Caz Validate

Proiectul a fost testat cu succes pe scenarii critice:
1.  **Validare Clinică**: Confirmă informații corecte (PTSD, CBT).
2.  **Respingere Pseudo-știință**: Refuză validarea terapiilor inexistente în DSM-5 (ex. cristale).
3.  **Fail-Safe**: Blochează răspunsurile când detectează erori logice interne (ex. calcul greșit al duratei simptomelor), prioritizând siguranța utilizatorului.