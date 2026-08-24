#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/runtime_export/export_runtime.py

Exportador determinista de bancos canónicos auditados a formato Runtime JSON v1
para Quiz Bible (Android/App).

Transforma los bancos canónicos estructurados (*-master-input.json) al contrato
definido en data/runtime/quiz_bible_runtime_v1.schema.json, preservando la
totalidad de la información editorial, trazabilidad, categorías, dificultades y
modos elegibles sin persistir texto bíblico RVR1960.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Esquema de validación predeterminado
DEFAULT_SCHEMA_PATH = REPO_ROOT / "data" / "runtime" / "quiz_bible_runtime_v1.schema.json"

# Claves prohibidas que indicarían persistencia no autorizada de texto bíblico
FORBIDDEN_SCRIPTURE_KEYS = {
    "verse_text",
    "versetext",
    "scripture_text",
    "scripturetext",
    "texto_biblico",
    "texto_bíblico",
    "textobiblico",
    "pasaje",
    "passage",
    "raw_verse",
    "biblical_text",
    "biblicaltext",
}

OLD_TESTAMENT_BOOKS = {
    "génesis", "genesis", "éxodo", "exodo", "levítico", "levitico",
    "números", "numeros", "deuteronomio", "josué", "josue", "jueces",
    "rut", "ruth", "1 samuel", "1samuel", "2 samuel", "2samuel",
    "1 reyes", "1kings", "2 reyes", "2kings", "1 crónicas", "1cronicas",
    "1chronicles", "2 crónicas", "2cronicas", "2chronicles",
    "esdras", "nehemías", "nehemias", "ester", "job", "salmos",
    "proverbios", "eclesiastés", "eclesiastes", "cantares", "cantar de los cantares",
    "isaías", "isaias", "jeremías", "jeremias", "lamentaciones",
    "ezequiel", "daniel", "oseas", "joel", "amós", "amos", "abdías", "abdias",
    "jonás", "jonas", "miqueas", "nahúm", "nahum", "habacuc",
    "sofonías", "sofonias", "hageo", "zacarías", "zacarias", "malaquías", "malaquias"
}

NEW_TESTAMENT_BOOKS = {
    "mateo", "matthew", "marcos", "mark", "lucas", "luke", "juan", "john",
    "hechos", "acts", "romanos", "romans", "1 corintios", "1corintios", "1corinthians",
    "2 corintios", "2corintios", "2corinthians", "gálatas", "galatas", "galatians",
    "efesios", "ephesians", "filipenses", "philippians", "colosenses", "colossians",
    "1 tesalonicenses", "1tesalonicenses", "1thessalonians",
    "2 tesalonicenses", "2tesalonicenses", "2thessalonians",
    "1 timoteo", "1timoteo", "1timothy", "2 timoteo", "2timoteo", "2timothy",
    "tito", "titus", "filemón", "filemon", "philemon", "hebreos", "hebrews",
    "santiago", "james", "1 pedro", "1pedro", "1peter", "2 pedro", "2pedro", "2peter",
    "1 juan", "1juan", "1john", "2 juan", "2juan", "2john", "3 juan", "3juan", "3john",
    "judas", "jude", "apocalipsis", "revelation"
}


def normalize_difficulty(diff_str: str) -> str:
    """Normaliza la dificultad canónica a la enumeración técnica de runtime."""
    s = str(diff_str).strip().lower()
    s_clean = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if s_clean in {"basico", "basic", "beginner", "facil"}:
        return "BASIC"
    if s_clean in {"intermedio", "intermediate", "medio"}:
        return "INTERMEDIATE"
    if s_clean in {"avanzado", "advanced", "dificil"}:
        return "ADVANCED"
    if s_clean in {"experto", "expert", "dificilismo"}:
        return "EXPERT"
    raise ValueError(f"Dificultad no reconocida: '{diff_str}'")


def normalize_question_type(qtype_str: str) -> str:
    """Normaliza el tipo de pregunta a la enumeración técnica de runtime (Fail-Closed)."""
    s = str(qtype_str).strip().lower()
    s_clean = s.replace("é", "e").replace("ó", "o").replace("ú", "u").replace("í", "i").replace("á", "a")
    if s_clean in {
        "seleccion multiple",
        "multiple_choice",
        "multiple choice",
        "mc",
        "opcion_multiple",
        "opcion multiple",
    }:
        return "MULTIPLE_CHOICE"
    if s_clean in {
        "verdadero_falso",
        "verdadero falso",
        "true_false",
        "true false",
        "tf",
        "vf",
    }:
        return "TRUE_FALSE"
    raise ValueError(f"Tipo de pregunta desconocido o no soportado: '{qtype_str}'. Fail-closed: exportación rechazada.")


def determine_testament(q: dict[str, Any]) -> str:
    """Determina el testamento canónico (OT / NT) a partir del ID o del libro (Fail-Closed)."""
    qid = str(q.get("id", "")).upper()
    book_name = str(q.get("book", "")).strip().lower()

    if "-AT-" in qid or book_name in OLD_TESTAMENT_BOOKS:
        return "OT"
    if "-NT-" in qid or book_name in NEW_TESTAMENT_BOOKS:
        return "NT"
    raise ValueError(
        f"No se pudo determinar el testamento canónico (OT/NT) para pregunta '{qid}' con libro '{q.get('book')}'. Fail-closed: exportación rechazada."
    )


def normalize_audit_status(status_str: str, strict: bool = True) -> str:
    """Normaliza el estado de auditoría a la enumeración técnica de runtime (Fail-Closed)."""
    if not status_str:
        raise ValueError("Estado de auditoría vacío o no definido. Fail-closed: exportación rechazada.")
    st_upper = str(status_str).strip().upper()
    if st_upper in {"VERIFICADO", "VERIFIED", "PASS"}:
        return "VERIFIED"
    if st_upper in {"NO_CONCLUYENTE", "INCONCLUSIVE"}:
        return "INCONCLUSIVE"
    if st_upper in {"REQUIERE_CORRECCION", "REQUIRES_CORRECTION", "FAIL"}:
        return "REQUIRES_CORRECTION"
    if st_upper == "UNKNOWN":
        if strict:
            raise ValueError(f"Estado de auditoría inválido 'UNKNOWN'. Fail-closed: exportación rechazada.")
        return "INCONCLUSIVE"
    raise ValueError(f"Estado de auditoría inválido o no reconocido: '{status_str}'. Fail-closed: exportación rechazada.")


def load_audit_status_map(
    sources: list[Path | str] | Path | str | None,
    strict: bool = True
) -> dict[str, str]:
    """Carga de forma exhaustiva el mapa de estados de auditoría desde archivos o directorios de artefactos."""
    if not sources:
        return {}
    if isinstance(sources, (str, Path)):
        sources = [sources]

    status_map: dict[str, str] = {}

    def add_status(qid: str, st_raw: str, origin: str) -> None:
        if not qid or not str(qid).strip():
            return
        qid_clean = str(qid).strip()
        norm_st = normalize_audit_status(st_raw, strict=strict)
        if qid_clean in status_map and status_map[qid_clean] != norm_st:
            raise ValueError(
                f"Conflicto de estado de auditoría para QID '{qid_clean}': '{status_map[qid_clean]}' vs '{norm_st}' en {origin}. Fail-closed: exportación rechazada."
            )
        status_map[qid_clean] = norm_st

    def process_file(p: Path) -> None:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return

        # 0. entries dict (formato canónico de status maps globales v1)
        entries = data.get("entries")
        if isinstance(entries, dict):
            for qid, entry in entries.items():
                if not str(qid).startswith("NQB-"):
                    continue
                if isinstance(entry, dict):
                    st = entry.get("audit_status") or entry.get("estado")
                else:
                    st = str(entry)
                if not st:
                    raise ValueError(f"Falta audit_status para QID '{qid}' en status map '{p}'. Fail-closed.")
                add_status(qid, st, f"{p} (entries)")

        # 1. results list (bloques de auditoría individual)
        for item in data.get("results", []):
            if isinstance(item, dict) and "id" in item:
                st = item.get("estado") or item.get("audit_status", "")
                if st:
                    add_status(item["id"], st, f"{p} (results)")

        # 2. evaluaciones dict
        if "evaluaciones" in data and isinstance(data["evaluaciones"], dict):
            for qid, ev in data["evaluaciones"].items():
                st = ev.get("estado") or ev.get("audit_status") if isinstance(ev, dict) else str(ev)
                if st:
                    add_status(qid, st, f"{p} (evaluaciones)")

        # 3. requires_correction_items
        for item in data.get("requires_correction_items", []):
            if isinstance(item, dict) and "id" in item:
                add_status(item["id"], "REQUIRES_CORRECTION", f"{p} (requires_correction_items)")

        # 4. inconclusive_items
        for item in data.get("inconclusive_items", []):
            if isinstance(item, dict) and "id" in item:
                add_status(item["id"], "INCONCLUSIVE", f"{p} (inconclusive_items)")

        # 5. revision-manual-pendiente
        for item in data.get("pendientes", data.get("items", [])):
            if isinstance(item, dict) and "id" in item:
                add_status(item["id"], item.get("estado", "INCONCLUSIVE"), f"{p} (pendientes)")

        # 6. Mapeo directo {qid: status}
        for k, v in data.items():
            if k.startswith("NQB-") and isinstance(v, str):
                add_status(k, v, f"{p} (direct key)")

    for src in sources:
        sp = Path(src)
        if sp.is_dir():
            for f in sorted(sp.rglob("*.json")):
                process_file(f)
        elif sp.is_file():
            process_file(sp)

    return status_map


def assert_no_forbidden_keys(obj: Any, path: str = "$") -> None:
    """Valida recursivamente que ningún objeto contenga claves de texto bíblico persistido."""
    if isinstance(obj, dict):
        if not path.endswith("options") and not re.search(r"options\[\d+\]$", path):
            if "text" in obj:
                raise ValueError(
                    f"Violación de no persistencia de texto bíblico: clave 'text' encontrada fuera de options en {path}.text"
                )
        for k, v in obj.items():
            k_lower = str(k).lower()
            if k_lower in FORBIDDEN_SCRIPTURE_KEYS:
                raise ValueError(
                    f"Violación de no persistencia de texto bíblico: clave prohibida '{k}' encontrada en {path}.{k}"
                )
            assert_no_forbidden_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            assert_no_forbidden_keys(item, f"{path}[{idx}]")


def export_question_to_runtime(
    canonical_q: dict[str, Any],
    audit_status: str,
    human_review_status: str = "PENDING"
) -> dict[str, Any]:
    """Transforma una pregunta canónica al modelo de runtime V1 aplicando política Fail-Closed."""
    qid = str(canonical_q["id"]).strip()
    book = str(canonical_q["book"]).strip()
    chapter = int(canonical_q["chapter"])
    verse_start = int(canonical_q["verse_start"])
    verse_end = int(canonical_q["verse_end"]) if canonical_q.get("verse_end") is not None else None
    ref_display = str(canonical_q.get("reference", f"{book} {chapter}:{verse_start}")).strip()

    category = str(canonical_q.get("category", "AT_GENERAL")).strip()
    subcategory = canonical_q.get("subcategory")
    if subcategory is not None:
        subcategory = str(subcategory).strip()

    characters = [str(c).strip() for c in canonical_q.get("characters", [])]
    difficulty = normalize_difficulty(str(canonical_q.get("difficulty", "Intermedio")))
    question_type = normalize_question_type(str(canonical_q.get("question_type", canonical_q.get("type", "Selección múltiple"))))
    prompt = str(canonical_q.get("question", "")).strip()

    opcion_a = str(canonical_q.get("opcion_a", "")).strip()
    opcion_b = str(canonical_q.get("opcion_b", "")).strip()
    opcion_c = str(canonical_q.get("opcion_c", "")).strip()
    opcion_d = str(canonical_q.get("opcion_d", "")).strip()

    correct_option_id = str(canonical_q.get("correct_option", "A")).strip().upper()

    if question_type == "MULTIPLE_CHOICE":
        if not opcion_a or not opcion_b or not opcion_c or not opcion_d:
            raise ValueError(f"Pregunta '{qid}' (MULTIPLE_CHOICE) contiene opciones vacías. Fail-closed: exportación rechazada.")
        options = [
            {"id": "A", "text": opcion_a},
            {"id": "B", "text": opcion_b},
            {"id": "C", "text": opcion_c},
            {"id": "D", "text": opcion_d},
        ]
        if correct_option_id not in {"A", "B", "C", "D"}:
            raise ValueError(f"correctOptionId '{correct_option_id}' no pertenece a las opciones A/B/C/D en '{qid}'. Fail-closed.")
    elif question_type == "TRUE_FALSE":
        if not opcion_a or not opcion_b:
            raise ValueError(f"Pregunta '{qid}' (TRUE_FALSE) carece de opción A o B. Fail-closed: exportación rechazada.")
        if opcion_c or opcion_d:
            raise ValueError(f"Pregunta '{qid}' (TRUE_FALSE) contiene opción C o D con contenido ('{opcion_c}', '{opcion_d}'). Fail-closed: exportación rechazada.")
        options = [
            {"id": "A", "text": opcion_a},
            {"id": "B", "text": opcion_b},
        ]
        if correct_option_id not in {"A", "B"}:
            raise ValueError(f"correctOptionId '{correct_option_id}' no pertenece a las opciones A/B en '{qid}'. Fail-closed.")
    else:
        raise ValueError(f"Tipo de pregunta no soportado '{question_type}' en '{qid}'. Fail-closed: exportación rechazada.")

    explanation = str(canonical_q.get("explanation", "")).strip()
    eligible_modes = [str(m).strip() for m in canonical_q.get("eligible_modes", ["AT", "AMBOS"])]

    validated_audit_status = normalize_audit_status(audit_status, strict=True)

    runtime_obj: dict[str, Any] = {
        "id": qid,
        "testament": determine_testament(canonical_q),
        "book": book,
        "chapter": chapter,
        "verseStart": verse_start,
        "verseEnd": verse_end,
        "referenceDisplay": ref_display,
        "category": category,
        "subcategory": subcategory,
        "characters": characters,
        "difficulty": difficulty,
        "questionType": question_type,
        "prompt": prompt,
        "options": options,
        "correctOptionId": correct_option_id,
        "explanation": explanation,
        "eligibleModes": eligible_modes,
        "verificationTranslation": "RVR1960",
        "auditStatus": validated_audit_status,
        "humanReviewStatus": human_review_status,
    }

    assert_no_forbidden_keys(runtime_obj, path=f"Question({qid})")
    return runtime_obj


def build_runtime_collection(
    questions: list[dict[str, Any]],
    generated_at: str = "2026-08-21T00:00:00Z",
    schema_version: str = "quizbible-runtime-v1"
) -> dict[str, Any]:
    """Empaqueta una lista de preguntas de runtime en el contenedor oficial."""
    return {
        "schemaVersion": schema_version,
        "generatedAt": generated_at,
        "totalQuestions": len(questions),
        "questions": questions,
    }


def validate_runtime_collection(
    data: dict[str, Any],
    schema_path: Path | str | None = None
) -> bool:
    """Valida la colección de runtime contra el schema JSON oficial."""
    sp = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    if not sp.exists():
        raise FileNotFoundError(f"Schema de runtime no encontrado en '{sp}'")

    schema_json = json.loads(sp.read_text(encoding="utf-8"))

    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema_json)
    except ImportError:
        if data.get("schemaVersion") != "quizbible-runtime-v1":
            raise ValueError("schemaVersion inválido")
        if not isinstance(data.get("questions"), list):
            raise ValueError("questions debe ser una lista")
        if data.get("totalQuestions") != len(data["questions"]):
            raise ValueError("totalQuestions no coincide con el conteo de preguntas")
        for q in data["questions"]:
            q_type = q.get("questionType")
            opts = q.get("options", [])
            if q_type == "MULTIPLE_CHOICE":
                if len(opts) != 4:
                    raise ValueError(f"Pregunta {q.get('id')} (MULTIPLE_CHOICE) no tiene 4 opciones")
                if q.get("correctOptionId") not in {"A", "B", "C", "D"}:
                    raise ValueError(f"correctOptionId canónico debe ser A/B/C/D en {q.get('id')}")
            elif q_type == "TRUE_FALSE":
                if len(opts) != 2:
                    raise ValueError(f"Pregunta {q.get('id')} (TRUE_FALSE) no tiene 2 opciones")
                if q.get("correctOptionId") not in {"A", "B"}:
                    raise ValueError(f"correctOptionId canónico debe ser A/B en {q.get('id')}")
            else:
                raise ValueError(f"questionType desconocido en {q.get('id')}: '{q_type}'")
            for opt in opts:
                if not opt.get("text") or not str(opt["text"]).strip():
                    raise ValueError(f"Opción vacía en pregunta {q.get('id')}")

    assert_no_forbidden_keys(data, path="RuntimeCollection")
    return True


def export_canonical_data(
    canonical_questions: list[dict[str, Any]],
    filter_ids: set[str] | list[str] | None = None,
    audit_status_map: dict[str, str] | None = None,
    audit_sources: list[Path | str] | Path | str | None = None,
    human_review_status_map: dict[str, str] | None = None,
    generated_at: str = "2026-08-21T00:00:00Z"
) -> dict[str, Any]:
    """Transforma una lista de preguntas canónicas a una colección runtime oficial (Fail-Closed)."""
    final_status_map: dict[str, str] = {}
    if audit_sources:
        final_status_map.update(load_audit_status_map(audit_sources, strict=True))
    if audit_status_map:
        for k, v in audit_status_map.items():
            norm_st = normalize_audit_status(v, strict=True)
            if k in final_status_map and final_status_map[k] != norm_st:
                raise ValueError(f"Conflicto de estado de auditoría para QID '{k}': '{final_status_map[k]}' vs '{norm_st}'. Fail-closed.")
            final_status_map[k] = norm_st

    runtime_questions: list[dict[str, Any]] = []
    filter_set = set(filter_ids) if filter_ids is not None else None

    for q in canonical_questions:
        qid = q.get("id")
        if filter_set is not None and qid not in filter_set:
            continue

        if qid not in final_status_map:
            raise ValueError(
                f"Pregunta '{qid}' no posee estado de auditoría registrado en las fuentes oficiales provistas. Fail-closed: exportación rechazada."
            )

        audit_st = final_status_map[qid]
        human_st = human_review_status_map.get(qid, "PENDING") if human_review_status_map else "PENDING"
        rt_q = export_question_to_runtime(q, audit_status=audit_st, human_review_status=human_st)
        runtime_questions.append(rt_q)

    if filter_ids is not None and isinstance(filter_ids, list):
        id_order = {qid: i for i, qid in enumerate(filter_ids)}
        runtime_questions.sort(key=lambda x: id_order.get(x["id"], 999999))

    collection = build_runtime_collection(runtime_questions, generated_at=generated_at)
    validate_runtime_collection(collection)
    return collection


def export_files_to_runtime(
    input_paths: list[Path],
    output_path: Path,
    filter_ids: set[str] | list[str] | None = None,
    audit_sources: list[Path | str] | Path | str | None = None,
    audit_status_map: dict[str, str] | None = None,
    generated_at: str = "2026-08-21T00:00:00Z"
) -> tuple[dict[str, Any], str]:
    """Lee archivos canónicos, los transforma, valida y escribe el runtime JSON determinista."""
    all_canonical_qs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for p in input_paths:
        if not p.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: '{p}'")
        raw = json.loads(p.read_text(encoding="utf-8"))
        qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        for q in qs:
            qid = q.get("id")
            if qid not in seen_ids:
                seen_ids.add(qid)
                all_canonical_qs.append(q)

    collection = export_canonical_data(
        all_canonical_qs,
        filter_ids=filter_ids,
        audit_sources=audit_sources,
        audit_status_map=audit_status_map,
        generated_at=generated_at
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(collection, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(serialized, encoding="utf-8")

    sha256_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return collection, sha256_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportador de preguntas canónicas a Runtime JSON v1 para Quiz Bible.")
    parser.add_argument("--inputs", nargs="+", help="Rutas de archivos *-master-input.json", required=True)
    parser.add_argument("--output", help="Ruta del archivo JSON runtime de salida", required=True)
    parser.add_argument("--audit-sources", "--audit-dir", nargs="*", help="Rutas de carpetas o archivos de informes de auditoría", default=None)
    parser.add_argument("--filter-ids", nargs="*", help="Lista opcional de IDs de preguntas a incluir", default=None)
    parser.add_argument("--generated-at", help="Marca de tiempo determinista ISO", default="2026-08-21T00:00:00Z")

    args = parser.parse_args()
    input_paths = [Path(p) for p in args.inputs]
    output_path = Path(args.output)
    filter_ids = args.filter_ids if args.filter_ids else None
    audit_sources = args.audit_sources if args.audit_sources else None

    collection, sha = export_files_to_runtime(
        input_paths,
        output_path,
        filter_ids=filter_ids,
        audit_sources=audit_sources,
        generated_at=args.generated_at
    )

    print(f"Exportación runtime exitosa (Fail-Closed):")
    print(f"  Preguntas exportadas: {collection['totalQuestions']}")
    print(f"  Archivo de salida: {output_path}")
    print(f"  SHA-256: {sha}")


if __name__ == "__main__":
    main()
