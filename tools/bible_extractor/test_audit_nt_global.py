#!/usr/bin/env python3
"""
Pruebas unitarias y de integración para la Auditoría Global del Nuevo Testamento.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.bible_extractor.audit_nt_global import (
    CANONICAL_BOOK_ORDER,
    EXPECTED_CATEGORIES,
    EXPECTED_DIFFICULTIES,
    EXPECTED_MODES,
    EXPECTED_QUESTION_TYPES,
    EXPECTED_TOTAL_ADDITIONAL_REFS,
    EXPECTED_TOTAL_BOOKS,
    EXPECTED_TOTAL_CHAPTERS,
    EXPECTED_TOTAL_QUESTIONS,
    EXPECTED_WITH_ADDITIONAL_REFS,
    GlobalNewTestamentAuditor,
    normalize_text_for_dup_check,
    tokenize_for_similarity,
)


class TestAuditNTGlobal(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_dir = Path(__file__).parent
        cls.manifest_path = cls.base_dir / "nt-global-manifest-v1.json"
        cls.status_map_path = cls.base_dir / "nt-global-audit-status-map-v1.json"
        cls.auditor = GlobalNewTestamentAuditor(base_dir=cls.base_dir)
        cls.auditor.load_manifest()
        cls.auditor.load_and_validate_all_books()
        cls.struct_summary = cls.auditor.validate_global_structural_integrity()
        cls.dup_summary = cls.auditor.detect_duplicates_and_similarity()
        cls.audit_summary = cls.auditor.reconcile_official_audits()
        cls.status_map_summary = cls.auditor.load_and_validate_audit_status_map()

    def test_total_books_and_canonical_order(self) -> None:
        """Verifica que el universo contenga exactamente los 27 libros en orden canónico."""
        self.assertEqual(len(self.auditor.loaded_books), EXPECTED_TOTAL_BOOKS)
        self.assertEqual(len(CANONICAL_BOOK_ORDER), EXPECTED_TOTAL_BOOKS)
        for idx, book in enumerate(self.auditor.loaded_books):
            expected_order, expected_key, expected_name, _, _, _ = CANONICAL_BOOK_ORDER[idx]
            self.assertEqual(book["order"], expected_order)
            self.assertEqual(book["book_key"], expected_key)
            self.assertEqual(book["canonical_name"], expected_name)

    def test_total_questions_and_unique_ids(self) -> None:
        """Verifica que existan exactamente 1227 preguntas y 1227 IDs únicos."""
        self.assertEqual(len(self.auditor.all_questions), EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["unique_ids_count"], EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["duplicate_ids_count"], 0)

    def test_difficulty_distribution(self) -> None:
        """Verifica la distribución global de dificultad (300/438/375/114)."""
        self.assertEqual(self.struct_summary["difficulty_counts"], EXPECTED_DIFFICULTIES)

    def test_category_distribution(self) -> None:
        """Verifica la distribución global de las 5 categorías NT (656/343/144/47/37)."""
        self.assertEqual(self.struct_summary["category_counts"], EXPECTED_CATEGORIES)

    def test_question_types_distribution(self) -> None:
        """Verifica la distribución global de tipos de pregunta (MC=1072, TF=155)."""
        self.assertEqual(self.struct_summary["question_type_counts"], EXPECTED_QUESTION_TYPES)

    def test_additional_references_counts(self) -> None:
        """Verifica conteos globales de referencias adicionales (220 preguntas con refs, 281 totales)."""
        self.assertEqual(self.struct_summary["questions_with_additional_references"], EXPECTED_WITH_ADDITIONAL_REFS)
        self.assertEqual(self.struct_summary["total_additional_references"], EXPECTED_TOTAL_ADDITIONAL_REFS)

    def test_eligible_modes_distribution(self) -> None:
        """Verifica la distribución de modos elegibles del NT."""
        self.assertEqual(self.struct_summary["eligible_modes_counts"], EXPECTED_MODES)

    def test_no_exact_duplicates(self) -> None:
        """Verifica que no existan duplicados exactos en las 1227 preguntas."""
        self.assertEqual(self.dup_summary["exact_duplicates_count"], 0)
        self.assertEqual(len(self.auditor.exact_duplicates), 0)

    def test_no_normalized_duplicates(self) -> None:
        """Verifica que no existan duplicados normalizados en las 1227 preguntas."""
        self.assertEqual(self.dup_summary["normalized_duplicates_count"], 0)
        self.assertEqual(len(self.auditor.normalized_duplicates), 0)

    def test_manifest_shas_match_actual_files(self) -> None:
        """Verifica que el SHA-256 de cada archivo maestro coincida 100% con el manifest oficial."""
        for b in self.auditor.loaded_books:
            manifest_sha = b["manifest_entry"]["canonical_sha256"]
            self.assertEqual(
                b["sha256"],
                manifest_sha,
                f"SHA mismatch en {b['book_key']}: real={b['sha256']} != manifest={manifest_sha}"
            )

    def test_total_reconciled_chapters(self) -> None:
        """Verifica que la cobertura sume exactamente los 260 capítulos del NT sin fallos."""
        self.assertEqual(self.audit_summary["total_chapters_reconciled"], EXPECTED_TOTAL_CHAPTERS)
        self.assertEqual(self.audit_summary["global_failed_chapters"], [])

    def test_global_requires_correction_zero(self) -> None:
        """Verifica que REQUIERE_CORRECCION global sea estrictamente 0."""
        self.assertEqual(self.audit_summary["global_requires_correction_count"], 0)

    def test_global_verified_and_inconclusive_sums(self) -> None:
        """Verifica que la suma de VERIFICADO (493) y NO_CONCLUYENTE (734) sea exactamente 1227."""
        self.assertEqual(self.audit_summary["global_verified_count"], 493)
        self.assertEqual(self.audit_summary["global_inconclusive_count"], 734)
        self.assertEqual(
            self.audit_summary["global_verified_count"] + self.audit_summary["global_inconclusive_count"],
            EXPECTED_TOTAL_QUESTIONS
        )

    def test_cross_validation_manifest_vs_status_map(self) -> None:
        """Prueba cruzada: manifest_totals == status_map_totals (493/734/0 = 1227)."""
        self.assertEqual(self.audit_summary["global_verified_count"], self.status_map_summary["verified_count"])
        self.assertEqual(self.audit_summary["global_inconclusive_count"], self.status_map_summary["inconclusive_count"])
        self.assertEqual(self.audit_summary["global_requires_correction_count"], self.status_map_summary["requires_correction_count"])
        self.assertEqual(self.status_map_summary["total_entries"], EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.status_map_summary["missing_count"], 0)
        self.assertEqual(self.status_map_summary["extra_count"], 0)
        self.assertEqual(self.status_map_summary["unknown_status_count"], 0)

    def test_per_book_status_map_and_manifest_reconciliation(self) -> None:
        """Verifica libro por libro que los conteos del status map coincidan 100% con el manifest."""
        status_map_data = json.loads(self.status_map_path.read_text(encoding="utf-8"))["entries"]
        
        for b in self.auditor.loaded_books:
            b_key = b["book_key"]
            m_ver = b["manifest_entry"]["verified_count"]
            m_inc = b["manifest_entry"]["inconclusive_count"]
            m_rc = b["manifest_entry"]["requires_correction_count"]
            m_total = b["questions_count"]

            book_qids = [q["id"] for q in b["questions"]]
            s_ver = sum(1 for qid in book_qids if status_map_data[qid]["audit_status"] == "VERIFIED")
            s_inc = sum(1 for qid in book_qids if status_map_data[qid]["audit_status"] == "INCONCLUSIVE")
            s_rc = sum(1 for qid in book_qids if status_map_data[qid]["audit_status"] == "REQUIRES_CORRECTION")

            self.assertEqual(s_ver, m_ver, f"Mismatch V en {b_key}: status_map={s_ver} != manifest={m_ver}")
            self.assertEqual(s_inc, m_inc, f"Mismatch I en {b_key}: status_map={s_inc} != manifest={m_inc}")
            self.assertEqual(s_rc, m_rc, f"Mismatch RC en {b_key}: status_map={s_rc} != manifest={m_rc}")
            self.assertEqual(s_ver + s_inc + s_rc, m_total, f"Sum mismatch en {b_key}")

    def test_source_text_not_persisted(self) -> None:
        """Verifica que ningún banco maestro contenga texto completo persistido de RVR1960."""
        for b in self.auditor.loaded_books:
            self.assertFalse(b["manifest_entry"].get("source_text_persisted", False))
            for q in b["questions"]:
                self.assertNotIn("source_text", q)
                self.assertNotIn("chapter_text", q)
                self.assertNotIn("rvr1960_text", q)

    def test_options_and_correct_answers_integrity(self) -> None:
        """Verifica que MC tenga correct_option=A y TF tenga neutralidad A/B."""
        for q in self.auditor.all_questions:
            q_type = q.get("question_type", q.get("type", "MULTIPLE_CHOICE"))
            if q_type == "TRUE_FALSE":
                self.assertIn(q.get("correct_option"), ("A", "B"), f"TF {q.get('id')} opción inválida")
                op_map = {"A": q.get("opcion_a"), "B": q.get("opcion_b")}
                self.assertEqual(q.get("correct_answer"), op_map[q.get("correct_option")], f"TF {q.get('id')} mismatch")
            else:
                self.assertEqual(q.get("correct_option"), "A", f"MC {q.get('id')} no tiene correct_option=A")
                self.assertEqual(q.get("correct_answer"), q.get("opcion_a"), f"MC {q.get('id')} respuesta no coincide con opcion_a")

    def test_generate_runtime_and_reports(self) -> None:
        """Verifica la generación correcta de todos los artefactos de reporte en build/audit/nt-global."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out = Path(tmp_dir) / "nt-global"
            auditor = GlobalNewTestamentAuditor(base_dir=self.base_dir, output_dir=tmp_out)
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            summary = auditor.generate_runtime_and_reports()
            
            self.assertEqual(summary["issues_count"], 0)
            self.assertEqual(summary["total_books"], EXPECTED_TOTAL_BOOKS)
            self.assertEqual(summary["total_questions"], EXPECTED_TOTAL_QUESTIONS)
            self.assertTrue(summary["fail_closed_ok"])
            
            expected_files = [
                "resumen-global-nt.json", "libros-nt.json", "integridad-bancos.json",
                "integridad-ids.json", "duplicados-exactos.json", "duplicados-normalizados.json",
                "similitud-semantica.json", "referencias-adicionales.json", "personajes-global.json",
                "modos-global.json", "auditorias-oficiales.json", "reconciliacion-artifacts.json",
                "evaluaciones.json", "runtime-global-check.json", "REPORTE_GLOBAL_NT.md"
            ]
            for ef in expected_files:
                p = tmp_out / ef
                self.assertTrue(p.exists(), f"Fichero esperado {ef} no fue generado")
                self.assertGreater(p.stat().st_size, 0, f"Fichero {ef} está vacío")

    def test_fail_closed_on_sha_mismatch(self) -> None:
        """Verifica que el auditor global detecte discrepancias de hash SHA-256."""
        auditor = GlobalNewTestamentAuditor(base_dir=self.base_dir)
        auditor.manifest_data = {
            "version": "1.0",
            "testament": "NEW_TESTAMENT",
            "total_books": EXPECTED_TOTAL_BOOKS,
            "books": [
                {
                    "order": b[0],
                    "book_key": b[1],
                    "canonical_name": b[2],
                    "input_file": f"tools/bible_extractor/{b[3]}",
                    "canonical_sha256": "0" * 64,
                    "total_chapters": b[4],
                    "total_questions": b[5],
                    "latest_verified_run_id": 1,
                    "latest_verified_run_number": 1,
                    "artifact_id": 1,
                    "artifact_name": "mock",
                    "artifact_digest": "mock",
                    "verified_count": b[5],
                    "inconclusive_count": 0,
                    "requires_correction_count": 0
                }
                for b in CANONICAL_BOOK_ORDER
            ]
        }
        auditor.load_and_validate_all_books()
        sha_issues = [iss for iss in auditor.issues if iss["type"] == "SHA_MISMATCH"]
        self.assertEqual(len(sha_issues), EXPECTED_TOTAL_BOOKS)

    def test_fail_closed_on_missing_or_unknown_status_in_status_map(self) -> None:
        """Verifica Fail-Closed si el status map tiene IDs faltantes o estados desconocidos."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_status_map = Path(tmp_dir) / "nt-global-audit-status-map-v1.json"
            # Mapa corrupto: le falta una pregunta y tiene un status desconocido
            corrupt_map = {
                "version": "1.0",
                "testament": "NEW_TESTAMENT",
                "entries": {
                    q["id"]: {"audit_status": "UNKNOWN_VAL"} if idx == 0 else {"audit_status": "VERIFIED"}
                    for idx, q in enumerate(self.auditor.all_questions[:-1])  # falta la última
                }
            }
            tmp_status_map.write_text(json.dumps(corrupt_map), encoding="utf-8")

            auditor = GlobalNewTestamentAuditor(base_dir=self.base_dir)
            auditor.status_map_path = tmp_status_map
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            auditor.load_and_validate_audit_status_map()

            issue_types = {iss["type"] for iss in auditor.issues}
            self.assertIn("MISSING_AUDIT_STATUS", issue_types)
            self.assertIn("UNKNOWN_AUDIT_STATUS", issue_types)

    def test_fail_closed_on_duplicate_id_and_invalid_data(self) -> None:
        """Verifica que el validador estructural detecte IDs duplicados y campos corruptos."""
        auditor = GlobalNewTestamentAuditor(base_dir=self.base_dir)
        auditor.all_questions = [
            {
                "id": "NQB-NT-MAT-0001",
                "question": "Pregunta de prueba 1",
                "opcion_a": "Respuesta A",
                "opcion_b": "Respuesta B",
                "opcion_c": "Respuesta C",
                "opcion_d": "Respuesta D",
                "correct_option": "A",
                "correct_answer": "Respuesta A",
                "difficulty": "Básico",
                "category": "NT_GENERAL",
                "eligible_modes": ["NT", "AMBOS"]
            },
            {
                "id": "NQB-NT-MAT-0001",
                "question": "Pregunta de prueba 2",
                "opcion_a": "",
                "opcion_b": "Respuesta B",
                "opcion_c": "Respuesta C",
                "opcion_d": "Respuesta D",
                "correct_option": "B",
                "correct_answer": "Respuesta B",
                "difficulty": "Invalida",
                "category": "AT_GENERAL",
                "eligible_modes": []
            }
        ]
        res = auditor.validate_global_structural_integrity()
        issue_types = {iss["type"] for iss in auditor.issues}
        self.assertIn("DUPLICATE_QUESTION_IDS", issue_types)
        self.assertIn("EMPTY_OPTION", issue_types)
        self.assertIn("INVALID_CORRECT_OPTION", issue_types)
        self.assertIn("INVALID_DIFFICULTY", issue_types)
        self.assertIn("INVALID_CATEGORY", issue_types)
        self.assertIn("EMPTY_ELIGIBLE_MODES", issue_types)


if __name__ == "__main__":
    unittest.main()
