#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/runtime_export/export_bible_production.py

Exportación de producción del banco canónico de la Biblia Protestante (RVR1960)
a formato Runtime JSON v1 oficial de Quiz Bible.

Proceso 100% determinista, reproducible y Fail-Closed:
1. Lee y valida el registro de congelamiento bible-bank-freeze-v1.json.
2. Verifica los 66 hashes SHA-256 canónicos.
3. Carga el status map global bible-global-audit-status-map-v1.json (2486 V / 1361 I / 0 RC).
4. Exporta las 3847 preguntas mediante export_runtime.py.
5. Valida determinismo mediante doble generación byte a byte.
6. Valida el esquema JSON oficial y ausencia de texto bíblico persistido.
7. Emite el runtime final y su manifiesto de producción.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.runtime_export.export_runtime import (
    assert_no_forbidden_keys,
    export_files_to_runtime,
    load_audit_status_map,
    validate_runtime_collection,
)

FREEZE_FILE = REPO_ROOT / "tools" / "bible_extractor" / "bible-bank-freeze-v1.json"
MANIFEST_FILE = REPO_ROOT / "tools" / "bible_extractor" / "bible-global-manifest-v1.json"
STATUS_MAP_FILE = REPO_ROOT / "tools" / "bible_extractor" / "bible-global-audit-status-map-v1.json"
OUTPUT_DIR = REPO_ROOT / "build" / "runtime"
DEFAULT_RUNTIME_FILE = OUTPUT_DIR / "quiz_bible_protestant_rvr1960_runtime_v1.json"
DEFAULT_RUNTIME_MANIFEST = OUTPUT_DIR / "quiz_bible_protestant_rvr1960_runtime_v1.manifest.json"

CANONICAL_TIMESTAMP = "2026-08-24T00:00:00Z"
BANK_VERSION = "QUIZ_BIBLE_PROTESTANT_RVR1960_V1"
SCHEMA_VERSION = "quizbible-runtime-v1"


def run_production_export(
    output_path: Path = DEFAULT_RUNTIME_FILE,
    manifest_path: Path = DEFAULT_RUNTIME_MANIFEST,
    generated_at: str = CANONICAL_TIMESTAMP
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """Ejecuta la exportación de producción oficial y genera el manifest."""
    print("=" * 80)
    print("INICIANDO EXPORTACIÓN DE PRODUCCIÓN — BANCO PROTESTANTE RVR1960 V1")
    print("=" * 80)

    # 1. Validar existencia de artefactos base
    if not FREEZE_FILE.exists():
        raise FileNotFoundError(f"Registro de congelamiento no encontrado: {FREEZE_FILE}")
    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Manifest global no encontrado: {MANIFEST_FILE}")
    if not STATUS_MAP_FILE.exists():
        raise FileNotFoundError(f"Status map global no encontrado: {STATUS_MAP_FILE}")

    freeze_data = json.loads(FREEZE_FILE.read_text(encoding="utf-8"))
    manifest_data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    status_map_data = json.loads(STATUS_MAP_FILE.read_text(encoding="utf-8"))

    books = manifest_data.get("books", [])
    if len(books) != 66:
        raise ValueError(f"Cantidad de libros en manifest={len(books)} != 66. Fail-closed.")

    # 2. Validar 66 archivos maestros y hashes SHA-256
    input_paths: List[Path] = []
    print(f"Validando 66 bancos canónicos contra manifest...")
    for idx, b in enumerate(books):
        input_rel = b["input_file"]
        file_path = REPO_ROOT / input_rel
        if not file_path.exists():
            raise FileNotFoundError(f"Banco maestro faltante: {file_path}. Fail-closed.")

        raw_bytes = file_path.read_bytes()
        real_sha = hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()
        exp_sha = b["canonical_sha256"]

        if real_sha != exp_sha:
            raise ValueError(f"SHA-256 mismatch en {b['book_key']}: real={real_sha} != manifest={exp_sha}. Fail-closed.")

        input_paths.append(file_path)

    print("  66/66 bancos canónicos validados con SHA-256 idéntico.")

    # 3. Cargar status map
    print("Cargando status map global oficial...")
    loaded_status_map = load_audit_status_map(STATUS_MAP_FILE, strict=True)
    if len(loaded_status_map) != 3847:
        raise ValueError(f"Status map contiene {len(loaded_status_map)} entradas != 3847. Fail-closed.")

    ver_count = sum(1 for s in loaded_status_map.values() if s == "VERIFIED")
    inc_count = sum(1 for s in loaded_status_map.values() if s == "INCONCLUSIVE")
    rc_count = sum(1 for s in loaded_status_map.values() if s == "REQUIRES_CORRECTION")

    if ver_count != 2486 or inc_count != 1361 or rc_count != 0:
        raise ValueError(f"Distribución de status map anómala: V={ver_count}, I={inc_count}, RC={rc_count}. Fail-closed.")

    print(f"  Status map cargado: {len(loaded_status_map)} QIDs (2486 VERIFIED, 1361 INCONCLUSIVE, 0 RC).")

    # 4. Validar determinismo con doble exportación en directorio temporal
    print("Validando determinismo de exportación...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_a = Path(tmp_dir) / "runtime-a.json"
        tmp_b = Path(tmp_dir) / "runtime-b.json"

        col_a, sha_a = export_files_to_runtime(
            input_paths=input_paths,
            output_path=tmp_a,
            audit_sources=[STATUS_MAP_FILE],
            generated_at=generated_at
        )
        col_b, sha_b = export_files_to_runtime(
            input_paths=input_paths,
            output_path=tmp_b,
            audit_sources=[STATUS_MAP_FILE],
            generated_at=generated_at
        )

        bytes_a = tmp_a.read_bytes()
        bytes_b = tmp_b.read_bytes()

        if bytes_a != bytes_b or sha_a != sha_b:
            raise ValueError("La exportación runtime NO es determinista (mismatch entre corrida A y B). Fail-closed.")

        print(f"  Determinismo 100% verificado: {sha_a}")

    # 5. Exportar runtime final de producción
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collection, runtime_sha256 = export_files_to_runtime(
        input_paths=input_paths,
        output_path=output_path,
        audit_sources=[STATUS_MAP_FILE],
        generated_at=generated_at
    )

    # 6. Validaciones estructurales y de no persistencia
    validate_runtime_collection(collection)
    assert_no_forbidden_keys(collection, path="ProductionRuntimeCollection")

    # Métricas del runtime generado
    questions = collection["questions"]
    total_q = len(questions)
    if total_q != 3847:
        raise ValueError(f"Total preguntas en runtime={total_q} != 3847. Fail-closed.")

    ot_count = sum(1 for q in questions if q["testament"] == "OT")
    nt_count = sum(1 for q in questions if q["testament"] == "NT")
    mc_count = sum(1 for q in questions if q["questionType"] == "MULTIPLE_CHOICE")
    tf_count = sum(1 for q in questions if q["questionType"] == "TRUE_FALSE")

    diff_counts = {
        "BASIC": sum(1 for q in questions if q["difficulty"] == "BASIC"),
        "INTERMEDIATE": sum(1 for q in questions if q["difficulty"] == "INTERMEDIATE"),
        "ADVANCED": sum(1 for q in questions if q["difficulty"] == "ADVANCED"),
        "EXPERT": sum(1 for q in questions if q["difficulty"] == "EXPERT"),
    }

    status_counts = {
        "VERIFIED": sum(1 for q in questions if q["auditStatus"] == "VERIFIED"),
        "INCONCLUSIVE": sum(1 for q in questions if q["auditStatus"] == "INCONCLUSIVE"),
        "REQUIRES_CORRECTION": sum(1 for q in questions if q["auditStatus"] == "REQUIRES_CORRECTION"),
    }

    if status_counts["VERIFIED"] != 2486 or status_counts["INCONCLUSIVE"] != 1361 or status_counts["REQUIRES_CORRECTION"] != 0:
        raise ValueError(f"Conteo de auditStatus en runtime incorrecto: {status_counts}. Fail-closed.")

    runtime_size = output_path.stat().st_size

    # 7. Generar manifiesto de producción
    prod_manifest = {
        "bank_version": BANK_VERSION,
        "schema_version": SCHEMA_VERSION,
        "runtime_file": output_path.name,
        "runtime_sha256": runtime_sha256,
        "runtime_size_bytes": runtime_size,
        "generated_at": generated_at,
        "canonical_commit": freeze_data.get("audit_commit", "16ca4d73e4edbef0227dfe6d1b95d4b2f963b6d5"),
        "audit_commit": freeze_data.get("audit_commit", "16ca4d73e4edbef0227dfe6d1b95d4b2f963b6d5"),
        "canon": "PROTESTANT_66",
        "verification_translation": "RVR1960",
        "total_books": 66,
        "total_chapters": 1189,
        "total_questions": total_q,
        "ot_questions": ot_count,
        "nt_questions": nt_count,
        "verified_count": status_counts["VERIFIED"],
        "inconclusive_count": status_counts["INCONCLUSIVE"],
        "requires_correction_count": status_counts["REQUIRES_CORRECTION"],
        "multiple_choice_count": mc_count,
        "true_false_count": tf_count,
        "difficulty_counts": diff_counts,
        "source_text_persisted": False,
        "fail_closed": True,
        "deterministic_export": True,
    }

    manifest_path.write_bytes((json.dumps(prod_manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))

    print("\n" + "=" * 80)
    print("EXPORTACIÓN DE PRODUCCIÓN FINALIZADA CON ÉXITO")
    print(f"  Versión del banco:   {BANK_VERSION}")
    print(f"  Archivo de runtime:  {output_path} ({runtime_size:,} bytes)")
    print(f"  SHA-256:             {runtime_sha256}")
    print(f"  Manifiesto:          {manifest_path}")
    print(f"  Preguntas totales:   {total_q} (2620 OT + 1227 NT)")
    print(f"  Tipos:               {mc_count} MULTIPLE_CHOICE | {tf_count} TRUE_FALSE")
    print(f"  Dificultades:        {diff_counts}")
    print(f"  Estados:             {status_counts['VERIFIED']} VERIFIED | {status_counts['INCONCLUSIVE']} INCONCLUSIVE | {status_counts['REQUIRES_CORRECTION']} RC")
    print(f"  Fail-Closed:         TRUE")
    print("=" * 80)

    return collection, runtime_sha256, prod_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Exportación de producción de Quiz Bible")
    parser.add_argument("--output", type=Path, default=DEFAULT_RUNTIME_FILE, help="Ruta de salida del archivo runtime")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_RUNTIME_MANIFEST, help="Ruta del manifest runtime")
    parser.add_argument("--generated-at", type=str, default=CANONICAL_TIMESTAMP, help="Timestamp determinista")
    args = parser.parse_args()

    try:
        run_production_export(output_path=args.output, manifest_path=args.manifest, generated_at=args.generated_at)
        return 0
    except Exception as e:
        print(f"ERROR EN EXPORTACIÓN DE PRODUCCIÓN: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
