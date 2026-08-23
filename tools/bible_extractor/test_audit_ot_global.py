#!/usr/bin/env python3
"""
Pruebas unitarias y de integración para la Auditoría Global del Antiguo Testamento.
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

from tools.bible_extractor.audit_ot_global import (
    CANONICAL_BOOK_ORDER,
    EXPECTED_CATEGORIES,
    EXPECTED_DIFFICULTIES,
    EXPECTED_TOTAL_ADDITIONAL_REFS,
    EXPECTED_TOTAL_BOOKS,
    EXPECTED_TOTAL_CHAPTERS,
    EXPECTED_TOTAL_QUESTIONS,
    EXPECTED_WITH_ADDITIONAL_REFS,
    GlobalOldTestamentAuditor,
    normalize_text_for_dup_check,
    tokenize_for_similarity,
)


class TestAuditOTGlobal(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_dir = Path(__file__).parent
        cls.manifest_path = cls.base_dir / "ot-global-manifest-v1.json"
        cls.auditor = GlobalOldTestamentAuditor(base_dir=cls.base_dir)
        cls.auditor.load_manifest()
        cls.auditor.load_and_validate_all_books()
        cls.struct_summary = cls.auditor.validate_global_structural_integrity()
        cls.dup_summary = cls.auditor.detect_duplicates_and_similarity()
        cls.audit_summary = cls.auditor.reconcile_official_audits()

    def test_total_books_and_canonical_order(self) -> None:
        """Verifica que el universo contenga exactamente los 39 libros en orden canónico."""
        self.assertEqual(len(self.auditor.loaded_books), EXPECTED_TOTAL_BOOKS)
        self.assertEqual(len(CANONICAL_BOOK_ORDER), EXPECTED_TOTAL_BOOKS)
        for idx, book in enumerate(self.auditor.loaded_books):
            expected_order, expected_key, expected_name, _, _, _ = CANONICAL_BOOK_ORDER[idx]
            self.assertEqual(book["order"], expected_order)
            self.assertEqual(book["book_key"], expected_key)
            self.assertEqual(book["canonical_name"], expected_name)

    def test_total_questions_and_unique_ids(self) -> None:
        """Verifica que existan exactamente 2620 preguntas y 2620 IDs únicos."""
        self.assertEqual(len(self.auditor.all_questions), EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["unique_ids_count"], EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["duplicate_ids_count"], 0)

    def test_difficulty_distribution(self) -> None:
        """Verifica la distribución global de dificultad (393/999/868/360)."""
        self.assertEqual(self.struct_summary["difficulty_counts"], EXPECTED_DIFFICULTIES)

    def test_category_distribution(self) -> None:
        """Verifica la distribución global de categorías (1615/1005)."""
        self.assertEqual(self.struct_summary["category_counts"], EXPECTED_CATEGORIES)

    def test_additional_references_counts(self) -> None:
        """Verifica conteos globales de referencias adicionales (51 preguntas con refs, 73 totales)."""
        self.assertEqual(self.struct_summary["questions_with_additional_references"], EXPECTED_WITH_ADDITIONAL_REFS)
        self.assertEqual(self.struct_summary["total_additional_references"], EXPECTED_TOTAL_ADDITIONAL_REFS)

    def test_no_exact_duplicates(self) -> None:
        """Verifica que no existan duplicados exactos en las 2620 preguntas."""
        self.assertEqual(self.dup_summary["exact_duplicates_count"], 0)
        self.assertEqual(len(self.auditor.exact_duplicates), 0)

    def test_no_normalized_duplicates(self) -> None:
        """Verifica que no existan duplicados normalizados en las 2620 preguntas."""
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
        """Verifica que la cobertura sume exactamente los 929 capítulos del AT sin fallos."""
        self.assertEqual(self.audit_summary["total_chapters_reconciled"], EXPECTED_TOTAL_CHAPTERS)
        self.assertEqual(self.audit_summary["global_failed_chapters"], [])

    def test_global_requires_correction_zero(self) -> None:
        """Verifica que REQUIERE_CORRECCION global sea estrictamente 0."""
        self.assertEqual(self.audit_summary["global_requires_correction_count"], 0)

    def test_global_verified_and_inconclusive_sums(self) -> None:
        """Verifica que la suma de VERIFICADO (1993) y NO_CONCLUYENTE (627) sea exactamente 2620."""
        self.assertEqual(self.audit_summary["global_verified_count"], 1993)
        self.assertEqual(self.audit_summary["global_inconclusive_count"], 627)
        self.assertEqual(
            self.audit_summary["global_verified_count"] + self.audit_summary["global_inconclusive_count"],
            EXPECTED_TOTAL_QUESTIONS
        )

    def test_source_text_not_persisted(self) -> None:
        """Verifica que ningún banco maestro contenga texto completo persistido de RVR1960."""
        for b in self.auditor.loaded_books:
            self.assertFalse(b["manifest_entry"].get("source_text_persisted", False))
            for q in b["questions"]:
                self.assertNotIn("source_text", q)
                self.assertNotIn("chapter_text", q)
                self.assertNotIn("rvr1960_text", q)

    def test_options_and_correct_answers_integrity(self) -> None:
        """Verifica que las 2620 preguntas tengan correct_option=A y correct_answer=opcion_a."""
        for q in self.auditor.all_questions:
            self.assertEqual(q.get("correct_option"), "A", f"Pregunta {q.get('id')} no tiene correct_option=A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"), f"Pregunta {q.get('id')} respuesta no coincide con opcion_a")

    def test_generate_runtime_and_reports(self) -> None:
        """Verifica la generación correcta de todos los artefactos de reporte en build/audit/ot-global."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out = Path(tmp_dir) / "ot-global"
            auditor = GlobalOldTestamentAuditor(base_dir=self.base_dir, output_dir=tmp_out)
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            summary = auditor.generate_runtime_and_reports()
            
            self.assertEqual(summary["issues_count"], 0)
            self.assertEqual(summary["total_books"], EXPECTED_TOTAL_BOOKS)
            self.assertEqual(summary["total_questions"], EXPECTED_TOTAL_QUESTIONS)
            
            expected_files = [
                "resumen-global-at.json", "libros-at.json", "integridad-bancos.json",
                "integridad-ids.json", "duplicados-exactos.json", "duplicados-normalizados.json",
                "similitud-semantica.json", "referencias-adicionales.json", "personajes-global.json",
                "modos-global.json", "auditorias-oficiales.json", "reconciliacion-artifacts.json",
                "runtime-global-check.json", "REPORTE_GLOBAL_AT.md"
            ]
            for ef in expected_files:
                p = tmp_out / ef
                self.assertTrue(p.exists(), f"Fichero esperado {ef} no fue generado")
                self.assertGreater(p.stat().st_size, 0, f"Fichero {ef} está vacío")

    def test_fail_closed_on_sha_mismatch(self) -> None:
        """Verifica que el auditor global detecte discrepancias de hash SHA-256."""
        auditor = GlobalOldTestamentAuditor(base_dir=self.base_dir)
        auditor.manifest_data = {
            "version": "1.0",
            "testament": "OLD_TESTAMENT",
            "total_books": EXPECTED_TOTAL_BOOKS,
            "books": [
                {
                    "order": b[0],
                    "book_key": b[1],
                    "canonical_name": b[2],
                    "input_file": f"tools/bible_extractor/{b[3]}",
                    "canonical_sha256": "0" * 64,  # SHA corrupto
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

    def test_fail_closed_on_duplicate_id_and_invalid_data(self) -> None:
        """Verifica que el validador estructural detecte IDs duplicados y campos corruptos."""
        auditor = GlobalOldTestamentAuditor(base_dir=self.base_dir)
        auditor.all_questions = [
            {
                "id": "NQB-AT-GEN-0001",
                "question": "Pregunta de prueba 1",
                "opcion_a": "Respuesta A",
                "opcion_b": "Respuesta B",
                "opcion_c": "Respuesta C",
                "opcion_d": "Respuesta D",
                "correct_option": "A",
                "correct_answer": "Respuesta A",
                "difficulty": "Básico",
                "category": "AT_GENERAL",
                "eligible_modes": ["AT"]
            },
            {
                "id": "NQB-AT-GEN-0001",  # ID duplicado
                "question": "Pregunta de prueba 2",
                "opcion_a": "",  # Opción vacía
                "opcion_b": "Respuesta B",
                "opcion_c": "Respuesta C",
                "opcion_d": "Respuesta D",
                "correct_option": "B",  # correct_option != A
                "correct_answer": "Respuesta B",
                "difficulty": "Invalida",  # Dificultad inválida
                "category": "NT_GENERAL",  # Categoría inválida
                "eligible_modes": []  # Modos vacíos
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
