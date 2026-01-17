-- 1. Activăm extensia vector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabela (doar dacă nu există deja)
CREATE TABLE IF NOT EXISTS public.dsm5 (
  id BIGSERIAL PRIMARY KEY,
  content TEXT,
  metadata JSONB,
  embedding vector(1536)
);

-- 3. Funcția de căutare FIXATA (rezolvă eroarea 'ambiguous id' și potrivește parametrii)
DROP FUNCTION IF EXISTS match_dsm5(vector, float, int);
DROP FUNCTION IF EXISTS match_dsm5(vector, int, jsonb);

CREATE OR REPLACE FUNCTION match_dsm5 (
  query_embedding vector(1536),
  match_count int DEFAULT null,
  filter jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,            -- Folosim aliasul 'd' pentru a evita ambiguitatea
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) AS similarity
  FROM dsm5 AS d
  WHERE d.metadata @> filter
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
