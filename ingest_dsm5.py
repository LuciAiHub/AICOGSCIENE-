import os
import json
from typing import List
from tqdm import tqdm  # Bara de progres
from dotenv import load_dotenv

# Librării pentru PDF și Text Splitting
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Clienții API
from supabase import create_client, Client
from openai import OpenAI

# Încarcă variabilele din .env
load_dotenv()

# --- CONFIGURARE ---
# Le citim din .env sau lăsăm string gol dacă nu există
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Configurare Model (CRITIC: Trebuie să fie același ca în n8n)
MODEL_NAME = "text-embedding-3-small" 

def get_embedding(text: str, client: OpenAI) -> List[float]:
    """Trimite textul la OpenAI și primește vectorul înapoi."""
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=MODEL_NAME)
    return response.data[0].embedding

def main():
    # Verificări chei
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ EROARE: Lipsesc credențialele Supabase (URL sau SERVICE_KEY) în fișierul .env")
        return
    if not OPENAI_API_KEY:
        print("❌ EROARE: Lipsește OPENAI_API_KEY în fișierul .env")
        return

    # Inițializare clienți
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"❌ EROARE la inițializare clienți: {e}")
        return

    pdf_path = os.path.join("data", "dsm5.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ Nu găsesc fișierul {pdf_path}. Te rog să îl pui în acest folder.")
        return

    print("📖 1. Citesc PDF-ul...")
    try:
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        print(f"✅ Încărcat {len(pages)} pagini.")
    except Exception as e:
        print(f"❌ EROARE la citirea PDF-ului: {e}")
        return

    print("✂️  2. Tai textul în bucăți (Chunking)...")
    # Chunk size 1000 caractere cu overlap 100 este standardul de aur pentru RAG
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(pages)
    print(f"✅ Rezultat: {len(chunks)} bucăți de text (chunks).")

    print(f"🚀 3. Generare Embeddings cu modelul '{MODEL_NAME}' și Upload în Supabase...")
    
    # Procesăm în loturi (batch-uri) de 50 pentru viteză
    batch_size = 50
    total_chunks = len(chunks)

    for i in tqdm(range(0, total_chunks, batch_size)):
        batch = chunks[i : i + batch_size]
        rows_to_insert = []

        for doc in batch:
            content = doc.page_content
            # Curățăm caracterele nule care dau eroare în Postgres
            content = content.replace('\x00', '')
            
            # Păstrăm numărul paginii pentru citări!
            metadata = doc.metadata # ex: {'source': 'dsm5.pdf', 'page': 45}

            try:
                # Generăm embedding
                vector = get_embedding(content, openai_client)
                
                rows_to_insert.append({
                    "content": content,
                    "metadata": metadata,
                    "embedding": vector
                })
            except Exception as e:
                print(f"⚠️ Eroare la embedding pentru un chunk: {e}")

        # Inserăm lotul în Supabase
        if rows_to_insert:
            try:
                supabase.table("dsm5").insert(rows_to_insert).execute()
            except Exception as e:
                print(f"❌ Eroare la upload Supabase: {e}")

    print("\n🎉 GATA! Baza de date a fost populată.")

if __name__ == "__main__":
    main()
