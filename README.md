# Chunker MVP — Chunking fixo + Compressão condicional + Manifest + Verify

Este mini-projeto quebra um arquivo grande em chunks de tamanho fixo, aplica **compressão gzip por chunk apenas quando vale a pena** (caso contrário salva o chunk **raw**), gera um `manifest.json` com hashes e metadados, e permite **reconstrução** e **verificação de integridade**.

## Por que compressão condicional?
Dados de alta entropia (ex.: `os.urandom`, muitos formatos já comprimidos) não comprimem bem. Nesses casos, comprimir gasta CPU e não reduz tamanho.  
Aqui, o chunk só é armazenado como gzip se for pelo menos **X% menor** (`--min-gain`, default 2%).

## Arquivos
- `chunker.py` — CLI (`chunk`, `rebuild`, `verify`, `stats`)
- `compression.py` — compressão/ descompressão
- `hashing.py` — SHA-256
- `manifest.py` — leitura/escrita do `manifest.json`

## Uso

### 1) Chunk + armazenar
```bash
python chunker.py chunk arquivo_grande.bin --chunk 1048576 --level 6 --min-gain 0.02
```
Isso cria uma pasta `chunks_<stem>/` com:
- arquivos `*.partXXXXXX.gz` (comprimidos) e/ou `*.partXXXXXX.raw` (não comprimidos)
- `manifest.json`

### 2) Verificar integridade
```bash
python chunker.py verify chunks_arquivo_grande
```

### 3) Reconstruir
```bash
python chunker.py rebuild chunks_arquivo_grande --out reconstruido.bin
```

### 4) Estatísticas
```bash
python chunker.py stats chunks_arquivo_grande
```

## Dicas
- Para reduzir o número de arquivos, aumente o chunk size (ex.: 8 MiB = `--chunk 8388608`).
- Arquivos já comprimidos (mp4/mkv/jpg/zip/7z) tendem a virar muitos chunks `raw` — isso é esperado.
