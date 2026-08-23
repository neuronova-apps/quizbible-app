#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/runtime_export/test_export_runtime.py

Suite integral de pruebas unitarias para el exportador de Runtime JSON v1 y
la validación del contrato arquitectónico con Android Quiz Bible.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.runtime_export.export_runtime import (
    DEFAULT_SCHEMA_PATH,
    assert_no_forbidden_keys,
    build_runtime_collection,
    determine_testament,
    export_canonical_data,
    export_files_to_runtime,
    export_question_to_runtime,
    normalize_difficulty,
    normalize_question_type,
    validate_runtime_collection,
)

SAMPLE_FIXTURE_IDS = [
    "NQB-AT-GEN-0001",
    "NQB-AT-GEN-0036",
    "NQB-AT-EXO-0002",
    "NQB-AT-EXO-0021",
    "NQB-AT-LEV-0017",
    "NQB-AT-LEV-0045",
    "NQB-AT-NUM-0001",
    "NQB-AT-NUM-0062",
    "NQB-AT-DEU-0013",
    "NQB-AT-DEU-0078",
    "NQB-AT-JOS-0001",
    "NQB-AT-JOS-0005",
    "NQB-AT-JUE-0048",
    "NQB-AT-RUT-0004",
    "NQB-AT-1SA-0043",
    "NQB-AT-2SA-0028",
    "NQB-AT-1RE-0011",
    "NQB-AT-2RE-0006",
    "NQB-AT-1CR-0066",
    "NQB-AT-2CR-0102",
]


class TestRuntimeExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parent.parent.parent
        cls.extractor_dir = cls.repo_root / "tools" / "bible_extractor"
        cls.canonical_files = sorted(list(cls.extractor_dir.glob("*-master-input.json")))

        cls.all_canonical_questions: dict[str, dict[str, Any]] = {}
        for p in cls.canonical_files:
            raw = json.loads(p.read_text(encoding="utf-8"))
            qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
            for q in qs:
                cls.all_canonical_questions[q["id"]] = q

        cls.sample_canonical = [
            cls.all_canonical_questions[qid] for qid in SAMPLE_FIXTURE_IDS if qid in cls.all_canonical_questions
        ]
        # Mapa de estado oficial para las 20 preguntas de la muestra
        cls.sample_audit_status_map = {qid: "VERIFIED" for qid in SAMPLE_FIXTURE_IDS}

    def test_fixture_ids_all_exist_in_canonical_banks(self) -> None:
        """Verifica que los 20 IDs de la muestra existan en los bancos canónicos."""
        self.assertEqual(
            len(self.sample_canonical),
            20,
            f"Se esperaban 20 preguntas en la muestra, se encontraron {len(self.sample_canonical)}"
        )

    def test_difficulty_normalization(self) -> None:
        """Verifica la correcta normalización de dificultades."""
        self.assertEqual(normalize_difficulty("Básico"), "BASIC")
        self.assertEqual(normalize_difficulty("Basico"), "BASIC")
        self.assertEqual(normalize_difficulty("beginner"), "BASIC")
        self.assertEqual(normalize_difficulty("Intermedio"), "INTERMEDIATE")
        self.assertEqual(normalize_difficulty("intermediate"), "INTERMEDIATE")
        self.assertEqual(normalize_difficulty("Avanzado"), "ADVANCED")
        self.assertEqual(normalize_difficulty("advanced"), "ADVANCED")
        self.assertEqual(normalize_difficulty("Experto"), "EXPERT")
        self.assertEqual(normalize_difficulty("expert"), "EXPERT")

        with self.assertRaises(ValueError):
            normalize_difficulty("NivelInvalido")

    def test_question_type_fail_closed(self) -> None:
        """Verifica que tipos desconocidos produzcan error y no se conviertan silenciosamente."""
        self.assertEqual(normalize_question_type("Selección múltiple"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("multiple_choice"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("MC"), "MULTIPLE_CHOICE")

        with self.assertRaises(ValueError):
            normalize_question_type("TIPO_DESCONOCIDO_FUTURO")
        with self.assertRaises(ValueError):
            normalize_question_type("")

    def test_testament_fail_closed(self) -> None:
        """Verifica la asignación de testamento (OT/NT) y error en casos desconocidos."""
        q_ot = {"id": "NQB-AT-GEN-0001", "book": "Génesis"}
        self.assertEqual(determine_testament(q_ot), "OT")
        q_nt = {"id": "NQB-NT-MAT-0001", "book": "Mateo"}
        self.assertEqual(determine_testament(q_nt), "NT")

        # Caso desconocido: libro apócrifo o no bíblico sin prefijo canónico
        q_unknown = {"id": "NQB-XX-EVANGELIO_TOMAS-0001", "book": "Evangelio de Tomas"}
        with self.assertRaises(ValueError):
            determine_testament(q_unknown)

    def test_audit_status_is_not_defaulted_to_verified(self) -> None:
        """Verifica que una pregunta sin estado de auditoría oficial no se convierta por defecto en VERIFIED."""
        # Sin mapa ni fuente de auditoría debe fallar (Fail-Closed)
        with self.assertRaises(ValueError):
            export_canonical_data(self.sample_canonical, audit_status_map=None, audit_sources=None)

        # Con mapa incompleto (falta un ID) debe fallar (Fail-Closed)
        incomplete_map = {qid: "VERIFIED" for qid in SAMPLE_FIXTURE_IDS[1:]}  # falta NQB-AT-GEN-0001
        with self.assertRaises(ValueError):
            export_canonical_data(self.sample_canonical, audit_status_map=incomplete_map)

    def test_2chronicles_runtime_preserves_official_audit_distribution(self) -> None:
        """Verifica que 2 Crónicas en runtime preserve exactamente 76 VERIFIED y 26 INCONCLUSIVE."""
        c2_path = self.extractor_dir / "2chronicles-master-input.json"
        audit_dir = self.repo_root / "build" / "audit" / "2chronicles"
        if not c2_path.exists() or not audit_dir.exists():
            self.skipTest("Artefactos de 2 Crónicas no disponibles localmente")

        raw_c2 = json.loads(c2_path.read_text(encoding="utf-8"))
        questions_c2 = raw_c2.get("questions", raw_c2)

        collection = export_canonical_data(questions_c2, audit_sources=audit_dir)
        self.assertEqual(collection["totalQuestions"], 102)

        from collections import Counter
        counts = Counter(q["auditStatus"] for q in collection["questions"])
        self.assertEqual(counts["VERIFIED"], 76, f"Se esperaban 76 VERIFIED, obtenidos: {counts.get('VERIFIED')}")
        self.assertEqual(counts["INCONCLUSIVE"], 26, f"Se esperaban 26 INCONCLUSIVE, obtenidos: {counts.get('INCONCLUSIVE')}")
        self.assertEqual(counts.get("REQUIRES_CORRECTION", 0), 0)

    def test_export_preserves_all_structural_fields(self) -> None:
        """Verifica que la transformación canónica a runtime conserve todos los campos."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        self.assertEqual(collection["schemaVersion"], "quizbible-runtime-v1")
        self.assertEqual(collection["totalQuestions"], 20)
        self.assertEqual(len(collection["questions"]), 20)

        for idx, (can_q, rt_q) in enumerate(zip(self.sample_canonical, collection["questions"])):
            self.assertEqual(rt_q["id"], can_q["id"])
            self.assertEqual(rt_q["book"], can_q["book"])
            self.assertEqual(rt_q["chapter"], can_q["chapter"])
            self.assertEqual(rt_q["verseStart"], can_q["verse_start"])
            self.assertEqual(rt_q["verseEnd"], can_q.get("verse_end"))
            self.assertEqual(rt_q["referenceDisplay"], can_q["reference"])
            self.assertEqual(rt_q["category"], can_q["category"])
            self.assertEqual(rt_q["subcategory"], can_q.get("subcategory"))
            self.assertEqual(rt_q["characters"], can_q.get("characters", []))
            self.assertEqual(rt_q["prompt"], can_q["question"])
            self.assertEqual(rt_q["explanation"], can_q["explanation"])
            self.assertEqual(rt_q["eligibleModes"], can_q["eligible_modes"])
            self.assertEqual(rt_q["verificationTranslation"], "RVR1960")
            self.assertEqual(rt_q["correctOptionId"], "A")

            # Opciones
            self.assertEqual(len(rt_q["options"]), 4)
            self.assertEqual(rt_q["options"][0], {"id": "A", "text": can_q["opcion_a"]})
            self.assertEqual(rt_q["options"][1], {"id": "B", "text": can_q["opcion_b"]})
            self.assertEqual(rt_q["options"][2], {"id": "C", "text": can_q["opcion_c"]})
            self.assertEqual(rt_q["options"][3], {"id": "D", "text": can_q["opcion_d"]})

    def test_no_scripture_text_persisted_recursive(self) -> None:
        """Verifica recursivamente que ninguna clave de texto bíblico se persista."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        assert_no_forbidden_keys(collection)

        # Si se inyecta una clave prohibida, debe fallar de inmediato
        bad_collection = copy.deepcopy(collection)
        bad_collection["questions"][0]["verse_text"] = "En el principio creó Dios los cielos y la tierra."
        with self.assertRaises(ValueError):
            assert_no_forbidden_keys(bad_collection)

    def test_deterministic_export_sha256(self) -> None:
        """Verifica que dos exportaciones sucesivas produzcan idéntico SHA-256."""
        temp_out1 = self.repo_root / "build" / "runtime" / "_test_temp1.json"
        temp_out2 = self.repo_root / "build" / "runtime" / "_test_temp2.json"

        try:
            _, sha1 = export_files_to_runtime(
                self.canonical_files,
                temp_out1,
                filter_ids=SAMPLE_FIXTURE_IDS,
                audit_status_map=self.sample_audit_status_map,
                generated_at="2026-08-21T00:00:00Z"
            )
            _, sha2 = export_files_to_runtime(
                self.canonical_files,
                temp_out2,
                filter_ids=SAMPLE_FIXTURE_IDS,
                audit_status_map=self.sample_audit_status_map,
                generated_at="2026-08-21T00:00:00Z"
            )
            self.assertEqual(sha1, sha2)
            self.assertEqual(temp_out1.read_bytes(), temp_out2.read_bytes())
        finally:
            temp_out1.unlink(missing_ok=True)
            temp_out2.unlink(missing_ok=True)

    def test_schema_validation_passes(self) -> None:
        """Valida que la colección de 20 preguntas cumpla el schema JSON oficial."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        is_valid = validate_runtime_collection(collection, schema_path=DEFAULT_SCHEMA_PATH)
        self.assertTrue(is_valid)

    def test_android_shuffle_simulation_preserves_correct_answer(self) -> None:
        """
        Simula el comportamiento del motor de juego Android:
        Baraja las opciones de una pregunta con diversas semillas aleatorias
        y confirma que el id 'A' identifica consistentemente la respuesta correcta
        incluso cuando cambia su posición visual en pantalla (0, 1, 2, 3).
        """
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        q = collection["questions"][0]  # Génesis 1:1
        original_correct_text = q["options"][0]["text"]
        original_correct_id = q["correctOptionId"]

        positions_seen: set[int] = set()

        for seed in range(50):
            rng = random.Random(seed)
            shuffled_options = copy.deepcopy(q["options"])
            rng.shuffle(shuffled_options)

            # Buscar la opción correcta tras el shuffle
            correct_option_post_shuffle = next(opt for opt in shuffled_options if opt["id"] == original_correct_id)
            correct_visual_index = shuffled_options.index(correct_option_post_shuffle)
            positions_seen.add(correct_visual_index)

            # Validar que el texto y el ID permanecen vinculados
            self.assertEqual(correct_option_post_shuffle["text"], original_correct_text)
            self.assertEqual(correct_option_post_shuffle["id"], "A")

        # Confirmar que 'A' ocupó las 4 posiciones posibles (0, 1, 2, 3) a lo largo de las tiradas
        self.assertEqual(positions_seen, {0, 1, 2, 3})

    def test_game_mode_filtering(self) -> None:
        """Verifica la capacidad de filtrado por modos de juego (AT, PERSONAJES_AT, AMBOS)."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        questions = collection["questions"]

        # Filtro AT
        at_questions = [q for q in questions if "AT" in q["eligibleModes"]]
        self.assertEqual(len(at_questions), 20)

        # Filtro PERSONAJES_AT
        personajes_at_questions = [q for q in questions if "PERSONAJES_AT" in q["eligibleModes"]]
        self.assertEqual(len(personajes_at_questions), 10)
        for q in personajes_at_questions:
            self.assertEqual(q["category"], "PERSONAJES_BIBLICOS")

        # Filtro AMBOS
        ambos_questions = [q for q in questions if "AMBOS" in q["eligibleModes"]]
        self.assertEqual(len(ambos_questions), 20)

    def test_difficulty_filtering(self) -> None:
        """Verifica la capacidad de filtrado por dificultad."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        questions = collection["questions"]

        basics = [q for q in questions if q["difficulty"] == "BASIC"]
        intermediates = [q for q in questions if q["difficulty"] == "INTERMEDIATE"]
        advanceds = [q for q in questions if q["difficulty"] == "ADVANCED"]
        experts = [q for q in questions if q["difficulty"] == "EXPERT"]

        self.assertEqual(len(basics) + len(intermediates) + len(advanceds) + len(experts), 20)
        self.assertEqual(len(basics), 6)
        self.assertEqual(len(intermediates), 6)
        self.assertEqual(len(advanceds), 5)
        self.assertEqual(len(experts), 3)

    def test_audit_and_human_review_status_coexistence(self) -> None:
        """Demuestra que auditStatus y humanReviewStatus coexisten y modelan el ciclo productivo."""
        collection = export_canonical_data(self.sample_canonical, audit_status_map=self.sample_audit_status_map)
        for q in collection["questions"]:
            self.assertIn(q["auditStatus"], {"VERIFIED", "INCONCLUSIVE"})
            self.assertEqual(q["humanReviewStatus"], "PENDING")

        # Simular aprobación humana de una pregunta
        q0 = copy.deepcopy(collection["questions"][0])
        q0["humanReviewStatus"] = "APPROVED"

        is_production_ready = (q0["auditStatus"] != "REQUIRES_CORRECTION") and (q0["humanReviewStatus"] == "APPROVED")
        self.assertTrue(is_production_ready)

        # Pregunta rechazada por revisión humana
        q0["humanReviewStatus"] = "REJECTED"
        is_production_ready_rejected = (q0["auditStatus"] != "REQUIRES_CORRECTION") and (q0["humanReviewStatus"] == "APPROVED")
        self.assertFalse(is_production_ready_rejected)

    def test_question_type_normalization_opcion_multiple(self) -> None:
        """Verifica que normalize_question_type soporte genéricamente variantes de OPCION_MULTIPLE y TRUE_FALSE y rechace tipos desconocidos (Fail-Closed)."""
        self.assertEqual(normalize_question_type("OPCION_MULTIPLE"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("opcion_multiple"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("opción múltiple"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("opcion multiple"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("MULTIPLE_CHOICE"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("seleccion multiple"), "MULTIPLE_CHOICE")
        self.assertEqual(normalize_question_type("mc"), "MULTIPLE_CHOICE")

        # TRUE_FALSE
        self.assertEqual(normalize_question_type("TRUE_FALSE"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("true_false"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("true false"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("verdadero_falso"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("verdadero falso"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("tf"), "TRUE_FALSE")
        self.assertEqual(normalize_question_type("vf"), "TRUE_FALSE")

        with self.assertRaises(ValueError):
            normalize_question_type("tipo_desconocido_invalido")

    def test_true_false_export_contract(self) -> None:
        """Verifica el contrato de exportación de TRUE_FALSE (exactamente 2 opciones A/B, sin C/D) y Fail-Closed."""
        q_tf = {
            "id": "NQB-NT-MAT-0004",
            "book": "Mateo",
            "chapter": 1,
            "verse_start": 22,
            "verse_end": 23,
            "reference": "Mateo 1:22-23",
            "category": "NT_GENERAL",
            "difficulty": "Básico",
            "question_type": "TRUE_FALSE",
            "question": "¿El nacimiento virginal cumplió la profecía de Emanuel?",
            "opcion_a": "Verdadero",
            "opcion_b": "Falso",
            "opcion_c": "",
            "opcion_d": "",
            "correct_option": "A",
            "correct_answer": "Verdadero",
            "explanation": "Mateo 1:22-23 declara el cumplimiento de la profecía de Emanuel.",
            "eligible_modes": ["NT", "AMBOS", "VERDADERO_FALSO_NT", "VERDADERO_FALSO_AMBOS"],
        }
        res = export_question_to_runtime(q_tf, audit_status="VERIFIED")
        self.assertEqual(res["questionType"], "TRUE_FALSE")
        self.assertEqual(len(res["options"]), 2)
        self.assertEqual([o["id"] for o in res["options"]], ["A", "B"])
        self.assertEqual(res["correctOptionId"], "A")
        self.assertEqual(res["testament"], "NT")

        # Fallo si falta opción B
        q_tf_bad = copy.deepcopy(q_tf)
        q_tf_bad["opcion_b"] = ""
        with self.assertRaises(ValueError):
            export_question_to_runtime(q_tf_bad, audit_status="VERIFIED")

        # Fallo si TRUE_FALSE tiene contenido en opción C
        q_tf_bad_c = copy.deepcopy(q_tf)
        q_tf_bad_c["opcion_c"] = "Distractor no permitido"
        with self.assertRaises(ValueError):
            export_question_to_runtime(q_tf_bad_c, audit_status="VERIFIED")

        # Fallo si MULTIPLE_CHOICE carece de opción C o D
        q_mc_bad = copy.deepcopy(q_tf)
        q_mc_bad["question_type"] = "MULTIPLE_CHOICE"
        with self.assertRaises(ValueError):
            export_question_to_runtime(q_mc_bad, audit_status="VERIFIED")

    def test_matthew_testament_nt_and_runtime_export(self) -> None:
        """Verifica que las preguntas de Mateo produzcan testament=NT y validen contra el schema."""
        mat_path = self.extractor_dir / "matthew-master-input.json"
        if not mat_path.exists():
            self.skipTest("matthew-master-input.json no disponible")
        raw = json.loads(mat_path.read_text(encoding="utf-8"))
        mat_qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        status_map = {q["id"]: "VERIFIED" for q in mat_qs}

        collection = export_canonical_data(mat_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 92)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Mateo")
        self.assertTrue(validate_runtime_collection(collection))

    def test_mark_testament_nt_and_runtime_export(self) -> None:
        """Verifica que las preguntas de Marcos produzcan testament=NT y validen contra el schema."""
        mar_path = self.extractor_dir / "mark-master-input.json"
        if not mar_path.exists():
            self.skipTest("mark-master-input.json no disponible")
        raw = json.loads(mar_path.read_text(encoding="utf-8"))
        mar_qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        status_map = {q["id"]: "VERIFIED" for q in mar_qs}

        collection = export_canonical_data(mar_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 74)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Marcos")
        self.assertTrue(validate_runtime_collection(collection))

    def test_luke_testament_nt_and_runtime_export(self) -> None:
        """Verifica que las preguntas de Lucas produzcan testament=NT y validen contra el schema."""
        luk_path = self.extractor_dir / "luke-master-input.json"
        if not luk_path.exists():
            self.skipTest("luke-master-input.json no disponible")
        raw = json.loads(luk_path.read_text(encoding="utf-8"))
        luk_qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        status_map = {q["id"]: "VERIFIED" for q in luk_qs}

        collection = export_canonical_data(luk_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 96)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Lucas")
        self.assertTrue(validate_runtime_collection(collection))

    def test_john_testament_nt_and_runtime_export(self) -> None:
        """Verifica que las preguntas de Juan produzcan testament=NT y validen contra el schema."""
        joh_path = self.extractor_dir / "john-master-input.json"
        if not joh_path.exists():
            self.skipTest("john-master-input.json no disponible")
        raw = json.loads(joh_path.read_text(encoding="utf-8"))
        joh_qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        status_map = {q["id"]: "VERIFIED" for q in joh_qs}

        collection = export_canonical_data(joh_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 100)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Juan")
        self.assertTrue(validate_runtime_collection(collection))

    def test_true_false_inverted_options_runtime_export(self) -> None:
        """Verifica que TRUE_FALSE con opcion_a='Falso' y opcion_b='Verdadero' se exporte preservando el texto de A y B."""
        q_tf = {
            "id": "NQB-NT-JUA-0009",
            "book": "Juan",
            "chapter": 2,
            "verse_start": 1,
            "verse_end": 12,
            "reference": "Juan 2:1-12",
            "category": "JESUS_MILAGROS",
            "difficulty": "Básico",
            "question_type": "TRUE_FALSE",
            "question": "¿El primer milagro de Jesús fue la multiplicación de los panes?",
            "opcion_a": "Falso",
            "opcion_b": "Verdadero",
            "opcion_c": "",
            "opcion_d": "",
            "correct_option": "A",
            "correct_answer": "Falso",
            "explanation": "El primer milagro fue convertir agua en vino en Caná."
        }
        res = export_question_to_runtime(q_tf, audit_status="VERIFIED")
        self.assertEqual(res["questionType"], "TRUE_FALSE")
        self.assertEqual(len(res["options"]), 2)
        self.assertEqual(res["options"][0], {"id": "A", "text": "Falso"})
        self.assertEqual(res["options"][1], {"id": "B", "text": "Verdadero"})
        self.assertEqual(res["correctOptionId"], "A")
        # Verificar que la opción A contiene el texto esperado "Falso"
        correct_text = next(opt["text"] for opt in res["options"] if opt["id"] == res["correctOptionId"])
        self.assertEqual(correct_text, "Falso")

    def test_export_acts_canonical_to_runtime(self) -> None:
        """Verifica la exportación del banco de Hechos al formato runtime."""
        act_path = REPO_ROOT / "tools" / "bible_extractor" / "acts-master-input.json"
        if not act_path.exists():
            self.skipTest("acts-master-input.json no encontrado")
        raw_act = json.loads(act_path.read_text(encoding="utf-8"))
        act_qs = raw_act.get("questions", raw_act)
        status_map = {q["id"]: "VERIFIED" for q in act_qs}

        collection = export_canonical_data(act_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 112)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Hechos")
        self.assertTrue(validate_runtime_collection(collection))

    def test_export_romans_canonical_to_runtime(self) -> None:
        """Verifica la exportación del banco de Romanos al formato runtime."""
        rom_path = REPO_ROOT / "tools" / "bible_extractor" / "romans-master-input.json"
        if not rom_path.exists():
            self.skipTest("romans-master-input.json no encontrado")
        raw_rom = json.loads(rom_path.read_text(encoding="utf-8"))
        rom_qs = raw_rom.get("questions", raw_rom)
        status_map = {q["id"]: "VERIFIED" for q in rom_qs}

        collection = export_canonical_data(rom_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 80)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Romanos")
        self.assertTrue(validate_runtime_collection(collection))

    def test_export_1corinthians_canonical_to_runtime(self) -> None:
        """Verifica la exportación del banco de 1 Corintios al formato runtime."""
        co1_path = REPO_ROOT / "tools" / "bible_extractor" / "1corinthians-master-input.json"
        if not co1_path.exists():
            self.skipTest("1corinthians-master-input.json no encontrado")
        raw_co1 = json.loads(co1_path.read_text(encoding="utf-8"))
        co1_qs = raw_co1.get("questions", raw_co1)
        status_map = {q["id"]: "VERIFIED" for q in co1_qs}

        collection = export_canonical_data(co1_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 80)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "1 Corintios")
        self.assertTrue(validate_runtime_collection(collection))

    def test_export_2corinthians_canonical_to_runtime(self) -> None:
        """Verifica la exportación del banco de 2 Corintios al formato runtime."""
        co2_path = REPO_ROOT / "tools" / "bible_extractor" / "2corinthians-master-input.json"
        if not co2_path.exists():
            self.skipTest("2corinthians-master-input.json no encontrado")
        raw_co2 = json.loads(co2_path.read_text(encoding="utf-8"))
        co2_qs = raw_co2.get("questions", raw_co2)
        status_map = {q["id"]: "VERIFIED" for q in co2_qs}

        collection = export_canonical_data(co2_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 65)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "2 Corintios")
        self.assertTrue(validate_runtime_collection(collection))

    def test_export_galatians_canonical_to_runtime(self) -> None:
        """Verifica la exportación del banco de Gálatas al formato runtime."""
        gal_path = REPO_ROOT / "tools" / "bible_extractor" / "galatians-master-input.json"
        if not gal_path.exists():
            self.skipTest("galatians-master-input.json no encontrado")
        raw_gal = json.loads(gal_path.read_text(encoding="utf-8"))
        gal_qs = raw_gal.get("questions", raw_gal)
        status_map = {q["id"]: "VERIFIED" for q in gal_qs}

        collection = export_canonical_data(gal_qs, audit_status_map=status_map)
        self.assertEqual(collection["totalQuestions"], 36)
        for q in collection["questions"]:
            self.assertEqual(q["testament"], "NT")
            self.assertEqual(q["book"], "Gálatas")
        self.assertTrue(validate_runtime_collection(collection))


if __name__ == "__main__":
    unittest.main()

