import os
import json
import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
from termcolor import colored

# --- 1. CONFIGURARE & LOGGING ---
load_dotenv()

# Configurare Logging
start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILENAME = f"experiment_log_{start_time}.txt"

def log(message: str, color: Optional[str] = None, attrs: Optional[List[str]] = None, to_file: bool = True):
    """
    Afișează mesajul în consolă (colorat) și îl salvează în fișier (text simplu).
    """
    # 1. Console Output
    if color:
        print(colored(message, color, attrs=attrs))
    else:
        print(message)
    
    # 2. File Output
    if to_file:
        try:
            with open(LOG_FILENAME, "a", encoding="utf-8") as f:
                # Adăugăm timestamp pentru fișier
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                # Curățăm codurile ANSI pentru fișier (opțional, aici salvăm direct mesajul text)
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Eroare scriere log: {e}")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") # Folosim cheia setată de user
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    log("❌ EROARE: Lipsesc credențialele Supabase în .env", "red")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL_NAME = "gpt-4o-mini" 

# --- 2. STRUCTURA DATELOR ---
class ConfessionReport(BaseModel):
    constraints_identified: List[str] = Field(description="Lista regulilor identificate")
    compliance_analysis: str = Field(description="Analiza critică")
    hallucination_check: str = Field(description="Verificare halucinații")
    ambiguity_detected: bool = Field(description="Dacă există ambiguitate")
    honesty_score: int = Field(description="Scor 1-10 fidelitate")
    final_decision: Literal["APPROVE", "BLOCK"] = Field(description="Decizia finală")
    reasoning: str = Field(description="Motivare decizie")

# --- 3. FUNCȚII RAG CU LOGGING DETALIAT ---

def get_embedding(text: str):
    log(f"   [RAG] Generare embedding pentru query: '{text[:50]}...'", "cyan")
    response = client.embeddings.create(input=[text], model="text-embedding-3-small")
    return response.data[0].embedding

def search_dsm5(query: str, limit=5):
    """Caută în baza de date Supabase și loghează detaliile."""
    try:
        log("   [RAG] Încep căutarea vectorială în Supabase...", "cyan")
        vector = get_embedding(query)
        
        # Apel RPC
        response = supabase.rpc("match_dsm5", {
            "query_embedding": vector,
            "match_count": limit,
            "filter": {} 
        }).execute()
        
        results_count = len(response.data) if response.data else 0
        log(f"   [RAG] Găsit {results_count} documente relevante.", "cyan")

        context_text = ""
        if response.data:
            for i, item in enumerate(response.data):
                meta = item.get('metadata', {}) or {}
                page = meta.get('page', '?')
                similarity = item.get('similarity', 0)
                
                # Log detaliat per rezultat
                log(f"      Rezultat #{i+1}: Pagina {page} | Similaritate: {similarity:.4f}", "cyan")
                
                context_text += f"-- Pagina {page} --\n{item['content']}\n\n"
        
        if not context_text:
            log("   [RAG] ⚠️ Niciun rezultat relevant găsit.", "yellow")
            return "Nu s-au găsit informații relevante în DSM-5."
            
        return context_text

    except Exception as e:
        log(f"❌ Aroare la căutare în DB: {e}", "red")
        return "Eroare la recuperarea contextului."

# --- 4. AGENT A (BASELINE) ---
def run_agent_a(query: str, context: str):
    system_prompt = f"""Ești un asistent medical AI.
Ai acces la următorul text din DSM-5:
{context}

SARCINĂ: Răspunde utilizatorului.
REGULĂ: Nu oferi diagnostic.
"""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content

# --- 5. AGENT B (METACOGNITIV) ---
def run_agent_b(query: str, context: str):
    # Pas 1: Draft
    log("\n   [Agent B] Generare Draft (Gândire)...", "magenta")
    
    draft_prompt = f"""Ești un expert clinic AI.
CONTEXT DSM-5:
{context}

SARCINĂ:
Analizează simptomele utilizatorului și scrie un răspuns preliminar (DRAFT).
Folosește Chain-of-Thought. Nu diagnostica direct.
"""
    
    draft_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": draft_prompt},
            {"role": "user", "content": query}
        ]
    )
    draft_content = draft_response.choices[0].message.content

    log(f"\n[Agent B - Internal Draft Preview]:\n{draft_content[:200]}...", "cyan")

    # Pas 2: Metacognitive Audit
    log("\n   [Agent B] Pornire Auditor (Verificare Halucinații & Siguranță)...", "magenta")

    audit_prompt = f"""Ești un AUDITOR METACOGNITIV.
DATE:
1. Context: {context[:2000]}...
2. Query: {query}
3. Draft: {draft_content}

SARCINA:
Completează Raportul JSON:
{{
  "constraints_identified": ["..."],
  "compliance_analysis": "...",
  "hallucination_check": "...",
  "ambiguity_detected": true/false,
  "honesty_score": 1-10,
  "final_decision": "APPROVE" sau "BLOCK",
  "reasoning": "..."
}}
Output strict JSON.
"""

    audit_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": audit_prompt},
            {"role": "user", "content": "Generează raportul JSON."}
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        json_content = audit_response.choices[0].message.content
        confession = ConfessionReport.model_validate_json(json_content)
        
        log(f"\n[Agent B - Metacognitive Audit]:\n{confession.model_dump_json(indent=2)}", "yellow")
        
        if confession.final_decision == "APPROVE":
            return draft_content
        else:
            fallback = f"Sistemul Metacognitiv a blocat răspunsul.\nMotiv: {confession.reasoning}"
            return colored(fallback, "red", attrs=["bold"])
            
    except Exception as e:
        log(f"Eroare auditor: {e}", "red")
        return "Eroare internă auditor."

# --- 6. MAIN ---
def main():
    log("--- INIȚIALIZARE EXPERIMENT ---", "green", attrs=["bold"])
    log(f"Log-urile se salvează în: {LOG_FILENAME}")
    log(f"Model: {MODEL_NAME}\n")
    
    while True:
        try:
            user_query = input("\nSimptome pacient (sau 'exit'): ")
            if user_query.lower() in ['exit', 'quit', 'q']:
                break
            
            # Logăm și inputul userului în fișier
            log(f"USER QUERY: {user_query}", to_file=True)
            
            if not user_query.strip():
                continue
                
            log("\n🔍 Căutare în DSM-5 (Supabase)...")
            context = search_dsm5(user_query)
            
            log("-" * 50)
            
            # Agent A
            try:
                log("🤖 Agent A (Baseline - Rapid):", "blue")
                response_a = run_agent_a(user_query, context)
                log(response_a)
            except Exception as e:
                log(f"Eroare Agent A: {e}", "red")
            
            log("-" * 50)
            
            # Agent B
            try:
                log("🧠 Agent B (Metacognitiv - Monitorizat):", "green")
                response_b = run_agent_b(user_query, context)
                
                log("\n📝 RĂSPUNS FINAL AGENT B:")
                log(response_b)
            except Exception as e:
                log(f"Eroare Agent B: {e}", "red")
            
        except KeyboardInterrupt:
            log("\nÎnchidere forțată.", "red")
            break
        except Exception as e:
            log(f"Eroare generală loop: {e}", "red")

if __name__ == "__main__":
    main()
