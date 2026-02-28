# Chunker(Compressão condicional + Manifesto + Integridade)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Ativo-brightgreen)
![Last Commit](https://img.shields.io/github/last-commit/RubensPaulo1/file-Chunking)
![Repo Size](https://img.shields.io/github/repo-size/RubensPaulo1/file-Chunking)
![Issues](https://img.shields.io/github/issues/RubensPaulo1/file-Chunking)
![Project Type](https://img.shields.io/badge/Project-File%20Processing-orange)

Este mini-projeto quebra um arquivo grande em chunks de tamanho fixo, aplica **compressão gzip por chunk apenas quando vale a pena** (caso contrário salva o chunk **raw**), gera um `manifest.json` com hashes e metadados, e permite **reconstrução** e **verificação de integridade**.

<img width="1536" height="1024" alt="diagrama" src="https://github.com/user-attachments/assets/8263ced8-bf8b-4d6f-8d06-d6d21d2c9eff" />

## Arquivos
- `chunker.py` — CLI (`chunk`, `rebuild`, `verify`, `stats`)
- `compression.py` — compressão/ descompressão
- `hashing.py` — SHA-256
- `manifest.py` — leitura/escrita do `manifest.json`

## Comandos

### 1) Chunk + armazenar
```bash
python chunker.py chunk arquivo.bin --level (1 ao 9)
```
Isso cria uma pasta `chunks_<stem>/` com:
- arquivos `*.partXXXXXX.gz` (comprimidos) ou `*.partXXXXXX.raw` (não comprimidos)
- `manifest.json`

### 2) Verificar integridade
```bash
python chunker.py verify chunks_arquivo
```

### 3) Reconstruir
```bash
python chunker.py rebuild chunks_arquivo_grande --out nomeNovo
```

### 4) Estatísticas
```bash
python chunker.py stats chunks_arquivo_grande
```
