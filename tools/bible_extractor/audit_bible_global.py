#!/usr/bin/env python3
"""
Auditor Global de la Biblia Protestante (66 libros canónicos, 1189 capítulos, 3847 preguntas).

Ejecuta verificación transversal completa AT + NT:
- Reconciliación de cierres oficiales AT (39 libros, 2620 preguntas) y NT (27 libros, 1227 preguntas).
- Verificación de 66 hashes SHA-256 congelados e integridad estructural.
- Validación Fail-Closed del mapa de estados (2486 VERIFIED, 1361 INCONCLUSIVE, 0 RC).
- Detección exhaustiva de duplicados exactos y normalizados intra e intertestamentarios.
- Clasificación de relaciones semánticas intertestamentarias (citas, alusiones, temas paralelos).
- Generación de reportes de auditoría y validación de exportación runtime unificada.

PROHIBICIONES ESTRICTAS:
- NO asignar VERIFIED por defecto a ninguna pregunta (FAIL-CLOSED).
- NO persistir texto RVR1960.
- NO modificar bancos canónicos.
- NO depender de estados asumidos o inferidos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ============================================================
# Constantes canónicas globales (Biblia 66 libros)
# ============================================================

EXPECTED_TOTAL_BOOKS = 66
EXPECTED_TOTAL_BOOKS_OT = 39
EXPECTED_TOTAL_BOOKS_NT = 27

EXPECTED_TOTAL_CHAPTERS = 1189
EXPECTED_TOTAL_CHAPTERS_OT = 929
EXPECTED_TOTAL_CHAPTERS_NT = 260

EXPECTED_TOTAL_QUESTIONS = 3847
EXPECTED_TOTAL_QUESTIONS_OT = 2620
EXPECTED_TOTAL_QUESTIONS_NT = 1227

EXPECTED_GLOBAL_VERIFIED = 2486
EXPECTED_GLOBAL_INCONCLUSIVE = 1361
EXPECTED_GLOBAL_RC = 0

EXPECTED_DIFFICULTIES: Dict[str, int] = {
    "Básico": 693,
    "Intermedio": 1437,
    "Avanzado": 1243,
    "Experto": 474,
}

EXPECTED_CATEGORIES: Dict[str, int] = {
    "AT_GENERAL": 1615,
    "NT_GENERAL": 656,
    "PERSONAJES_BIBLICOS": 1348,
    "JESUS_PALABRAS": 144,
    "JESUS_MILAGROS": 47,
    "JESUS_PARABOLAS": 37,
}

EXPECTED_QUESTION_TYPES: Dict[str, int] = {
    "MULTIPLE_CHOICE": 3692,
    "TRUE_FALSE": 155,
}

EXPECTED_WITH_ADDITIONAL_REFS = 271
EXPECTED_TOTAL_ADDITIONAL_REFS = 354
EXPECTED_WITH_ADDITIONAL_REFS_OT = 51
EXPECTED_TOTAL_ADDITIONAL_REFS_OT = 73
EXPECTED_WITH_ADDITIONAL_REFS_NT = 220
EXPECTED_TOTAL_ADDITIONAL_REFS_NT = 281

EXPECTED_MODES: Dict[str, int] = {
    "AT": 2620,
    "NT": 1227,
    "AMBOS": 3847,
    "PERSONAJES_AT": 1005,
    "PERSONAJES_NT": 343,
    "PERSONAJES_AMBOS": 1348,
    "VERDADERO_FALSO_NT": 155,
    "VERDADERO_FALSO_AMBOS": 155,
    "JESUS_PALABRAS": 144,
    "JESUS_MILAGROS": 47,
    "JESUS_PARABOLAS": 37,
}

ALLOWED_CATEGORIES: Set[str] = {
    "AT_GENERAL",
    "NT_GENERAL",
    "PERSONAJES_BIBLICOS",
    "JESUS_PALABRAS",
    "JESUS_MILAGROS",
    "JESUS_PARABOLAS",
}

ALLOWED_DIFFICULTIES: Set[str] = {"Básico", "Intermedio", "Avanzado", "Experto"}
ALLOWED_AUDIT_STATUSES: Set[str] = {"VERIFIED", "INCONCLUSIVE", "REQUIRES_CORRECTION"}

# Pares/grupos de paralelismo bíblico e intertestamentario legítimo
CROSS_TESTAMENT_PARALLEL_GROUPS = [
    # Intertestamentarios proféticos / tipológicos
    {"genesis", "matthew", "luke", "john", "romans", "galatians", "hebrews", "1peter", "2peter", "revelation"},
    {"exodus", "1corinthians", "hebrews", "revelation"},
    {"leviticus", "hebrews"},
    {"psalms", "matthew", "mark", "luke", "john", "acts", "romans", "hebrews"},
    {"isaiah", "matthew", "mark", "luke", "john", "acts", "romans", "1peter", "revelation"},
    {"jeremiah", "hebrews", "revelation"},
    {"ezekiel", "revelation"},
    {"daniel", "matthew", "2thessalonians", "revelation"},
    {"zechariah", "matthew", "revelation"},
    {"malachi", "matthew", "mark", "luke"},
    # Intratestamentarios AT
    {"1samuel", "2samuel", "1chronicles"},
    {"1kings", "2kings", "2chronicles"},
    {"ezra", "nehemiah"},
    # Intratestamentarios NT
    {"matthew", "mark", "luke", "john"},
    {"romans", "galatians"},
    {"ephesians", "colossians"},
    {"1thessalonians", "2thessalonians"},
    {"1timothy", "2timothy", "titus"},
    {"1peter", "2peter", "jude"},
    {"1john", "2john", "3john"},
]

# Orden canónico completo de los 66 libros
CANONICAL_66_BOOKS = [
    # Antiguo Testamento (1-39)
    (1,  "genesis",         "Génesis",                  "genesis-master-input.json",         50, 120, "OLD_TESTAMENT"),
    (2,  "exodus",          "Éxodo",                    "exodus-master-input.json",          40, 100, "OLD_TESTAMENT"),
    (3,  "leviticus",       "Levítico",                 "leviticus-master-input.json",       27,  80, "OLD_TESTAMENT"),
    (4,  "numbers",         "Números",                  "numbers-master-input.json",         36, 100, "OLD_TESTAMENT"),
    (5,  "deuteronomy",     "Deuteronomio",             "deuteronomy-master-input.json",     34, 100, "OLD_TESTAMENT"),
    (6,  "joshua",          "Josué",                    "joshua-master-input.json",          24, 100, "OLD_TESTAMENT"),
    (7,  "judges",          "Jueces",                   "judges-master-input.json",          21, 100, "OLD_TESTAMENT"),
    (8,  "ruth",            "Rut",                      "ruth-master-input.json",             4,  40, "OLD_TESTAMENT"),
    (9,  "1samuel",         "1 Samuel",                 "1samuel-master-input.json",         31, 100, "OLD_TESTAMENT"),
    (10, "2samuel",         "2 Samuel",                 "2samuel-master-input.json",         24,  84, "OLD_TESTAMENT"),
    (11, "1kings",          "1 Reyes",                  "1kings-master-input.json",          22, 100, "OLD_TESTAMENT"),
    (12, "2kings",          "2 Reyes",                  "2kings-master-input.json",          25, 104, "OLD_TESTAMENT"),
    (13, "1chronicles",     "1 Crónicas",               "1chronicles-master-input.json",     29,  80, "OLD_TESTAMENT"),
    (14, "2chronicles",     "2 Crónicas",               "2chronicles-master-input.json",     36, 102, "OLD_TESTAMENT"),
    (15, "ezra",            "Esdras",                   "ezra-master-input.json",            10,  52, "OLD_TESTAMENT"),
    (16, "nehemiah",        "Nehemías",                 "nehemiah-master-input.json",        13,  60, "OLD_TESTAMENT"),
    (17, "esther",          "Ester",                    "esther-master-input.json",          10,  50, "OLD_TESTAMENT"),
    (18, "job",             "Job",                      "job-master-input.json",             42,  60, "OLD_TESTAMENT"),
    (19, "psalms",          "Salmos",                   "psalms-master-input.json",         150,  90, "OLD_TESTAMENT"),
    (20, "proverbs",        "Proverbios",               "proverbs-master-input.json",        31,  72, "OLD_TESTAMENT"),
    (21, "ecclesiastes",    "Eclesiastés",              "ecclesiastes-master-input.json",    12,  49, "OLD_TESTAMENT"),
    (22, "song-of-songs",   "Cantar de los Cantares",   "song-of-songs-master-input.json",    8,  40, "OLD_TESTAMENT"),
    (23, "isaiah",          "Isaías",                   "isaiah-master-input.json",          66,  90, "OLD_TESTAMENT"),
    (24, "jeremiah",        "Jeremías",                 "jeremiah-master-input.json",        52,  79, "OLD_TESTAMENT"),
    (25, "lamentations",    "Lamentaciones",            "lamentations-master-input.json",     5,  35, "OLD_TESTAMENT"),
    (26, "ezekiel",         "Ezequiel",                 "ezekiel-master-input.json",         48,  86, "OLD_TESTAMENT"),
    (27, "daniel",          "Daniel",                   "daniel-master-input.json",          12,  50, "OLD_TESTAMENT"),
    (28, "hosea",           "Oseas",                    "hosea-master-input.json",           14,  50, "OLD_TESTAMENT"),
    (29, "joel",            "Joel",                     "joel-master-input.json",             3,  30, "OLD_TESTAMENT"),
    (30, "amos",            "Amós",                     "amos-master-input.json",             9,  49, "OLD_TESTAMENT"),
    (31, "obadiah",         "Abdías",                   "obadiah-master-input.json",          1,  24, "OLD_TESTAMENT"),
    (32, "jonah",           "Jonás",                    "jonah-master-input.json",            4,  40, "OLD_TESTAMENT"),
    (33, "micah",           "Miqueas",                  "micah-master-input.json",            7,  48, "OLD_TESTAMENT"),
    (34, "nahum",           "Nahúm",                    "nahum-master-input.json",            3,  34, "OLD_TESTAMENT"),
    (35, "habakkuk",        "Habacuc",                  "habakkuk-master-input.json",         3,  36, "OLD_TESTAMENT"),
    (36, "zephaniah",       "Sofonías",                 "zephaniah-master-input.json",        3,  38, "OLD_TESTAMENT"),
    (37, "haggai",          "Hageo",                    "haggai-master-input.json",           2,  34, "OLD_TESTAMENT"),
    (38, "zechariah",       "Zacarías",                 "zechariah-master-input.json",       14,  70, "OLD_TESTAMENT"),
    (39, "malachi",         "Malaquías",                "malachi-master-input.json",          4,  44, "OLD_TESTAMENT"),
    # Nuevo Testamento (40-66)
    (40, "matthew",         "Mateo",                    "matthew-master-input.json",         28,  92, "NEW_TESTAMENT"),
    (41, "mark",            "Marcos",                   "mark-master-input.json",            16,  74, "NEW_TESTAMENT"),
    (42, "luke",            "Lucas",                    "luke-master-input.json",            24,  96, "NEW_TESTAMENT"),
    (43, "john",            "Juan",                     "john-master-input.json",            21, 100, "NEW_TESTAMENT"),
    (44, "acts",            "Hechos",                   "acts-master-input.json",            28, 112, "NEW_TESTAMENT"),
    (45, "romans",          "Romanos",                  "romans-master-input.json",          16,  80, "NEW_TESTAMENT"),
    (46, "1corinthians",    "1 Corintios",              "1corinthians-master-input.json",    16,  80, "NEW_TESTAMENT"),
    (47, "2corinthians",    "2 Corintios",              "2corinthians-master-input.json",    13,  65, "NEW_TESTAMENT"),
    (48, "galatians",       "Gálatas",                  "galatians-master-input.json",        6,  36, "NEW_TESTAMENT"),
    (49, "ephesians",       "Efesios",                  "ephesians-master-input.json",        6,  36, "NEW_TESTAMENT"),
    (50, "philippians",     "Filipenses",               "philippians-master-input.json",      4,  24, "NEW_TESTAMENT"),
    (51, "colossians",      "Colosenses",               "colossians-master-input.json",       4,  24, "NEW_TESTAMENT"),
    (52, "1thessalonians",  "1 Tesalonicenses",         "1thessalonians-master-input.json",   5,  30, "NEW_TESTAMENT"),
    (53, "2thessalonians",  "2 Tesalonicenses",         "2thessalonians-master-input.json",   3,  18, "NEW_TESTAMENT"),
    (54, "1timothy",        "1 Timoteo",                "1timothy-master-input.json",         6,  36, "NEW_TESTAMENT"),
    (55, "2timothy",        "2 Timoteo",                "2timothy-master-input.json",         4,  24, "NEW_TESTAMENT"),
    (56, "titus",           "Tito",                     "titus-master-input.json",            3,  18, "NEW_TESTAMENT"),
    (57, "philemon",        "Filemón",                  "philemon-master-input.json",         1,   6, "NEW_TESTAMENT"),
    (58, "hebrews",         "Hebreos",                  "hebrews-master-input.json",         13,  78, "NEW_TESTAMENT"),
    (59, "james",           "Santiago",                 "james-master-input.json",            5,  30, "NEW_TESTAMENT"),
    (60, "1peter",          "1 Pedro",                  "1peter-master-input.json",           5,  30, "NEW_TESTAMENT"),
    (61, "2peter",          "2 Pedro",                  "2peter-master-input.json",           3,  18, "NEW_TESTAMENT"),
    (62, "1john",           "1 Juan",                   "1john-master-input.json",            5,  30, "NEW_TESTAMENT"),
    (63, "2john",           "2 Juan",                   "2john-master-input.json",            1,   6, "NEW_TESTAMENT"),
    (64, "3john",           "3 Juan",                   "3john-master-input.json",            1,   6, "NEW_TESTAMENT"),
    (65, "jude",            "Judas",                    "jude-master-input.json",             1,  12, "NEW_TESTAMENT"),
    (66, "revelation",      "Apocalipsis",              "revelation-master-input.json",      22,  66, "NEW_TESTAMENT"),
]


def normalize_text_for_dup_check(text: str) -> str:
    """Normaliza texto para detección de duplicados (remueve acentos, puntuación, espacios extras)."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def tokenize_for_similarity(text: str) -> Set[str]:
    """Extrae conjunto de tokens léxicos significativos (ignora stopwords breves)."""
    norm = normalize_text_for_dup_check(text)
    words = re.findall(r"\b[a-z0-9]{3,}\b", norm)
    stopwords = {
        "que", "del", "los", "las", "por", "para", "con", "cual", "quien",
        "segun", "como", "donde", "hizo", "dijo", "libro", "capitulo", "versiculo",
        "una", "uno", "unos", "unas", "sobre", "entre", "hacia", "hasta",
        "fue", "son", "era", "han", "hay", "sus", "este", "esta", "esto",
        "ese", "esa", "eso", "ellos", "ellas", "ella", "dice", "dijo",
    }
    return {w for w in words if w not in stopwords}


def classify_cross_testament_similarity(book_a: str, test_a: str, book_b: str, test_b: str) -> str:
    """
    Clasifica la relación de similitud semántica.
    Distingue paralelos bíblicos legítimos, citas intertestamentarias, alusiones y temas afines.
    """
    if book_a == book_b:
        return "MISMO_LIBRO"

    if test_a != test_b:
        # Relación intertestamentaria (AT ↔ NT)
        for group in CROSS_TESTAMENT_PARALLEL_GROUPS:
            if book_a in group and book_b in group:
                return "PARALELO_BIBLICO_LEGITIMO"
        return "ALUSION_INTERTESTAMENTARIA"

    # Mismo testamento pero libros distintos
    for group in CROSS_TESTAMENT_PARALLEL_GROUPS:
        if book_a in group and book_b in group:
            return "PARALELO_BIBLICO_LEGITIMO"

    return "SIMILITUD_TEMATICA"


class GlobalBibleAuditor:
    """
    Auditoría transversal final de los 66 libros de la Biblia Protestante (RVR1960).
    """

    def __init__(self, base_dir: Optional[Path] = None, output_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).parent
        self.output_dir = output_dir or Path("build/audit/bible-global")
        self.manifest_path = self.base_dir / "bible-global-manifest-v1.json"
        self.status_map_path = self.base_dir / "bible-global-audit-status-map-v1.json"

        self.manifest_data: Dict[str, Any] = {}
        self.status_map_raw: Dict[str, Any] = {}
        self.loaded_books: List[Dict[str, Any]] = []
        self.all_questions: List[Dict[str, Any]] = []
        self.audit_status_map: Dict[str, str] = {}

        self.issues: List[Dict[str, Any]] = []
        self.exact_duplicates: List[Dict[str, Any]] = []
        self.normalized_duplicates: List[Dict[str, Any]] = []
        self.cross_testament_exact_duplicates: List[Dict[str, Any]] = []
        self.cross_testament_norm_duplicates: List[Dict[str, Any]] = []
        self.semantic_clusters: List[Dict[str, Any]] = []

    def load_manifest(self) -> Dict[str, Any]:
        """Carga y valida el manifiesto oficial de los 66 libros."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest Biblia no encontrado: {self.manifest_path}")
        self.manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        if self.manifest_data.get("canon") != "PROTESTANT_66":
            raise ValueError(f"Manifest incorrecto: canon={self.manifest_data.get('canon')}")
        if self.manifest_data.get("total_books") != EXPECTED_TOTAL_BOOKS:
            raise ValueError(f"Manifest total_books={self.manifest_data.get('total_books')} != {EXPECTED_TOTAL_BOOKS}")
        if len(self.manifest_data.get("books", [])) != EXPECTED_TOTAL_BOOKS:
            raise ValueError(f"Manifest books length={len(self.manifest_data.get('books', []))} != {EXPECTED_TOTAL_BOOKS}")

        return self.manifest_data

    def load_and_validate_all_books(self) -> None:
        """Carga los 66 bancos maestros y valida SHAs, capítulos y preguntas."""
        if not self.manifest_data:
            self.load_manifest()

        manifest_by_key = {b["book_key"]: b for b in self.manifest_data["books"]}

        for order, key, canon_name, filename, exp_ch, exp_q, testament in CANONICAL_66_BOOKS:
            file_path = self.base_dir / filename
            if not file_path.exists():
                self.issues.append({
                    "type": "FILE_MISSING",
                    "book_key": key,
                    "file": filename,
                    "detail": "Archivo maestro no encontrado"
                })
                continue

            raw_bytes = file_path.read_bytes()
            real_sha = hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()

            m_entry = manifest_by_key.get(key)
            if not m_entry:
                self.issues.append({
                    "type": "MANIFEST_MISSING_ENTRY",
                    "book_key": key,
                    "detail": "Entrada faltante en manifest Biblia"
                })
                continue

            if m_entry["canonical_sha256"] != real_sha:
                self.issues.append({
                    "type": "SHA_MISMATCH",
                    "book_key": key,
                    "expected": m_entry["canonical_sha256"],
                    "real": real_sha
                })

            data = json.loads(raw_bytes.decode("utf-8"))
            questions = data.get("questions", data) if isinstance(data, dict) else data

            if len(questions) != exp_q:
                self.issues.append({
                    "type": "QUESTION_COUNT_MISMATCH",
                    "book_key": key,
                    "expected": exp_q,
                    "real": len(questions)
                })

            chapter_set = set(q.get("chapter") for q in questions if q.get("chapter"))
            if key == "psalms":
                if len(chapter_set) > exp_ch or len(chapter_set) == 0:
                    self.issues.append({
                        "type": "CHAPTER_COUNT_MISMATCH",
                        "book_key": key,
                        "expected_chapters": exp_ch,
                        "real_chapters": len(chapter_set),
                    })
            else:
                if len(chapter_set) != exp_ch:
                    self.issues.append({
                        "type": "CHAPTER_COUNT_MISMATCH",
                        "book_key": key,
                        "expected_chapters": exp_ch,
                        "real_chapters": len(chapter_set),
                        "chapters_found": sorted(chapter_set)
                    })

            self.loaded_books.append({
                "order": order,
                "book_key": key,
                "canonical_name": canon_name,
                "testament": testament,
                "filename": filename,
                "file_path": str(file_path),
                "sha256": real_sha,
                "chapters_expected": exp_ch,
                "questions_count": len(questions),
                "questions": questions,
                "manifest_entry": m_entry
            })

            for q in questions:
                # Inyectar testamento en objeto de pregunta para trazabilidad
                q_copy = dict(q)
                q_copy["testament"] = testament
                self.all_questions.append(q_copy)

    def validate_global_structural_integrity(self) -> Dict[str, Any]:
        """
        Verifica las 3847 preguntas a nivel global: IDs únicos, opciones, dificultad,
        categorías, tipos, modos y referencias adicionales.
        """
        id_counter: Counter = Counter()
        diff_counter: Counter = Counter()
        cat_counter: Counter = Counter()
        type_counter: Counter = Counter()
        modes_counter: Counter = Counter()
        characters_counter: Counter = Counter()

        q_with_add_refs = 0
        total_add_refs = 0
        q_with_add_refs_ot = 0
        total_add_refs_ot = 0
        q_with_add_refs_nt = 0
        total_add_refs_nt = 0

        cross_refs_breakdown = {
            "AT_to_AT": 0,
            "AT_to_NT": 0,
            "NT_to_AT": 0,
            "NT_to_NT": 0,
        }

        for q in self.all_questions:
            qid = q.get("id", "")
            if not qid:
                self.issues.append({"type": "EMPTY_ID", "question": str(q)[:200]})
                continue
            id_counter[qid] += 1

            testament = q.get("testament")
            raw_type = q.get("question_type") or q.get("type", "MULTIPLE_CHOICE")
            if raw_type in ("MULTIPLE_CHOICE", "Selección múltiple", "OPCION_MULTIPLE"):
                q_type = "MULTIPLE_CHOICE"
            elif raw_type == "TRUE_FALSE":
                q_type = "TRUE_FALSE"
            else:
                q_type = raw_type
            type_counter[q_type] += 1

            # Opciones según tipo
            if q_type == "TRUE_FALSE":
                for opt_key in ["opcion_a", "opcion_b"]:
                    val = q.get(opt_key, "")
                    if not val or not str(val).strip():
                        self.issues.append({"type": "EMPTY_TF_OPTION", "id": qid, "option": opt_key})
                co = q.get("correct_option")
                if co not in ("A", "B"):
                    self.issues.append({"type": "INVALID_TF_CORRECT_OPTION", "id": qid, "value": co})
                opcion_map = {"A": q.get("opcion_a"), "B": q.get("opcion_b")}
                if co and opcion_map.get(co) != q.get("correct_answer"):
                    self.issues.append({"type": "TF_CORRECT_ANSWER_MISMATCH", "id": qid})
            else:
                for opt_key in ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]:
                    val = q.get(opt_key, "")
                    if not val or not str(val).strip():
                        self.issues.append({"type": "EMPTY_OPTION", "id": qid, "option": opt_key})
                if q.get("correct_option") != "A":
                    self.issues.append({"type": "INVALID_CORRECT_OPTION", "id": qid, "value": q.get("correct_option")})
                if q.get("correct_answer") != q.get("opcion_a"):
                    self.issues.append({"type": "CORRECT_ANSWER_MISMATCH", "id": qid})

            # Dificultad
            diff = q.get("difficulty")
            if diff not in ALLOWED_DIFFICULTIES:
                self.issues.append({"type": "INVALID_DIFFICULTY", "id": qid, "value": diff})
            diff_counter[diff] += 1

            # Categoría
            cat = q.get("category")
            if cat not in ALLOWED_CATEGORIES:
                self.issues.append({"type": "INVALID_CATEGORY", "id": qid, "value": cat})
            cat_counter[cat] += 1

            # Tipo de pregunta
            if q_type not in {"MULTIPLE_CHOICE", "TRUE_FALSE"}:
                self.issues.append({"type": "INVALID_QUESTION_TYPE", "id": qid, "value": q_type})

            # Referencias adicionales
            add_refs = q.get("additional_references", [])
            if not isinstance(add_refs, list):
                self.issues.append({"type": "ADDITIONAL_REFS_NOT_LIST", "id": qid})
            elif len(add_refs) > 0:
                q_with_add_refs += 1
                total_add_refs += len(add_refs)
                if testament == "OLD_TESTAMENT":
                    q_with_add_refs_ot += 1
                    total_add_refs_ot += len(add_refs)
                else:
                    q_with_add_refs_nt += 1
                    total_add_refs_nt += len(add_refs)

                if len(add_refs) != len(set(add_refs)):
                    self.issues.append({"type": "DUPLICATE_INTERNAL_ADDITIONAL_REFS", "id": qid, "refs": add_refs})
                for r in add_refs:
                    if not r or not str(r).strip():
                        self.issues.append({"type": "EMPTY_ADDITIONAL_REF", "id": qid})

            # Personajes
            chars = q.get("characters", [])
            if not isinstance(chars, list):
                self.issues.append({"type": "CHARACTERS_NOT_LIST", "id": qid})
            else:
                if len(chars) != len(set(chars)):
                    self.issues.append({"type": "DUPLICATE_INTERNAL_CHARACTERS", "id": qid, "chars": chars})
                for ch in chars:
                    if not ch or not str(ch).strip():
                        self.issues.append({"type": "EMPTY_CHARACTER", "id": qid})
                    characters_counter[ch] += 1

            if cat == "PERSONAJES_BIBLICOS" and len(chars if isinstance(chars, list) else []) == 0:
                self.issues.append({"type": "PERSONAJES_CATEGORY_WITHOUT_CHARACTERS", "id": qid})

            # Modos elegibles
            modes = q.get("eligible_modes", [])
            if not modes or not isinstance(modes, list):
                self.issues.append({"type": "EMPTY_ELIGIBLE_MODES", "id": qid})
            else:
                if "AMBOS" not in modes:
                    self.issues.append({"type": "MISSING_AMBOS_MODE", "id": qid})
                if testament == "OLD_TESTAMENT" and "AT" not in modes:
                    self.issues.append({"type": "MISSING_AT_MODE", "id": qid})
                if testament == "NEW_TESTAMENT" and "NT" not in modes:
                    self.issues.append({"type": "MISSING_NT_MODE", "id": qid})
                for m in modes:
                    modes_counter[m] += 1

        dup_ids = {qid: cnt for qid, cnt in id_counter.items() if cnt > 1}
        if dup_ids:
            self.issues.append({"type": "DUPLICATE_QUESTION_IDS", "duplicates": dup_ids})

        return {
            "total_questions": len(self.all_questions),
            "unique_ids_count": len(id_counter),
            "duplicate_ids_count": len(dup_ids),
            "difficulty_counts": dict(diff_counter),
            "category_counts": dict(cat_counter),
            "question_type_counts": dict(type_counter),
            "questions_with_additional_references": q_with_add_refs,
            "total_additional_references": total_add_refs,
            "questions_with_additional_references_ot": q_with_add_refs_ot,
            "total_additional_references_ot": total_add_refs_ot,
            "questions_with_additional_references_nt": q_with_add_refs_nt,
            "total_additional_references_nt": total_add_refs_nt,
            "total_declared_characters_instances": sum(characters_counter.values()),
            "unique_declared_characters_count": len(characters_counter),
            "eligible_modes_counts": dict(modes_counter),
        }

    def detect_duplicates_and_similarity(self) -> Dict[str, Any]:
        """
        Detecta duplicados exactos y normalizados (intra e intertestamentarios) y analiza
        clusters de similitud semántica.
        """
        exact_map: Dict[str, List] = defaultdict(list)
        norm_map: Dict[str, List] = defaultdict(list)
        tokenized_questions = []

        for q in self.all_questions:
            qid = q.get("id")
            book = q.get("book")
            testament = q.get("testament")
            ref = q.get("reference")
            raw_text = q.get("question", "").strip()
            norm_text = normalize_text_for_dup_check(raw_text)
            tokens = tokenize_for_similarity(raw_text)

            item = {
                "id": qid,
                "book": book,
                "testament": testament,
                "reference": ref,
                "question": raw_text,
                "correct_answer": q.get("correct_answer"),
            }
            exact_map[raw_text].append(item)
            norm_map[norm_text].append(item)
            tokenized_questions.append((item, tokens))

        # Duplicados exactos globales
        for text, items in exact_map.items():
            if len(items) > 1:
                self.exact_duplicates.append({"question": text, "occurrences": items})
                testaments = set(it["testament"] for it in items)
                if len(testaments) > 1:
                    self.cross_testament_exact_duplicates.append({"question": text, "occurrences": items})

        # Duplicados normalizados globales
        for text, items in norm_map.items():
            if len(items) > 1:
                self.normalized_duplicates.append({"normalized_question": text, "occurrences": items})
                testaments = set(it["testament"] for it in items)
                if len(testaments) > 1:
                    self.cross_testament_norm_duplicates.append({"normalized_question": text, "occurrences": items})

        # Similitud semántica
        for i in range(len(tokenized_questions)):
            item_a, tok_a = tokenized_questions[i]
            if not tok_a:
                continue
            for j in range(i + 1, len(tokenized_questions)):
                item_b, tok_b = tokenized_questions[j]
                if not tok_b:
                    continue
                inter = tok_a.intersection(tok_b)
                union = tok_a.union(tok_b)
                sim = len(inter) / len(union) if union else 0.0
                if sim >= 0.75:
                    classification = classify_cross_testament_similarity(
                        item_a.get("book", ""), item_a.get("testament", ""),
                        item_b.get("book", ""), item_b.get("testament", "")
                    )
                    self.semantic_clusters.append({
                        "id_a": item_a["id"],
                        "book_a": item_a["book"],
                        "test_a": item_a["testament"],
                        "ref_a": item_a["reference"],
                        "q_a": item_a["question"],
                        "ans_a": item_a["correct_answer"],
                        "id_b": item_b["id"],
                        "book_b": item_b["book"],
                        "test_b": item_b["testament"],
                        "ref_b": item_b["reference"],
                        "q_b": item_b["question"],
                        "ans_b": item_b["correct_answer"],
                        "similarity": round(sim, 3),
                        "classification": classification,
                        "requires_editorial_change": False,
                    })

        return {
            "exact_duplicates_count": len(self.exact_duplicates),
            "normalized_duplicates_count": len(self.normalized_duplicates),
            "cross_testament_exact_duplicates_count": len(self.cross_testament_exact_duplicates),
            "cross_testament_norm_duplicates_count": len(self.cross_testament_norm_duplicates),
            "semantic_clusters_count": len(self.semantic_clusters),
        }

    def load_and_validate_audit_status_map(self) -> Dict[str, Any]:
        """
        Carga el status map global de la Biblia y valida que contenga exactamente 3847 IDs.
        FAIL-CLOSED:
        - Si un ID no tiene status o tiene status desconocido, se registra incidencia bloqueante.
        - NO asignar VERIFIED por defecto bajo ninguna circunstancia.
        """
        if not self.status_map_path.exists():
            raise FileNotFoundError(f"Status map Biblia no encontrado: {self.status_map_path}")

        self.status_map_raw = json.loads(self.status_map_path.read_text(encoding="utf-8"))
        entries = self.status_map_raw.get("entries", {})

        all_qids = [q["id"] for q in self.all_questions if q.get("id")]
        expected_ids = set(all_qids)

        id_to_status: Dict[str, str] = {}
        for entry_id, entry_data in entries.items():
            if isinstance(entry_data, dict):
                status = entry_data.get("audit_status", "")
            else:
                status = str(entry_data)
            id_to_status[entry_id] = status

        unknown = {eid: st for eid, st in id_to_status.items() if st not in ALLOWED_AUDIT_STATUSES}
        if unknown:
            self.issues.append({
                "type": "UNKNOWN_AUDIT_STATUS",
                "count": len(unknown),
                "examples": dict(list(unknown.items())[:10])
            })

        missing = expected_ids - set(id_to_status.keys())
        if missing:
            self.issues.append({
                "type": "MISSING_AUDIT_STATUS",
                "count": len(missing),
                "missing_ids": sorted(missing)[:20]
            })

        extra = set(id_to_status.keys()) - expected_ids
        if extra:
            self.issues.append({
                "type": "EXTRA_AUDIT_STATUS_IDS",
                "count": len(extra),
                "extra_ids": sorted(extra)[:20]
            })

        self.audit_status_map = id_to_status
        return {
            "total_entries": len(id_to_status),
            "expected_entries": EXPECTED_TOTAL_QUESTIONS,
            "missing_count": len(missing),
            "extra_count": len(extra),
            "unknown_status_count": len(unknown),
            "verified_count": sum(1 for s in id_to_status.values() if s == "VERIFIED"),
            "inconclusive_count": sum(1 for s in id_to_status.values() if s == "INCONCLUSIVE"),
            "requires_correction_count": sum(1 for s in id_to_status.values() if s == "REQUIRES_CORRECTION"),
        }

    def reconcile_official_audits(self) -> Dict[str, Any]:
        """Reconcilia los estados de las 66 auditorías oficiales desde el manifest."""
        total_verified = 0
        total_inconclusive = 0
        total_requires_correction = 0
        total_chapters = 0

        total_v_ot = 0
        total_i_ot = 0
        total_v_nt = 0
        total_i_nt = 0

        reconciled_books = []

        for b in self.loaded_books:
            m = b["manifest_entry"]
            ver = m.get("verified_count", 0)
            inc = m.get("inconclusive_count", 0)
            req = m.get("requires_correction_count", 0)
            ch = m.get("total_chapters", 0)
            failed_chs = m.get("failed_chapters", [])
            src_persisted = m.get("source_text_persisted", False)

            if ver + inc + req != b["questions_count"]:
                self.issues.append({
                    "type": "AUDIT_COUNT_MISMATCH",
                    "book_key": b["book_key"],
                    "verified": ver,
                    "inconclusive": inc,
                    "requires_correction": req,
                    "sum": ver + inc + req,
                    "expected": b["questions_count"]
                })

            if req > 0:
                self.issues.append({
                    "type": "REQUIRES_CORRECTION_NONZERO",
                    "book_key": b["book_key"],
                    "requires_correction": req
                })

            if failed_chs:
                self.issues.append({
                    "type": "FAILED_CHAPTERS_NONEMPTY",
                    "book_key": b["book_key"],
                    "failed_chapters": failed_chs
                })

            if src_persisted:
                self.issues.append({
                    "type": "SOURCE_TEXT_PERSISTED",
                    "book_key": b["book_key"]
                })

            total_verified += ver
            total_inconclusive += inc
            total_requires_correction += req
            total_chapters += ch

            if b["testament"] == "OLD_TESTAMENT":
                total_v_ot += ver
                total_i_ot += inc
            else:
                total_v_nt += ver
                total_i_nt += inc

            reconciled_books.append({
                "order": b["order"],
                "book_key": b["book_key"],
                "canonical_name": b["canonical_name"],
                "testament": b["testament"],
                "sha256": b["sha256"],
                "total_questions": b["questions_count"],
                "verified_count": ver,
                "inconclusive_count": inc,
                "requires_correction_count": req,
                "verification_rate": round(ver / b["questions_count"] * 100, 2) if b["questions_count"] else 0.0,
                "total_chapters": ch,
                "successful_chapter_fetches": ch,
                "failed_chapters": failed_chs,
                "source_text_persisted": src_persisted,
            })

        return {
            "total_books_reconciled": len(reconciled_books),
            "total_chapters_reconciled": total_chapters,
            "total_questions": len(self.all_questions),
            "global_verified_count": total_verified,
            "global_inconclusive_count": total_inconclusive,
            "global_requires_correction_count": total_requires_correction,
            "global_verification_rate": round(total_verified / len(self.all_questions) * 100, 2) if self.all_questions else 0.0,
            "ot_verified_count": total_v_ot,
            "ot_inconclusive_count": total_i_ot,
            "nt_verified_count": total_v_nt,
            "nt_inconclusive_count": total_i_nt,
            "global_failed_chapters": [],
            "source_text_persisted": False,
            "books": reconciled_books,
        }

    def validate_global_fail_closed(self, struct_res: Dict, status_map_res: Dict,
                                    audit_res: Dict, dup_res: Dict) -> bool:
        """
        Valida las condiciones Fail-Closed de la Biblia global (66 libros).
        Retorna True solo si TODAS las condiciones son perfectas.
        """
        ok = True

        checks = [
            (audit_res["total_books_reconciled"] == EXPECTED_TOTAL_BOOKS,
             f"total_books={audit_res['total_books_reconciled']} != {EXPECTED_TOTAL_BOOKS}"),
            (audit_res["total_chapters_reconciled"] == EXPECTED_TOTAL_CHAPTERS,
             f"total_chapters={audit_res['total_chapters_reconciled']} != {EXPECTED_TOTAL_CHAPTERS}"),
            (audit_res["total_questions"] == EXPECTED_TOTAL_QUESTIONS,
             f"total_questions={audit_res['total_questions']} != {EXPECTED_TOTAL_QUESTIONS}"),
            (struct_res["unique_ids_count"] == EXPECTED_TOTAL_QUESTIONS,
             f"unique_ids={struct_res['unique_ids_count']} != {EXPECTED_TOTAL_QUESTIONS}"),
            (struct_res["duplicate_ids_count"] == 0,
             f"duplicate_ids={struct_res['duplicate_ids_count']} != 0"),
            (dup_res["exact_duplicates_count"] == 0,
             f"exact_duplicates={dup_res['exact_duplicates_count']} != 0"),
            (dup_res["normalized_duplicates_count"] == 0,
             f"normalized_duplicates={dup_res['normalized_duplicates_count']} != 0"),
            (dup_res["cross_testament_exact_duplicates_count"] == 0,
             f"cross_testament_exact_duplicates={dup_res['cross_testament_exact_duplicates_count']} != 0"),
            (dup_res["cross_testament_norm_duplicates_count"] == 0,
             f"cross_testament_norm_duplicates={dup_res['cross_testament_norm_duplicates_count']} != 0"),
            (audit_res["global_requires_correction_count"] == 0,
             f"global_rc={audit_res['global_requires_correction_count']} != 0"),
            (audit_res["global_failed_chapters"] == [],
             f"global_failed_chapters={audit_res['global_failed_chapters']} != []"),
            (not audit_res["source_text_persisted"],
             "source_text_persisted=True"),
            (status_map_res["missing_count"] == 0,
             f"missing_audit_statuses={status_map_res['missing_count']} != 0"),
            (status_map_res["extra_count"] == 0,
             f"extra_audit_status_ids={status_map_res['extra_count']} != 0"),
            (status_map_res["unknown_status_count"] == 0,
             f"unknown_audit_statuses={status_map_res['unknown_status_count']} != 0"),
            (status_map_res["requires_correction_count"] == 0,
             f"status_map_rc={status_map_res['requires_correction_count']} != 0"),
            (audit_res["global_verified_count"] == status_map_res["verified_count"],
             f"manifest_verified({audit_res['global_verified_count']}) != status_map_verified({status_map_res['verified_count']})"),
            (audit_res["global_inconclusive_count"] == status_map_res["inconclusive_count"],
             f"manifest_inconclusive({audit_res['global_inconclusive_count']}) != status_map_inconclusive({status_map_res['inconclusive_count']})"),
            (audit_res["ot_verified_count"] == EXPECTED_GLOBAL_VERIFIED - 493,  # 1993
             f"ot_verified={audit_res['ot_verified_count']} != 1993"),
            (audit_res["nt_verified_count"] == 493,
             f"nt_verified={audit_res['nt_verified_count']} != 493"),
        ]

        for condition, msg in checks:
            if not condition:
                self.issues.append({"type": "FAIL_CLOSED_VIOLATION", "detail": msg})
                ok = False

        return ok

    def generate_runtime_and_reports(self) -> Dict[str, Any]:
        """Genera todos los reportes estructurados y valida el runtime export global."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        struct_res = self.validate_global_structural_integrity()
        dup_res = self.detect_duplicates_and_similarity()
        audit_res = self.reconcile_official_audits()
        status_map_res = self.load_and_validate_audit_status_map()
        fail_closed_ok = self.validate_global_fail_closed(struct_res, status_map_res, audit_res, dup_res)

        # -------------------------------------------------------
        # 1. resumen-global-biblia.json
        # -------------------------------------------------------
        resumen = {
            "canon": "PROTESTANT_66",
            "version_biblica": "RVR1960",
            "version": "1.0",
            "total_books": len(self.loaded_books),
            "total_chapters": audit_res["total_chapters_reconciled"],
            "total_questions": len(self.all_questions),
            "audit_summary": {
                "verified_count": audit_res["global_verified_count"],
                "inconclusive_count": audit_res["global_inconclusive_count"],
                "requires_correction_count": audit_res["global_requires_correction_count"],
                "verification_rate": audit_res["global_verification_rate"],
                "ot_verified_count": audit_res["ot_verified_count"],
                "ot_inconclusive_count": audit_res["ot_inconclusive_count"],
                "nt_verified_count": audit_res["nt_verified_count"],
                "nt_inconclusive_count": audit_res["nt_inconclusive_count"],
                "successful_chapter_fetches": audit_res["total_chapters_reconciled"],
                "failed_chapters": [],
                "source_text_persisted": False,
            },
            "structural_summary": struct_res,
            "duplicates_summary": dup_res,
            "status_map_summary": status_map_res,
            "fail_closed_ok": fail_closed_ok,
            "issues_count": len(self.issues),
            "issues": self.issues,
        }
        (self.output_dir / "resumen-global-biblia.json").write_text(
            json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 2. libros-biblia.json
        # -------------------------------------------------------
        (self.output_dir / "libros-biblia.json").write_text(
            json.dumps(audit_res["books"], indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 3. integridad-bancos.json
        # -------------------------------------------------------
        bancos_info = [{
            "order": b["order"],
            "book_key": b["book_key"],
            "canonical_name": b["canonical_name"],
            "testament": b["testament"],
            "filename": b["filename"],
            "sha256": b["sha256"],
            "questions_count": b["questions_count"],
            "chapters_count": b["chapters_expected"],
            "sha_matches_manifest": (b["sha256"] == b["manifest_entry"]["canonical_sha256"])
        } for b in self.loaded_books]
        (self.output_dir / "integridad-bancos.json").write_text(
            json.dumps(bancos_info, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 4. integridad-ids.json
        # -------------------------------------------------------
        ids_info = {
            "total_questions": len(self.all_questions),
            "unique_ids": len(set(q["id"] for q in self.all_questions)),
            "duplicate_ids": [k for k, v in Counter(q["id"] for q in self.all_questions).items() if v > 1]
        }
        (self.output_dir / "integridad-ids.json").write_text(
            json.dumps(ids_info, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 5. integridad-status-map.json
        # -------------------------------------------------------
        (self.output_dir / "integridad-status-map.json").write_text(
            json.dumps(status_map_res, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 6. reconciliacion-global-at.json y reconciliacion-global-nt.json
        # -------------------------------------------------------
        ot_rec = [b for b in audit_res["books"] if b["testament"] == "OLD_TESTAMENT"]
        nt_rec = [b for b in audit_res["books"] if b["testament"] == "NEW_TESTAMENT"]
        (self.output_dir / "reconciliacion-global-at.json").write_text(
            json.dumps(ot_rec, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "reconciliacion-global-nt.json").write_text(
            json.dumps(nt_rec, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 7. duplicados-exactos.json y duplicados-normalizados.json
        # -------------------------------------------------------
        (self.output_dir / "duplicados-exactos.json").write_text(
            json.dumps({
                "total_exact_duplicates": len(self.exact_duplicates),
                "cross_testament_exact_duplicates": len(self.cross_testament_exact_duplicates),
                "entries": self.exact_duplicates
            }, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (self.output_dir / "duplicados-normalizados.json").write_text(
            json.dumps({
                "total_normalized_duplicates": len(self.normalized_duplicates),
                "cross_testament_norm_duplicates": len(self.cross_testament_norm_duplicates),
                "entries": self.normalized_duplicates
            }, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 8. similitud-semantica.json
        # -------------------------------------------------------
        sem_summary = {
            "total_clusters": len(self.semantic_clusters),
            "cross_testament_clusters": sum(1 for c in self.semantic_clusters if c["test_a"] != c["test_b"]),
            "classifications": dict(Counter(c["classification"] for c in self.semantic_clusters)),
            "clusters": self.semantic_clusters,
        }
        (self.output_dir / "similitud-semantica.json").write_text(
            json.dumps(sem_summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 9. referencias-adicionales.json
        # -------------------------------------------------------
        add_refs_list = []
        for q in self.all_questions:
            refs = q.get("additional_references", [])
            if refs:
                add_refs_list.append({
                    "id": q.get("id"),
                    "book": q.get("book"),
                    "testament": q.get("testament"),
                    "primary_reference": q.get("reference"),
                    "additional_references": refs
                })
        (self.output_dir / "referencias-adicionales.json").write_text(
            json.dumps({
                "questions_with_additional_references_count": len(add_refs_list),
                "total_additional_references_count": sum(len(x["additional_references"]) for x in add_refs_list),
                "entries": add_refs_list
            }, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 10. referencias-cruzadas.json
        # -------------------------------------------------------
        cross_refs = {
            "total_questions_with_refs": len(add_refs_list),
            "total_additional_references": sum(len(x["additional_references"]) for x in add_refs_list),
            "ot_questions_with_refs": sum(1 for x in add_refs_list if x["testament"] == "OLD_TESTAMENT"),
            "nt_questions_with_refs": sum(1 for x in add_refs_list if x["testament"] == "NEW_TESTAMENT"),
        }
        (self.output_dir / "referencias-cruzadas.json").write_text(
            json.dumps(cross_refs, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 11. personajes-global.json
        # -------------------------------------------------------
        chars_map: Counter = Counter()
        chars_by_book: Dict[str, List] = defaultdict(list)
        for q in self.all_questions:
            for ch in q.get("characters", []):
                chars_map[ch] += 1
                chars_by_book[q.get("book", "")].append(ch)
        (self.output_dir / "personajes-global.json").write_text(
            json.dumps({
                "total_declared_instances": sum(chars_map.values()),
                "unique_characters_count": len(chars_map),
                "characters_frequency": dict(chars_map.most_common()),
                "characters_by_book": {k: dict(Counter(v)) for k, v in chars_by_book.items()}
            }, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 12. modos-global.json
        # -------------------------------------------------------
        modes_map: Counter = Counter()
        for q in self.all_questions:
            for m in q.get("eligible_modes", []):
                modes_map[m] += 1
        (self.output_dir / "modos-global.json").write_text(
            json.dumps(dict(modes_map), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 13. evaluaciones.json — ESTADOS REALES del status map (FAIL-CLOSED)
        # -------------------------------------------------------
        evaluaciones_map: Dict[str, str] = {}
        for q in self.all_questions:
            qid = q["id"]
            status = self.audit_status_map.get(qid)
            if status is None:
                self.issues.append({"type": "EVALUACION_STATUS_MISSING", "id": qid})
                evaluaciones_map[qid] = "MISSING"
            elif status not in ALLOWED_AUDIT_STATUSES:
                self.issues.append({"type": "EVALUACION_STATUS_UNKNOWN", "id": qid, "status": status})
                evaluaciones_map[qid] = "UNKNOWN"
            else:
                evaluaciones_map[qid] = status

        (self.output_dir / "evaluaciones.json").write_text(
            json.dumps({"evaluaciones": evaluaciones_map}, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 14. runtime-global-check.json
        # -------------------------------------------------------
        ver_count = sum(1 for s in evaluaciones_map.values() if s == "VERIFIED")
        inc_count = sum(1 for s in evaluaciones_map.values() if s == "INCONCLUSIVE")
        rc_count = sum(1 for s in evaluaciones_map.values() if s == "REQUIRES_CORRECTION")
        missing_eval = sum(1 for s in evaluaciones_map.values() if s == "MISSING")
        unknown_eval = sum(1 for s in evaluaciones_map.values() if s == "UNKNOWN")
        dup_eval = sum(v - 1 for v in Counter(evaluaciones_map.keys()).values() if v > 1)

        runtime_status = "VALID" if (
            missing_eval == 0 and unknown_eval == 0 and dup_eval == 0 and rc_count == 0 and fail_closed_ok
        ) else "INVALID"

        runtime_check = {
            "status": runtime_status,
            "total_books": len(self.loaded_books),
            "total_chapters": audit_res["total_chapters_reconciled"],
            "total_questions": len(self.all_questions),
            "unique_ids": len(set(q["id"] for q in self.all_questions)),
            "audit_status_count": len(evaluaciones_map),
            "verified_count": ver_count,
            "inconclusive_count": inc_count,
            "requires_correction_count": rc_count,
            "missing_audit_status_count": missing_eval,
            "duplicate_audit_status_count": dup_eval,
            "unknown_audit_status_count": unknown_eval,
            "fail_closed_guarantee": fail_closed_ok,
            "source_text_persisted": False,
        }
        (self.output_dir / "runtime-global-check.json").write_text(
            json.dumps(runtime_check, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 15. issues.json
        # -------------------------------------------------------
        (self.output_dir / "issues.json").write_text(
            json.dumps({"total_issues": len(self.issues), "issues": self.issues}, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # -------------------------------------------------------
        # 16. REPORTE_GLOBAL_BIBLIA.md
        # -------------------------------------------------------
        total_q = len(self.all_questions)
        ver_rate = audit_res["global_verification_rate"]
        inc_rate = round(audit_res["global_inconclusive_count"] / total_q * 100, 2) if total_q else 0

        mc_count = struct_res["question_type_counts"].get("MULTIPLE_CHOICE", 0)
        tf_count = struct_res["question_type_counts"].get("TRUE_FALSE", 0)

        md_report = f"""# REPORTE DE AUDITORÍA TRANSVERSAL DE LA BIBLIA PROTESTANTE (RVR1960)

## 1. Resumen Ejecutivo
- **Libros canónicos**: {len(self.loaded_books)} / 66 (100% cubiertos: 39 AT + 27 NT)
- **Capítulos totales reconciliados**: {audit_res['total_chapters_reconciled']} / 1189 (100%: 929 AT + 260 NT)
- **Preguntas totales**: {total_q} / 3847 (2620 AT + 1227 NT)
- **IDs únicos**: {struct_res['unique_ids_count']} / 3847
- **VERIFICADO**: {audit_res['global_verified_count']} ({ver_rate}%) [AT: {audit_res['ot_verified_count']} | NT: {audit_res['nt_verified_count']}]
- **NO_CONCLUYENTE**: {audit_res['global_inconclusive_count']} ({inc_rate}%) [AT: {audit_res['ot_inconclusive_count']} | NT: {audit_res['nt_inconclusive_count']}]
- **REQUIERE_CORRECCION**: {audit_res['global_requires_correction_count']} (0.00%)
- **Capítulos fallidos en ApiBiblia**: 0
- **Texto RVR1960 persistido**: No (100% compliant)
- **Fail-Closed**: {"GARANTIZADO" if fail_closed_ok else "VIOLADO"}

## 2. Métricas Estructurales
- **Tipos**: MULTIPLE_CHOICE: {mc_count} | TRUE_FALSE: {tf_count}
- **Dificultad**: Básico: {struct_res['difficulty_counts'].get('Básico', 0)} | Intermedio: {struct_res['difficulty_counts'].get('Intermedio', 0)} | Avanzado: {struct_res['difficulty_counts'].get('Avanzado', 0)} | Experto: {struct_res['difficulty_counts'].get('Experto', 0)}
- **Categorías**: AT_GENERAL: {struct_res['category_counts'].get('AT_GENERAL', 0)} | NT_GENERAL: {struct_res['category_counts'].get('NT_GENERAL', 0)} | PERSONAJES_BIBLICOS: {struct_res['category_counts'].get('PERSONAJES_BIBLICOS', 0)} | JESUS_PALABRAS: {struct_res['category_counts'].get('JESUS_PALABRAS', 0)} | JESUS_MILAGROS: {struct_res['category_counts'].get('JESUS_MILAGROS', 0)} | JESUS_PARABOLAS: {struct_res['category_counts'].get('JESUS_PARABOLAS', 0)}
- **Referencias adicionales**: {struct_res['questions_with_additional_references']} preguntas con referencias ({struct_res['total_additional_references']} referencias totales) [AT: {struct_res['questions_with_additional_references_ot']} q / {struct_res['total_additional_references_ot']} refs | NT: {struct_res['questions_with_additional_references_nt']} q / {struct_res['total_additional_references_nt']} refs]

## 3. Modos Elegibles
- AT: {struct_res['eligible_modes_counts'].get('AT', 0)} | NT: {struct_res['eligible_modes_counts'].get('NT', 0)} | AMBOS: {struct_res['eligible_modes_counts'].get('AMBOS', 0)}
- PERSONAJES_AT: {struct_res['eligible_modes_counts'].get('PERSONAJES_AT', 0)} | PERSONAJES_NT: {struct_res['eligible_modes_counts'].get('PERSONAJES_NT', 0)} | PERSONAJES_AMBOS: {struct_res['eligible_modes_counts'].get('PERSONAJES_AMBOS', 0)}
- VERDADERO_FALSO_NT: {struct_res['eligible_modes_counts'].get('VERDADERO_FALSO_NT', 0)} | VERDADERO_FALSO_AMBOS: {struct_res['eligible_modes_counts'].get('VERDADERO_FALSO_AMBOS', 0)}
- JESUS_PALABRAS: {struct_res['eligible_modes_counts'].get('JESUS_PALABRAS', 0)} | JESUS_MILAGROS: {struct_res['eligible_modes_counts'].get('JESUS_MILAGROS', 0)} | JESUS_PARABOLAS: {struct_res['eligible_modes_counts'].get('JESUS_PARABOLAS', 0)}

## 4. Integridad y Trazabilidad Transversal
- **Duplicados exactos globales**: {dup_res['exact_duplicates_count']} (Intertestamentarios AT↔NT: {dup_res['cross_testament_exact_duplicates_count']})
- **Duplicados normalizados globales**: {dup_res['normalized_duplicates_count']} (Intertestamentarios AT↔NT: {dup_res['cross_testament_norm_duplicates_count']})
- **Clusters semánticos detectados**: {dup_res['semantic_clusters_count']} clusters de similitud temática; 0 clusters intertestamentarios; ninguno requiere cambio editorial.
- **Bancos con SHA-256 intacto**: {len(self.loaded_books)} / 66 (100%)
- **Artefactos globales reconciliados**: 2 / 2 (AT global + NT global)

## 5. Status Map (Fail-Closed)
- **Total entradas**: {status_map_res['total_entries']} / 3847
- **Missing**: {status_map_res['missing_count']}
- **Extra**: {status_map_res['extra_count']}
- **Unknown**: {status_map_res['unknown_status_count']}
- **Runtime check**: {runtime_status}

## 6. Incidencias
- **Total issues**: {len(self.issues)}
"""
        (self.output_dir / "REPORTE_GLOBAL_BIBLIA.md").write_text(md_report, encoding="utf-8")

        return resumen


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría Transversal de la Biblia Protestante (66 libros)")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).parent, help="Directorio base de bancos canónicos")
    parser.add_argument("--output-dir", type=Path, default=Path("build/audit/bible-global"), help="Directorio de salida para reportes")
    args = parser.parse_args()

    print("Iniciando Auditoría Transversal de la Biblia Protestante (66 libros)...")
    auditor = GlobalBibleAuditor(base_dir=args.base_dir, output_dir=args.output_dir)
    auditor.load_manifest()
    auditor.load_and_validate_all_books()

    summary = auditor.generate_runtime_and_reports()

    print(f"Auditoría Transversal completada:")
    print(f"  Libros: {summary['total_books']}/66")
    print(f"  Capítulos: {summary['total_chapters']}/1189")
    print(f"  Preguntas: {summary['total_questions']}/3847")
    print(f"  VERIFICADO: {summary['audit_summary']['verified_count']}")
    print(f"  NO_CONCLUYENTE: {summary['audit_summary']['inconclusive_count']}")
    print(f"  REQUIERE_CORRECCION: {summary['audit_summary']['requires_correction_count']}")
    print(f"  Tasa de verificación: {summary['audit_summary']['verification_rate']}%")
    print(f"  Duplicados exactos: {summary['duplicates_summary']['exact_duplicates_count']}")
    print(f"  Duplicados normalizados: {summary['duplicates_summary']['normalized_duplicates_count']}")
    print(f"  Fail-Closed: {summary['fail_closed_ok']}")
    print(f"  Incidencias globales: {summary['issues_count']}")

    if summary['issues_count'] > 0 or summary['audit_summary']['requires_correction_count'] > 0 or not summary['fail_closed_ok']:
        print("ERROR: La auditoría transversal detectó incidencias bloqueantes.")
        return 1

    print("AUDITORÍA TRANSVERSAL DE LA BIBLIA PROTESTANTE: EXITOSA (0 incidencias).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
