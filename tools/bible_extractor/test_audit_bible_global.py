#!/usr/bin/env python3
"""
Pruebas unitarias y de integración para la Auditoría Transversal de la Biblia Protestante (66 libros).
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

from tools.bible_extractor.audit_bible_global import (
    CANONICAL_66_BOOKS,
    EXPECTED_CATEGORIES,
    EXPECTED_DIFFICULTIES,
    EXPECTED_GLOBAL_INCONCLUSIVE,
    EXPECTED_GLOBAL_RC,
    EXPECTED_GLOBAL_VERIFIED,
    EXPECTED_MODES,
    EXPECTED_QUESTION_TYPES,
    EXPECTED_TOTAL_ADDITIONAL_REFS,
    EXPECTED_TOTAL_ADDITIONAL_REFS_NT,
    EXPECTED_TOTAL_ADDITIONAL_REFS_OT,
    EXPECTED_TOTAL_BOOKS,
    EXPECTED_TOTAL_BOOKS_NT,
    EXPECTED_TOTAL_BOOKS_OT,
    EXPECTED_TOTAL_CHAPTERS,
    EXPECTED_TOTAL_CHAPTERS_NT,
    EXPECTED_TOTAL_CHAPTERS_OT,
    EXPECTED_TOTAL_QUESTIONS,
    EXPECTED_TOTAL_QUESTIONS_NT,
    EXPECTED_TOTAL_QUESTIONS_OT,
    EXPECTED_WITH_ADDITIONAL_REFS,
    EXPECTED_WITH_ADDITIONAL_REFS_NT,
    EXPECTED_WITH_ADDITIONAL_REFS_OT,
    GlobalBibleAuditor,
    normalize_text_for_dup_check,
    tokenize_for_similarity,
)


class TestAuditBibleGlobal(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_dir = Path(__file__).parent
        cls.manifest_path = cls.base_dir / "bible-global-manifest-v1.json"
        cls.status_map_path = cls.base_dir / "bible-global-audit-status-map-v1.json"
        cls.ot_status_map_path = cls.base_dir / "ot-global-audit-status-map-v1.json"
        cls.nt_status_map_path = cls.base_dir / "nt-global-audit-status-map-v1.json"

        cls.auditor = GlobalBibleAuditor(base_dir=cls.base_dir)
        cls.auditor.load_manifest()
        cls.auditor.load_and_validate_all_books()
        cls.struct_summary = cls.auditor.validate_global_structural_integrity()
        cls.dup_summary = cls.auditor.detect_duplicates_and_similarity()
        cls.audit_summary = cls.auditor.reconcile_official_audits()
        cls.status_map_summary = cls.auditor.load_and_validate_audit_status_map()

    def test_total_books_and_canonical_order(self) -> None:
        """Verifica que el universo contenga exactamente los 66 libros en orden canónico (39 AT + 27 NT)."""
        self.assertEqual(len(self.auditor.loaded_books), EXPECTED_TOTAL_BOOKS)
        self.assertEqual(len(CANONICAL_66_BOOKS), EXPECTED_TOTAL_BOOKS)

        ot_loaded = [b for b in self.auditor.loaded_books if b["testament"] == "OLD_TESTAMENT"]
        nt_loaded = [b for b in self.auditor.loaded_books if b["testament"] == "NEW_TESTAMENT"]

        self.assertEqual(len(ot_loaded), EXPECTED_TOTAL_BOOKS_OT)
        self.assertEqual(len(nt_loaded), EXPECTED_TOTAL_BOOKS_NT)

        for idx, book in enumerate(self.auditor.loaded_books):
            exp_order, exp_key, exp_name, _, _, _, exp_testament = CANONICAL_66_BOOKS[idx]
            self.assertEqual(book["order"], exp_order)
            self.assertEqual(book["book_key"], exp_key)
            self.assertEqual(book["canonical_name"], exp_name)
            self.assertEqual(book["testament"], exp_testament)

    def test_total_questions_and_unique_ids(self) -> None:
        """Verifica que existan exactamente 3847 preguntas y 3847 IDs únicos sin duplicados."""
        self.assertEqual(len(self.auditor.all_questions), EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["unique_ids_count"], EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.struct_summary["duplicate_ids_count"], 0)

    def test_difficulty_distribution(self) -> None:
        """Verifica la distribución global de dificultad (693/1437/1243/474)."""
        self.assertEqual(self.struct_summary["difficulty_counts"], EXPECTED_DIFFICULTIES)

    def test_category_distribution(self) -> None:
        """Verifica la distribución global de categorías (1615/656/1348/144/47/37)."""
        self.assertEqual(self.struct_summary["category_counts"], EXPECTED_CATEGORIES)

    def test_question_type_distribution(self) -> None:
        """Verifica la distribución global de tipos (3692 MULTIPLE_CHOICE, 155 TRUE_FALSE)."""
        self.assertEqual(self.struct_summary["question_type_counts"], EXPECTED_QUESTION_TYPES)

    def test_additional_references_counts(self) -> None:
        """Verifica conteos globales de referencias adicionales (271 q / 354 refs: 51/73 AT, 220/281 NT)."""
        self.assertEqual(self.struct_summary["questions_with_additional_references"], EXPECTED_WITH_ADDITIONAL_REFS)
        self.assertEqual(self.struct_summary["total_additional_references"], EXPECTED_TOTAL_ADDITIONAL_REFS)
        self.assertEqual(self.struct_summary["questions_with_additional_references_ot"], EXPECTED_WITH_ADDITIONAL_REFS_OT)
        self.assertEqual(self.struct_summary["total_additional_references_ot"], EXPECTED_TOTAL_ADDITIONAL_REFS_OT)
        self.assertEqual(self.struct_summary["questions_with_additional_references_nt"], EXPECTED_WITH_ADDITIONAL_REFS_NT)
        self.assertEqual(self.struct_summary["total_additional_references_nt"], EXPECTED_TOTAL_ADDITIONAL_REFS_NT)

    def test_eligible_modes_counts(self) -> None:
        """Verifica conteos de los modos globales."""
        self.assertEqual(self.struct_summary["eligible_modes_counts"], EXPECTED_MODES)

    def test_no_exact_duplicates_global_and_cross_testament(self) -> None:
        """Verifica que no existan duplicados exactos ni globalmente ni intertestamentarios AT↔NT."""
        self.assertEqual(self.dup_summary["exact_duplicates_count"], 0)
        self.assertEqual(self.dup_summary["cross_testament_exact_duplicates_count"], 0)
        self.assertEqual(len(self.auditor.exact_duplicates), 0)
        self.assertEqual(len(self.auditor.cross_testament_exact_duplicates), 0)

    def test_no_normalized_duplicates_global_and_cross_testament(self) -> None:
        """Verifica que no existan duplicados normalizados ni globalmente ni intertestamentarios AT↔NT."""
        self.assertEqual(self.dup_summary["normalized_duplicates_count"], 0)
        self.assertEqual(self.dup_summary["cross_testament_norm_duplicates_count"], 0)
        self.assertEqual(len(self.auditor.normalized_duplicates), 0)
        self.assertEqual(len(self.auditor.cross_testament_norm_duplicates), 0)

    def test_manifest_shas_match_all_66_files(self) -> None:
        """Verifica que el SHA-256 de los 66 archivos maestros coincida 100% con el manifest oficial."""
        for b in self.auditor.loaded_books:
            manifest_sha = b["manifest_entry"]["canonical_sha256"]
            self.assertEqual(
                b["sha256"],
                manifest_sha,
                f"SHA mismatch en {b['book_key']}: real={b['sha256']} != manifest={manifest_sha}"
            )

    def test_total_reconciled_chapters(self) -> None:
        """Verifica que la cobertura sume exactamente 1189 capítulos (929 AT + 260 NT)."""
        self.assertEqual(self.audit_summary["total_chapters_reconciled"], EXPECTED_TOTAL_CHAPTERS)
        self.assertEqual(self.audit_summary["global_failed_chapters"], [])

    def test_global_verified_and_inconclusive_sums(self) -> None:
        """Verifica que VERIFICADO (2486) + NO_CONCLUYENTE (1361) = 3847 (RC = 0)."""
        self.assertEqual(self.audit_summary["global_verified_count"], EXPECTED_GLOBAL_VERIFIED)
        self.assertEqual(self.audit_summary["global_inconclusive_count"], EXPECTED_GLOBAL_INCONCLUSIVE)
        self.assertEqual(self.audit_summary["global_requires_correction_count"], EXPECTED_GLOBAL_RC)
        self.assertEqual(self.audit_summary["ot_verified_count"], 1993)
        self.assertEqual(self.audit_summary["ot_inconclusive_count"], 627)
        self.assertEqual(self.audit_summary["nt_verified_count"], 493)
        self.assertEqual(self.audit_summary["nt_inconclusive_count"], 734)
        self.assertEqual(
            self.audit_summary["global_verified_count"] + self.audit_summary["global_inconclusive_count"],
            EXPECTED_TOTAL_QUESTIONS
        )

    def test_cross_validation_manifest_vs_status_map(self) -> None:
        """Prueba cruzada: manifest_totals == status_map_totals (2486/1361/0 = 3847)."""
        self.assertEqual(self.audit_summary["global_verified_count"], self.status_map_summary["verified_count"])
        self.assertEqual(self.audit_summary["global_inconclusive_count"], self.status_map_summary["inconclusive_count"])
        self.assertEqual(self.audit_summary["global_requires_correction_count"], self.status_map_summary["requires_correction_count"])
        self.assertEqual(self.status_map_summary["total_entries"], EXPECTED_TOTAL_QUESTIONS)
        self.assertEqual(self.status_map_summary["missing_count"], 0)
        self.assertEqual(self.status_map_summary["extra_count"], 0)
        self.assertEqual(self.status_map_summary["unknown_status_count"], 0)

    def test_status_map_union_and_disjoint_set(self) -> None:
        """Verifica que los conjuntos de IDs de AT y NT sean disjuntos y su unión sea 3847."""
        ot_map = json.loads(self.ot_status_map_path.read_text(encoding="utf-8"))["entries"]
        nt_map = json.loads(self.nt_status_map_path.read_text(encoding="utf-8"))["entries"]
        bible_map = json.loads(self.status_map_path.read_text(encoding="utf-8"))["entries"]

        ot_keys = set(ot_map.keys())
        nt_keys = set(nt_map.keys())
        bible_keys = set(bible_map.keys())

        self.assertEqual(len(ot_keys), EXPECTED_TOTAL_QUESTIONS_OT)
        self.assertEqual(len(nt_keys), EXPECTED_TOTAL_QUESTIONS_NT)
        self.assertEqual(len(bible_keys), EXPECTED_TOTAL_QUESTIONS)

        self.assertEqual(ot_keys.intersection(nt_keys), set())
        self.assertEqual(ot_keys.union(nt_keys), bible_keys)

    def test_per_book_status_map_and_manifest_reconciliation(self) -> None:
        """Verifica libro por libro (66 libros) que los conteos del status map coincidan con el manifest."""
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
        """Verifica que ningún banco maestro de los 66 contenga texto completo persistido de RVR1960."""
        for b in self.auditor.loaded_books:
            self.assertFalse(b["manifest_entry"].get("source_text_persisted", False))
            for q in b["questions"]:
                self.assertNotIn("source_text", q)
                self.assertNotIn("chapter_text", q)
                self.assertNotIn("rvr1960_text", q)

    def test_generate_runtime_and_reports(self) -> None:
        """Verifica la generación correcta de los 16 artefactos de reporte en build/audit/bible-global."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out = Path(tmp_dir) / "bible-global"
            auditor = GlobalBibleAuditor(base_dir=self.base_dir, output_dir=tmp_out)
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            summary = auditor.generate_runtime_and_reports()

            self.assertEqual(summary["issues_count"], 0)
            self.assertEqual(summary["total_books"], EXPECTED_TOTAL_BOOKS)
            self.assertEqual(summary["total_questions"], EXPECTED_TOTAL_QUESTIONS)
            self.assertTrue(summary["fail_closed_ok"])

            expected_files = [
                "resumen-global-biblia.json", "libros-biblia.json", "integridad-bancos.json",
                "integridad-ids.json", "integridad-status-map.json", "reconciliacion-global-at.json",
                "reconciliacion-global-nt.json", "duplicados-exactos.json", "duplicados-normalizados.json",
                "similitud-semantica.json", "referencias-adicionales.json", "referencias-cruzadas.json",
                "personajes-global.json", "modos-global.json", "evaluaciones.json",
                "runtime-global-check.json", "issues.json", "REPORTE_GLOBAL_BIBLIA.md"
            ]
            for ef in expected_files:
                p = tmp_out / ef
                self.assertTrue(p.exists(), f"Fichero esperado {ef} no fue generado")
                self.assertGreater(p.stat().st_size, 0, f"Fichero {ef} está vacío")

    def test_fail_closed_on_sha_mismatch(self) -> None:
        """Verifica que el auditor global detecte discrepancias de hash SHA-256."""
        auditor = GlobalBibleAuditor(base_dir=self.base_dir)
        auditor.manifest_data = {
            "version": "1.0",
            "canon": "PROTESTANT_66",
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
                    "verified_count": b[5],
                    "inconclusive_count": 0,
                    "requires_correction_count": 0
                }
                for b in CANONICAL_66_BOOKS
            ]
        }
        auditor.load_and_validate_all_books()
        sha_issues = [iss for iss in auditor.issues if iss["type"] == "SHA_MISMATCH"]
        self.assertEqual(len(sha_issues), EXPECTED_TOTAL_BOOKS)

    def test_fail_closed_on_missing_or_unknown_status_in_status_map(self) -> None:
        """Verifica Fail-Closed si el status map tiene IDs faltantes o estados desconocidos."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_status_map = Path(tmp_dir) / "bible-global-audit-status-map-v1.json"
            corrupt_map = {
                "version": "1.0",
                "canon": "PROTESTANT_66",
                "entries": {
                    q["id"]: {"audit_status": "UNKNOWN_VAL"} if idx == 0 else {"audit_status": "VERIFIED"}
                    for idx, q in enumerate(self.auditor.all_questions[:-1])
                }
            }
            tmp_status_map.write_text(json.dumps(corrupt_map), encoding="utf-8")

            auditor = GlobalBibleAuditor(base_dir=self.base_dir)
            auditor.status_map_path = tmp_status_map
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            auditor.load_and_validate_audit_status_map()

            issue_types = {iss["type"] for iss in auditor.issues}
            self.assertIn("MISSING_AUDIT_STATUS", issue_types)
            self.assertIn("UNKNOWN_AUDIT_STATUS", issue_types)

    def test_fail_closed_no_default_verified(self) -> None:
        """Garantiza que una pregunta sin status explícito NO pueda ser VERIFIED."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_status_map = Path(tmp_dir) / "bible-global-audit-status-map-v1.json"
            partial_entries = {
                q["id"]: {"audit_status": "INCONCLUSIVE"}
                for q in self.auditor.all_questions[1:]
            }
            tmp_status_map.write_text(json.dumps({
                "version": "1.0",
                "canon": "PROTESTANT_66",
                "entries": partial_entries
            }), encoding="utf-8")

            auditor = GlobalBibleAuditor(base_dir=self.base_dir, output_dir=Path(tmp_dir)/"out")
            auditor.status_map_path = tmp_status_map
            auditor.load_manifest()
            auditor.load_and_validate_all_books()
            summary = auditor.generate_runtime_and_reports()

            evals = json.loads((Path(tmp_dir)/"out"/"evaluaciones.json").read_text(encoding="utf-8"))["evaluaciones"]
            first_id = self.auditor.all_questions[0]["id"]
            self.assertEqual(evals.get(first_id), "MISSING")
            self.assertFalse(summary["fail_closed_ok"])

    def test_cross_testament_duplicate_detector_finds_injected_duplicate(self) -> None:
        """Verifica que el detector intertestamentario detecte duplicados exactos inyectados en test fixture."""
        auditor = GlobalBibleAuditor(base_dir=self.base_dir)
        auditor.all_questions = [
            {
                "id": "NQB-AT-GEN-0001",
                "book": "genesis",
                "testament": "OLD_TESTAMENT",
                "reference": "Génesis 1:1",
                "question": "¿Quién creó los cielos y la tierra en el principio?",
                "correct_answer": "Dios"
            },
            {
                "id": "NQB-NT-JHN-0001",
                "book": "john",
                "testament": "NEW_TESTAMENT",
                "reference": "Juan 1:1",
                "question": "¿Quién creó los cielos y la tierra en el principio?",
                "correct_answer": "Dios"
            }
        ]
        dup_res = auditor.detect_duplicates_and_similarity()
        self.assertEqual(dup_res["exact_duplicates_count"], 1)
        self.assertEqual(dup_res["cross_testament_exact_duplicates_count"], 1)
        self.assertEqual(len(auditor.cross_testament_exact_duplicates), 1)


if __name__ == "__main__":
    unittest.main()
