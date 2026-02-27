from __future__ import annotations

import argparse
import time
from pathlib import Path

from compression import compress_conditional, decompress
from hashing import sha256_hex
from manifest import Manifest, ChunkEntry, write_manifest, read_manifest

DEFAULT_CHUNK_SIZE = 1024 * 1024  


def chunk_file(
    file_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    compression_level: int = 6,
    min_gain_ratio: float = 0.02,
) -> Path:

    src = Path(file_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")

    folder = Path(out_dir) if out_dir else (src.parent / f"chunks_{src.stem}")
    folder.mkdir(parents=True, exist_ok=True)

    file_hasher = _sha256_stream_init()
    size_raw_total = 0
    size_stored_total = 0

    chunks: list[ChunkEntry] = []

    with src.open("rb") as f:
        idx = 0
        while True:
            raw = f.read(chunk_size)
            if not raw:
                break

            size_raw_total += len(raw)
            file_hasher.update(raw)

            sha_raw = sha256_hex(raw)
            res = compress_conditional(raw, level=compression_level, min_gain_ratio=min_gain_ratio)
            sha_stored = sha256_hex(res.payload)

            ext = "raw" if res.stored_as == "raw" else "gz"
            filename = f"{src.stem}.part{idx:06d}.{ext}"
            (folder / filename).write_bytes(res.payload)

            size_stored_total += len(res.payload)

            chunks.append(
                ChunkEntry(
                    index=idx,
                    filename=filename,
                    stored_as=res.stored_as,
                    size_raw=len(raw),
                    size_stored=len(res.payload),
                    sha256_raw=sha_raw,
                    sha256_stored=sha_stored,
                )
            )
            idx += 1

    manifest = Manifest(
        version=1,
        original_filename=src.name,
        chunk_size=chunk_size,
        compression_level=compression_level,
        min_gain_ratio=min_gain_ratio,
        created_at_unix=int(time.time()),
        chunks=chunks,
        sha256_file_raw=file_hasher.hexdigest(),
        size_file_raw=size_raw_total,
        size_file_stored_total=size_stored_total,
    )

    write_manifest(folder, manifest)
    return folder


def rebuild(chunks_folder: str | Path, output_path: str | Path) -> None:
    """Rebuild the original file from a folder containing manifest.json + chunk files."""
    folder = Path(chunks_folder)
    mf = read_manifest(folder)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    file_hasher = _sha256_stream_init()
    bytes_written = 0

    with out.open("wb") as f_out:
        for c in mf.chunks:
            p = folder / c.filename
            payload = p.read_bytes()

            # Validate stored bytes
            if sha256_hex(payload) != c.sha256_stored:
                raise RuntimeError(f"Chunk {c.index}: sha256_stored mismatch ({c.filename})")

            raw = decompress(payload, c.stored_as)

            if len(raw) != c.size_raw:
                raise RuntimeError(f"Chunk {c.index}: tamanho raw diferente do esperado")

            if sha256_hex(raw) != c.sha256_raw:
                raise RuntimeError(f"Chunk {c.index}: sha256_raw mismatch")

            f_out.write(raw)
            file_hasher.update(raw)
            bytes_written += len(raw)

    if bytes_written != mf.size_file_raw:
        raise RuntimeError("Arquivo reconstruído com tamanho incorreto (manifest não bate)")

    if file_hasher.hexdigest() != mf.sha256_file_raw:
        raise RuntimeError("Arquivo reconstruído corrompido (sha256 do arquivo não bate)")


def verify(chunks_folder: str | Path) -> dict:
    """Verify all chunks and reconstructed-file hash without writing output."""
    folder = Path(chunks_folder)
    mf = read_manifest(folder)

    file_hasher = _sha256_stream_init()
    total_raw = 0
    total_stored = 0

    for c in mf.chunks:
        p = folder / c.filename
        if not p.exists():
            return {"ok": False, "reason": f"faltando: {c.filename}"}

        payload = p.read_bytes()
        total_stored += len(payload)

        if sha256_hex(payload) != c.sha256_stored:
            return {"ok": False, "reason": f"chunk {c.index}: sha256_stored mismatch"}

        raw = decompress(payload, c.stored_as)
        total_raw += len(raw)

        if len(raw) != c.size_raw:
            return {"ok": False, "reason": f"chunk {c.index}: tamanho raw mismatch"}

        if sha256_hex(raw) != c.sha256_raw:
            return {"ok": False, "reason": f"chunk {c.index}: sha256_raw mismatch"}

        file_hasher.update(raw)

    if total_raw != mf.size_file_raw:
        return {"ok": False, "reason": "tamanho total raw mismatch"}

    if file_hasher.hexdigest() != mf.sha256_file_raw:
        return {"ok": False, "reason": "sha256 do arquivo mismatch"}

    return {
        "ok": True,
        "chunks": len(mf.chunks),
        "size_file_raw": mf.size_file_raw,
        "size_file_stored_total": mf.size_file_stored_total,
        "ratio": (mf.size_file_stored_total / mf.size_file_raw) if mf.size_file_raw else 0.0,
        "algo": "gzip + conditional(raw fallback)",
        "min_gain_ratio": mf.min_gain_ratio,
    }


def stats(chunks_folder: str | Path) -> dict:
    folder = Path(chunks_folder)
    mf = read_manifest(folder)

    raw_chunks = sum(1 for c in mf.chunks if c.stored_as == "raw")
    gz_chunks = len(mf.chunks) - raw_chunks
    stored_actual = 0
    for c in mf.chunks:
        stored_actual += (folder / c.filename).stat().st_size

    return {
        "chunks_total": len(mf.chunks),
        "chunks_raw": raw_chunks,
        "chunks_gzip": gz_chunks,
        "chunk_size": mf.chunk_size,
        "size_file_raw": mf.size_file_raw,
        "size_file_stored_manifest": mf.size_file_stored_total,
        "size_file_stored_actual": stored_actual,
        "ratio": (stored_actual / mf.size_file_raw) if mf.size_file_raw else 0.0,
    }


def _sha256_stream_init():
    import hashlib
    return hashlib.sha256()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chunker", description="Fixed-size chunking with conditional gzip + manifest + verify")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_chunk = sub.add_parser("chunk", help="Chunk + store (conditionally compressed) + write manifest.json")
    s_chunk.add_argument("file", help="arquivo de entrada")
    s_chunk.add_argument("--out", help="pasta de saída (default: chunks_<stem>)")
    s_chunk.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE, help=f"tamanho do chunk (bytes). default={DEFAULT_CHUNK_SIZE}")
    s_chunk.add_argument("--level", type=int, default=6, help="gzip level 1..9 (default=6)")
    s_chunk.add_argument("--min-gain", type=float, default=0.02, help="ganho mínimo p/ comprimir (ex: 0.02 = 2%%). default=0.02")

    s_rebuild = sub.add_parser("rebuild", help="Rebuild file from chunks folder (manifest.json required)")
    s_rebuild.add_argument("folder", help="pasta com chunks + manifest.json")
    s_rebuild.add_argument("--out", required=True, help="arquivo de saída reconstruído")

    s_verify = sub.add_parser("verify", help="Verify chunks + hashes (manifest.json required)")
    s_verify.add_argument("folder")

    s_stats = sub.add_parser("stats", help="Show stats (how many raw vs gzip chunks, ratio, etc.)")
    s_stats.add_argument("folder")

    args = p.parse_args(argv)

    try:
        if args.cmd == "chunk":
            folder = chunk_file(
                args.file,
                out_dir=args.out,
                chunk_size=args.chunk,
                compression_level=args.level,
                min_gain_ratio=args.min_gain,
            )
            print(f"OK: chunks em {folder}")
            print(f"OK: manifest em {folder / 'manifest.json'}")
            return 0

        if args.cmd == "rebuild":
            rebuild(args.folder, args.out)
            print(f"OK: reconstruído em {args.out}")
            return 0

        if args.cmd == "verify":
            r = verify(args.folder)
            if r.get("ok"):
                print(f"OK: íntegro | chunks={r['chunks']} | ratio={r['ratio']:.2f} | min_gain={r['min_gain_ratio']}")
                return 0
            print(f"FAIL: {r.get('reason','unknown')}")
            return 2

        if args.cmd == "stats":
            r = stats(args.folder)
            print(
                "STATS: "
                f"chunks_total={r['chunks_total']} raw={r['chunks_raw']} gzip={r['chunks_gzip']} "
                f"chunk_size={r['chunk_size']} "
                f"size_raw={r['size_file_raw']} size_stored={r['size_file_stored_actual']} "
                f"ratio={r['ratio']:.2f}"
            )
            return 0

        return 1
    except Exception as e:
        print(f"ERRO: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
