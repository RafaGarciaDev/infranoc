# ADR-002: Assistente de IA local com hibrido tool calling + RAG

## Status
Aceito (Fase 7, 2026-07-12)

## Contexto
A Fase 7 adiciona um assistente de IA ao InfraNOC com restricao de
custo zero: stack 100% local, sem APIs pagas. O modelo que cabe no
hardware disponivel (CPU, sem GPU) e pequeno — qwen2.5:3b via Ollama
em Docker. Modelos dessa escala tem limitacoes conhecidas: contam mal,
alucinam argumentos de funcao e nem sempre decidem corretamente quando
usar uma ferramenta.

## Decisao
Arquitetura hibrida com duas fontes de dados, cada uma pelo canal que
melhor funciona com modelo pequeno:

1. **Dados dinamicos (CMDB, alertas, metricas): tool calling.**
   As tools devolvem **agregados prontos** (ex.: `{"total": N}`),
   nunca listas para a IA contar. Entradas em portugues sao
   normalizadas para os enums em ingles (`_normalizar_tipo`).
2. **Conhecimento estatico (runbooks): RAG por injecao direta.**
   O documento top-1 da busca vetorial e injetado no system prompt a
   cada pergunta, em vez de exposto como tool — o modelo 3b nao e
   confiavel para decidir chamar uma tool de busca. Custo: ~700
   tokens/pergunta; beneficio: o conhecimento sempre chega.
3. **Embeddings locais**: sentence-transformers com
   `intfloat/multilingual-e5-small` (384 dims), pgvector no Postgres.
   Reindexacao via APScheduler (startup + a cada 6h) lendo
   `docs/runbooks/`.
4. **Robustez para modelo pequeno**: `_run_tool` blindado — nome de
   tool desconhecido ou argumentos alucinados (TypeError) viram
   mensagem de erro devolvida ao modelo em vez de derrubar o stream;
   timeout httpx de 300s (CPU: ~2 tokens/s na geracao).

## Consequencias
- (+) Zero custo de API; dados nunca saem do host.
- (+) Respostas com dados reais do CMDB e procedimentos dos runbooks.
- (-) Latencia alta em CPU (2-5 min por resposta); aceitavel para o
  caso de uso (consulta operacional, nao chat em tempo real).
- (-) Injecao top-1 limita a 1 runbook por pergunta; suficiente para
  perguntas de procedimento tipicas.
- **Indice vetorial**: o ivfflat (lists=100) retornava 0 resultados de
  forma intermitente com poucas linhas (centroides treinados com a
  tabela vazia + probes=1). Removido (migration `a1b2c3d4e5f6`);
  busca exata e rapida e correta nesta escala. Recriar como **HNSW**
  quando a base passar de alguns milhares de documentos.

## Alternativas consideradas
- **API paga (Claude/GPT)**: descartada pela restricao de custo.
- **RAG como tool** (`buscar_conhecimento`): testado implicitamente —
  o modelo 3b ignorava o canal; injecao direta e deterministica.
- **Modelo maior (7b+)**: inviavel no hardware atual; a arquitetura
  (agregados prontos, injecao top-1) foi desenhada para compensar.
