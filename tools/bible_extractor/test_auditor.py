#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json,
exodus-master-input.json, leviticus-master-input.json y numbers-master-input.json,
realizando mutaciones controladas sobre copias profundas (deepcopy) para verificar:
- Soporte multilibro (Génesis, Éxodo, Levítico, Números);
- Tratamiento estricto de artículos indefinidos 'un/una' frente a cantidades reales (NUM-0009, NUM-0095, NUM-0058, NUM-0064, NUM-0088);
- Preposición 'sin' no detectada como falso topónimo (NUM-0012, NUM-0041, NUM-0073);
- Equivalencia editorial de nombres propios RVR1960 (Miriam ↔ María en NUM-0026, NUM-0027, NUM-0044; Sihón ↔ Sehón en NUM-0051);
- Parsing de números compuestos grandes (601 730 en NUM-0062) y mutación negativa;
- División en dos partes / partir por mitad (NUM-0076) y mutación negativa;
- NQB-AT-LEV-0079: 'La décima parte' vs diezmo de la tierra en Levítico 27:30;
- NQB-AT-LEV-0079 negativo: 'La quinta parte' produce FAIL;
- NQB-AT-LEV-0080: 'Cada décimo animal' vs concepto de diezmo/vara en Levítico 27:32;
- NQB-AT-LEV-0080 negativo: 'Cada séptimo animal' produce FAIL;
- No generación automática de 10 ante apariciones no cuantitativas de 'diezmo';
- NQB-AT-LEV-0019: rango aislado 8:12 insuficiente vs contexto 8:10 con Moisés;
- NQB-AT-LEV-0038: suertes sobre machos cabríos no produce falso FAIL;
- NQB-AT-LEV-0065: período descriptivo 'un año de reposo' no produce falso FAIL contra 7;
- NQB-AT-EXO-0003 (Nilo / río);
- NQB-AT-EXO-0027 (Egipto como marco ambiental);
- NQB-AT-EXO-0074 (Dos corderos, uno...);
- Diagnóstico de NQB-AT-GEN-0110 sin y con Génesis 44:18;
- Manejo de fallos de API como NO_CONCLUYENTE;
- Pruebas negativas estrictas de contradicción objetiva en números, lugares y entidades.
"""

from __future__ import annotations

import collections
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditor import (
    evaluate_question, run_audit, extract_numbers, normalize, detect_book_key,
    token_matches_text, BOOK_CONFIGS, is_locative_or_collective_entity, resolve_implicit_speaker,
    is_narrative_source_attribution, is_biblical_place_usage, is_biblical_person_usage,
    BIBLICAL_PERSON_ALIASES, person_token_matches_text, BIBLE_PERSONAJES
)

GENESIS_PATH = Path(__file__).parent / "genesis-master-input.json"
EXODUS_PATH = Path(__file__).parent / "exodus-master-input.json"
LEVITICUS_PATH = Path(__file__).parent / "leviticus-master-input.json"
NUMBERS_PATH = Path(__file__).parent / "numbers-master-input.json"
DEUTERONOMY_PATH = Path(__file__).parent / "deuteronomy-master-input.json"
JOSHUA_PATH = Path(__file__).parent / "joshua-master-input.json"
JUDGES_PATH = Path(__file__).parent / "judges-master-input.json"
RUTH_PATH = Path(__file__).parent / "ruth-master-input.json"
SAMUEL1_PATH = Path(__file__).parent / "1samuel-master-input.json"
SAMUEL2_PATH = Path(__file__).parent / "2samuel-master-input.json"
KINGS1_PATH = Path(__file__).parent / "1kings-master-input.json"
KINGS2_PATH = Path(__file__).parent / "2kings-master-input.json"
CHRONICLES1_PATH = Path(__file__).parent / "1chronicles-master-input.json"
CHRONICLES2_PATH = Path(__file__).parent / "2chronicles-master-input.json"
EZRA_PATH = Path(__file__).parent / "ezra-master-input.json"
NEHEMIAH_PATH = Path(__file__).parent / "nehemiah-master-input.json"
ESTHER_PATH = Path(__file__).parent / "esther-master-input.json"
JOB_PATH = Path(__file__).parent / "job-master-input.json"
PSALMS_PATH = Path(__file__).parent / "psalms-master-input.json"
PROVERBS_PATH = Path(__file__).parent / "proverbs-master-input.json"
ECCLESIASTES_PATH = Path(__file__).parent / "ecclesiastes-master-input.json"
SONG_OF_SONGS_PATH = Path(__file__).parent / "song-of-songs-master-input.json"
ISAIAH_PATH = Path(__file__).parent / "isaiah-master-input.json"
JEREMIAH_PATH = Path(__file__).parent / "jeremiah-master-input.json"
LAMENTATIONS_PATH = Path(__file__).parent / "lamentations-master-input.json"
EZEKIEL_PATH = Path(__file__).parent / "ezekiel-master-input.json"
DANIEL_PATH = Path(__file__).parent / "daniel-master-input.json"
HOSEA_PATH = Path(__file__).parent / "hosea-master-input.json"
JOEL_PATH = Path(__file__).parent / "joel-master-input.json"
AMOS_PATH = Path(__file__).parent / "amos-master-input.json"
OBADIAH_PATH = Path(__file__).parent / "obadiah-master-input.json"
JONAH_PATH = Path(__file__).parent / "jonah-master-input.json"
MICAH_PATH = Path(__file__).parent / "micah-master-input.json"
NAHUM_PATH = Path(__file__).parent / "nahum-master-input.json"
HABAKKUK_PATH = Path(__file__).parent / "habakkuk-master-input.json"
ZEPHANIAH_PATH = Path(__file__).parent / "zephaniah-master-input.json"
HAGGAI_PATH = Path(__file__).parent / "haggai-master-input.json"
ZECHARIAH_PATH = Path(__file__).parent / "zechariah-master-input.json"
MALACHI_PATH = Path(__file__).parent / "malachi-master-input.json"
MATTHEW_PATH = Path(__file__).parent / "matthew-master-input.json"
MARK_PATH = Path(__file__).parent / "mark-master-input.json"
LUKE_PATH = Path(__file__).parent / "luke-master-input.json"
JOHN_PATH = Path(__file__).parent / "john-master-input.json"
ACTS_PATH = Path(__file__).parent / "acts-master-input.json"
ROMANS_PATH = Path(__file__).parent / "romans-master-input.json"
CORINTHIANS1_PATH = Path(__file__).parent / "1corinthians-master-input.json"
CORINTHIANS2_PATH = Path(__file__).parent / "2corinthians-master-input.json"
GALATIANS_PATH = Path(__file__).parent / "galatians-master-input.json"
EPHESIANS_PATH = Path(__file__).parent / "ephesians-master-input.json"
PHILIPPIANS_PATH = Path(__file__).parent / "philippians-master-input.json"
COLOSSIANS_PATH = Path(__file__).parent / "colossians-master-input.json"
THESSALONIANS1_PATH = Path(__file__).parent / "1thessalonians-master-input.json"
THESSALONIANS2_PATH = Path(__file__).parent / "2thessalonians-master-input.json"
TIMOTHY1_PATH = Path(__file__).parent / "1timothy-master-input.json"
TIMOTHY2_PATH = Path(__file__).parent / "2timothy-master-input.json"
TITUS_PATH = Path(__file__).parent / "titus-master-input.json"
PHILEMON_PATH = Path(__file__).parent / "philemon-master-input.json"
HEBREWS_PATH = Path(__file__).parent / "hebrews-master-input.json"
JAMES_PATH = Path(__file__).parent / "james-master-input.json"
PETER1_PATH = Path(__file__).parent / "1peter-master-input.json"
PETER2_PATH = Path(__file__).parent / "2peter-master-input.json"
JOHN1_PATH = Path(__file__).parent / "1john-master-input.json"
JOHN2_PATH = Path(__file__).parent / "2john-master-input.json"
JOHN3_PATH = Path(__file__).parent / "3john-master-input.json"
JUDE_PATH = Path(__file__).parent / "jude-master-input.json"
REVELATION_PATH = Path(__file__).parent / "revelation-master-input.json"


class TestAuditorCanonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw_gen = json.loads(GENESIS_PATH.read_text(encoding="utf-8"))
        cls.genesis_questions = {q["id"]: q for q in (raw_gen.get("questions", []) if isinstance(raw_gen, dict) else raw_gen)}

        if EXODUS_PATH.exists():
            raw_exo = json.loads(EXODUS_PATH.read_text(encoding="utf-8"))
            cls.exodus_questions = {q["id"]: q for q in (raw_exo.get("questions", []) if isinstance(raw_exo, dict) else raw_exo)}
        else:
            cls.exodus_questions = {}

        if LEVITICUS_PATH.exists():
            raw_lev = json.loads(LEVITICUS_PATH.read_text(encoding="utf-8"))
            cls.leviticus_questions = {q["id"]: q for q in (raw_lev.get("questions", []) if isinstance(raw_lev, dict) else raw_lev)}
        else:
            cls.leviticus_questions = {}

        if NUMBERS_PATH.exists():
            raw_num = json.loads(NUMBERS_PATH.read_text(encoding="utf-8"))
            cls.numbers_questions = {q["id"]: q for q in (raw_num.get("questions", []) if isinstance(raw_num, dict) else raw_num)}
        else:
            cls.numbers_questions = {}

        if DEUTERONOMY_PATH.exists():
            raw_deut = json.loads(DEUTERONOMY_PATH.read_text(encoding="utf-8"))
            cls.deuteronomy_questions = {q["id"]: q for q in (raw_deut.get("questions", []) if isinstance(raw_deut, dict) else raw_deut)}
        else:
            cls.deuteronomy_questions = {}

        if JOSHUA_PATH.exists():
            raw_jos = json.loads(JOSHUA_PATH.read_text(encoding="utf-8"))
            cls.joshua_questions = {q["id"]: q for q in (raw_jos.get("questions", []) if isinstance(raw_jos, dict) else raw_jos)}
        else:
            cls.joshua_questions = {}

        if JUDGES_PATH.exists():
            raw_jue = json.loads(JUDGES_PATH.read_text(encoding="utf-8"))
            cls.judges_questions = {q["id"]: q for q in (raw_jue.get("questions", []) if isinstance(raw_jue, dict) else raw_jue)}
        else:
            cls.judges_questions = {}

        if RUTH_PATH.exists():
            raw_rut = json.loads(RUTH_PATH.read_text(encoding="utf-8"))
            cls.ruth_questions = {q["id"]: q for q in (raw_rut.get("questions", []) if isinstance(raw_rut, dict) else raw_rut)}
        else:
            cls.ruth_questions = {}

        if SAMUEL1_PATH.exists():
            raw_1sa = json.loads(SAMUEL1_PATH.read_text(encoding="utf-8"))
            cls.samuel1_questions = {q["id"]: q for q in (raw_1sa.get("questions", []) if isinstance(raw_1sa, dict) else raw_1sa)}
        else:
            cls.samuel1_questions = {}

        if SAMUEL2_PATH.exists():
            raw_2sa = json.loads(SAMUEL2_PATH.read_text(encoding="utf-8"))
            cls.samuel2_questions = {q["id"]: q for q in (raw_2sa.get("questions", []) if isinstance(raw_2sa, dict) else raw_2sa)}
        else:
            cls.samuel2_questions = {}

        if KINGS1_PATH.exists():
            raw_1ki = json.loads(KINGS1_PATH.read_text(encoding="utf-8"))
            cls.kings1_questions = {q["id"]: q for q in (raw_1ki.get("questions", []) if isinstance(raw_1ki, dict) else raw_1ki)}
        else:
            cls.kings1_questions = {}

        if KINGS2_PATH.exists():
            raw_2ki = json.loads(KINGS2_PATH.read_text(encoding="utf-8"))
            cls.kings2_questions = {q["id"]: q for q in (raw_2ki.get("questions", []) if isinstance(raw_2ki, dict) else raw_2ki)}
        else:
            cls.kings2_questions = {}

        if CHRONICLES1_PATH.exists():
            raw_1ch = json.loads(CHRONICLES1_PATH.read_text(encoding="utf-8"))
            cls.chronicles1_questions = {q["id"]: q for q in (raw_1ch.get("questions", []) if isinstance(raw_1ch, dict) else raw_1ch)}
        else:
            cls.chronicles1_questions = {}

        if CHRONICLES2_PATH.exists():
            raw_2ch = json.loads(CHRONICLES2_PATH.read_text(encoding="utf-8"))
            cls.chronicles2_questions = {q["id"]: q for q in (raw_2ch.get("questions", []) if isinstance(raw_2ch, dict) else raw_2ch)}
        else:
            cls.chronicles2_questions = {}

        if EZRA_PATH.exists():
            raw_ezr = json.loads(EZRA_PATH.read_text(encoding="utf-8"))
            cls.ezra_questions = {q["id"]: q for q in (raw_ezr.get("questions", []) if isinstance(raw_ezr, dict) else raw_ezr)}
        else:
            cls.ezra_questions = {}

        if NEHEMIAH_PATH.exists():
            raw_neh = json.loads(NEHEMIAH_PATH.read_text(encoding="utf-8"))
            cls.nehemiah_questions = {q["id"]: q for q in (raw_neh.get("questions", []) if isinstance(raw_neh, dict) else raw_neh)}
        else:
            cls.nehemiah_questions = {}

        if ESTHER_PATH.exists():
            raw_est = json.loads(ESTHER_PATH.read_text(encoding="utf-8"))
            cls.esther_questions = {q["id"]: q for q in (raw_est.get("questions", []) if isinstance(raw_est, dict) else raw_est)}
        else:
            cls.esther_questions = {}

        if JOB_PATH.exists():
            raw_job = json.loads(JOB_PATH.read_text(encoding="utf-8"))
            cls.job_questions = {q["id"]: q for q in (raw_job.get("questions", []) if isinstance(raw_job, dict) else raw_job)}
        else:
            cls.job_questions = {}

        if PSALMS_PATH.exists():
            raw_psa = json.loads(PSALMS_PATH.read_text(encoding="utf-8"))
            cls.psalms_questions = {q["id"]: q for q in (raw_psa.get("questions", []) if isinstance(raw_psa, dict) else raw_psa)}
        else:
            cls.psalms_questions = {}

        if PROVERBS_PATH.exists():
            raw_pro = json.loads(PROVERBS_PATH.read_text(encoding="utf-8"))
            cls.proverbs_questions = {q["id"]: q for q in (raw_pro.get("questions", []) if isinstance(raw_pro, dict) else raw_pro)}
        else:
            cls.proverbs_questions = {}

        if ECCLESIASTES_PATH.exists():
            raw_ecl = json.loads(ECCLESIASTES_PATH.read_text(encoding="utf-8"))
            cls.ecclesiastes_questions = {q["id"]: q for q in (raw_ecl.get("questions", []) if isinstance(raw_ecl, dict) else raw_ecl)}
        else:
            cls.ecclesiastes_questions = {}

        if SONG_OF_SONGS_PATH.exists():
            raw_sos = json.loads(SONG_OF_SONGS_PATH.read_text(encoding="utf-8"))
            cls.song_of_songs_questions = {q["id"]: q for q in (raw_sos.get("questions", []) if isinstance(raw_sos, dict) else raw_sos)}
        else:
            cls.song_of_songs_questions = {}

        if ISAIAH_PATH.exists():
            raw_isa = json.loads(ISAIAH_PATH.read_text(encoding="utf-8"))
            cls.isaiah_questions = {q["id"]: q for q in (raw_isa.get("questions", []) if isinstance(raw_isa, dict) else raw_isa)}
        else:
            cls.isaiah_questions = {}

        if JEREMIAH_PATH.exists():
            raw_jer = json.loads(JEREMIAH_PATH.read_text(encoding="utf-8"))
            cls.jeremiah_questions = {q["id"]: q for q in (raw_jer.get("questions", []) if isinstance(raw_jer, dict) else raw_jer)}
        else:
            cls.jeremiah_questions = {}

        if LAMENTATIONS_PATH.exists():
            raw_lam = json.loads(LAMENTATIONS_PATH.read_text(encoding="utf-8"))
            cls.lamentations_questions = {q["id"]: q for q in (raw_lam.get("questions", []) if isinstance(raw_lam, dict) else raw_lam)}
        else:
            cls.lamentations_questions = {}

        if EZEKIEL_PATH.exists():
            raw_eze = json.loads(EZEKIEL_PATH.read_text(encoding="utf-8"))
            cls.ezekiel_questions = {q["id"]: q for q in (raw_eze.get("questions", []) if isinstance(raw_eze, dict) else raw_eze)}
        else:
            cls.ezekiel_questions = {}

        if DANIEL_PATH.exists():
            raw_dan = json.loads(DANIEL_PATH.read_text(encoding="utf-8"))
            cls.daniel_questions = {q["id"]: q for q in (raw_dan.get("questions", []) if isinstance(raw_dan, dict) else raw_dan)}
        else:
            cls.daniel_questions = {}

        if HOSEA_PATH.exists():
            raw_hos = json.loads(HOSEA_PATH.read_text(encoding="utf-8"))
            cls.hosea_questions = {q["id"]: q for q in (raw_hos.get("questions", []) if isinstance(raw_hos, dict) else raw_hos)}
        else:
            cls.hosea_questions = {}

        if JOEL_PATH.exists():
            raw_joe = json.loads(JOEL_PATH.read_text(encoding="utf-8"))
            cls.joel_questions = {q["id"]: q for q in (raw_joe.get("questions", []) if isinstance(raw_joe, dict) else raw_joe)}
        else:
            cls.joel_questions = {}

        if AMOS_PATH.exists():
            raw_amo = json.loads(AMOS_PATH.read_text(encoding="utf-8"))
            cls.amos_questions = {q["id"]: q for q in (raw_amo.get("questions", []) if isinstance(raw_amo, dict) else raw_amo)}
        else:
            cls.amos_questions = {}

        if OBADIAH_PATH.exists():
            raw_oba = json.loads(OBADIAH_PATH.read_text(encoding="utf-8"))
            cls.obadiah_questions = {q["id"]: q for q in (raw_oba.get("questions", []) if isinstance(raw_oba, dict) else raw_oba)}
        else:
            cls.obadiah_questions = {}

        if JONAH_PATH.exists():
            raw_jon = json.loads(JONAH_PATH.read_text(encoding="utf-8"))
            cls.jonah_questions = {q["id"]: q for q in (raw_jon.get("questions", []) if isinstance(raw_jon, dict) else raw_jon)}
        else:
            cls.jonah_questions = {}

        if MICAH_PATH.exists():
            raw_mic = json.loads(MICAH_PATH.read_text(encoding="utf-8"))
            cls.micah_questions = {q["id"]: q for q in (raw_mic.get("questions", []) if isinstance(raw_mic, dict) else raw_mic)}
        else:
            cls.micah_questions = {}

        if NAHUM_PATH.exists():
            raw_nah = json.loads(NAHUM_PATH.read_text(encoding="utf-8"))
            cls.nahum_questions = {q["id"]: q for q in (raw_nah.get("questions", []) if isinstance(raw_nah, dict) else raw_nah)}
        else:
            cls.nahum_questions = {}

        if HABAKKUK_PATH.exists():
            raw_hab = json.loads(HABAKKUK_PATH.read_text(encoding="utf-8"))
            cls.habakkuk_questions = {q["id"]: q for q in (raw_hab.get("questions", []) if isinstance(raw_hab, dict) else raw_hab)}
        else:
            cls.habakkuk_questions = {}

        if ZEPHANIAH_PATH.exists():
            raw_zep = json.loads(ZEPHANIAH_PATH.read_text(encoding="utf-8"))
            cls.zephaniah_questions = {q["id"]: q for q in (raw_zep.get("questions", []) if isinstance(raw_zep, dict) else raw_zep)}
        else:
            cls.zephaniah_questions = {}

        if HAGGAI_PATH.exists():
            raw_hag = json.loads(HAGGAI_PATH.read_text(encoding="utf-8"))
            cls.haggai_questions = {q["id"]: q for q in (raw_hag.get("questions", []) if isinstance(raw_hag, dict) else raw_hag)}
        else:
            cls.haggai_questions = {}

        if ZECHARIAH_PATH.exists():
            raw_zec = json.loads(ZECHARIAH_PATH.read_text(encoding="utf-8"))
            cls.zechariah_questions = {q["id"]: q for q in (raw_zec.get("questions", []) if isinstance(raw_zec, dict) else raw_zec)}
        else:
            cls.zechariah_questions = {}

        if MALACHI_PATH.exists():
            raw_mal = json.loads(MALACHI_PATH.read_text(encoding="utf-8"))
            cls.malachi_questions = {q["id"]: q for q in (raw_mal.get("questions", []) if isinstance(raw_mal, dict) else raw_mal)}
        else:
            cls.malachi_questions = {}

        if MATTHEW_PATH.exists():
            raw_mat = json.loads(MATTHEW_PATH.read_text(encoding="utf-8"))
            cls.matthew_questions = {q["id"]: q for q in (raw_mat.get("questions", []) if isinstance(raw_mat, dict) else raw_mat)}
        else:
            cls.matthew_questions = {}

        if MARK_PATH.exists():
            raw_mar = json.loads(MARK_PATH.read_text(encoding="utf-8"))
            cls.mark_questions = {q["id"]: q for q in (raw_mar.get("questions", []) if isinstance(raw_mar, dict) else raw_mar)}
        else:
            cls.mark_questions = {}

        if LUKE_PATH.exists():
            raw_luk = json.loads(LUKE_PATH.read_text(encoding="utf-8"))
            cls.luke_questions = {q["id"]: q for q in (raw_luk.get("questions", []) if isinstance(raw_luk, dict) else raw_luk)}
        else:
            cls.luke_questions = {}

        if JOHN_PATH.exists():
            raw_joh = json.loads(JOHN_PATH.read_text(encoding="utf-8"))
            cls.john_questions = {q["id"]: q for q in (raw_joh.get("questions", []) if isinstance(raw_joh, dict) else raw_joh)}
        else:
            cls.john_questions = {}

        if ACTS_PATH.exists():
            raw_act = json.loads(ACTS_PATH.read_text(encoding="utf-8"))
            cls.acts_questions = {q["id"]: q for q in (raw_act.get("questions", []) if isinstance(raw_act, dict) else raw_act)}
        else:
            cls.acts_questions = {}

        if ROMANS_PATH.exists():
            raw_rom = json.loads(ROMANS_PATH.read_text(encoding="utf-8"))
            cls.romans_questions = {q["id"]: q for q in (raw_rom.get("questions", []) if isinstance(raw_rom, dict) else raw_rom)}
        else:
            cls.romans_questions = {}

        if CORINTHIANS1_PATH.exists():
            raw_1co = json.loads(CORINTHIANS1_PATH.read_text(encoding="utf-8"))
            cls.corinthians1_questions = {q["id"]: q for q in (raw_1co.get("questions", []) if isinstance(raw_1co, dict) else raw_1co)}
        else:
            cls.corinthians1_questions = {}

        if CORINTHIANS2_PATH.exists():
            raw_2co = json.loads(CORINTHIANS2_PATH.read_text(encoding="utf-8"))
            cls.corinthians2_questions = {q["id"]: q for q in (raw_2co.get("questions", []) if isinstance(raw_2co, dict) else raw_2co)}
        else:
            cls.corinthians2_questions = {}

        if GALATIANS_PATH.exists():
            raw_gal = json.loads(GALATIANS_PATH.read_text(encoding="utf-8"))
            cls.galatians_questions = {q["id"]: q for q in (raw_gal.get("questions", []) if isinstance(raw_gal, dict) else raw_gal)}
        else:
            cls.galatians_questions = {}

        if EPHESIANS_PATH.exists():
            raw_efe = json.loads(EPHESIANS_PATH.read_text(encoding="utf-8"))
            cls.ephesians_questions = {q["id"]: q for q in (raw_efe.get("questions", []) if isinstance(raw_efe, dict) else raw_efe)}
        else:
            cls.ephesians_questions = {}

        if PHILIPPIANS_PATH.exists():
            raw_fil = json.loads(PHILIPPIANS_PATH.read_text(encoding="utf-8"))
            cls.philippians_questions = {q["id"]: q for q in (raw_fil.get("questions", []) if isinstance(raw_fil, dict) else raw_fil)}
        else:
            cls.philippians_questions = {}

        if COLOSSIANS_PATH.exists():
            raw_col = json.loads(COLOSSIANS_PATH.read_text(encoding="utf-8"))
            cls.colossians_questions = {q["id"]: q for q in (raw_col.get("questions", []) if isinstance(raw_col, dict) else raw_col)}
        else:
            cls.colossians_questions = {}

        if THESSALONIANS1_PATH.exists():
            raw_1ts = json.loads(THESSALONIANS1_PATH.read_text(encoding="utf-8"))
            cls.thessalonians1_questions = {q["id"]: q for q in (raw_1ts.get("questions", []) if isinstance(raw_1ts, dict) else raw_1ts)}
        else:
            cls.thessalonians1_questions = {}

        if THESSALONIANS2_PATH.exists():
            raw_2ts = json.loads(THESSALONIANS2_PATH.read_text(encoding="utf-8"))
            cls.thessalonians2_questions = {q["id"]: q for q in (raw_2ts.get("questions", []) if isinstance(raw_2ts, dict) else raw_2ts)}
        else:
            cls.thessalonians2_questions = {}

        if TIMOTHY1_PATH.exists():
            raw_1ti = json.loads(TIMOTHY1_PATH.read_text(encoding="utf-8"))
            cls.timothy1_questions = {q["id"]: q for q in (raw_1ti.get("questions", []) if isinstance(raw_1ti, dict) else raw_1ti)}
        else:
            cls.timothy1_questions = {}

        if TIMOTHY2_PATH.exists():
            raw_2ti = json.loads(TIMOTHY2_PATH.read_text(encoding="utf-8"))
            cls.timothy2_questions = {q["id"]: q for q in (raw_2ti.get("questions", []) if isinstance(raw_2ti, dict) else raw_2ti)}
        else:
            cls.timothy2_questions = {}

        if TITUS_PATH.exists():
            raw_tit = json.loads(TITUS_PATH.read_text(encoding="utf-8"))
            cls.titus_questions = {q["id"]: q for q in (raw_tit.get("questions", []) if isinstance(raw_tit, dict) else raw_tit)}
        else:
            cls.titus_questions = {}

        if PHILEMON_PATH.exists():
            raw_flm = json.loads(PHILEMON_PATH.read_text(encoding="utf-8"))
            cls.philemon_questions = {q["id"]: q for q in (raw_flm.get("questions", []) if isinstance(raw_flm, dict) else raw_flm)}
        else:
            cls.philemon_questions = {}

        if HEBREWS_PATH.exists():
            raw_heb = json.loads(HEBREWS_PATH.read_text(encoding="utf-8"))
            cls.hebrews_questions = {q["id"]: q for q in (raw_heb.get("questions", []) if isinstance(raw_heb, dict) else raw_heb)}
        else:
            cls.hebrews_questions = {}

        if JAMES_PATH.exists():
            raw_san = json.loads(JAMES_PATH.read_text(encoding="utf-8"))
            cls.james_questions = {q["id"]: q for q in (raw_san.get("questions", []) if isinstance(raw_san, dict) else raw_san)}
        else:
            cls.james_questions = {}

        if PETER1_PATH.exists():
            raw_1pe = json.loads(PETER1_PATH.read_text(encoding="utf-8"))
            cls.peter1_questions = {q["id"]: q for q in (raw_1pe.get("questions", []) if isinstance(raw_1pe, dict) else raw_1pe)}
        else:
            cls.peter1_questions = {}

        if PETER2_PATH.exists():
            raw_2pe = json.loads(PETER2_PATH.read_text(encoding="utf-8"))
            cls.peter2_questions = {q["id"]: q for q in (raw_2pe.get("questions", []) if isinstance(raw_2pe, dict) else raw_2pe)}
        else:
            cls.peter2_questions = {}

        if JOHN1_PATH.exists():
            raw_1jn = json.loads(JOHN1_PATH.read_text(encoding="utf-8"))
            cls.john1_questions = {q["id"]: q for q in (raw_1jn.get("questions", []) if isinstance(raw_1jn, dict) else raw_1jn)}
        else:
            cls.john1_questions = {}

        if JOHN2_PATH.exists():
            raw_2jn = json.loads(JOHN2_PATH.read_text(encoding="utf-8"))
            cls.john2_questions = {q["id"]: q for q in (raw_2jn.get("questions", []) if isinstance(raw_2jn, dict) else raw_2jn)}
        else:
            cls.john2_questions = {}

        if JOHN3_PATH.exists():
            raw_3jn = json.loads(JOHN3_PATH.read_text(encoding="utf-8"))
            cls.john3_questions = {q["id"]: q for q in (raw_3jn.get("questions", []) if isinstance(raw_3jn, dict) else raw_3jn)}
        else:
            cls.john3_questions = {}

        if JUDE_PATH.exists():
            raw_jud = json.loads(JUDE_PATH.read_text(encoding="utf-8"))
            cls.jude_questions = {q["id"]: q for q in (raw_jud.get("questions", []) if isinstance(raw_jud, dict) else raw_jud)}
        else:
            cls.jude_questions = {}

        if REVELATION_PATH.exists():
            raw_rev = json.loads(REVELATION_PATH.read_text(encoding="utf-8"))
            cls.revelation_questions = {q["id"]: q for q in (raw_rev.get("questions", []) if isinstance(raw_rev, dict) else raw_rev)}
        else:
            cls.revelation_questions = {}

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_genesis_question(self, qid: str) -> dict:
        self.assertIn(qid, self.genesis_questions, f"ID '{qid}' no encontrado en genesis-master-input.json")
        return copy.deepcopy(self.genesis_questions[qid])

    def get_exodus_question(self, qid: str) -> dict:
        self.assertIn(qid, self.exodus_questions, f"ID '{qid}' no encontrado en exodus-master-input.json")
        return copy.deepcopy(self.exodus_questions[qid])

    def get_leviticus_question(self, qid: str) -> dict:
        self.assertIn(qid, self.leviticus_questions, f"ID '{qid}' no encontrado en leviticus-master-input.json")
        return copy.deepcopy(self.leviticus_questions[qid])

    def get_numbers_question(self, qid: str) -> dict:
        self.assertIn(qid, self.numbers_questions, f"ID '{qid}' no encontrado en numbers-master-input.json")
        return copy.deepcopy(self.numbers_questions[qid])

    def get_deuteronomy_question(self, qid: str) -> dict:
        self.assertIn(qid, self.deuteronomy_questions, f"ID '{qid}' no encontrado en deuteronomy-master-input.json")
        return copy.deepcopy(self.deuteronomy_questions[qid])

    def get_joshua_question(self, qid: str) -> dict:
        self.assertIn(qid, self.joshua_questions, f"ID '{qid}' no encontrado en joshua-master-input.json")
        return copy.deepcopy(self.joshua_questions[qid])

    def get_judges_question(self, qid: str) -> dict:
        self.assertIn(qid, self.judges_questions, f"ID '{qid}' no encontrado en judges-master-input.json")
        return copy.deepcopy(self.judges_questions[qid])

    def get_ruth_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ruth_questions, f"ID '{qid}' no encontrado en ruth-master-input.json")
        return copy.deepcopy(self.ruth_questions[qid])

    def get_1samuel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.samuel1_questions, f"ID '{qid}' no encontrado en 1samuel-master-input.json")
        return copy.deepcopy(self.samuel1_questions[qid])

    def get_2samuel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.samuel2_questions, f"ID '{qid}' no encontrado en 2samuel-master-input.json")
        return copy.deepcopy(self.samuel2_questions[qid])

    def get_1kings_question(self, qid: str) -> dict:
        self.assertIn(qid, self.kings1_questions, f"ID '{qid}' no encontrado en 1kings-master-input.json")
        return copy.deepcopy(self.kings1_questions[qid])

    def get_2kings_question(self, qid: str) -> dict:
        self.assertIn(qid, self.kings2_questions, f"ID '{qid}' no encontrado en 2kings-master-input.json")
        return copy.deepcopy(self.kings2_questions[qid])

    def get_1chronicles_question(self, qid: str) -> dict:
        self.assertIn(qid, self.chronicles1_questions, f"ID '{qid}' no encontrado en 1chronicles-master-input.json")
        return copy.deepcopy(self.chronicles1_questions[qid])

    def get_2chronicles_question(self, qid: str) -> dict:
        self.assertIn(qid, self.chronicles2_questions, f"ID '{qid}' no encontrado en 2chronicles-master-input.json")
        return copy.deepcopy(self.chronicles2_questions[qid])

    def get_ezra_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ezra_questions, f"ID '{qid}' no encontrado en ezra-master-input.json")
        return copy.deepcopy(self.ezra_questions[qid])

    def get_nehemiah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.nehemiah_questions, f"ID '{qid}' no encontrado en nehemiah-master-input.json")
        return copy.deepcopy(self.nehemiah_questions[qid])

    def get_esther_question(self, qid: str) -> dict:
        self.assertIn(qid, self.esther_questions, f"ID '{qid}' no encontrado en esther-master-input.json")
        return copy.deepcopy(self.esther_questions[qid])

    def get_job_question(self, qid: str) -> dict:
        self.assertIn(qid, self.job_questions, f"ID '{qid}' no encontrado en job-master-input.json")
        return copy.deepcopy(self.job_questions[qid])

    def get_psalms_question(self, qid: str) -> dict:
        self.assertIn(qid, self.psalms_questions, f"ID '{qid}' no encontrado en psalms-master-input.json")
        return copy.deepcopy(self.psalms_questions[qid])

    def get_proverbs_question(self, qid: str) -> dict:
        self.assertIn(qid, self.proverbs_questions, f"ID '{qid}' no encontrado en proverbs-master-input.json")
        return copy.deepcopy(self.proverbs_questions[qid])

    def get_ecclesiastes_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ecclesiastes_questions, f"ID '{qid}' no encontrado en ecclesiastes-master-input.json")
        return copy.deepcopy(self.ecclesiastes_questions[qid])

    def get_song_of_songs_question(self, qid: str) -> dict:
        self.assertIn(qid, self.song_of_songs_questions, f"ID '{qid}' no encontrado en song-of-songs-master-input.json")
        return copy.deepcopy(self.song_of_songs_questions[qid])

    def get_isaiah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.isaiah_questions, f"ID '{qid}' no encontrado en isaiah-master-input.json")
        return copy.deepcopy(self.isaiah_questions[qid])

    def get_jeremiah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.jeremiah_questions, f"ID '{qid}' no encontrado en jeremiah-master-input.json")
        return copy.deepcopy(self.jeremiah_questions[qid])

    def get_lamentations_question(self, qid: str) -> dict:
        self.assertIn(qid, self.lamentations_questions, f"ID '{qid}' no encontrado en lamentations-master-input.json")
        return copy.deepcopy(self.lamentations_questions[qid])

    def get_ezekiel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ezekiel_questions, f"ID '{qid}' no encontrado en ezekiel-master-input.json")
        return copy.deepcopy(self.ezekiel_questions[qid])

    def get_daniel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.daniel_questions, f"ID '{qid}' no encontrado en daniel-master-input.json")
        return copy.deepcopy(self.daniel_questions[qid])

    def get_hosea_question(self, qid: str) -> dict:
        self.assertIn(qid, self.hosea_questions, f"ID '{qid}' no encontrado en hosea-master-input.json")
        return copy.deepcopy(self.hosea_questions[qid])

    def get_joel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.joel_questions, f"ID '{qid}' no encontrado en joel-master-input.json")
        return copy.deepcopy(self.joel_questions[qid])

    def get_amos_question(self, qid: str) -> dict:
        self.assertIn(qid, self.amos_questions, f"ID '{qid}' no encontrado en amos-master-input.json")
        return copy.deepcopy(self.amos_questions[qid])

    def get_obadiah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.obadiah_questions, f"ID '{qid}' no encontrado en obadiah-master-input.json")
        return copy.deepcopy(self.obadiah_questions[qid])

    def get_jonah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.jonah_questions, f"ID '{qid}' no encontrado en jonah-master-input.json")
        return copy.deepcopy(self.jonah_questions[qid])

    def get_micah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.micah_questions, f"ID '{qid}' no encontrado en micah-master-input.json")
        return copy.deepcopy(self.micah_questions[qid])

    def get_nahum_question(self, qid: str) -> dict:
        self.assertIn(qid, self.nahum_questions, f"ID '{qid}' no encontrado en nahum-master-input.json")
        return copy.deepcopy(self.nahum_questions[qid])

    def get_habakkuk_question(self, qid: str) -> dict:
        self.assertIn(qid, self.habakkuk_questions, f"ID '{qid}' no encontrado en habakkuk-master-input.json")
        return copy.deepcopy(self.habakkuk_questions[qid])

    def get_zephaniah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.zephaniah_questions, f"ID '{qid}' no encontrado en zephaniah-master-input.json")
        return copy.deepcopy(self.zephaniah_questions[qid])

    def get_haggai_question(self, qid: str) -> dict:
        self.assertIn(qid, self.haggai_questions, f"ID '{qid}' no encontrado en haggai-master-input.json")
        return copy.deepcopy(self.haggai_questions[qid])

    def get_zechariah_question(self, qid: str) -> dict:
        self.assertIn(qid, self.zechariah_questions, f"ID '{qid}' no encontrado en zechariah-master-input.json")
        return copy.deepcopy(self.zechariah_questions[qid])

    def get_malachi_question(self, qid: str) -> dict:
        self.assertIn(qid, self.malachi_questions, f"ID '{qid}' no encontrado en malachi-master-input.json")
        return copy.deepcopy(self.malachi_questions[qid])

    # --- TEST GLOBAL DE CONSISTENCIA DE IDs Y REFERENCIAS ---

    def test_global_canonical_id_reference_integrity_genesis(self) -> None:
        """Verifica consistencia de IDs y referencias en Génesis."""
        for qid, q in self.genesis_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_exodus(self) -> None:
        """Verifica consistencia de IDs y referencias en Éxodo."""
        if not self.exodus_questions:
            self.skipTest("exodus-master-input.json no disponible")
        for qid, q in self.exodus_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_leviticus(self) -> None:
        """Verifica consistencia de IDs y referencias en Levítico."""
        if not self.leviticus_questions:
            self.skipTest("leviticus-master-input.json no disponible")
        for qid, q in self.leviticus_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_numbers(self) -> None:
        """Verifica consistencia de IDs y referencias en Números."""
        if not self.numbers_questions:
            self.skipTest("numbers-master-input.json no disponible")
        for qid, q in self.numbers_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_deuteronomy(self) -> None:
        """Verifica consistencia de IDs y referencias en Deuteronomio."""
        if not self.deuteronomy_questions:
            self.skipTest("deuteronomy-master-input.json no disponible")
        for qid, q in self.deuteronomy_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_joshua(self) -> None:
        """Verifica consistencia de IDs y referencias en Josué."""
        if not self.joshua_questions:
            self.skipTest("joshua-master-input.json no disponible")
        for qid, q in self.joshua_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_judges(self) -> None:
        """Verifica consistencia de IDs y referencias en Jueces si el archivo está presente."""
        if not self.judges_questions:
            self.skipTest("judges-master-input.json aún no presente")
        for qid, q in self.judges_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_ruth(self) -> None:
        """Verifica consistencia de IDs y referencias en Rut."""
        if not self.ruth_questions:
            self.skipTest("ruth-master-input.json aún no presente")
        self.assertEqual(len(self.ruth_questions), 40)
        for qid, q in self.ruth_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_1samuel(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Samuel."""
        if not self.samuel1_questions:
            self.skipTest("1samuel-master-input.json aún no presente")
        self.assertEqual(len(self.samuel1_questions), 100)
        for qid, q in self.samuel1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_2samuel(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Samuel."""
        if not self.samuel2_questions:
            self.skipTest("2samuel-master-input.json aún no presente")
        self.assertEqual(len(self.samuel2_questions), 84)
        for qid, q in self.samuel2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_1kings(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Reyes."""
        if not self.kings1_questions:
            self.skipTest("1kings-master-input.json aún no presente")
        self.assertEqual(len(self.kings1_questions), 100)
        for qid, q in self.kings1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_2kings(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Reyes."""
        if not self.kings2_questions:
            self.skipTest("2kings-master-input.json aún no presente")
        self.assertEqual(len(self.kings2_questions), 104)
        for qid, q in self.kings2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_1chronicles(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Crónicas."""
        if not self.chronicles1_questions:
            self.skipTest("1chronicles-master-input.json aún no presente")
        self.assertEqual(len(self.chronicles1_questions), 80)
        for qid, q in self.chronicles1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_2chronicles(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Crónicas."""
        if not self.chronicles2_questions:
            self.skipTest("2chronicles-master-input.json aún no presente")
        self.assertEqual(len(self.chronicles2_questions), 102)
        for qid, q in self.chronicles2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_numbers_book_detection(self) -> None:
        """Verifica detección de configuración de Números."""
        if not self.numbers_questions:
            self.skipTest("numbers-master-input.json no disponible")
        book_key = detect_book_key(list(self.numbers_questions.values()))
        self.assertEqual(book_key, "numeros")

    def test_deuteronomy_book_detection(self) -> None:
        """Verifica detección de configuración de Deuteronomio."""
        if not self.deuteronomy_questions:
            self.skipTest("deuteronomy-master-input.json no disponible")
        book_key = detect_book_key(list(self.deuteronomy_questions.values()))
        self.assertEqual(book_key, "deuteronomio")

    def test_joshua_book_detection(self) -> None:
        """Verifica detección de configuración de Josué."""
        if not self.joshua_questions:
            self.skipTest("joshua-master-input.json no disponible")
        book_key = detect_book_key(list(self.joshua_questions.values()))
        self.assertEqual(book_key, "josue")

    def test_judges_book_detection(self) -> None:
        """Verifica detección de configuración de Jueces."""
        sample_q = [{"id": "NQB-AT-JUE-0001", "book": "Jueces", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "jueces")

    def test_ruth_book_detection(self) -> None:
        """Verifica detección de configuración de Rut."""
        sample_q = [{"id": "NQB-AT-RUT-0001", "book": "Rut", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "rut")
        self.assertEqual(BOOK_CONFIGS["rut"]["total_chapters"], 4)
        self.assertIn("ruth", BOOK_CONFIGS["rut"]["aliases"])

    def test_1samuel_book_detection(self) -> None:
        """Verifica detección de configuración de 1 Samuel."""
        sample_q = [{"id": "NQB-AT-1SA-0001", "book": "1 Samuel", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "1samuel")
        self.assertEqual(BOOK_CONFIGS["1samuel"]["total_chapters"], 31)
        self.assertIn("1 samuel", BOOK_CONFIGS["1samuel"]["aliases"])

    def test_2samuel_book_detection(self) -> None:
        """Verifica detección de configuración de 2 Samuel."""
        sample_q = [{"id": "NQB-AT-2SA-0001", "book": "2 Samuel", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "2samuel")
        self.assertEqual(BOOK_CONFIGS["2samuel"]["total_chapters"], 24)
        self.assertIn("2 samuel", BOOK_CONFIGS["2samuel"]["aliases"])

    def test_1kings_book_detection(self) -> None:
        """Verifica detección de configuración de 1 Reyes."""
        sample_q = [{"id": "NQB-AT-1RE-0001", "book": "1 Reyes", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "1kings")
        self.assertEqual(BOOK_CONFIGS["1kings"]["total_chapters"], 22)
        self.assertIn("1 reyes", BOOK_CONFIGS["1kings"]["aliases"])

    def test_2kings_book_detection(self) -> None:
        """Verifica detección de configuración de 2 Reyes."""
        sample_q = [{"id": "NQB-AT-2RE-0001", "book": "2 Reyes", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "2kings")
        self.assertEqual(BOOK_CONFIGS["2kings"]["total_chapters"], 25)
        self.assertIn("2 reyes", BOOK_CONFIGS["2kings"]["aliases"])

    def test_1chronicles_book_detection(self) -> None:
        """Verifica detección de configuración de 1 Crónicas."""
        sample_q = [{"id": "NQB-AT-1CR-0001", "book": "1 Crónicas", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "1chronicles")
        self.assertEqual(BOOK_CONFIGS["1chronicles"]["total_chapters"], 29)
        self.assertIn("1 crónicas", BOOK_CONFIGS["1chronicles"]["aliases"])
        self.assertIn("1 cronicas", BOOK_CONFIGS["1chronicles"]["aliases"])
        self.assertIn("1chronicles", BOOK_CONFIGS["1chronicles"]["aliases"])

    def test_2chronicles_book_detection(self) -> None:
        """Verifica detección de configuración de 2 Crónicas."""
        sample_q = [{"id": "NQB-AT-2CR-0001", "book": "2 Crónicas", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "2chronicles")
        self.assertEqual(BOOK_CONFIGS["2chronicles"]["total_chapters"], 36)
        self.assertIn("2 crónicas", BOOK_CONFIGS["2chronicles"]["aliases"])
        self.assertIn("2 cronicas", BOOK_CONFIGS["2chronicles"]["aliases"])
        self.assertIn("2chronicles", BOOK_CONFIGS["2chronicles"]["aliases"])

    def test_joshua_0061_with_additional_reference(self) -> None:
        """NQB-AT-JOS-0061: Josué 20:9 con additional_references=['Números 35:15'] se evalúa correctamente."""
        q61 = self.get_joshua_question("NQB-AT-JOS-0061")
        self.assertEqual(q61["reference"], "Josué 20:9")
        v61 = {9: "Estas fueron las ciudades señaladas para todos los hijos de Israel, y para el extranjero que morase entre ellos, para que se acogiese a ellas cualquiera que hiriese a alguno de muerte por yerro, y no muriese a mano del vengador de la sangre, hasta que compareciese delante de la congregación."}
        res61 = evaluate_question(q61, v61, book_key="josue")
        self.assertEqual(res61["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res61["estado"], "VERIFICADO")

    # --- REGRESIONES DE ARTÍCULOS INDEFINIDOS UN / UNA Y FRACCIONES EN NÚMEROS ---

    def test_num_0009_una_quinta_parte_no_spurious_one(self) -> None:
        """NUM-0009: 'Una quinta parte adicional' reconoce quinta=5 sin número 1 espurio."""
        q9 = self.get_numbers_question("NQB-AT-NUM-0009")
        v9 = {7: "confesarán su pecado que cometieron, y compensarán su ofensa enteramente, y añadirán sobre ello la quinta parte, y lo darán a aquel contra quien pecaron."}
        res9 = evaluate_question(q9, v9, book_key="numeros")
        self.assertEqual(res9["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res9["estado"], "REQUIERE_CORRECCION")

        # Mutación negativa
        q9_neg = copy.deepcopy(q9)
        q9_neg["opcion_a"] = "Una tercera parte adicional"
        q9_neg["correct_answer"] = "Una tercera parte adicional"
        res9_neg = evaluate_question(q9_neg, v9, book_key="numeros")
        self.assertEqual(res9_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res9_neg["estado"], "REQUIERE_CORRECCION")

    def test_num_indefinite_articles_not_converted_to_numbers(self) -> None:
        """Verifica que 'un/una' como artículo indefinido no extraiga cantidad 1 (NUM-0095, NUM-0058, NUM-0064, NUM-0088)."""
        # NUM-0095: Tomó un incensario...
        q95 = self.get_numbers_question("NQB-AT-NUM-0095")
        v95 = {
            46: "Y dijo Moisés a Aarón: Toma el incensario, y pon en él fuego del altar...",
            47: "Entonces tomó Aarón el incensario, como Moisés dijo, y corrió en medio de la congregación...",
            48: "Y se puso entre los muertos y los vivos; y cesó la mortandad."
        }
        res95 = evaluate_question(q95, v95, book_key="numeros")
        self.assertEqual(res95["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res95["estado"], "REQUIERE_CORRECCION")

        # NUM-0058: Una estrella
        q58 = self.get_numbers_question("NQB-AT-NUM-0058")
        v58 = {17: "Lo veré, mas no ahora; lo miraré, mas no de cerca; saldrá estrella de Jacob, y se levantará cetro de Israel..."}
        res58 = evaluate_question(q58, v58, book_key="numeros")
        self.assertEqual(res58["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res58["estado"], "REQUIERE_CORRECCION")

        # NUM-0064: Recibir una propiedad...
        q64 = self.get_numbers_question("NQB-AT-NUM-0064")
        v64 = {
            1: "Vinieron las hijas de Zelofehad hijo de Hefer...",
            2: "y se presentaron delante de Moisés y delante del sacerdote Eleazar...",
            3: "Nuestro padre murió en el desierto...",
            4: "¿Por qué será quitado el nombre de nuestro padre de entre su familia, por no haber tenido hijo? Danos heredad entre los hermanos de nuestro padre."
        }
        res64 = evaluate_question(q64, v64, book_key="numeros")
        self.assertEqual(res64["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res64["estado"], "REQUIERE_CORRECCION")

        # NUM-0088: una muerte sin intención
        q88 = self.get_numbers_question("NQB-AT-NUM-0088")
        v88 = {
            11: "os señalaréis ciudades, ciudades de refugio tendréis, donde huya el homicida que hiriere a alguno de muerte sin intención.",
            12: "Y os serán aquellas ciudades por refugio del vengador, y no morirá el homicida hasta que entre en juicio delante de la congregación."
        }
        res88 = evaluate_question(q88, v88, book_key="numeros")
        self.assertEqual(res88["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res88["estado"], "REQUIERE_CORRECCION")

    def test_explicit_counting_un_cordero(self) -> None:
        """En preguntas cuantitativas explícitas, 'Un cordero' sí debe extraer 1."""
        nums = extract_numbers("Un cordero", is_quantitative_context=True)
        self.assertIn(1, nums)

    # --- REGRESIONES ESPECÍFICAS DE DEUTERONOMIO ---

    def test_deu_0003_comparative_father_son_metaphor(self) -> None:
        """DEU-0003: 'Como un padre que lleva a su hijo' frente a 'como trae el hombre a su hijo' en Deuteronomio 1:31."""
        q3 = self.get_deuteronomy_question("NQB-AT-DEU-0003")
        v3 = {31: "Y en el desierto has visto que Jehová tu Dios te ha traído, como trae el hombre a su hijo, por todo el camino que habéis andado, hasta llegar a este lugar."}
        res3 = evaluate_question(q3, v3, book_key="deuteronomio")
        self.assertEqual(res3["controles_superados"]["control_relaciones_personajes"], "PASS")
        self.assertEqual(res3["estado"], "VERIFICADO")

    def test_literal_kinship_missing_produces_fail(self) -> None:
        """Pregunta de parentesco literal sin respaldo en el pasaje produce FAIL en control_relaciones_personajes."""
        q_literal = {
            "id": "TEST-KINSHIP-LITERAL",
            "book": "Deuteronomio",
            "chapter": 1,
            "verse_start": 38,
            "verse_end": 38,
            "reference": "Deuteronomio 1:38",
            "question": "¿Qué parentesco tenía Nun respecto de Josué según el texto?",
            "opcion_a": "Era el padre de Josué",
            "opcion_b": "Era el tío",
            "opcion_c": "Era el hermano",
            "opcion_d": "Era el abuelo",
            "correct_option": "A",
            "correct_answer": "Era el padre de Josué",
            "explanation": "Nun era el padre de Josué...",
            "characters": ["Josué", "Nun"],
            "difficulty": "Básico",
            "category": "PERSONAJES_BIBLICOS",
        }
        # 1. Pasaje con 'padre' explícito -> PASS
        v_pass = {38: "Josué hijo de Nun, y su padre Nun le enseñó..."}
        res_pass = evaluate_question(q_literal, v_pass, book_key="deuteronomio")
        self.assertEqual(res_pass["controles_superados"]["control_relaciones_personajes"], "PASS")

        # 2. Pasaje sin 'padre' -> FAIL
        v_fail = {38: "Josué, el cual te sirve, él entrará allá; anímale, porque él la hará heredar a Israel."}
        res_fail = evaluate_question(q_literal, v_fail, book_key="deuteronomio")
        self.assertEqual(res_fail["controles_superados"]["control_relaciones_personajes"], "FAIL")

    def test_deu_0060_action_measure_no_spurious_one(self) -> None:
        """DEU-0060: '¿Qué medida de seguridad...?' con 'Construir una protección...' no extrae 1 espurio."""
        q60 = self.get_deuteronomy_question("NQB-AT-DEU-0060")
        v60 = {8: "Cuando edifiques casa nueva, harás pretil a tu terrado, para que no pongas culpa de sangre sobre tu casa, si de él cayere alguno."}
        res60 = evaluate_question(q60, v60, book_key="deuteronomio")
        self.assertEqual(res60["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertEqual(res60["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res60["estado"], "VERIFICADO")

    def test_explicit_quant_context_evaluations(self) -> None:
        """Verifica que preguntas con '¿Cuántas...?' y '¿Cuánto debía medir...?' evalúen cantidades correctamente."""
        # Cuántas -> extrae 1
        nums_cuantas = extract_numbers("Una", is_quantitative_context=True)
        self.assertEqual(nums_cuantas, [1])

        # Medida de seguridad (cualitativo) -> no extrae 1
        nums_cual = extract_numbers("Construir una protección", is_quantitative_context=False)
        self.assertEqual(nums_cual, [])

    # --- REGRESIONES ESPECÍFICAS DE NÚMEROS (SIN, MIRIAM, SIHÓN, 601730, MITADES) ---

    def test_num_sin_preposition_not_detected_as_place(self) -> None:
        """Verifica que la preposición 'sin' no se detecte como topónimo (NUM-0012, NUM-0041, NUM-0073)."""
        # NUM-0012: sin pasar navaja
        q12 = self.get_numbers_question("NQB-AT-NUM-0012")
        v12 = {5: "Todos los días del voto de su nazareato no pasará navaja sobre su cabeza; hasta que sean cumplidos los días... dejará crecer su cabello."}
        res12 = evaluate_question(q12, v12, book_key="numeros")
        self.assertNotEqual(res12["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res12["estado"], "VERIFICADO")

        # NUM-0041: sin defecto
        q41 = self.get_numbers_question("NQB-AT-NUM-0041")
        v41 = {2: "Esta es la ordenanza de la ley... una vaca alazana, perfecta, en la cual no haya falta, sobre la cual no se haya puesto yugo;"}
        res41 = evaluate_question(q41, v41, book_key="numeros")
        self.assertNotEqual(res41["controles_superados"]["control_lugares"], "FAIL")
        self.assertNotEqual(res41["estado"], "REQUIERE_CORRECCION")

        # NUM-0073: sin efecto
        q73 = self.get_numbers_question("NQB-AT-NUM-0073")
        v73 = {
            3: "Mas la mujer, cuando hiciere voto a Jehová...",
            4: "si su padre oyere su voto... todos los votos de ella serán firmes...",
            5: "Mas si su padre le vedare el día que oyere... no serán firmes;"
        }
        res73 = evaluate_question(q73, v73, book_key="numeros")
        self.assertNotEqual(res73["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res73["estado"], "VERIFICADO")

    def test_num_miriam_maria_equivalence(self) -> None:
        """Verifica equivalencia Miriam ↔ María en RVR1960 (NUM-0026, NUM-0027, NUM-0044)."""
        q26 = self.get_numbers_question("NQB-AT-NUM-0026")
        v26 = {
            1: "María y Aarón hablaron contra Moisés a causa de la mujer cusita que había tomado...",
            2: "Y dijeron: ¿Solamente por Moisés ha hablado Jehová? ¿No ha hablado también por nosotros? Y lo oyó Jehová."
        }
        res26 = evaluate_question(q26, v26, book_key="numeros")
        self.assertEqual(res26["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res26["estado"], "REQUIERE_CORRECCION")

        q27 = self.get_numbers_question("NQB-AT-NUM-0027")
        v27 = {10: "Y la nube se apartó del tabernáculo, y he aquí que María estaba leprosa como la nieve; y miró Aarón a María, y he aquí que estaba leprosa."}
        res27 = evaluate_question(q27, v27, book_key="numeros")
        self.assertEqual(res27["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res27["estado"], "REQUIERE_CORRECCION")

        q44 = self.get_numbers_question("NQB-AT-NUM-0044")
        v44 = {1: "Llegaron los hijos de Israel, toda la congregación, al desierto de Zin, en el mes primero, y acampó el pueblo en Cades; y allí murió María, y allí fue sepultada."}
        res44 = evaluate_question(q44, v44, book_key="numeros")
        self.assertEqual(res44["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res44["estado"], "VERIFICADO")

    def test_num_sihon_sehon_equivalence(self) -> None:
        """Verifica equivalencia Sihón ↔ Sehón (NUM-0051)."""
        q51 = self.get_numbers_question("NQB-AT-NUM-0051")
        v51 = {
            21: "Entonces envió Israel embajadores a Sehón rey de los amorreos, diciendo:",
            22: "Pasaré por tu tierra...",
            23: "Mas Sehón no dejó pasar a Israel...",
            24: "E Israel lo hirió a filo de espada, y tomó su tierra..."
        }
        res51 = evaluate_question(q51, v51, book_key="numeros")
        self.assertEqual(res51["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res51["estado"], "VERIFICADO")

    def test_num_compound_number_601730(self) -> None:
        """Verifica parsing de 601 730 (NUM-0062) y mutación negativa."""
        q62 = self.get_numbers_question("NQB-AT-NUM-0062")
        v62 = {51: "Estos son los contados de los hijos de Israel, seiscientos un mil setecientos treinta."}
        res62 = evaluate_question(q62, v62, book_key="numeros")
        self.assertEqual(res62["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res62["estado"], "REQUIERE_CORRECCION")

        # Mutación negativa
        q62_neg = copy.deepcopy(q62)
        q62_neg["opcion_a"] = "603 550"
        q62_neg["correct_answer"] = "603 550"
        res62_neg = evaluate_question(q62_neg, v62, book_key="numeros")
        self.assertEqual(res62_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res62_neg["estado"], "REQUIERE_CORRECCION")

    def test_num_division_dos_partes_mitad(self) -> None:
        """Verifica 'En dos partes' vs 'partir por mitad' (NUM-0076) y mutación negativa."""
        q76 = self.get_numbers_question("NQB-AT-NUM-0076")
        v76 = {
            25: "Y Jehová habló a Moisés, diciendo:",
            26: "Toma la cuenta del botín que se ha hecho...",
            27: "Y partirás por mitad el botín entre los que pelearon, los que salieron a la guerra, y toda la congregación."
        }
        res76 = evaluate_question(q76, v76, book_key="numeros")
        self.assertEqual(res76["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res76["estado"], "VERIFICADO")

        # Mutación negativa
        q76_neg = copy.deepcopy(q76)
        q76_neg["opcion_a"] = "En tres partes iguales"
        q76_neg["correct_answer"] = "En tres partes iguales"
        res76_neg = evaluate_question(q76_neg, v76, book_key="numeros")
        self.assertEqual(res76_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res76_neg["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0079: LA DÉCIMA PARTE Y DIEZMO DE LA TIERRA EN LEVÍTICO 27:30 ---

    def test_positive_lev_0079_decima_parte_tithe(self) -> None:
        """NQB-AT-LEV-0079: 'La décima parte' respalda el diezmo de la tierra."""
        q = self.get_leviticus_question("NQB-AT-LEV-0079")
        self.assertEqual(q["reference"], "Levítico 27:30")
        self.assertEqual(q["opcion_a"], "La décima parte")
        verse_map = {
            30: "Y el diezmo de la tierra, así de la simiente de la tierra como del fruto de los árboles, de Jehová es; es cosa dedicada a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_lev_0079_contradictory_fraction(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0079: 'La quinta parte' produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0079")
        q["opcion_a"] = "La quinta parte"
        q["correct_answer"] = "La quinta parte"
        verse_map = {
            30: "Y el diezmo de la tierra, así de la simiente de la tierra como del fruto de los árboles, de Jehová es; es cosa dedicada a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0080: CADA DÉCIMO ANIMAL Y DIEZMO EN LEVÍTICO 27:32 ---

    def test_positive_lev_0080_decimo_animal_tithe(self) -> None:
        """NQB-AT-LEV-0080: 'Cada décimo animal' respalda el diezmo del ganado bajo la vara."""
        q = self.get_leviticus_question("NQB-AT-LEV-0080")
        self.assertEqual(q["reference"], "Levítico 27:32")
        self.assertEqual(q["opcion_a"], "Cada décimo animal")
        verse_map = {
            32: "Y todo diezmo de vacas o de ovejas, de todo lo que pasa bajo la vara, el diezmo será consagrado a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_lev_0080_contradictory_number(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0080: 'Cada séptimo animal' produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0080")
        q["opcion_a"] = "Cada séptimo animal"
        q["correct_answer"] = "Cada séptimo animal"
        verse_map = {
            32: "Y todo diezmo de vacas o de ovejas, de todo lo que pasa bajo la vara, el diezmo será consagrado a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_non_quantitative_diezmo_does_not_extract_10_blindly(self) -> None:
        """Mención no cuantitativa de 'diezmo' sin conteo/fracción no produce número 10."""
        text_non_quant = "Y el diezmo de la tierra de Jehová es santificado."
        nums = extract_numbers(text_non_quant, is_quantitative_context=False)
        self.assertNotIn(10, nums)

    # --- CASO NQB-AT-LEV-0019: LEVÍTICO 8:12 Y REFERENCIA ADICIONAL LEVÍTICO 8:10 ---

    def test_lev_0019_without_and_with_additional_reference(self) -> None:
        """NQB-AT-LEV-0019: 8:12 aislado produce REQUIERE_CORRECCION; con 8:10 valida a Moisés."""
        q = self.get_leviticus_question("NQB-AT-LEV-0019")
        self.assertEqual(q["reference"], "Levítico 8:12")
        self.assertEqual(q["opcion_a"], "Moisés")

        # 1. Rango aislado 8:12 -> Falta el sujeto Moisés (FAIL)
        v12_only = {12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo."}
        q_isolated = copy.deepcopy(q)
        q_isolated["additional_references"] = []
        res_without = evaluate_question(q_isolated, v12_only, book_key="levitico")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res_without["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res_without["controles_superados"]["control_rango_suficiente"], "FAIL")

        # 2. Con additional_references=["Levítico 8:10"] -> Moisés presente en v10 (PASS)
        v_with_10 = {
            10: "Y tomó Moisés el aceite de la unción y ungió el tabernáculo, y todas las cosas que estaban en él, y las santificó.",
            12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo.",
        }
        res_with = evaluate_question(q, v_with_10, book_key="levitico")
        self.assertEqual(res_with["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res_with["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res_with["estado"], "VERIFICADO")

    # --- CASO NQB-AT-LEV-0038: CONSTRUCCIÓN DISTRIBUTIVA EN LEVÍTICO 16:8-10 ---

    def test_positive_lev_0038_distributive_uno_otro(self) -> None:
        """NQB-AT-LEV-0038: 'Uno para Dios y otro para Azazel' no extrae número 1 contradictorio."""
        q = self.get_leviticus_question("NQB-AT-LEV-0038")
        self.assertEqual(q["reference"], "Levítico 16:8-10")
        verse_map = {
            8: "Y echará suertes Aarón sobre los dos machos cabríos; una suerte por Jehová, y otra suerte por Azazel.",
            9: "Y hará traer Aarón el macho cabrío sobre el cual cayere la suerte por Jehová, y lo ofrecerá en expiación.",
            10: "Mas el macho cabrío sobre el cual cayere la suerte por Azazel, lo presentará vivo delante de Jehová...",
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_negative_lev_0038_contradictory_number(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0038: cantidad explícita contradictoria produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0038")
        q["opcion_a"] = "Cinco machos cabríos para Jehová y tres para Azazel"
        q["correct_answer"] = "Cinco machos cabríos para Jehová y tres para Azazel"
        verse_map = {
            8: "Y echará suertes Aarón sobre los dos machos cabríos; una suerte por Jehová, y otra suerte por Azazel.",
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0065: PERÍODO DESCRIPTIVO EN LEVÍTICO 25:4 ---

    def test_positive_lev_0065_qualitative_period(self) -> None:
        """NQB-AT-LEV-0065: 'un año de reposo' no genera contradicción cuantitativa contra 7."""
        q = self.get_leviticus_question("NQB-AT-LEV-0065")
        self.assertEqual(q["reference"], "Levítico 25:4")
        verse_map = {
            4: "pero el séptimo año la tierra tendrá reposo, sábado de reposo para Jehová; no sembrarás tu tierra, ni podarás tu viña."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertNotEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_negative_lev_0065_contradictory_period(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0065: cifra errónea explícita (diez años de reposo)."""
        q = self.get_leviticus_question("NQB-AT-LEV-0065")
        q["opcion_a"] = "Debía tener diez años de reposo"
        q["correct_answer"] = "Debía tener diez años de reposo"
        verse_map = {
            4: "pero el séptimo año la tierra tendrá reposo, sábado de reposo para Jehová..."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASOS ÉXODO (NILO, EGIPTO, CANTIDADES) ---

    def test_positive_exo_0003_nilo_rio_equivalence(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0003")
        verse_map = {22: "Entonces Faraón mandó a todo su pueblo, diciendo: Echad en el río a todo hijo que nazca, y a toda hija preservad la vida."}
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_exo_0027_ambient_place_egypt(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0027")
        verse_map = {
            24: "Entonces Faraón hizo llamar a Moisés, y dijo: Id, servid a Jehová; solamente queden vuestras ovejas y vuestras vacas; vayan también vuestros niños con vosotros.",
            25: "Y Moisés respondió: Tú también nos darás sacrificios y holocaustos que sacrifiquemos para Jehová nuestro Dios.",
            26: "Nuestros ganados irán también con nosotros; no quedará ni una pezuña...",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_exo_0074_compound_numbers_dos_uno(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0074")
        verse_map = {
            38: "Esto es lo que ofrecerás sobre el altar: dos corderos de un año cada día, continuamente.",
            39: "Ofrecerás uno de los corderos por la mañana, y el otro cordero ofrecerás a la caída de la tarde.",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    # --- REGRESIÓN ESPECÍFICA NQB-AT-GEN-0110 (Génesis 44:33-34 y 44:18) ---

    def test_regression_nqb_0110_without_and_with_additional_ref(self) -> None:
        q_canonical = self.get_genesis_question("NQB-AT-GEN-0110")
        q_without = copy.deepcopy(q_canonical)
        q_without["additional_references"] = []
        verse_map_33_34 = {
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_without = evaluate_question(q_without, verse_map_33_34, book_key="genesis")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")

        verse_map_with_18 = {
            18: "Entonces Judá se acercó a él, y dijo: ¡Ay, señor mío! te ruego que permitas que hable tu siervo una palabra en oídos de mi señor...",
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_with = evaluate_question(q_canonical, verse_map_with_18, book_key="genesis")
        self.assertEqual(res_with["estado"], "VERIFICADO")

    # --- PRUEBAS DE NORMALIZACIÓN MORFOLÓGICA Y SINONIMIA BÍBLICA ---

    def test_token_matches_text_morphological_and_synonyms(self) -> None:
        """Verifica concordancia singular/plural y sinónimos bíblicos genéricos."""
        self.assertTrue(token_matches_text("extranjeros", "morase extranjero entre ellos"))
        self.assertTrue(token_matches_text("ciudades", "ciudad de refugio"))
        self.assertTrue(token_matches_text("otoniel", "otniel tomo quiriat-sefer"))
        self.assertTrue(token_matches_text("sorteada", "repartieron por suerte"))
        self.assertTrue(token_matches_text("combatir", "fueron a pelear contra ellos"))

    def test_joshua_cases_semantic_resolution(self) -> None:
        """Verifica resolución semántica de preguntas representativas de Josué."""
        # NQB-AT-JOS-0046: Otoniel
        q46 = self.get_joshua_question("NQB-AT-JOS-0046")
        v46 = {
            16: "Y dijo Caleb: Al que atacare a Quiriat-sefer, y la tomare, yo le daré a Acsa mi hija por mujer.",
            17: "Y la tomó Otoniel, hijo de Cenaz hermano de Caleb; y él le dio a Acsa su hija por mujer.",
        }
    # --- PRUEBAS DE REGRESIÓN DE JUECES Y GENTILICIOS BÍBLICOS ---

    def test_benjamita_benjamin_demonyms(self) -> None:
        """Verifica equivalencia genérica entre gentilicios bíblicos y nombres de tribus/lugares."""
        self.assertTrue(token_matches_text("benjamin", "aod hijo de gera benjamita"))
        self.assertTrue(token_matches_text("benjamita", "tribu de benjamin"))
        self.assertTrue(token_matches_text("efrain", "monte de los efraimitas"))
        self.assertTrue(token_matches_text("galaad", "jefte galaadita"))
        self.assertTrue(token_matches_text("dan", "familia de los danitas"))

    def test_ordinal_sequence_vs_quantitative(self) -> None:
        """Verifica que 'primero' discursivo/secuencial no genere conteo numérico falso."""
        nums_seq = extract_numbers("Primero que el vellón quedara mojado", is_quantitative_context=False)
        self.assertEqual(nums_seq, [])

        nums_seq2 = extract_numbers("a quien saliera primero de su casa", is_quantitative_context=False)
        self.assertEqual(nums_seq2, [])

        nums_quant = extract_numbers("el séptimo año la tierra tendrá reposo", is_quantitative_context=False)
        self.assertEqual(nums_quant, [7])

        nums_frac = extract_numbers("la décima parte", is_quantitative_context=True)
        self.assertEqual(nums_frac, [10])

    def test_judges_regression_four_cases(self) -> None:
        """Verifica resolución limpia sin FAIL en NQB-AT-JUE-0008, 0020, 0028 y 0094."""
        # JUE-0008: Aod benjamita vs tribu de Benjamín
        q8 = self.get_judges_question("NQB-AT-JUE-0008")
        v8 = {15: "Y clamaron los hijos de Israel a Jehová; y Jehová les levantó un libertador, a Aod hijo de Gera, benjamita, el cual era zurdo..."}
        res8 = evaluate_question(q8, v8, book_key="jueces")
        self.assertNotEqual(res8["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res8["controles_superados"]["control_nombres_propios"], "PASS")

        # JUE-0020: Secuencia de señales de Gedeón
        q20 = self.get_judges_question("NQB-AT-JUE-0020")
        v20 = {
            36: "Y Gedeón dijo a Dios: Si has de salvar a Israel por mi mano, como has dicho,",
            37: "he aquí que yo pondré un vellón de lana en la era; y si el rocío estuviere en el vellón solamente, quedando seca toda la tierra, entonces entenderé que salvarás a Israel por mi mano, como has dicho.",
            38: "Y aconteció así...",
            39: "Mas Gedeón dijo a Dios... Te ruego que solamente el vellón quede seco, y el rocío sobre la tierra.",
            40: "Y aquella noche lo hizo Dios así; sólo el vellón quedó seco, y en toda la tierra hubo rocío."
        }
        res20 = evaluate_question(q20, v20, book_key="jueces")
        self.assertNotEqual(res20["estado"], "REQUIERE_CORRECCION")

        # JUE-0028: Refusal of bread by Succoth to Gideon's men
        q28 = self.get_judges_question("NQB-AT-JUE-0028")
        v28 = {6: "Y los principales de Sucot respondieron: ¿Están ya en tu mano las cabezas de Zeba y de Zalmuna, para que demos pan a tu ejército?"}
        res28 = evaluate_question(q28, v28, book_key="jueces")
        self.assertNotEqual(res28["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res28["controles_superados"]["control_nombres_propios"], "PASS")

        # JUE-0094: Voto de Jefté
        q94 = self.get_judges_question("NQB-AT-JUE-0094")
        v94 = {
            30: "Y Jefté hizo voto a Jehová, diciendo: Si entregares a los amonitas en mis manos,",
            31: "cualquiera que saliere de las puertas de mi casa a recibirme, cuando regrese victorioso de los amonitas, será de Jehová, y lo ofreceré en holocausto."
        }
        res94 = evaluate_question(q94, v94, book_key="jueces")
        self.assertNotEqual(res94["estado"], "REQUIERE_CORRECCION")

    def test_ruth_cases_representative(self) -> None:
        """Verifica evaluación de casos representativos de Rut (efa de cebada, seis medidas, diez ancianos, genealogía)."""
        # RUT-0012: Un efa de cebada (Rut 2:17)
        q12 = self.get_ruth_question("NQB-AT-RUT-0012")
        v12 = {17: "Espigó, pues, en el campo hasta la noche, y desgranó lo que había recogido, y fue como un efa de cebada."}
        res12 = evaluate_question(q12, v12, book_key="rut")
        self.assertNotEqual(res12["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res12["controles_superados"]["control_nombres_propios"], "PASS")

        # RUT-0018: Diez ancianos (Rut 4:1-2)
        q18 = self.get_ruth_question("NQB-AT-RUT-0018")
        v18 = {
            1: "Booz subió a la puerta y se sentó allí...",
            2: "Y él tomó diez varones de los ancianos de la ciudad, y dijo: Sentaos aquí. Y ellos se sentaron."
        }
        res18 = evaluate_question(q18, v18, book_key="rut")
        self.assertNotEqual(res18["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res18["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_ruth_anaphoric_resolution_rut_0011_and_0033(self) -> None:
        """Verifica que referencias anafóricas/relacionales (su suegra -> Noemí, aquel hombre -> Booz) se resuelvan sin FAIL."""
        # RUT-0011: Booz destaca conducta hacia 'su suegra' (Noemí) en Rut 2:10-12
        q11 = self.get_ruth_question("NQB-AT-RUT-0011")
        v11 = {
            2: "Y Rut la moabita dijo a Noemí: Te ruego que me dejes ir al campo...",
            10: "Ella bajando su rostro se inclinó a tierra...",
            11: "Y respondiendo Booz, le dijo: He sabido todo lo que has hecho con tu suegra después de la muerte de tu marido, y que dejando a tu padre y a tu madre y la tierra donde naciste, has venido a un pueblo que no conociste antes.",
            12: "Jehová recompense tu obra..."
        }
        res11 = evaluate_question(q11, v11, book_key="rut")
        self.assertEqual(res11["estado"], "VERIFICADO")
        self.assertEqual(res11["controles_superados"]["control_nombres_propios"], "PASS")

        # RUT-0033: 'aquel hombre' (Booz) en Rut 3:18
        q33 = self.get_ruth_question("NQB-AT-RUT-0033")
        v33 = {
            2: "¿No es Booz nuestro pariente...?",
            18: "Entonces Noemí dijo: Espérate, hija mía, hasta que sepas cómo se resuelve el caso; porque aquel hombre no descansará hasta que concluya el asunto hoy."
        }
        res33 = evaluate_question(q33, v33, book_key="rut")
        self.assertEqual(res33["estado"], "VERIFICADO")
        self.assertEqual(res33["controles_superados"]["control_nombres_propios"], "PASS")

    def test_anaphoric_character_contradiction_fail(self) -> None:
        """Verifica que un personaje objetivamente contradictorio sin vínculo anafórico genere FAIL."""
        q = self.get_ruth_question("NQB-AT-RUT-0033")
        q["opcion_a"] = "Porque estaba convencida de que Saúl no descansaría hasta resolverlo ese mismo día"
        q["correct_answer"] = q["opcion_a"]
        v33 = {
            18: "Entonces Noemí dijo: Espérate, hija mía, hasta que sepas cómo se resuelve el caso; porque aquel hombre no descansará hasta que concluya el asunto hoy."
        }
        res = evaluate_question(q, v33, book_key="rut")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_1samuel_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 1 Samuel (Ofni/Finees, 30.000, 5 tumores/ratones, 100/200 prepucios, etc.)."""
        # 1SA-0004: Ofni y Finees hijos de Elí (1 Samuel 1:3)
        q4 = self.get_1samuel_question("NQB-AT-1SA-0004")
        v4 = {3: "Y todos los años aquel varón subía de su ciudad para adorar y para ofrecer sacrificios a Jehová de los ejércitos en Silo, donde estaban dos hijos de Elí, Ofni y Finees, sacerdotes de Jehová."}
        res4 = evaluate_question(q4, v4, book_key="1samuel")
        self.assertNotEqual(res4["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res4["controles_superados"]["control_nombres_propios"], "PASS")

        # 1SA-0014: Treinta mil soldados (1 Samuel 4:10)
        q14 = self.get_1samuel_question("NQB-AT-1SA-0014")
        v14 = {10: "Pelearon, pues, los filisteos, e Israel fue vencido, y huyeron cada cual a sus tiendas; y fue hecha muy grande mortandad, pues cayeron de Israel treinta mil hombres de a pie."}
        res14 = evaluate_question(q14, v14, book_key="1samuel")
        self.assertNotEqual(res14["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res14["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0019: Cinco tumores y cinco ratones de oro (1 Samuel 6:4-5)
        q19 = self.get_1samuel_question("NQB-AT-1SA-0019")
        v19 = {
            4: "Y ellos dijeron: ¿Y qué será la expiación que le pagaremos? Ellos respondieron: Cinco tumores de oro, y cinco ratones de oro, conforme al número de los príncipes de los filisteos...",
            5: "Haréis, pues, figuras de vuestros tumores, y figuras de vuestros ratones que destruyen la tierra..."
        }
        res19 = evaluate_question(q19, v19, book_key="1samuel")
        self.assertNotEqual(res19["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res19["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0058: Cinco piedras lisas del arroyo (1 Samuel 17:40)
        q58 = self.get_1samuel_question("NQB-AT-1SA-0058")
        v58 = {40: "Y tomó su cayado en su mano, y escogió cinco piedras lisas del arroyo, y las puso en el saco pastoril..."}
        res58 = evaluate_question(q58, v58, book_key="1samuel")
        self.assertNotEqual(res58["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res58["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0098: Jonatán, Abinadab y Malquisúa (1 Samuel 31:2)
        q98 = self.get_1samuel_question("NQB-AT-1SA-0098")
        v98 = {2: "Y siguiendo los filisteos a Saúl y a sus hijos, mataron a Jonatán, a Abinadab y a Malquisúa, hijos de Saúl."}
        res98 = evaluate_question(q98, v98, book_key="1samuel")
        self.assertNotEqual(res98["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res98["controles_superados"]["control_nombres_propios"], "PASS")

    def test_2samuel_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 2 Samuel (amalecita, Is-boset, Mefi-boset, 30.000, 9 meses y 20 días)."""
        # 2SA-0002: Amalecita (2 Samuel 1:13)
        q2 = self.get_2samuel_question("NQB-AT-2SA-0002")
        v2 = {13: "Y dijo David a aquel joven que le había traído las nuevas: ¿De dónde eres tú? Y él respondió: Yo soy hijo de un extranjero, amalecita."}
        res2 = evaluate_question(q2, v2, book_key="2samuel")
        self.assertNotEqual(res2["estado"], "REQUIERE_CORRECCION")

        # 2SA-0007: Is-boset hijo de Saúl proclamado rey (2 Samuel 2:8-10)
        q7 = self.get_2samuel_question("NQB-AT-2SA-0007")
        v7 = {
            8: "Pero Abner hijo de Ner, general del ejército de Saúl, tomó a Is-boset hijo de Saúl, y lo llevó a Mahanaim,",
            9: "y lo hizo rey sobre Galaad...",
            10: "De cuarenta años era Is-boset hijo de Saúl cuando comenzó a reinar sobre Israel..."
        }
        res7 = evaluate_question(q7, v7, book_key="2samuel")
        self.assertNotEqual(res7["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res7["controles_superados"]["control_nombres_propios"], "PASS")

        # 2SA-0012: Mefi-boset hijo de Jonatán lisiado de los pies (2 Samuel 4:4)
        q12 = self.get_2samuel_question("NQB-AT-2SA-0012")
        v12 = {4: "Y Jonatán hijo de Saúl tenía un hijo lisiado de los pies. Tenía cinco años de edad cuando llegaron de Jezreel las noticias de la muerte de Saúl y de Jonatán... y quedó cojo. Su nombre era Mefi-boset."}
        res12 = evaluate_question(q12, v12, book_key="2samuel")
        self.assertNotEqual(res12["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res12["controles_superados"]["control_nombres_propios"], "PASS")

        # 2SA-0018: Treinta mil escogidos (2 Samuel 6:1)
        q18 = self.get_2samuel_question("NQB-AT-2SA-0018")
        v18 = {1: "David volvió a reunir a todos los escogidos de Israel, treinta mil."}
        res18 = evaluate_question(q18, v18, book_key="2samuel")
        self.assertNotEqual(res18["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res18["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2SA-0029: Ziba / Siba (2 Samuel 9:2-5)
        q29 = self.get_2samuel_question("NQB-AT-2SA-0029")
        v29 = {
            2: "Y había un siervo de la casa de Saúl, que se llamaba Siba, al cual llamaron para que viniese a David...",
            3: "Y el siervo respondió al rey: Aún queda un hijo de Jonatán, lisiado de los pies.",
            4: "Entonces dijo el rey: ¿Dónde está? Y Siba respondió al rey...",
            5: "Entonces envió el rey David, y le trajo de la casa de Maquir..."
        }
        res29 = evaluate_question(q29, v29, book_key="2samuel")
        self.assertNotEqual(res29["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res29["controles_superados"]["control_nombres_propios"], "PASS")

        # 2SA-0078: Nueve meses y veinte días (2 Samuel 24:8-9)
        q78 = self.get_2samuel_question("NQB-AT-2SA-0078")
        v78 = {
            8: "Después que hubieron recorrido toda la tierra, volvieron a Jerusalén al cabo de nueve meses y veinte días.",
            9: "Y Joab dio el número del censo del pueblo al rey..."
        }
        res78 = evaluate_question(q78, v78, book_key="2samuel")
        self.assertNotEqual(res78["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res78["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_1kings_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 1 Reyes (Hiram rey vs artesano, Jaquín y Boaz, 700/300 mujeres, Hazael/Jehú/Eliseo, 7000)."""
        # 1RE-0020: Hiram rey de Tiro (1 Reyes 5:1-12)
        q20 = self.get_1kings_question("NQB-AT-1RE-0020")
        v20 = {i: "..." for i in range(1, 13)}
        v20[1] = "Hiram rey de Tiro envió también sus siervos a Salomón, luego que oyó que le habían ungido por rey en lugar de su padre; porque Hiram siempre había amado a David."
        v20[8] = "Y envió Hiram a decir a Salomón: He oído lo que me mandaste a decir; yo haré todo lo que te agrada acerca de la madera de cedro y la madera de ciprés."
        v20[12] = "Y Jehová dio sabiduría a Salomón, como le había dicho; y hubo paz entre Hiram y Salomón, e hicieron pacto entre ambos."
        res20 = evaluate_question(q20, v20, book_key="1kings")
        self.assertNotEqual(res20["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res20["controles_superados"]["control_nombres_propios"], "PASS")

        # 1RE-0031: Hiram artesano (1 Reyes 7:13-14)
        q31 = self.get_1kings_question("NQB-AT-1RE-0031")
        v31 = {
            13: "Y envió el rey Salomón, e hizo venir de Tiro a Hiram,",
            14: "hijo de una viuda de la tribu de Neftalí. Su padre, que era de Tiro, trabajaba en bronce; y era lleno de sabiduría, inteligencia y ciencia para toda obra en bronce..."
        }
        res31 = evaluate_question(q31, v31, book_key="1kings")
        self.assertNotEqual(res31["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res31["controles_superados"]["control_nombres_propios"], "PASS")

        # 1RE-0032: Jaquín y Boaz columnas (1 Reyes 7:21)
        q32 = self.get_1kings_question("NQB-AT-1RE-0032")
        v32 = {21: "Estas columnas erigió en el pórtico del templo; y cuando hubiese alzado la columna del lado derecho, llamó su nombre Jaquín, y alzando la columna del lado izquierdo, llamó su nombre Boaz."}
        res32 = evaluate_question(q32, v32, book_key="1kings")
        self.assertNotEqual(res32["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res32["controles_superados"]["control_nombres_propios"], "PASS")

        # 1RE-0047: Setecientas mujeres reinas y trescientas concubinas (1 Reyes 11:1-4)
        q47 = self.get_1kings_question("NQB-AT-1RE-0047")
        v47 = {
            1: "Pero el rey Salomón amó, además de la hija de Faraón, a muchas mujeres extranjeras...",
            2: "de las naciones de las cuales Jehová había dicho a los hijos de Israel...",
            3: "Y tuvo setecientas mujeres reinas y trescientas concubinas; y sus mujeres desviaron su corazón.",
            4: "Y cuando Salomón era ya viejo, sus mujeres inclinaron su corazón tras dioses ajenos..."
        }
        res47 = evaluate_question(q47, v47, book_key="1kings")
        self.assertNotEqual(res47["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res47["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1RE-0099: Hazael, Jehú y Eliseo (1 Reyes 19:15-16)
        q99 = self.get_1kings_question("NQB-AT-1RE-0099")
        v99 = {
            15: "Y le dijo Jehová: Ve, vuélvete por tu camino, por el desierto de Damasco; y llegarás, y ungirás a Hazael por rey de Siria.",
            16: "A Jehú hijo de Nimsi ungirás por rey sobre Israel; y a Eliseo hijo de Safat, de Abel-mehola, ungirás para que sea profeta en tu lugar."
        }
        res99 = evaluate_question(q99, v99, book_key="1kings")
        self.assertNotEqual(res99["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res99["controles_superados"]["control_nombres_propios"], "PASS")

        # 1RE-0100: Siete mil (1 Reyes 19:18)
        q100 = self.get_1kings_question("NQB-AT-1RE-0100")
        v100 = {18: "Y yo haré que queden en Israel siete mil, cuyas rodillas no se doblaron ante Baal, y cuyas bocas no lo besaron."}
        res100 = evaluate_question(q100, v100, book_key="1kings")
        self.assertNotEqual(res100["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res100["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_2kings_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 2 Reyes (rutas, milagros, cantidades y desenlaces dinásticos)."""
        # 2RE-0005: Gilgal -> Bet-el -> Jericó -> Jordán (2 Reyes 2:1-8)
        q5 = self.get_2kings_question("NQB-AT-2RE-0005")
        v5 = {i: "..." for i in range(1, 9)}
        v5[1] = "Aconteció que cuando quiso Jehová alzar a Elías en un torbellino al cielo, Elías venía con Eliseo de Gilgal."
        v5[2] = "Y dijo Elías a Eliseo: Quédate aquí ahora, porque Jehová me ha enviado a Bet-el..."
        v5[4] = "Y Elías le volvió a decir: Eliseo, quédate aquí ahora, porque Jehová me ha enviado a Jericó..."
        v5[6] = "Y Elías le dijo: Te ruego que te quedes aquí, porque Jehová me ha enviado al Jordán..."
        v5[8] = "Tomando entonces Elías su manto, lo dobló, y golpeó las aguas, las cuales se apartaron a uno y a otro lado, y pasaron ambos por lo seco."
        res5 = evaluate_question(q5, v5, book_key="2kings")
        self.assertNotEqual(res5["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res5["controles_superados"]["control_lugares"], "PASS")

        # 2RE-0007: Carro de fuego y torbellino (2 Reyes 2:11-12)
        q7 = self.get_2kings_question("NQB-AT-2RE-0007")
        v7 = {
            11: "Y aconteció que yendo ellos y hablando, he aquí un carro de fuego con caballos de fuego apartó a los dos; y Elías subió al cielo en un torbellino.",
            12: "Viéndolo Eliseo, clamaba: ¡Padre mío, padre mío, carro de Israel y su gente de a caballo! Y nunca más le vio; y trabando de sus vestidos, los rompió en dos partes."
        }
        res7 = evaluate_question(q7, v7, book_key="2kings")
        self.assertNotEqual(res7["estado"], "REQUIERE_CORRECCION")

        # 2RE-0016: Siete estornudos del hijo de la sunamita (2 Reyes 4:32-37)
        q16 = self.get_2kings_question("NQB-AT-2RE-0016")
        v16 = {i: "..." for i in range(32, 38)}
        v16[35] = "Volviéndose luego, se paseó por la casa a una y otra parte, y después subió, y se tendió sobre él nuevamente, y el joven estornudó siete veces, y abrió sus ojos."
        res16 = evaluate_question(q16, v16, book_key="2kings")
        self.assertNotEqual(res16["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res16["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0017: 20 panes y 100 hombres (2 Reyes 4:42-44)
        q17 = self.get_2kings_question("NQB-AT-2RE-0017")
        v17 = {
            42: "Vino entonces un hombre de Baal-salisa, el cual trajo al varón de Dios panes de primicias, veinte panes de cebada, y trigo nuevo en su espiga. Y él dijo: Da a la gente para que coma.",
            43: "Y respondió su sirviente: ¿Cómo pondré esto delante de cien hombres? Pero él volvió a decir: Da a la gente para que coma, porque así ha dicho Jehová: Comerán, y sobrará.",
            44: "Entonces lo puso delante de ellos, y comieron, y sobró, conforme a la palabra de Jehová."
        }
        res17 = evaluate_question(q17, v17, book_key="2kings")
        self.assertNotEqual(res17["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res17["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0019: Siete veces en el Jordán (2 Reyes 5:8-14)
        q19 = self.get_2kings_question("NQB-AT-2RE-0019")
        v19 = {i: "..." for i in range(8, 15)}
        v19[10] = "Entonces Eliseo le envió un mensajero, diciendo: Ve y lávate siete veces en el Jordán, y tu carne se te restaurará, y serás limpio."
        v19[14] = "El entonces descendió, y se zambulló siete veces en el Jordán, conforme a la palabra del varón de Dios; y su carne se volvió como la carne de un niño, y quedó limpio."
        res19 = evaluate_question(q19, v19, book_key="2kings")
        self.assertNotEqual(res19["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res19["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0077: 185000 asirios (2 Reyes 19:32-37)
        q77 = self.get_2kings_question("NQB-AT-2RE-0077")
        v77 = {i: "..." for i in range(32, 38)}
        v77[32] = "Por tanto, así dice Jehová acerca del rey de Asiria: No entrará en esta ciudad, ni echará saeta en ella; ni vendrá delante de ella con escudo, ni levantará contra ella baluarte."
        v77[35] = "Y aconteció que aquella misma noche salió el ángel de Jehová, y mató en el campamento de los asirios a ciento ochenta y cinco mil; y cuando se levantaron por la mañana, he aquí que todo era cuerpos de muertos."
        v77[36] = "Entonces Senaquerib rey de Asiria se fue, y volvió a Nínive..."
        v77[37] = "Y aconteció que mientras adoraba en el templo de Nisroc su dios, Adramelec y Sarezer sus hijos lo hirieron a espada..."
        res77 = evaluate_question(q77, v77, book_key="2kings")
        self.assertNotEqual(res77["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res77["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0078: Quince años añadidos a Ezequías (2 Reyes 20:1-7)
        q78 = self.get_2kings_question("NQB-AT-2RE-0078")
        v78 = {i: "..." for i in range(1, 8)}
        v78[6] = "Y añadiré a tus días quince años, y te libraré a ti y a esta ciudad de mano del rey de Asiria; y ampararé esta ciudad por amor a mí mismo, y por amor a David mi siervo."
        res78 = evaluate_question(q78, v78, book_key="2kings")
        self.assertNotEqual(res78["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res78["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0084: Josías tenía ocho años (2 Reyes 22:1-2)
        q84 = self.get_2kings_question("NQB-AT-2RE-0084")
        v84 = {
            1: "Cuando Josías comenzó a reinar era de ocho años, y reinó en Jerusalén treinta y un años. El nombre de su madre fue Jedida hija de Adaía, de Boscat.",
            2: "E hizo lo recto ante los ojos de Jehová, y anduvo en todo el camino de David su padre, sin apartarse a derecha ni a izquierda."
        }
        res84 = evaluate_question(q84, v84, book_key="2kings")
        self.assertNotEqual(res84["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res84["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0050: Dos siervos conspiraron (2 Reyes 12:20-21)
        q50 = self.get_2kings_question("NQB-AT-2RE-0050")
        v50 = {
            20: "Y se levantaron sus siervos y conspiraron en conjuración, y mataron a Joás en la casa de Milo, cuando descendía a Sila;",
            21: "porque Josacar hijo de Simeat y Jozabad hijo de Somer, sus siervos, le hirieron, y murió. Y le sepultaron con sus padres en la ciudad de David, y reinó en su lugar Amasías su hijo."
        }
        res50 = evaluate_question(q50, v50, book_key="2kings")
        self.assertNotEqual(res50["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res50["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2RE-0102: Hazael asciende tras muerte de Ben-adad (2 Reyes 8:14-15)
        q102 = self.get_2kings_question("NQB-AT-2RE-0102")
        v102 = {
            14: "Y Hazael se fue de delante de Eliseo, y vino a su señor, el cual le dijo: ¿Qué te ha dicho Eliseo? Y él respondió: Me dijo que de cierto vivirás.",
            15: "El día siguiente, tomó un paño grueso, y lo metió en agua, y lo puso sobre el rostro de Ben-adad, y murió; y reinó Hazael en su lugar."
        }
        res102 = evaluate_question(q102, v102, book_key="2kings")
        self.assertNotEqual(res102["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res102["controles_superados"]["control_nombres_propios"], "PASS")

    # --- CASOS DE REGRESIÓN Y COBERTURA DE 1 CRÓNICAS ---

    def test_1chronicles_regression_and_cases(self) -> None:
        """Verifica casos canónicos y numéricos de 1 Crónicas."""
        if not self.chronicles1_questions:
            self.skipTest("1chronicles-master-input.json no disponible")

        # 1CR-0001: Sem a Abram/Abraham (1 Crónicas 1:24-27)
        q1 = self.get_1chronicles_question("NQB-AT-1CR-0001")
        v1 = {
            24: "Sem, Arfaxad, Sala,",
            25: "Heber, Peleg, Reu,",
            26: "Serug, Nacor, Taré,",
            27: "y Abram, el cual es Abraham."
        }
        res1 = evaluate_question(q1, v1, book_key="1chronicles")
        self.assertNotEqual(res1["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res1["controles_superados"]["control_nombres_propios"], "PASS")

        # 1CR-0004: Sarvia y sus hijos (1 Crónicas 2:13-17)
        q4 = self.get_1chronicles_question("NQB-AT-1CR-0004")
        v4 = {
            13: "Isaí engendró a Eliab su primogénito, el segundo Abinadab, Simea el tercero,",
            14: "el cuarto Natanael, el quinto Radai,",
            15: "el sexto Ozem, el séptimo David,",
            16: "de los cuales Sarvia y Abigail fueron hermanas. Los hijos de Sarvia fueron tres: Abisai, Joab y Asael.",
            17: "Abigail dio a luz a Amasa, cuyo padre fue Jeter ismaelita."
        }
        res4 = evaluate_question(q4, v4, book_key="1chronicles")
        self.assertNotEqual(res4["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res4["controles_superados"]["control_nombres_propios"], "PASS")

        # 1CR-0022: Jasobeam y los 300 (1 Crónicas 11:10-11)
        q22 = self.get_1chronicles_question("NQB-AT-1CR-0022")
        v22 = {
            10: "Estos son los principales de los valientes que tuvo David, y los que le ayudaron en su reino...",
            11: "Y este es el número de los valientes que tuvo David: Jasobeam hijo de Hacmoni, caudillo de los treinta, el cual blandió su lanza una vez contra trescientos, a los cuales mató."
        }
        res22 = evaluate_question(q22, v22, book_key="1chronicles")
        self.assertNotEqual(res22["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res22["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res22["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0036: 7 novillos y 7 carneros (1 Crónicas 15:25-28)
        q36 = self.get_1chronicles_question("NQB-AT-1CR-0036")
        v36 = {
            25: "David, pues, y los ancianos de Israel y los capitanes de millares, fueron a traer el arca del pacto de Jehová, de casa de Obed-edom, con alegría.",
            26: "Y con la ayuda de Dios a los levitas que llevaban el arca del pacto de Jehová, sacrificaron siete novillos y siete carneros.",
            27: "Y David iba vestido de lino fino...",
            28: "De esta manera llevaba todo Israel el arca del pacto de Jehová, con júbilo y sonido de bocinas..."
        }
        res36 = evaluate_question(q36, v36, book_key="1chronicles")
        self.assertNotEqual(res36["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res36["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0045: 1000 carros, 7000 de a caballo, 20000 hombres de a pie (1 Crónicas 18:3-4)
        q45 = self.get_1chronicles_question("NQB-AT-1CR-0045")
        v45 = {
            3: "Asimismo derrotó David a Hadad-ezer rey de Soba, en Hamat, yendo éste a asegurar su dominio junto al río Eufrates.",
            4: "Y le tomó David mil carros, siete mil de a caballo, y veinte mil hombres de a pie; y desjarretó David los caballos de todos los carros, excepto los de cien carros que reservó."
        }
        res45 = evaluate_question(q45, v45, book_key="1chronicles")
        self.assertNotEqual(res45["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res45["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0052: 6 dedos por mano/pie, 24 en total (1 Crónicas 20:6-8)
        q52 = self.get_1chronicles_question("NQB-AT-1CR-0052")
        v52 = {
            6: "Y volvió a haber guerra en Gat, donde había un hombre de grande estatura, el cual tenía seis dedos en pies y manos, veinticuatro por todos; y era también hijo del gigante.",
            7: "Este desafió a Israel, pero lo mató Jonatán hijo de Simea, hermano de David.",
            8: "Estos eran hijos del gigante en Gat, los cuales cayeron por mano de David y de sus siervos."
        }
        res52 = evaluate_question(q52, v52, book_key="1chronicles")
        self.assertNotEqual(res52["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res52["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0054: 1100000 Israel, 470000 Judá, Leví y Benjamín excluidos (1 Crónicas 21:5-6)
        q54 = self.get_1chronicles_question("NQB-AT-1CR-0054")
        v54 = {
            5: "Y dio Joab el número del censo del pueblo a David; y de todo Israel había un millón cien mil hombres que sacaban espada, y de Judá cuatrocientos setenta mil hombres que sacaban espada.",
            6: "Entre éstos no fueron contados los levitas, ni los hijos de Benjamín, porque la orden del rey era abominable a Joab."
        }
        res54 = evaluate_question(q54, v54, book_key="1chronicles")
        self.assertNotEqual(res54["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res54["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0056: 600 siclos de oro a Ornán (1 Crónicas 21:24-27)
        q56 = self.get_1chronicles_question("NQB-AT-1CR-0056")
        v56 = {
            24: "Y el rey David dijo a Ornán: No, sino que por su justo precio la compraré...",
            25: "Y dio David a Ornán por el lugar el peso de seiscientos siclos de oro.",
            26: "Y edificó allí David un altar a Jehová...",
            27: "Y Jehová habló al ángel, y éste volvió su espada a la vaina."
        }
        res56 = evaluate_question(q56, v56, book_key="1chronicles")
        self.assertNotEqual(res56["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res56["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0061: 38000 levitas distribuidos (1 Crónicas 23:3-6)
        q61 = self.get_1chronicles_question("NQB-AT-1CR-0061")
        v61 = {
            3: "Y fueron contados los levitas de treinta años arriba; y fue el número de ellos por sus cabezas, contados uno por uno, treinta y ocho mil.",
            4: "De éstos, veinticuatro mil para dirigir la obra de la casa de Jehová, y seis mil oficiales y jueces.",
            5: "Además, cuatro mil porteros, y cuatro mil para alabar a Jehová con los instrumentos que David había hecho para tributar alabanzas.",
            6: "Y los repartió David en grupos conforme a los hijos de Leví: Gersón, Coat y Merari."
        }
        res61 = evaluate_question(q61, v61, book_key="1chronicles")
        self.assertNotEqual(res61["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res61["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0064: 16 suertes de Eleazar y 8 de Itamar (1 Crónicas 24:1-6)
        q64 = self.get_1chronicles_question("NQB-AT-1CR-0064")
        v64 = {
            1: "También los hijos de Aarón tuvieron sus distribuciones. Los hijos de Aarón: Nadab, Abiú, Eleazar e Itamar.",
            2: "Mas Nadab y Abiú murieron antes que su padre, y no tuvieron hijos; y Eleazar e Itamar ejercieron el sacerdocio.",
            3: "Y David, con Sadoc de los hijos de Eleazar, y Ahimelec de los hijos de Itamar, los repartió por sus turnos en el ministerio.",
            4: "Y de los hijos de Eleazar se hallaron más varones principales que de los hijos de Itamar; y los repartieron así: De los hijos de Eleazar, dieciséis cabezas de casas paternas; y de los hijos de Itamar, por sus casas paternas, ocho.",
            5: "Los repartieron, pues, por suerte los unos con los otros...",
            6: "Y el escriba Semaías hijo de Natanael, de los levitas, los escribió delante del rey..."
        }
        res64 = evaluate_question(q64, v64, book_key="1chronicles")
        self.assertNotEqual(res64["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res64["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0066: 288 músicos (1 Crónicas 25:7-8)
        q66 = self.get_1chronicles_question("NQB-AT-1CR-0066")
        v66 = {
            7: "Y el número de ellos, con sus hermanos, instruidos en el canto para Jehová, todos los aptos, fue doscientos ochenta y ocho.",
            8: "Y echaron suertes para servir por turnos, entrando el pequeño con el grande, lo mismo el maestro que el discípulo."
        }
        res66 = evaluate_question(q66, v66, book_key="1chronicles")
        self.assertNotEqual(res66["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res66["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0075: 3000 oro de Ofir y 7000 plata (1 Crónicas 29:1-5)
        q75 = self.get_1chronicles_question("NQB-AT-1CR-0075")
        v75 = {
            1: "Después dijo el rey David a toda la asamblea: Solamente a Salomón mi hijo ha elegido Dios; él es joven y tierno...",
            2: "Yo con todas mis fuerzas he preparado para la casa de mi Dios...",
            3: "Además de esto, por cuanto tengo mi afecto en la casa de mi Dios, yo guardo en mi tesoro particular oro y plata que, además de todas las cosas que he preparado para la casa del santuario, he dado para la casa de mi Dios:",
            4: "tres mil talentos de oro, de oro de Ofir, y siete mil talentos de plata refinada para cubrir las paredes de las casas;",
            5: "oro, pues, para las cosas de oro, y plata para las cosas de plata..."
        }
        res75 = evaluate_question(q75, v75, book_key="1chronicles")
        self.assertNotEqual(res75["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res75["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0076: 5000 talentos + 10000 dracmas de oro (1 Crónicas 29:6-9)
        q76 = self.get_1chronicles_question("NQB-AT-1CR-0076")
        v76 = {
            6: "Entonces los jefes de familia, y los príncipes de las tribus de Israel, jefes de millares y de centenas, con los administradores de la hacienda del rey, ofrecieron voluntariamente.",
            7: "Y dieron para el servicio de la casa de Dios cinco mil talentos y diez mil dracmas de oro, diez mil talentos de plata, dieciocho mil talentos de bronce, y cien mil talentos de hierro.",
            8: "Y todo el que tenía piedras preciosas las dio para el tesoro de la casa de Jehová...",
            9: "Y se alegró el pueblo por haber contribuido voluntariamente..."
        }
        res76 = evaluate_question(q76, v76, book_key="1chronicles")
        self.assertNotEqual(res76["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res76["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1CR-0080: 40 años total (7 en Hebrón, 33 en Jerusalén) (1 Crónicas 29:26-30)
        q80 = self.get_1chronicles_question("NQB-AT-1CR-0080")
        v80 = {
            26: "Así reinó David hijo de Isaí sobre todo Israel.",
            27: "El tiempo que reinó sobre Israel fue cuarenta años. Siete años reinó en Hebrón, y treinta y tres años reinó en Jerusalén.",
            28: "Y murió en buena vejez, lleno de días, de riquezas y de gloria; y reinó en su lugar Salomón su hijo.",
            29: "Y los hechos del rey David, primeros y postreros, están escritos en el libro de las crónicas de Samuel vidente, en las crónicas del profeta Natán, y en las crónicas de Gad vidente,",
            30: "con todo lo relativo a su reinado, y a su poder, y los tiempos que pasaron sobre él, y sobre Israel y sobre todos los reinos de aquellas tierras."
        }
        res80 = evaluate_question(q80, v80, book_key="1chronicles")
        self.assertNotEqual(res80["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res80["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res80["controles_superados"]["control_nombres_propios"], "PASS")

    # --- CASOS DE REGRESIÓN Y COBERTURA DE 2 CRÓNICAS ---

    def test_2chronicles_regression_and_cases(self) -> None:
        """Verifica casos canónicos, cuantitativos e históricos de 2 Crónicas."""
        if not self.chronicles2_questions:
            self.skipTest("2chronicles-master-input.json no disponible")

        # 2CR-0002: 1000 holocaustos en Gabaón (2 Crónicas 1:6)
        q2 = self.get_2chronicles_question("NQB-AT-2CR-0002")
        v2 = {6: "Y subió Salomón allá delante de Jehová, al altar de bronce que estaba en el tabernáculo de reunión, y ofreció sobre él mil holocaustos."}
        res2 = evaluate_question(q2, v2, book_key="2chronicles")
        self.assertNotEqual(res2["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res2["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0003: 70000, 80000, 3600 trabajadores (2 Crónicas 2:2)
        q3 = self.get_2chronicles_question("NQB-AT-2CR-0003")
        v3 = {2: "Y designó Salomón setenta mil hombres que llevasen cargas, y ochenta mil hombres que cortasen en el monte, y tres mil seiscientos que los vigilasen."}
        res3 = evaluate_question(q3, v3, book_key="2chronicles")
        self.assertNotEqual(res3["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res3["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0010: Asaf, Hemán, Jedutún y 120 trompetistas (2 Crónicas 5:11-14)
        q10 = self.get_2chronicles_question("NQB-AT-2CR-0010")
        v10 = {
            11: "Y cuando los sacerdotes salieron del santuario...",
            12: "y los levitas cantores, todos los de Asaf, los de Hemán, y los de Jedutún, juntamente con sus hijos y sus hermanos, vestidos de lino fino, estaban con címbalos y salterios y arpas al oriente del altar; y con ellos ciento veinte sacerdotes que tocaban trompetas:",
            13: "cuando sonaban, pues, las trompetas y cantaban todos a una...",
            14: "Y no podían los sacerdotes estar allí para ministrar, por causa de la nube; porque la gloria de Jehová había llenado la casa de Dios."
        }
        res10 = evaluate_question(q10, v10, book_key="2chronicles")
        self.assertNotEqual(res10["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res10["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res10["controles_superados"]["control_nombres_propios"], "PASS")

        # 2CR-0026: Sisac, 1200 carros, 60000 de a caballo, libios, suquienos, etíopes (2 Crónicas 12:2-4)
        q26 = self.get_2chronicles_question("NQB-AT-2CR-0026")
        v26 = {
            2: "Y en el quinto año del rey Roboam subió Sisac rey de Egipto contra Jerusalén, por cuanto se habían rebelado contra Jehová,",
            3: "con mil doscientos carros, y con sesenta mil hombres de a caballo; mas el pueblo que venía con él de Egipto, esto es, libios, suquienos y etíopes, no tenía número.",
            4: "Y tomó las ciudades fortificadas de Judá, y llegó hasta Jerusalén."
        }
        res26 = evaluate_question(q26, v26, book_key="2chronicles")
        self.assertNotEqual(res26["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res26["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0033: Zera etíope, 1,000,000 hombres, 300 carros (2 Crónicas 14:9-10)
        q33 = self.get_2chronicles_question("NQB-AT-2CR-0033")
        v33 = {
            9: "Y salió contra ellos Zera etíope con un ejército de un millón de hombres y trescientos carros; y vino hasta Maresa.",
            10: "Entonces salió Asa contra él, y ordenaron la batalla en el valle de Zefata junto a Maresa."
        }
        res33 = evaluate_question(q33, v33, book_key="2chronicles")
        self.assertNotEqual(res33["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res33["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0047: Amarías y Zebadías (2 Crónicas 19:8-11)
        q47 = self.get_2chronicles_question("NQB-AT-2CR-0047")
        v47 = {
            8: "Puso también Josafat en Jerusalén algunos de los levitas y sacerdotes, y de los padres de familias de Israel, para el juicio de Jehová y para las causas...",
            9: "Y les mandó diciendo: Procederéis asimismo con temor de Jehová, con verdad, y con corazón íntegro.",
            10: "En cualquier causa que viniere a vosotros de vuestros hermanos que habitan en las ciudades...",
            11: "Y he aquí el sacerdote Amarías será el que os presida en todo asunto de Jehová, y Zebadías hijo de Ismael, príncipe de la casa de Judá, en todos los negocios del rey; también los levitas serán oficiales en presencia vuestra. Esforzaos, pues, para obrar, y Jehová será con el bueno."
        }
        res47 = evaluate_question(q47, v47, book_key="2chronicles")
        self.assertNotEqual(res47["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res47["controles_superados"]["control_nombres_propios"], "PASS")

        # 2CR-0052: 3 días de botín, bendición en Beraca (2 Crónicas 20:24-30)
        q52 = self.get_2chronicles_question("NQB-AT-2CR-0052")
        v52 = {
            24: "Y luego que vino Judá a la torre del desierto, miraron hacia la multitud, y he aquí yacían ellos en tierra muertos, pues ninguno había escapado.",
            25: "Viniendo entonces Josafat y su pueblo a despojarlos, hallaron entre los cadáveres muchas riquezas, así vestidos como alhajas preciosas, que tomaron para sí, tantos, que no los podían llevar; tres días estuvieron recogiendo el botín, porque era mucho.",
            26: "Y al cuarto día se juntaron en el valle de Beraca; porque allí bendijeron a Jehová, y por esto llamaron el nombre de aquel paraje el valle de Beraca, hasta hoy.",
            27: "Y todo Judá y los de Jerusalén, y Josafat a la cabeza de ellos, volvieron para regresar a Jerusalén gozosos, porque Jehová les había dado gozo librándolos de sus enemigos.",
            28: "Y vinieron a Jerusalén con salterios, arpas y trompetas, a la casa de Jehová.",
            29: "Y el pavor de Dios cayó sobre todos los reinos de aquella tierra, cuando oyeron que Jehová había peleado contra los enemigos de Israel.",
            30: "Y el reino de Josafat tuvo paz; porque su Dios le dio paz por todas partes."
        }
        res52 = evaluate_question(q52, v52, book_key="2chronicles")
        self.assertNotEqual(res52["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res52["controles_superados"]["control_lugares"], "PASS")

        # 2CR-0079: 7 novillos, 7 carneros, 7 corderos, 7 machos cabríos (2 Crónicas 29:20-27)
        q79 = self.get_2chronicles_question("NQB-AT-2CR-0079")
        v79 = {
            20: "Y levantándose de mañana el rey Ezequías reunió los principales de la ciudad, y subió a la casa de Jehová.",
            21: "Y trajeron siete novillos, siete carneros, siete corderos y siete machos cabríos, para expiación por el reino, por el santuario y por Judá...",
            22: "Mataron, pues, los novillos, y los sacerdotes tomaron la sangre...",
            23: "Hicieron luego acercar los machos cabríos de la expiación delante del rey y de la multitud, y pusieron sobre ellos sus manos;",
            24: "y los sacerdotes los mataron, y expiaron con la sangre de ellos sobre el altar, para reconciliar a todo Israel; porque por todo Israel mandó el rey hacer el holocausto y la expiación.",
            25: "Puso también levitas en la casa de Jehová con címbalos, salterios y arpas, conforme al mandamiento de David, de Gad vidente del rey, y del profeta Natán...",
            26: "Y los levitas estaban con los instrumentos de David, y los sacerdotes con trompetas.",
            27: "Entonces mandó Ezequías ofrecer el holocausto en el altar; y cuando comenzó el holocausto, comenzó también el cántico de Jehová, con las trompetas y los instrumentos de David rey de Israel."
        }
        res79 = evaluate_question(q79, v79, book_key="2chronicles")
        self.assertNotEqual(res79["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res79["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0096: Josías 30000 animales y 3000 bueyes (2 Crónicas 35:5-9)
        q96 = self.get_2chronicles_question("NQB-AT-2CR-0096")
        v96 = {
            5: "y estad en el lugar santo según las divisiones de las familias de vuestros hermanos los hijos del pueblo, y según la división de la familia de los levitas.",
            6: "Santificaos, pues, y santificad a vuestros hermanos, y disponed a vuestros hermanos para que hagan conforme a la palabra de Jehová dada por medio de Moisés.",
            7: "Y el rey Josías dio a los del pueblo ovejas, corderos y cabritos de los rebaños, en número de treinta mil, y tres mil bueyes, todo para la pascua, para todos los que se hallaban presentes; esto de la hacienda del rey.",
            8: "También sus príncipes dieron con liberalidad al pueblo, a los sacerdotes y a los levitas. Hilcías, Zacarías y Jehiel, oficiales de la casa de Dios, dieron a los sacerdotes, para celebrar la pascua, dos mil seiscientas ovejas, y trescientos bueyes.",
            9: "Asimismo Conanías, y Semaías y Natanael sus hermanos, y Hasabías, Jeiel y Jozabad, principales de los levitas, dieron a los levitas para los sacrificios de la pascua cinco mil ovejas, y quinientos bueyes."
        }
        res96 = evaluate_question(q96, v96, book_key="2chronicles")
        self.assertNotEqual(res96["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res96["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2CR-0102: Decreto de Ciro (2 Crónicas 36:22-23)
        q102 = self.get_2chronicles_question("NQB-AT-2CR-0102")
        v102 = {
            22: "Mas al primer año de Ciro rey de los persas, para que se cumpliese la palabra de Jehová por boca de Jeremías, Jehová despertó el espíritu de Ciro rey de los persas, el cual hizo pregonar de palabra y también por escrito, por todo su reino, diciendo:",
            23: "Así dice Ciro, rey de los persas: Jehová, el Dios de los cielos, me ha dado todos los reinos de la tierra; y él me ha mandado que le edifique casa en Jerusalén, que está en Judá. Quien haya entre vosotros de todo su pueblo, sea Jehová su Dios con él, y suba."
        }
        res102 = evaluate_question(q102, v102, book_key="2chronicles")
        self.assertNotEqual(res102["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res102["controles_superados"]["control_nombres_propios"], "PASS")

    # --- REGRESIONES Y PRUEBAS ESPECÍFICAS DE ESDRAS ---

    def test_detect_book_key_ezra(self) -> None:
        """Verifica la detección automática del libro Esdras."""
        spec_ezra = {"questions": [{"id": "NQB-AT-ESD-0001", "book": "Esdras"}]}
        self.assertEqual(detect_book_key(spec_ezra), "ezra")

        spec_alias = [{"id": "NQB-AT-ESD-0002", "book": "Ezra"}]
        self.assertEqual(detect_book_key(spec_alias), "ezra")

    def test_ezra_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica, aliases y bloques de Esdras."""
        self.assertIn("ezra", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["ezra"]
        self.assertEqual(cfg["canonical_name"], "Esdras")
        self.assertEqual(cfg["api_name"], "Esdras")
        self.assertEqual(cfg["total_chapters"], 10)
        self.assertTrue({"esdras", "ezra"}.issubset(cfg["aliases"]))
        self.assertEqual(len(cfg["blocks"]), 2)

    def test_global_canonical_id_reference_integrity_ezra(self) -> None:
        """Verifica consistencia de IDs y referencias en Esdras."""
        if not self.ezra_questions:
            self.skipTest("ezra-master-input.json no disponible")
        self.assertEqual(len(self.ezra_questions), 52)
        for qid, q in self.ezra_questions.items():
            self.assertTrue(qid.startswith("NQB-AT-ESD-"))
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_ezra_specific_evaluations_and_regressions(self) -> None:
        """Pruebas de evaluación RVR1960 para casos representativos de Esdras."""
        if not self.ezra_questions:
            self.skipTest("ezra-master-input.json no disponible")

        # ESD-0001: Decreto de Ciro y ofrendas voluntarias (Esdras 1:1-6)
        q1 = self.get_ezra_question("NQB-AT-ESD-0001")
        v1 = {
            1: "En el primer año de Ciro rey de Persia, para que se cumpliese la palabra de Jehová por boca de Jeremías, despertó Jehová el espíritu de Ciro rey de Persia...",
            2: "Así ha dicho Ciro rey de Persia: Jehová el Dios de los cielos me ha dado todos los reinos de la tierra, y me ha mandado que le edifique casa en Jerusalén...",
            3: "¿Quién hay entre vosotros de su pueblo? Sea Dios con él, y suba a Jerusalén...",
            4: "Y a todo el que haya quedado, en cualquier lugar donde more, ayúdenle los hombres de su lugar con plata, oro, bienes y ganados, además de ofrendas voluntarias para la casa de Dios, la cual está en Jerusalén.",
            5: "Entonces se levantaron los cabezas de las casas paternas de Judá y de Benjamín, y los sacerdotes y levitas, todos aquellos cuyo espíritu despertó Dios para subir a edificar la casa de Jehová, la cual está en Jerusalén.",
            6: "Y todos los que estaban en sus derredores les ayudaron con plata, oro, bienes, ganado y cosas preciosas, además de todo lo que se ofreció voluntariamente."
        }
        res1 = evaluate_question(q1, v1, book_key="ezra")
        self.assertNotEqual(res1["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res1["controles_superados"]["control_opcion_a_correcta"], "PASS")

        # ESD-0002: 5400 utensilios entregados a Sesbasar (Esdras 1:7-11)
        q2 = self.get_ezra_question("NQB-AT-ESD-0002")
        v2 = {
            7: "Y el rey Ciro sacó los utensilios de la casa de Jehová, que Nabucodonosor había traído de Jerusalén, y los había puesto en la casa de sus dioses.",
            8: "Los sacó, pues, Ciro rey de Persia, por mano de Mitrídates tesorero, el cual los dio por cuenta a Sesbasar príncipe de Judá.",
            9: "Y esta es la cuenta de ellos: treinta tazones de oro, mil tazones de plata, veintinueve cuchillos,",
            10: "treinta tazas de oro, otras tazas de plata de segunda clase, cuatrocientas diez, y otros vasos, mil.",
            11: "Todos los utensilios de oro y de plata eran cinco mil cuatrocientos. Todos los hizo llevar Sesbasar con los que subieron del cautiverio de Babilonia a Jerusalén."
        }
        res2 = evaluate_question(q2, v2, book_key="ezra")
        self.assertNotEqual(res2["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res2["controles_superados"]["control_nombres_propios"], "PASS")

        # ESD-0010: Levitas de 20 años o más para supervisar la obra (Esdras 3:8-9)
        q10 = self.get_ezra_question("NQB-AT-ESD-0010")
        v10 = {
            8: "En el año segundo de su venida a la casa de Dios en Jerusalén, en el mes segundo, comenzaron Zorobabel hijo de Salatiel, Jesúa hijo de Josadac y los otros sus hermanos, los sacerdotes y los levitas, y todos los que habían venido del cautiverio a Jerusalén; y pusieron a los levitas de veinte años arriba para que activasen la obra de la casa de Jehová.",
            9: "Jesúa también, sus hijos y sus hermanos, Cadmiel y sus hijos, hijos de Judá, se pusieron a una para activar a los que hacían la obra en la casa de Dios, junto con los hijos de Henadad, sus hijos y sus hermanos levitas."
        }
        res10 = evaluate_question(q10, v10, book_key="ezra")
        self.assertNotEqual(res10["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res10["controles_superados"]["control_numeros_cantidades"], "PASS")

        # ESD-0017: Profetas Hageo y Zacarías (Esdras 5:1-2)
        q17 = self.get_ezra_question("NQB-AT-ESD-0017")
        v17 = {
            1: "Profetizaron Hageo y Zacarías hijo de Iddo, ambos profetas, a los judíos que estaban en Judá y en Jerusalén en el nombre del Dios de Israel quien estaba sobre ellos.",
            2: "Entonces se levantaron Zorobabel hijo de Salatiel y Jesúa hijo de Josadac, y comenzaron a reedificar la casa de Dios que estaba en Jerusalén; y con ellos los profetas de Dios que les ayudaban."
        }
        res17 = evaluate_question(q17, v17, book_key="ezra")
        self.assertNotEqual(res17["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res17["controles_superados"]["control_nombres_propios"], "PASS")

        # ESD-0024: 3 de Adar, año 6 de Darío (Esdras 6:13-15)
        q24 = self.get_ezra_question("NQB-AT-ESD-0024")
        v24 = {
            13: "Entonces Tatnai gobernador del otro lado del río, y Setar-boznai y sus compañeros, hicieron puntualmente según el rey Darío había enviado.",
            14: "Y los ancianos de los judíos edificaban y prosperaban, conforme a la profecía del profeta Hageo y de Zacarías hijo de Iddo. Edificaron, pues, y terminaron, por orden del Dios de Israel, y por mandato de Ciro, de Darío, y de Artajerjes rey de Persia.",
            15: "Esta casa fue terminada el tercer día del mes de Adar, que era el sexto año del reinado del rey Darío."
        }
        res24 = evaluate_question(q24, v24, book_key="ezra")
        self.assertNotEqual(res24["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res24["controles_superados"]["control_numeros_cantidades"], "PASS")

        # ESD-0027: Linaje sacerdotal y escriba diligente (Esdras 7:1-6)
        q27 = self.get_ezra_question("NQB-AT-ESD-0027")
        v27 = {
            1: "Pasadas estas cosas, en el reinado de Artajerjes rey de Persia, Esdras hijo de Seraías, hijo de Azarías, hijo de Hilcías,",
            2: "hijo de Salum, hijo de Sadoc, hijo de Ahitob,",
            3: "hijo de Amarías, hijo de Azarías, hijo de Meraiot,",
            4: "hijo de Zeraías, hijo de Uzi, hijo de Buqui,",
            5: "hijo de Abisúa, hijo de Finees, hijo de Eleazar, hijo de Aarón, primer sacerdote,",
            6: "este Esdras subió de Babilonia. Era escriba diligente en la ley de Moisés, que Jehová Dios de Israel había dado; y le concedió el rey todo lo que pidió, porque la mano de Jehová su Dios estaba sobre Esdras."
        }
        res27 = evaluate_question(q27, v27, book_key="ezra")
        self.assertNotEqual(res27["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res27["controles_superados"]["control_nombres_propios"], "PASS")

        # ESD-0036: Casifia 18, 20 y 220 sirvientes (Esdras 8:18-20)
        q36 = self.get_ezra_question("NQB-AT-ESD-0036")
        v36 = {
            18: "Y nos trajeron según la buena mano de nuestro Dios sobre nosotros, un varón entendido, de los hijos de Mahli hijo de Leví, hijo de Israel; a Serebías con sus hijos y sus hermanos, dieciocho;",
            19: "a Hasabías, y con él a Jesaías de los hijos de Merari, a sus hermanos y a sus hijos, veinte;",
            20: "y de los sirvientes del templo, a quienes David y los príncipes habían puesto para el ministerio de los levitas, doscientos veinte sirvientes del templo, todos los cuales fueron designados por sus nombres."
        }
        res36 = evaluate_question(q36, v36, book_key="ezra")
        self.assertNotEqual(res36["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res36["controles_superados"]["control_numeros_cantidades"], "PASS")

        # ESD-0048: Plazo 3 días, día 20 del mes 9 (Esdras 10:7-9)
        q48 = self.get_ezra_question("NQB-AT-ESD-0048")
        v48 = {
            7: "E hicieron pregonar en Judá y en Jerusalén a todos los hijos del cautiverio, que se reuniesen en Jerusalén;",
            8: "y que el que no viniera dentro de tres días, conforme al acuerdo de los príncipes y de los ancianos, perdiese toda su hacienda, y el tal fuese excluido de la congregación de los del cautiverio.",
            9: "Así todos los hombres de Judá y de Benjamín se reunieron en Jerusalén dentro de los tres días, a los veinte días del mes, el cual era el mes noveno; y se sentó todo el pueblo en la plaza de la casa de Dios, temblando con motivo de aquel asunto, y a causa de las grandes lluvias."
        }
        res48 = evaluate_question(q48, v48, book_key="ezra")
        self.assertNotEqual(res48["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res48["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_extract_numbers_thousands_grouping(self) -> None:
        """Verifica la normalización rigurosa de millares (punto, coma, espacio) sin afectar decimales ni referencias."""
        # Agrupaciones de miles válidas
        self.assertEqual(extract_numbers("42.360 personas"), [42360])
        self.assertEqual(extract_numbers("42,360 personas"), [42360])
        self.assertEqual(extract_numbers("42 360 personas"), [42360])
        self.assertEqual(extract_numbers("42360 personas"), [42360])
        self.assertEqual(extract_numbers("1.000.000 de hombres"), [1000000])
        self.assertEqual(extract_numbers("601 730 guerreros"), [601730])

        # Decimales: no colapsar '3.14' a 314
        self.assertNotIn(314, extract_numbers("El número pi es 3.14"))

        # Referencias: no extraer números de 'Esdras 2:64-70' o '7:11-16'
        self.assertEqual(extract_numbers("Según Esdras 2:64-70 en la congregación"), [])
        self.assertEqual(extract_numbers("Esdras 7:11-16 relata la comisión"), [])

    def test_polysemous_entity_disambiguation(self) -> None:
        """Verifica que entidades polisémicas (Judá, Israel, etc.) se desambigüen por contexto locativo/colectivo."""
        # Judá y Jerusalén (locativo) -> no personaje
        self.assertTrue(is_locative_or_collective_entity("juda", "Examinar la situación de Judá y Jerusalén", []))
        self.assertTrue(is_locative_or_collective_entity("juda", "ciudades de Judá y Benjamín", []))
        self.assertTrue(is_locative_or_collective_entity("juda", "reino de Judá", []))
        self.assertTrue(is_locative_or_collective_entity("juda", "tribu de Judá", []))

        # Judá como persona cuando el banco lo declara explícitamente
        self.assertFalse(is_locative_or_collective_entity("juda", "Judá engendró a Fares", ["Judá"]))

    def test_implicit_speaker_resolution(self) -> None:
        """Verifica la resolución contextual del hablante en discurso en 1ª persona."""
        v_map_single_speaker = {
            5: "Y a la hora del sacrificio de la tarde me levanté de mi aflicción, y extendí mis manos a Jehová mi Dios,",
            6: "y dije: Dios mío, confuso y avergonzado estoy para levantar mi rostro a ti, porque nuestras iniquidades se han multiplicado,",
            10: "Pero ahora, ¿qué diremos, oh Dios nuestro, después de esto? Porque nosotros hemos dejado tus mandamientos,"
        }
        passage = "pero ahora que diremos oh dios nuestro despues de esto porque nosotros hemos dejado tus mandamientos"
        # Nombre identificado en contexto previo + 1ª persona sostenida -> PASS
        self.assertTrue(resolve_implicit_speaker("esdras", passage, v_map_single_speaker, 10, ["Esdras"], book_key="ezra"))

        # Conflicto con dos hablantes introducidos -> False
        v_map_conflict = {
            5: "Y habló Sanbalat diciendo...",
            6: "Y respondió Tobías diciendo...",
            10: "Pero ahora, ¿qué diremos, oh Dios nuestro...?"
        }
        self.assertFalse(resolve_implicit_speaker("esdras", passage, v_map_conflict, 10, ["Esdras"], book_key="ezra"))

    def test_ezra_previously_failing_cases_esd0005_esd0030_esd0044(self) -> None:
        """Verifica que los 3 casos que fallaron en el Run 41 queden completamente resueltos sin REQUIERE_CORRECCION."""
        if not self.ezra_questions:
            self.skipTest("ezra-master-input.json no disponible")

        # 1. ESD-0005: 42.360 personas (Esdras 2:64-70)
        q5 = self.get_ezra_question("NQB-AT-ESD-0005")
        v5 = {
            64: "Toda la congregación, unida como un solo hombre, era de cuarenta y dos mil trescientos sesenta,",
            65: "sin los siervos y siervas de ellos, que eran siete mil trescientos treinta y siete; y tenían doscientos cantores y cantoras.",
            66: "Sus caballos eran setecientos treinta y seis; sus mulos, doscientos cuarenta y cinco;",
            67: "sus camellos, cuatrocientos treinta y cinco; asnos, seis mil setecientos veinte.",
            68: "Y algunos de los cabezas de familias, cuando vinieron a la casa de Jehová que estaba en Jerusalén, hicieron ofrendas voluntarias para la casa de Dios, para reedificarla en su sitio.",
            69: "Según sus fuerzas dieron al tesorero de la obra sesenta y un mil dracmas de oro, cinco mil libras de plata, y cien túnicas sacerdotales.",
            70: "Y habitaron los sacerdotes, los levitas, los del pueblo, los cantores, los porteros y los sirvientes del templo en sus ciudades; y todo Israel en sus ciudades."
        }
        res5 = evaluate_question(q5, v5, book_key="ezra")
        self.assertNotEqual(res5["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res5["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2. ESD-0030: Judá y Jerusalén (Esdras 7:11-16)
        q30 = self.get_ezra_question("NQB-AT-ESD-0030")
        v30 = {
            11: "Esta es la copia de la carta que dio el rey Artajerjes al sacerdote Esdras, escriba versado en los mandamientos de Jehová y en sus estatutos a Israel:",
            12: "Artajerjes rey de reyes, a Esdras, sacerdote y escriba docto en la ley del Dios del cielo: Paz.",
            13: "Por mí es dada orden que cualquiera en mi reino, del pueblo de Israel y de sus sacerdotes y levitas, que quiera ir contigo a Jerusalén, vaya.",
            14: "Porque de parte del rey y de sus siete consejeros eres enviado a visitar a Judá y a Jerusalén, conforme a la ley de tu Dios que está en tu mano;",
            15: "y a llevar la plata y el oro que el rey y sus consejeros voluntariamente ofrecen al Dios de Israel, cuya morada está en Jerusalén,",
            16: "y toda la plata y el oro que hallares en toda la provincia de Babilonia, con las ofrendas voluntarias del pueblo y de los sacerdotes, que voluntariamente ofrecieren para la casa de su Dios, la cual está en Jerusalén."
        }
        res30 = evaluate_question(q30, v30, book_key="ezra")
        self.assertNotEqual(res30["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res30["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res30["controles_superados"]["control_lugares"], "PASS")

        # 3. ESD-0044: Oración de Esdras (Esdras 9:10-12)
        q44 = self.get_ezra_question("NQB-AT-ESD-0044")
        v44 = {
            1: "Acabadas estas cosas, los príncipes vinieron a mí, diciendo: El pueblo de Israel y los sacerdotes y los levitas no se han separado de los pueblos de las tierras...",
            3: "Cuando oí esto, rasgué mi vestido y mi manto, y arranqué pelo de mi cabeza y de mi barba, y me senté angustiado en extremo.",
            5: "Y a la hora del sacrificio de la tarde me levanté de mi aflicción, y habiendo rasgado mi vestido y mi manto, me postré de rodillas, y extendí mis manos a Jehová mi Dios,",
            6: "y dije: Dios mío, confuso y avergonzado estoy para levantar, oh Dios mío, mi rostro a ti, porque nuestras iniquidades se han multiplicado sobre nuestra cabeza, y nuestros delitos han crecido hasta el cielo.",
            10: "Pero ahora, ¿qué diremos, oh Dios nuestro, después de esto? Porque nosotros hemos dejado tus mandamientos,",
            11: "los cuales prescribiste por medio de tus siervos los profetas, diciendo: La tierra a la cual entráis para poseerla, tierra inmunda es...",
            12: "Ahora, pues, no daréis vuestras hijas a los hijos de ellos, ni sus hijas tomaréis para vuestros hijos, ni procuraréis jamás su paz ni su prosperidad; para que seáis fuertes y comáis el bien de la tierra, y la dejéis por heredad a vuestros hijos para siempre."
        }
        res44 = evaluate_question(q44, v44, book_key="ezra")
        self.assertNotEqual(res44["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res44["controles_superados"]["control_nombres_propios"], "PASS")

    # --- TESTS PARA NEHEMÍAS ---

    def test_detect_book_key_nehemiah(self) -> None:
        """Verifica la detección automática de clave para Nehemías."""
        spec_neh = {"questions": [{"id": "NQB-AT-NEH-0001", "book": "Nehemías"}]}
        self.assertEqual(detect_book_key(spec_neh), "nehemiah")

        spec_alias = {"questions": [{"id": "NQB-AT-NEH-0001", "book": "nehemias"}]}
        self.assertEqual(detect_book_key(spec_alias), "nehemiah")

        spec_en = {"questions": [{"id": "NQB-AT-NEH-0001", "book": "Nehemiah"}]}
        self.assertEqual(detect_book_key(spec_en), "nehemiah")

        spec_libro = {"questions": [{"id": "NQB-AT-NEH-0001", "book": "Libro de Nehemías"}]}
        self.assertEqual(detect_book_key(spec_libro), "nehemiah")

    def test_nehemiah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Nehemías: 13 capítulos, 2 bloques."""
        self.assertIn("nehemiah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["nehemiah"]
        self.assertEqual(cfg["canonical_name"], "Nehemías")
        self.assertEqual(cfg["api_name"], "Nehemías")
        self.assertEqual(cfg["total_chapters"], 13)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertEqual(cfg["blocks"][0], (1, 10, "nehemiah-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 13, "nehemiah-11-13.json"))
        self.assertTrue({"nehemías", "nehemias", "nehemiah", "neh"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_nehemiah(self) -> None:
        """Verifica consistencia de IDs y referencias en Nehemías."""
        if not self.nehemiah_questions:
            self.skipTest("nehemiah-master-input.json no disponible")
        self.assertEqual(len(self.nehemiah_questions), 60)
        for qid, q in self.nehemiah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    # --- TESTS PARA ESTER ---

    def test_detect_book_key_esther(self) -> None:
        """Verifica la detección automática de clave para Ester."""
        spec_est = {"questions": [{"id": "NQB-AT-EST-0001", "book": "Ester"}]}
        self.assertEqual(detect_book_key(spec_est), "esther")

        spec_alias = {"questions": [{"id": "NQB-AT-EST-0001", "book": "ester"}]}
        self.assertEqual(detect_book_key(spec_alias), "esther")

        spec_en = {"questions": [{"id": "NQB-AT-EST-0001", "book": "Esther"}]}
        self.assertEqual(detect_book_key(spec_en), "esther")

        spec_libro = {"questions": [{"id": "NQB-AT-EST-0001", "book": "Libro de Ester"}]}
        self.assertEqual(detect_book_key(spec_libro), "esther")

    def test_esther_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Ester: 10 capítulos, 1 bloque."""
        self.assertIn("esther", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["esther"]
        self.assertEqual(cfg["canonical_name"], "Ester")
        self.assertEqual(cfg["api_name"], "Ester")
        self.assertEqual(cfg["total_chapters"], 10)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 10, "esther-01-10.json"))
        self.assertTrue({"ester", "esther", "est"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_esther(self) -> None:
        """Verifica consistencia de IDs y referencias en Ester."""
        if not self.esther_questions:
            self.skipTest("esther-master-input.json no disponible")
        self.assertEqual(len(self.esther_questions), 50)
        for qid, q in self.esther_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    # --- TESTS PARA JOB ---

    def test_detect_book_key_job(self) -> None:
        """Verifica la detección automática de clave para Job."""
        spec_job = {"questions": [{"id": "NQB-AT-JOB-0001", "book": "Job"}]}
        self.assertEqual(detect_book_key(spec_job), "job")

        spec_alias = {"questions": [{"id": "NQB-AT-JOB-0001", "book": "job"}]}
        self.assertEqual(detect_book_key(spec_alias), "job")

        spec_libro = {"questions": [{"id": "NQB-AT-JOB-0001", "book": "Libro de Job"}]}
        self.assertEqual(detect_book_key(spec_libro), "job")

    def test_job_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Job: 42 capítulos, 5 bloques."""
        self.assertIn("job", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["job"]
        self.assertEqual(cfg["canonical_name"], "Job")
        self.assertEqual(cfg["api_name"], "Job")
        self.assertEqual(cfg["total_chapters"], 42)
        self.assertEqual(len(cfg["blocks"]), 5)
        self.assertEqual(cfg["blocks"][0], (1, 10, "job-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 20, "job-11-20.json"))
        self.assertEqual(cfg["blocks"][2], (21, 30, "job-21-30.json"))
        self.assertEqual(cfg["blocks"][3], (31, 40, "job-31-40.json"))
        self.assertEqual(cfg["blocks"][4], (41, 42, "job-41-42.json"))
        self.assertTrue({"job", "libro de job"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_job(self) -> None:
        """Verifica consistencia de IDs y referencias en Job."""
        if not self.job_questions:
            self.skipTest("job-master-input.json no disponible")
        self.assertEqual(len(self.job_questions), 60)
        for qid, q in self.job_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    # --- TESTS PARA SALMOS ---

    def test_detect_book_key_psalms(self) -> None:
        """Verifica la detección automática de clave para Salmos."""
        spec_sal = {"questions": [{"id": "NQB-AT-SAL-0001", "book": "Salmos"}]}
        self.assertEqual(detect_book_key(spec_sal), "psalms")

        spec_alias = {"questions": [{"id": "NQB-AT-SAL-0001", "book": "salmos"}]}
        self.assertEqual(detect_book_key(spec_alias), "psalms")

        spec_en = {"questions": [{"id": "NQB-AT-SAL-0001", "book": "Psalms"}]}
        self.assertEqual(detect_book_key(spec_en), "psalms")

        spec_sing = {"questions": [{"id": "NQB-AT-SAL-0001", "book": "Salmo"}]}
        self.assertEqual(detect_book_key(spec_sing), "psalms")

        spec_libro = {"questions": [{"id": "NQB-AT-SAL-0001", "book": "Libro de los Salmos"}]}
        self.assertEqual(detect_book_key(spec_libro), "psalms")

    def test_psalms_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Salmos: 150 capítulos, 15 bloques."""
        self.assertIn("psalms", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["psalms"]
        self.assertEqual(cfg["canonical_name"], "Salmos")
        self.assertEqual(cfg["api_name"], "Salmos")
        self.assertEqual(cfg["total_chapters"], 150)
        self.assertEqual(len(cfg["blocks"]), 15)
        self.assertEqual(cfg["blocks"][0], (1, 10, "psalms-001-010.json"))
        self.assertEqual(cfg["blocks"][14], (141, 150, "psalms-141-150.json"))
        self.assertTrue({"salmos", "salmo", "psalms", "psalm"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_psalms(self) -> None:
        """Verifica consistencia de IDs y referencias en Salmos (90 preguntas, 79 salmos representados de 150)."""
        if not self.psalms_questions:
            self.skipTest("psalms-master-input.json no disponible")
        self.assertEqual(len(self.psalms_questions), 90)
        chapters_seen = set()
        for qid, q in self.psalms_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 150, f"Capítulo {ch} fuera del rango 1..150 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
        self.assertEqual(len(chapters_seen), 79, f"Se esperaban 79 salmos representados editorialmente, hallados {len(chapters_seen)}")

    # --- TESTS PARA PROVERBIOS ---

    def test_detect_book_key_proverbs(self) -> None:
        """Verifica la detección automática de clave para Proverbios."""
        spec_pro = {"questions": [{"id": "NQB-AT-PRO-0001", "book": "Proverbios"}]}
        self.assertEqual(detect_book_key(spec_pro), "proverbs")

        spec_alias = {"questions": [{"id": "NQB-AT-PRO-0001", "book": "proverbios"}]}
        self.assertEqual(detect_book_key(spec_alias), "proverbs")

        spec_en = {"questions": [{"id": "NQB-AT-PRO-0001", "book": "Proverbs"}]}
        self.assertEqual(detect_book_key(spec_en), "proverbs")

        spec_sing = {"questions": [{"id": "NQB-AT-PRO-0001", "book": "Proverbio"}]}
        self.assertEqual(detect_book_key(spec_sing), "proverbs")

        spec_libro = {"questions": [{"id": "NQB-AT-PRO-0001", "book": "Libro de Proverbios"}]}
        self.assertEqual(detect_book_key(spec_libro), "proverbs")

    def test_proverbs_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Proverbios: 31 capítulos, 4 bloques."""
        self.assertIn("proverbs", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["proverbs"]
        self.assertEqual(cfg["canonical_name"], "Proverbios")
        self.assertEqual(cfg["api_name"], "Proverbios")
        self.assertEqual(cfg["total_chapters"], 31)
        self.assertEqual(len(cfg["blocks"]), 4)
        self.assertEqual(cfg["blocks"][0], (1, 10, "proverbs-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 20, "proverbs-11-20.json"))
        self.assertEqual(cfg["blocks"][2], (21, 30, "proverbs-21-30.json"))
        self.assertEqual(cfg["blocks"][3], (31, 31, "proverbs-31.json"))
        self.assertTrue({"proverbios", "proverbio", "proverbs", "proverb"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_proverbs(self) -> None:
        """Verifica consistencia de IDs y referencias en Proverbios (72 preguntas, 31/31 capítulos cubiertos)."""
        if not self.proverbs_questions:
            self.skipTest("proverbs-master-input.json no disponible")
        self.assertEqual(len(self.proverbs_questions), 72)
        chapters_seen = set()
        for qid, q in self.proverbs_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 31, f"Capítulo {ch} fuera del rango 1..31 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
        self.assertEqual(len(chapters_seen), 31, f"Se esperaban 31 capítulos cubiertos, hallados {len(chapters_seen)}")

    # --- TESTS PARA ECLESIASTÉS ---

    def test_detect_book_key_ecclesiastes(self) -> None:
        """Verifica la detección automática de clave para Eclesiastés (con y sin tilde)."""
        spec_ecl = {"questions": [{"id": "NQB-AT-ECL-0001", "book": "Eclesiastés"}]}
        self.assertEqual(detect_book_key(spec_ecl), "ecclesiastes")

        spec_notilde = {"questions": [{"id": "NQB-AT-ECL-0001", "book": "Eclesiastes"}]}
        self.assertEqual(detect_book_key(spec_notilde), "ecclesiastes")

        spec_alias = {"questions": [{"id": "NQB-AT-ECL-0001", "book": "eclesiastes"}]}
        self.assertEqual(detect_book_key(spec_alias), "ecclesiastes")

        spec_en = {"questions": [{"id": "NQB-AT-ECL-0001", "book": "Ecclesiastes"}]}
        self.assertEqual(detect_book_key(spec_en), "ecclesiastes")

        spec_libro = {"questions": [{"id": "NQB-AT-ECL-0001", "book": "Libro de Eclesiastés"}]}
        self.assertEqual(detect_book_key(spec_libro), "ecclesiastes")

    def test_ecclesiastes_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Eclesiastés: 12 capítulos, 2 bloques."""
        self.assertIn("ecclesiastes", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["ecclesiastes"]
        self.assertEqual(cfg["canonical_name"], "Eclesiastés")
        self.assertEqual(cfg["api_name"], "Eclesiastés")
        self.assertEqual(cfg["total_chapters"], 12)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertEqual(cfg["blocks"][0], (1, 10, "ecclesiastes-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 12, "ecclesiastes-11-12.json"))
        self.assertTrue({"eclesiastes", "eclesiastés", "ecclesiastes"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_ecclesiastes(self) -> None:
        """Verifica consistencia de IDs, referencias y tipos en Eclesiastés (49 preguntas, 12/12 capítulos cubiertos)."""
        if not self.ecclesiastes_questions:
            self.skipTest("ecclesiastes-master-input.json no disponible")
        self.assertEqual(len(self.ecclesiastes_questions), 49)
        chapters_seen = set()
        for qid, q in self.ecclesiastes_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 12, f"Capítulo {ch} fuera del rango 1..12 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")
        self.assertEqual(len(chapters_seen), 12, f"Se esperaban 12 capítulos cubiertos, hallados {len(chapters_seen)}")

    # --- TESTS PARA CANTAR DE LOS CANTARES ---

    def test_detect_book_key_song_of_songs(self) -> None:
        """Verifica la detección automática de clave para Cantar de los Cantares."""
        spec_sos = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Cantar de los Cantares"}]}
        self.assertEqual(detect_book_key(spec_sos), "song_of_songs")

        spec_cantares = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Cantares"}]}
        self.assertEqual(detect_book_key(spec_cantares), "song_of_songs")

        spec_cantar = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Cantar"}]}
        self.assertEqual(detect_book_key(spec_cantar), "song_of_songs")

        spec_en = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Song of Songs"}]}
        self.assertEqual(detect_book_key(spec_en), "song_of_songs")

        spec_solomon = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Song of Solomon"}]}
        self.assertEqual(detect_book_key(spec_solomon), "song_of_songs")

        spec_libro = {"questions": [{"id": "NQB-AT-CAN-0001", "book": "Libro de los Cantares"}]}
        self.assertEqual(detect_book_key(spec_libro), "song_of_songs")

    def test_song_of_songs_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Cantar de los Cantares: 8 capítulos, 1 bloque."""
        self.assertIn("song_of_songs", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["song_of_songs"]
        self.assertEqual(cfg["canonical_name"], "Cantar de los Cantares")
        self.assertEqual(cfg["api_name"], "Cantares")
        self.assertEqual(cfg["total_chapters"], 8)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 8, "song-of-songs-01-08.json"))
        self.assertTrue({"cantar de los cantares", "cantares", "cantar", "song of songs"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_song_of_songs(self) -> None:
        """Verifica consistencia de IDs, referencias y campos en Cantar de los Cantares (40 preguntas, 8/8 capítulos cubiertos)."""
        if not self.song_of_songs_questions:
            self.skipTest("song-of-songs-master-input.json no disponible")
        self.assertEqual(len(self.song_of_songs_questions), 40)
        chapters_seen = set()
        for qid, q in self.song_of_songs_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 8, f"Capítulo {ch} fuera del rango 1..8 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("category"), "AT_GENERAL")
        self.assertEqual(len(chapters_seen), 8, f"Se esperaban 8 capítulos cubiertos, hallados {len(chapters_seen)}")

    # --- TESTS PARA ISAÍAS ---

    def test_detect_book_key_isaiah(self) -> None:
        """Verifica la detección automática de clave para Isaías (con y sin tilde)."""
        spec_isa = {"questions": [{"id": "NQB-AT-ISA-0001", "book": "Isaías"}]}
        self.assertEqual(detect_book_key(spec_isa), "isaiah")

        spec_notilde = {"questions": [{"id": "NQB-AT-ISA-0001", "book": "Isaias"}]}
        self.assertEqual(detect_book_key(spec_notilde), "isaiah")

        spec_alias = {"questions": [{"id": "NQB-AT-ISA-0001", "book": "isaias"}]}
        self.assertEqual(detect_book_key(spec_alias), "isaiah")

        spec_en = {"questions": [{"id": "NQB-AT-ISA-0001", "book": "Isaiah"}]}
        self.assertEqual(detect_book_key(spec_en), "isaiah")

        spec_libro = {"questions": [{"id": "NQB-AT-ISA-0001", "book": "Libro de Isaías"}]}
        self.assertEqual(detect_book_key(spec_libro), "isaiah")

    def test_isaiah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Isaías: 66 capítulos, 7 bloques."""
        self.assertIn("isaiah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["isaiah"]
        self.assertEqual(cfg["canonical_name"], "Isaías")
        self.assertEqual(cfg["api_name"], "Isaías")
        self.assertEqual(cfg["total_chapters"], 66)
        self.assertEqual(len(cfg["blocks"]), 7)
        self.assertEqual(cfg["blocks"][0], (1, 10, "isaiah-01-10.json"))
        self.assertEqual(cfg["blocks"][6], (61, 66, "isaiah-61-66.json"))
        self.assertTrue({"isaías", "isaias", "isaiah"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_isaiah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Isaías (90 preguntas, 66/66 capítulos cubiertos, 11 con additional_references, 16 totales)."""
        if not self.isaiah_questions:
            self.skipTest("isaiah-master-input.json no disponible")
        self.assertEqual(len(self.isaiah_questions), 90)
        chapters_seen = set()
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.isaiah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 66, f"Capítulo {ch} fuera del rango 1..66 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        self.assertEqual(len(chapters_seen), 66, f"Se esperaban 66 capítulos cubiertos, hallados {len(chapters_seen)}")
        self.assertEqual(questions_with_add_refs, 11, f"Se esperaban 11 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 16, f"Se esperaban 16 referencias adicionales en total, halladas {total_add_refs}")

    # --- TESTS PARA JEREMÍAS ---

    def test_detect_book_key_jeremiah(self) -> None:
        """Verifica la detección automática de clave para Jeremías (con y sin tilde)."""
        spec_jer = {"questions": [{"id": "NQB-AT-JER-0001", "book": "Jeremías"}]}
        self.assertEqual(detect_book_key(spec_jer), "jeremiah")

        spec_notilde = {"questions": [{"id": "NQB-AT-JER-0001", "book": "Jeremias"}]}
        self.assertEqual(detect_book_key(spec_notilde), "jeremiah")

        spec_alias = {"questions": [{"id": "NQB-AT-JER-0001", "book": "jeremias"}]}
        self.assertEqual(detect_book_key(spec_alias), "jeremiah")

        spec_en = {"questions": [{"id": "NQB-AT-JER-0001", "book": "Jeremiah"}]}
        self.assertEqual(detect_book_key(spec_en), "jeremiah")

        spec_libro = {"questions": [{"id": "NQB-AT-JER-0001", "book": "Libro de Jeremías"}]}
        self.assertEqual(detect_book_key(spec_libro), "jeremiah")

    def test_jeremiah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Jeremías: 52 capítulos, 6 bloques."""
        self.assertIn("jeremiah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["jeremiah"]
        self.assertEqual(cfg["canonical_name"], "Jeremías")
        self.assertEqual(cfg["api_name"], "Jeremías")
        self.assertEqual(cfg["total_chapters"], 52)
        self.assertEqual(len(cfg["blocks"]), 6)
        self.assertEqual(cfg["blocks"][0], (1, 10, "jeremiah-01-10.json"))
        self.assertEqual(cfg["blocks"][5], (51, 52, "jeremiah-51-52.json"))
        self.assertTrue({"jeremías", "jeremias", "jeremiah"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_jeremiah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Jeremías (79 preguntas, 52/52 capítulos cubiertos, 4 con additional_references, 8 totales)."""
        if not self.jeremiah_questions:
            self.skipTest("jeremiah-master-input.json no disponible")
        self.assertEqual(len(self.jeremiah_questions), 79)
        chapters_seen = set()
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.jeremiah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 52, f"Capítulo {ch} fuera del rango 1..52 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        self.assertEqual(len(chapters_seen), 52, f"Se esperaban 52 capítulos cubiertos, hallados {len(chapters_seen)}")
        self.assertEqual(questions_with_add_refs, 4, f"Se esperaban 4 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 8, f"Se esperaban 8 referencias adicionales en total, halladas {total_add_refs}")

    # --- TESTS PARA LAMENTACIONES ---

    def test_detect_book_key_lamentations(self) -> None:
        """Verifica la detección automática de clave para Lamentaciones."""
        spec_lam = {"questions": [{"id": "NQB-AT-LAM-0001", "book": "Lamentaciones"}]}
        self.assertEqual(detect_book_key(spec_lam), "lamentations")

        spec_alias = {"questions": [{"id": "NQB-AT-LAM-0001", "book": "lamentaciones"}]}
        self.assertEqual(detect_book_key(spec_alias), "lamentations")

        spec_en = {"questions": [{"id": "NQB-AT-LAM-0001", "book": "Lamentations"}]}
        self.assertEqual(detect_book_key(spec_en), "lamentations")

        spec_libro = {"questions": [{"id": "NQB-AT-LAM-0001", "book": "Libro de Lamentaciones"}]}
        self.assertEqual(detect_book_key(spec_libro), "lamentations")

        spec_las = {"questions": [{"id": "NQB-AT-LAM-0001", "book": "Libro de las Lamentaciones"}]}
        self.assertEqual(detect_book_key(spec_las), "lamentations")

    def test_lamentations_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Lamentaciones: 5 capítulos, 1 bloque."""
        self.assertIn("lamentations", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["lamentations"]
        self.assertEqual(cfg["canonical_name"], "Lamentaciones")
        self.assertEqual(cfg["api_name"], "Lamentaciones")
        self.assertEqual(cfg["total_chapters"], 5)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 5, "lamentations-01-05.json"))
        self.assertTrue({"lamentaciones", "lamentations"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_lamentations(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Lamentaciones (35 preguntas, 5/5 capítulos cubiertos, distribución 7/6/10/6/6, 0 additional_refs, 0 characters)."""
        if not self.lamentations_questions:
            self.skipTest("lamentations-master-input.json no disponible")
        self.assertEqual(len(self.lamentations_questions), 35)
        chapter_counts = {}
        for qid, q in self.lamentations_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 5, f"Capítulo {ch} fuera del rango 1..5 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")
            self.assertEqual(q.get("category"), "AT_GENERAL")
            self.assertEqual(len(q.get("additional_references", [])), 0)
            self.assertEqual(len(q.get("characters", [])), 0)

        self.assertEqual(chapter_counts, {1: 7, 2: 6, 3: 10, 4: 6, 5: 6})

    # --- TESTS PARA EZEQUIEL ---

    def test_detect_book_key_ezekiel(self) -> None:
        """Verifica la detección automática de clave para Ezequiel."""
        spec_eze = {"questions": [{"id": "NQB-AT-EZE-0001", "book": "Ezequiel"}]}
        self.assertEqual(detect_book_key(spec_eze), "ezekiel")

        spec_alias = {"questions": [{"id": "NQB-AT-EZE-0001", "book": "ezequiel"}]}
        self.assertEqual(detect_book_key(spec_alias), "ezekiel")

        spec_en = {"questions": [{"id": "NQB-AT-EZE-0001", "book": "Ezekiel"}]}
        self.assertEqual(detect_book_key(spec_en), "ezekiel")

        spec_libro = {"questions": [{"id": "NQB-AT-EZE-0001", "book": "Libro de Ezequiel"}]}
        self.assertEqual(detect_book_key(spec_libro), "ezekiel")

    def test_ezekiel_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Ezequiel: 48 capítulos, 5 bloques."""
        self.assertIn("ezekiel", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["ezekiel"]
        self.assertEqual(cfg["canonical_name"], "Ezequiel")
        self.assertEqual(cfg["api_name"], "Ezequiel")
        self.assertEqual(cfg["total_chapters"], 48)
        self.assertEqual(len(cfg["blocks"]), 5)
        self.assertEqual(cfg["blocks"][0], (1, 10, "ezekiel-01-10.json"))
        self.assertEqual(cfg["blocks"][4], (41, 48, "ezekiel-41-48.json"))
        self.assertTrue({"ezequiel", "ezekiel"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_ezekiel(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Ezequiel (86 preguntas, 48/48 capítulos cubiertos, 18 PERSONAJES_BIBLICOS, 68 AT_GENERAL, 0 additional_refs)."""
        if not self.ezekiel_questions:
            self.skipTest("ezekiel-master-input.json no disponible")
        self.assertEqual(len(self.ezekiel_questions), 86)
        chapters_seen = set()
        personajes_count = 0
        general_count = 0
        for qid, q in self.ezekiel_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 48, f"Capítulo {ch} fuera del rango 1..48 en {qid}")
            chapters_seen.add(ch)
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")
            self.assertEqual(len(q.get("additional_references", [])), 0)

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertEqual(q.get("characters"), ["Ezequiel"])
            elif cat == "AT_GENERAL":
                general_count += 1

        self.assertEqual(len(chapters_seen), 48, f"Se esperaban 48 capítulos cubiertos, hallados {len(chapters_seen)}")
        self.assertEqual(personajes_count, 18, f"Se esperaban 18 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 68, f"Se esperaban 68 preguntas de AT_GENERAL, halladas {general_count}")

    # --- TESTS PARA DANIEL ---

    def test_detect_book_key_daniel(self) -> None:
        """Verifica la detección automática de clave para Daniel."""
        spec_dan = {"questions": [{"id": "NQB-AT-DAN-0001", "book": "Daniel"}]}
        self.assertEqual(detect_book_key(spec_dan), "daniel")

        spec_alias = {"questions": [{"id": "NQB-AT-DAN-0001", "book": "daniel"}]}
        self.assertEqual(detect_book_key(spec_alias), "daniel")

        spec_libro = {"questions": [{"id": "NQB-AT-DAN-0001", "book": "Libro de Daniel"}]}
        self.assertEqual(detect_book_key(spec_libro), "daniel")

    def test_daniel_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Daniel: 12 capítulos, 1 bloque."""
        self.assertIn("daniel", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["daniel"]
        self.assertEqual(cfg["canonical_name"], "Daniel")
        self.assertEqual(cfg["api_name"], "Daniel")
        self.assertEqual(cfg["total_chapters"], 12)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 12, "daniel-01-12.json"))
        self.assertTrue({"daniel", "dan"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_daniel(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Daniel (50 preguntas, 12/12 capítulos cubiertos, distribución 5/6/5/4/4/5/5/4/5/2/3/2, 33 PERSONAJES_BIBLICOS, 17 AT_GENERAL, 0 additional_refs)."""
        if not self.daniel_questions:
            self.skipTest("daniel-master-input.json no disponible")
        self.assertEqual(len(self.daniel_questions), 50)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        for qid, q in self.daniel_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 12, f"Capítulo {ch} fuera del rango 1..12 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")
            self.assertEqual(len(q.get("additional_references", [])), 0)

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

        self.assertEqual(chapter_counts, {1: 5, 2: 6, 3: 5, 4: 4, 5: 4, 6: 5, 7: 5, 8: 4, 9: 5, 10: 2, 11: 3, 12: 2})
        self.assertEqual(personajes_count, 33, f"Se esperaban 33 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 17, f"Se esperaban 17 preguntas de AT_GENERAL, halladas {general_count}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Daniel"], 26)
        self.assertEqual(char_counts["Ananías"], 6)
        self.assertEqual(char_counts["Misael"], 6)
        self.assertEqual(char_counts["Azarías"], 6)
        self.assertEqual(char_counts["Nabucodonosor"], 10)
        self.assertEqual(char_counts["Sadrac"], 4)
        self.assertEqual(char_counts["Mesac"], 4)
        self.assertEqual(char_counts["Abed-nego"], 4)
        self.assertEqual(char_counts["Belsasar"], 4)
        self.assertEqual(char_counts["Darío"], 4)
        self.assertEqual(char_counts["Gabriel"], 2)
        self.assertEqual(char_counts["Miguel"], 2)

    # --- TESTS PARA OSEAS ---

    def test_detect_book_key_hosea(self) -> None:
        """Verifica la detección automática de clave para Oseas."""
        spec_hos = {"questions": [{"id": "NQB-AT-OSE-0001", "book": "Oseas"}]}
        self.assertEqual(detect_book_key(spec_hos), "hosea")

        spec_alias = {"questions": [{"id": "NQB-AT-OSE-0001", "book": "oseas"}]}
        self.assertEqual(detect_book_key(spec_alias), "hosea")

        spec_en = {"questions": [{"id": "NQB-AT-OSE-0001", "book": "Hosea"}]}
        self.assertEqual(detect_book_key(spec_en), "hosea")

        spec_libro = {"questions": [{"id": "NQB-AT-OSE-0001", "book": "Libro de Oseas"}]}
        self.assertEqual(detect_book_key(spec_libro), "hosea")

    def test_hosea_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Oseas: 14 capítulos, 1 bloque."""
        self.assertIn("hosea", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["hosea"]
        self.assertEqual(cfg["canonical_name"], "Oseas")
        self.assertEqual(cfg["api_name"], "Oseas")
        self.assertEqual(cfg["total_chapters"], 14)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 14, "hosea-01-14.json"))
        self.assertTrue({"oseas", "hosea", "os"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_hosea(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Oseas (50 preguntas, 14/14 capítulos cubiertos, distribución exacta, 42 AT_GENERAL, 8 PERSONAJES_BIBLICOS, 4 con additional_refs, 7 totales)."""
        if not self.hosea_questions:
            self.skipTest("hosea-master-input.json no disponible")
        self.assertEqual(len(self.hosea_questions), 50)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.hosea_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 14, f"Capítulo {ch} fuera del rango 1..14 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 5, 2: 5, 3: 4, 4: 4, 5: 3, 6: 4, 7: 3, 8: 3, 9: 3, 10: 3, 11: 4, 12: 3, 13: 3, 14: 3}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 8, f"Se esperaban 8 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 42, f"Se esperaban 42 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 4, f"Se esperaban 4 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 7, f"Se esperaban 7 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Oseas"], 8)
        self.assertEqual(char_counts["Gomer"], 1)
        self.assertEqual(char_counts["Jezreel"], 1)
        self.assertEqual(char_counts["Lo-ruhama"], 1)
        self.assertEqual(char_counts["Lo-ammi"], 1)

    # --- TESTS PARA JOEL ---

    def test_detect_book_key_joel(self) -> None:
        """Verifica la detección automática de clave para Joel."""
        spec_joe = {"questions": [{"id": "NQB-AT-JOE-0001", "book": "Joel"}]}
        self.assertEqual(detect_book_key(spec_joe), "joel")

        spec_alias = {"questions": [{"id": "NQB-AT-JOE-0001", "book": "joel"}]}
        self.assertEqual(detect_book_key(spec_alias), "joel")

        spec_libro = {"questions": [{"id": "NQB-AT-JOE-0001", "book": "Libro de Joel"}]}
        self.assertEqual(detect_book_key(spec_libro), "joel")

    def test_joel_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Joel: 3 capítulos (RVR1960), 1 bloque."""
        self.assertIn("joel", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["joel"]
        self.assertEqual(cfg["canonical_name"], "Joel")
        self.assertEqual(cfg["api_name"], "Joel")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 3, "joel-01-03.json"))
        self.assertTrue({"joel", "jl"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_joel(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Joel (30 preguntas, 3/3 capítulos cubiertos, distribución 9/13/8, 29 AT_GENERAL, 1 PERSONAJES_BIBLICOS, 3 con additional_refs, 4 totales)."""
        if not self.joel_questions:
            self.skipTest("joel-master-input.json no disponible")
        self.assertEqual(len(self.joel_questions), 30)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.joel_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 3, f"Capítulo {ch} fuera del rango 1..3 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertEqual(q.get("characters"), ["Joel"])
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 9, 2: 13, 3: 8}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 1, f"Se esperaba 1 pregunta de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 29, f"Se esperaban 29 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 3, f"Se esperaban 3 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 4, f"Se esperaban 4 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Joel"], 1)

    # --- TESTS PARA AMÓS ---

    def test_detect_book_key_amos(self) -> None:
        """Verifica la detección automática de clave para Amós."""
        spec_amo = {"questions": [{"id": "NQB-AT-AMO-0001", "book": "Amós"}]}
        self.assertEqual(detect_book_key(spec_amo), "amos")

        spec_alias = {"questions": [{"id": "NQB-AT-AMO-0001", "book": "amos"}]}
        self.assertEqual(detect_book_key(spec_alias), "amos")

        spec_en = {"questions": [{"id": "NQB-AT-AMO-0001", "book": "Amos"}]}
        self.assertEqual(detect_book_key(spec_en), "amos")

        spec_libro = {"questions": [{"id": "NQB-AT-AMO-0001", "book": "Libro de Amós"}]}
        self.assertEqual(detect_book_key(spec_libro), "amos")

    def test_amos_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Amós: 9 capítulos, 1 bloque."""
        self.assertIn("amos", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["amos"]
        self.assertEqual(cfg["canonical_name"], "Amós")
        self.assertEqual(cfg["api_name"], "Amos")
        self.assertEqual(cfg["total_chapters"], 9)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 9, "amos-01-09.json"))
        self.assertTrue({"amos", "amós", "am"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_amos(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Amós (49 preguntas, 9/9 capítulos cubiertos, distribución 5/6/5/5/8/4/6/4/6, 43 AT_GENERAL, 6 PERSONAJES_BIBLICOS, 2 con additional_refs, 2 totales)."""
        if not self.amos_questions:
            self.skipTest("amos-master-input.json no disponible")
        self.assertEqual(len(self.amos_questions), 49)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.amos_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 9, f"Capítulo {ch} fuera del rango 1..9 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 5, 2: 6, 3: 5, 4: 5, 5: 8, 6: 4, 7: 6, 8: 4, 9: 6}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 6, f"Se esperaban 6 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 43, f"Se esperaban 43 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 2, f"Se esperaban 2 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 2, f"Se esperaban 2 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Amós"], 6)
        self.assertEqual(char_counts["Amasías"], 2)
        self.assertEqual(char_counts["Jeroboam"], 1)

    # --- TESTS PARA ABDÍAS ---

    def test_detect_book_key_obadiah(self) -> None:
        """Verifica la detección automática de clave para Abdías."""
        spec_oba = {"questions": [{"id": "NQB-AT-ABD-0001", "book": "Abdías"}]}
        self.assertEqual(detect_book_key(spec_oba), "obadiah")

        spec_alias = {"questions": [{"id": "NQB-AT-ABD-0001", "book": "abdias"}]}
        self.assertEqual(detect_book_key(spec_alias), "obadiah")

        spec_en = {"questions": [{"id": "NQB-AT-ABD-0001", "book": "Obadiah"}]}
        self.assertEqual(detect_book_key(spec_en), "obadiah")

        spec_libro = {"questions": [{"id": "NQB-AT-ABD-0001", "book": "Libro de Abdías"}]}
        self.assertEqual(detect_book_key(spec_libro), "obadiah")

    def test_obadiah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Abdías: 1 capítulo, 1 bloque."""
        self.assertIn("obadiah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["obadiah"]
        self.assertEqual(cfg["canonical_name"], "Abdías")
        self.assertEqual(cfg["api_name"], "Abdias")
        self.assertEqual(cfg["total_chapters"], 1)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 1, "obadiah-01-01.json"))
        self.assertTrue({"abdias", "abdías", "obadiah", "ob"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_obadiah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Abdías (24 preguntas, 1/1 capítulos cubiertos, distribución 1=24, 23 AT_GENERAL, 1 PERSONAJES_BIBLICOS, 3 con additional_refs, 3 totales)."""
        if not self.obadiah_questions:
            self.skipTest("obadiah-master-input.json no disponible")
        self.assertEqual(len(self.obadiah_questions), 24)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.obadiah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertEqual(ch, 1, f"Capítulo fuera de rango en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertEqual(q.get("characters"), ["Abdías"])
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 24}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 1, f"Se esperaba 1 pregunta de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 23, f"Se esperaban 23 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 3, f"Se esperaban 3 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 3, f"Se esperaban 3 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Abdías"], 1)

    # --- TESTS PARA JONÁS ---

    def test_detect_book_key_jonah(self) -> None:
        """Verifica la detección automática de clave para Jonás."""
        spec_jon = {"questions": [{"id": "NQB-AT-JON-0001", "book": "Jonás"}]}
        self.assertEqual(detect_book_key(spec_jon), "jonah")

        spec_alias = {"questions": [{"id": "NQB-AT-JON-0001", "book": "jonas"}]}
        self.assertEqual(detect_book_key(spec_alias), "jonah")

        spec_en = {"questions": [{"id": "NQB-AT-JON-0001", "book": "Jonah"}]}
        self.assertEqual(detect_book_key(spec_en), "jonah")

        spec_libro = {"questions": [{"id": "NQB-AT-JON-0001", "book": "Libro de Jonás"}]}
        self.assertEqual(detect_book_key(spec_libro), "jonah")

    def test_jonah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Jonás: 4 capítulos, 1 bloque."""
        self.assertIn("jonah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["jonah"]
        self.assertEqual(cfg["canonical_name"], "Jonás")
        self.assertEqual(cfg["api_name"], "Jonas")
        self.assertEqual(cfg["total_chapters"], 4)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 4, "jonah-01-04.json"))
        self.assertTrue({"jonas", "jonás", "jonah", "jon"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_jonah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Jonás (40 preguntas, 4/4 capítulos cubiertos, distribución 11/9/10/10, 13 AT_GENERAL, 27 PERSONAJES_BIBLICOS, 2 con additional_refs, 3 totales)."""
        if not self.jonah_questions:
            self.skipTest("jonah-master-input.json no disponible")
        self.assertEqual(len(self.jonah_questions), 40)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.jonah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 4, f"Capítulo {ch} fuera del rango 1..4 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 11, 2: 9, 3: 10, 4: 10}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 27, f"Se esperaban 27 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 13, f"Se esperaban 13 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 2, f"Se esperaban 2 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 3, f"Se esperaban 3 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Jonás"], 22)
        self.assertEqual(char_counts["Marineros"], 6)
        self.assertEqual(char_counts["Capitán"], 1)
        self.assertEqual(char_counts["Rey de Nínive"], 3)
        self.assertEqual(char_counts["Ninivitas"], 1)

    # --- TESTS PARA MIQUEAS ---

    def test_detect_book_key_micah(self) -> None:
        """Verifica la detección automática de clave para Miqueas."""
        spec_mic = {"questions": [{"id": "NQB-AT-MIQ-0001", "book": "Miqueas"}]}
        self.assertEqual(detect_book_key(spec_mic), "micah")

        spec_alias = {"questions": [{"id": "NQB-AT-MIQ-0001", "book": "miqueas"}]}
        self.assertEqual(detect_book_key(spec_alias), "micah")

        spec_en = {"questions": [{"id": "NQB-AT-MIQ-0001", "book": "Micah"}]}
        self.assertEqual(detect_book_key(spec_en), "micah")

        spec_libro = {"questions": [{"id": "NQB-AT-MIQ-0001", "book": "Libro de Miqueas"}]}
        self.assertEqual(detect_book_key(spec_libro), "micah")

    def test_micah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Miqueas: 7 capítulos, 1 bloque."""
        self.assertIn("micah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["micah"]
        self.assertEqual(cfg["canonical_name"], "Miqueas")
        self.assertEqual(cfg["api_name"], "Miqueas")
        self.assertEqual(cfg["total_chapters"], 7)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 7, "micah-01-07.json"))
        self.assertTrue({"miqueas", "micah", "miq"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_micah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Miqueas (48 preguntas, 7/7 capítulos cubiertos, distribución 6/7/7/8/7/7/6, 41 AT_GENERAL, 7 PERSONAJES_BIBLICOS, 3 con additional_refs, 4 totales)."""
        if not self.micah_questions:
            self.skipTest("micah-master-input.json no disponible")
        self.assertEqual(len(self.micah_questions), 48)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.micah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 7, f"Capítulo {ch} fuera del rango 1..7 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 6, 2: 7, 3: 7, 4: 8, 5: 7, 6: 7, 7: 6}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 7, f"Se esperaban 7 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 41, f"Se esperaban 41 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 3, f"Se esperaban 3 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 4, f"Se esperaban 4 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Miqueas"], 5)
        self.assertEqual(char_counts["Gobernantes de Israel"], 1)
        self.assertEqual(char_counts["Profetas"], 1)

    # --- TESTS PARA NAHÚM ---

    def test_detect_book_key_nahum(self) -> None:
        """Verifica la detección automática de clave para Nahúm."""
        spec_nah = {"questions": [{"id": "NQB-AT-NAH-0001", "book": "Nahúm"}]}
        self.assertEqual(detect_book_key(spec_nah), "nahum")

        spec_alias = {"questions": [{"id": "NQB-AT-NAH-0001", "book": "nahum"}]}
        self.assertEqual(detect_book_key(spec_alias), "nahum")

        spec_en = {"questions": [{"id": "NQB-AT-NAH-0001", "book": "Nahum"}]}
        self.assertEqual(detect_book_key(spec_en), "nahum")

        spec_libro = {"questions": [{"id": "NQB-AT-NAH-0001", "book": "Libro de Nahúm"}]}
        self.assertEqual(detect_book_key(spec_libro), "nahum")

    def test_nahum_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Nahúm: 3 capítulos, 1 bloque."""
        self.assertIn("nahum", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["nahum"]
        self.assertEqual(cfg["canonical_name"], "Nahúm")
        self.assertEqual(cfg["api_name"], "Nahum")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 3, "nahum-01-03.json"))
        self.assertTrue({"nahum", "nahúm", "nah"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_nahum(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Nahúm (34 preguntas, 3/3 capítulos cubiertos, distribución 12/11/11, 33 AT_GENERAL, 1 PERSONAJES_BIBLICOS, 1 con additional_refs, 1 total)."""
        if not self.nahum_questions:
            self.skipTest("nahum-master-input.json no disponible")
        self.assertEqual(len(self.nahum_questions), 34)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.nahum_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 3, f"Capítulo {ch} fuera del rango 1..3 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 12, 2: 11, 3: 11}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 1, f"Se esperaba 1 pregunta de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 33, f"Se esperaban 33 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 1, f"Se esperaba 1 pregunta con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 1, f"Se esperaba 1 referencia adicional en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Nahúm"], 1)

    # --- TESTS PARA HABACUC ---

    def test_detect_book_key_habakkuk(self) -> None:
        """Verifica la detección automática de clave para Habacuc."""
        spec_hab = {"questions": [{"id": "NQB-AT-HAB-0001", "book": "Habacuc"}]}
        self.assertEqual(detect_book_key(spec_hab), "habakkuk")

        spec_alias = {"questions": [{"id": "NQB-AT-HAB-0001", "book": "habacuc"}]}
        self.assertEqual(detect_book_key(spec_alias), "habakkuk")

        spec_en = {"questions": [{"id": "NQB-AT-HAB-0001", "book": "Habakkuk"}]}
        self.assertEqual(detect_book_key(spec_en), "habakkuk")

        spec_libro = {"questions": [{"id": "NQB-AT-HAB-0001", "book": "Libro de Habacuc"}]}
        self.assertEqual(detect_book_key(spec_libro), "habakkuk")

    def test_habakkuk_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Habacuc: 3 capítulos, 1 bloque."""
        self.assertIn("habakkuk", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["habakkuk"]
        self.assertEqual(cfg["canonical_name"], "Habacuc")
        self.assertEqual(cfg["api_name"], "Habacuc")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 3, "habakkuk-01-03.json"))
        self.assertTrue({"habacuc", "habakkuk", "hab"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_habakkuk(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Habacuc (36 preguntas, 3/3 capítulos cubiertos, distribución 12/13/11, 29 AT_GENERAL, 7 PERSONAJES_BIBLICOS, 2 con additional_refs, 4 totales)."""
        if not self.habakkuk_questions:
            self.skipTest("habakkuk-master-input.json no disponible")
        self.assertEqual(len(self.habakkuk_questions), 36)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.habakkuk_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 3, f"Capítulo {ch} fuera del rango 1..3 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 12, 2: 13, 3: 11}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 7, f"Se esperaban 7 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 29, f"Se esperaban 29 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 2, f"Se esperaban 2 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 4, f"Se esperaban 4 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Habacuc"], 7)

    # --- TESTS PARA SOFONÍAS ---

    def test_detect_book_key_zephaniah(self) -> None:
        """Verifica la detección automática de clave para Sofonías."""
        spec_zep = {"questions": [{"id": "NQB-AT-SOF-0001", "book": "Sofonías"}]}
        self.assertEqual(detect_book_key(spec_zep), "zephaniah")

        spec_alias = {"questions": [{"id": "NQB-AT-SOF-0001", "book": "sofonias"}]}
        self.assertEqual(detect_book_key(spec_alias), "zephaniah")

        spec_en = {"questions": [{"id": "NQB-AT-SOF-0001", "book": "Zephaniah"}]}
        self.assertEqual(detect_book_key(spec_en), "zephaniah")

        spec_libro = {"questions": [{"id": "NQB-AT-SOF-0001", "book": "Libro de Sofonías"}]}
        self.assertEqual(detect_book_key(spec_libro), "zephaniah")

    def test_zephaniah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Sofonías: 3 capítulos, 1 bloque."""
        self.assertIn("zephaniah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["zephaniah"]
        self.assertEqual(cfg["canonical_name"], "Sofonías")
        self.assertEqual(cfg["api_name"], "Sofonias")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 3, "zephaniah-01-03.json"))
        self.assertTrue({"sofonias", "sofonías", "zephaniah", "sof"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_zephaniah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Sofonías (38 preguntas, 3/3 capítulos cubiertos, distribución 14/11/13, 36 AT_GENERAL, 2 PERSONAJES_BIBLICOS, 0 con additional_refs, 0 totales)."""
        if not self.zephaniah_questions:
            self.skipTest("zephaniah-master-input.json no disponible")
        self.assertEqual(len(self.zephaniah_questions), 38)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.zephaniah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 3, f"Capítulo {ch} fuera del rango 1..3 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 14, 2: 11, 3: 13}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 2, f"Se esperaban 2 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 36, f"Se esperaban 36 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 0, f"Se esperaban 0 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 0, f"Se esperaban 0 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Sofonías"], 2)
        self.assertEqual(char_counts["Josías"], 1)

    # --- TESTS PARA HAGEO ---

    def test_detect_book_key_haggai(self) -> None:
        """Verifica la detección automática de clave para Hageo."""
        spec_hag = {"questions": [{"id": "NQB-AT-HAG-0001", "book": "Hageo"}]}
        self.assertEqual(detect_book_key(spec_hag), "haggai")

        spec_alias = {"questions": [{"id": "NQB-AT-HAG-0001", "book": "hageo"}]}
        self.assertEqual(detect_book_key(spec_alias), "haggai")

        spec_en = {"questions": [{"id": "NQB-AT-HAG-0001", "book": "Haggai"}]}
        self.assertEqual(detect_book_key(spec_en), "haggai")

        spec_libro = {"questions": [{"id": "NQB-AT-HAG-0001", "book": "Libro de Hageo"}]}
        self.assertEqual(detect_book_key(spec_libro), "haggai")

    def test_haggai_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Hageo: 2 capítulos, 1 bloque."""
        self.assertIn("haggai", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["haggai"]
        self.assertEqual(cfg["canonical_name"], "Hageo")
        self.assertEqual(cfg["api_name"], "Hageo")
        self.assertEqual(cfg["total_chapters"], 2)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 2, "haggai-01-02.json"))
        self.assertTrue({"hageo", "haggai", "hag"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_haggai(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Hageo (34 preguntas, 2/2 capítulos cubiertos, distribución 14/20, 28 AT_GENERAL, 6 PERSONAJES_BIBLICOS, 1 con additional_refs, 1 total)."""
        if not self.haggai_questions:
            self.skipTest("haggai-master-input.json no disponible")
        self.assertEqual(len(self.haggai_questions), 34)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.haggai_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 2, f"Capítulo {ch} fuera del rango 1..2 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 14, 2: 20}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 6, f"Se esperaban 6 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 28, f"Se esperaban 28 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 1, f"Se esperaba 1 pregunta con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 1, f"Se esperaba 1 referencia adicional en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Hageo"], 4)
        self.assertEqual(char_counts["Zorobabel"], 5)
        self.assertEqual(char_counts["Josué"], 4)
        self.assertEqual(char_counts["remanente"], 3)

    # --- TESTS PARA ZACARÍAS ---

    def test_detect_book_key_zechariah(self) -> None:
        """Verifica la detección automática de clave para Zacarías."""
        spec_zec = {"questions": [{"id": "NQB-AT-ZAC-0001", "book": "Zacarías"}]}
        self.assertEqual(detect_book_key(spec_zec), "zechariah")

        spec_alias = {"questions": [{"id": "NQB-AT-ZAC-0001", "book": "zacarias"}]}
        self.assertEqual(detect_book_key(spec_alias), "zechariah")

        spec_en = {"questions": [{"id": "NQB-AT-ZAC-0001", "book": "Zechariah"}]}
        self.assertEqual(detect_book_key(spec_en), "zechariah")

        spec_libro = {"questions": [{"id": "NQB-AT-ZAC-0001", "book": "Libro de Zacarías"}]}
        self.assertEqual(detect_book_key(spec_libro), "zechariah")

    def test_zechariah_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Zacarías: 14 capítulos, 1 bloque."""
        self.assertIn("zechariah", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["zechariah"]
        self.assertEqual(cfg["canonical_name"], "Zacarías")
        self.assertEqual(cfg["api_name"], "Zacarias")
        self.assertEqual(cfg["total_chapters"], 14)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 14, "zechariah-01-14.json"))
        self.assertTrue({"zacarias", "zacarías", "zechariah", "zac"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_zechariah(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Zacarías (70 preguntas, 14/14 capítulos cubiertos, distribución 5/cap, 57 AT_GENERAL, 13 PERSONAJES_BIBLICOS, 5 con additional_refs, 8 totales)."""
        if not self.zechariah_questions:
            self.skipTest("zechariah-master-input.json no disponible")
        self.assertEqual(len(self.zechariah_questions), 70)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.zechariah_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 14, f"Capítulo {ch} fuera del rango 1..14 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {i: 5 for i in range(1, 15)}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 13, f"Se esperaban 13 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 57, f"Se esperaban 57 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 5, f"Se esperaban 5 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 8, f"Se esperaban 8 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Zacarías"], 6)
        self.assertEqual(char_counts["Darío"], 1)
        self.assertEqual(char_counts["ángel intérprete"], 2)
        self.assertEqual(char_counts["Josué"], 5)
        self.assertEqual(char_counts["Satanás"], 2)
        self.assertEqual(char_counts["ángel de Jehová"], 1)
        self.assertEqual(char_counts["Zorobabel"], 2)
        self.assertEqual(char_counts["enviados de Bet-el"], 1)

    # --- TESTS PARA MALAQUÍAS ---

    def test_detect_book_key_malachi(self) -> None:
        """Verifica la detección automática de clave para Malaquías."""
        spec_mal = {"questions": [{"id": "NQB-AT-MAL-0001", "book": "Malaquías"}]}
        self.assertEqual(detect_book_key(spec_mal), "malachi")

        spec_alias = {"questions": [{"id": "NQB-AT-MAL-0001", "book": "malaquias"}]}
        self.assertEqual(detect_book_key(spec_alias), "malachi")

        spec_en = {"questions": [{"id": "NQB-AT-MAL-0001", "book": "Malachi"}]}
        self.assertEqual(detect_book_key(spec_en), "malachi")

        spec_libro = {"questions": [{"id": "NQB-AT-MAL-0001", "book": "Libro de Malaquías"}]}
        self.assertEqual(detect_book_key(spec_libro), "malachi")

    def test_malachi_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Malaquías: 4 capítulos, 1 bloque."""
        self.assertIn("malachi", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["malachi"]
        self.assertEqual(cfg["canonical_name"], "Malaquías")
        self.assertEqual(cfg["api_name"], "Malaquias")
        self.assertEqual(cfg["total_chapters"], 4)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertEqual(cfg["blocks"][0], (1, 4, "malachi-01-04.json"))
        self.assertTrue({"malaquias", "malaquías", "malachi", "mal"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_malachi(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Malaquías (44 preguntas, 4/4 capítulos cubiertos, distribución 10/12/15/7, 42 AT_GENERAL, 2 PERSONAJES_BIBLICOS, 4 con additional_refs, 6 totales)."""
        if not self.malachi_questions:
            self.skipTest("malachi-master-input.json no disponible")
        self.assertEqual(len(self.malachi_questions), 44)
        chapter_counts = {}
        personajes_count = 0
        general_count = 0
        all_chars = []
        questions_with_add_refs = 0
        total_add_refs = 0
        for qid, q in self.malachi_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 4, f"Capítulo {ch} fuera del rango 1..4 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))
            self.assertEqual(q.get("question_type"), "MULTIPLE_CHOICE")

            all_chars.extend(q.get("characters", []))

            cat = q.get("category")
            if cat == "PERSONAJES_BIBLICOS":
                personajes_count += 1
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")
            elif cat == "AT_GENERAL":
                general_count += 1

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_dist = {1: 10, 2: 12, 3: 15, 4: 7}
        self.assertEqual(chapter_counts, expected_dist)
        self.assertEqual(personajes_count, 2, f"Se esperaban 2 preguntas de PERSONAJES_BIBLICOS, halladas {personajes_count}")
        self.assertEqual(general_count, 42, f"Se esperaban 42 preguntas de AT_GENERAL, halladas {general_count}")
        self.assertEqual(questions_with_add_refs, 4, f"Se esperaban 4 preguntas con additional_references, halladas {questions_with_add_refs}")
        self.assertEqual(total_add_refs, 6, f"Se esperaban 6 referencias adicionales en total, halladas {total_add_refs}")

        char_counts = collections.Counter(all_chars)
        self.assertEqual(char_counts["Malaquías"], 1)
        self.assertEqual(char_counts["Elías"], 1)

    def get_matthew_question(self, qid: str) -> dict:
        self.assertIn(qid, self.matthew_questions, f"ID '{qid}' no encontrado en matthew-master-input.json")
        return copy.deepcopy(self.matthew_questions[qid])

    def test_detect_book_key_matthew(self) -> None:
        """Verifica detección de book_key para Mateo y sus variantes."""
        spec_mat = {"questions": [{"id": "NQB-NT-MAT-0001", "book": "Mateo"}]}
        self.assertEqual(detect_book_key(spec_mat), "matthew")

        spec_alias = {"questions": [{"id": "NQB-NT-MAT-0001", "book": "mateo"}]}
        self.assertEqual(detect_book_key(spec_alias), "matthew")

        spec_en = {"questions": [{"id": "NQB-NT-MAT-0001", "book": "Matthew"}]}
        self.assertEqual(detect_book_key(spec_en), "matthew")

        spec_libro = {"questions": [{"id": "NQB-NT-MAT-0001", "book": "Evangelio de Mateo"}]}
        self.assertEqual(detect_book_key(spec_libro), "matthew")

    def test_matthew_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Mateo: 28 capítulos, 3 bloques."""
        self.assertIn("matthew", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["matthew"]
        self.assertEqual(cfg["canonical_name"], "Mateo")
        self.assertEqual(cfg["api_name"], "Mateo")
        self.assertEqual(cfg["total_chapters"], 28)
        self.assertEqual(len(cfg["blocks"]), 3)
        self.assertEqual(cfg["blocks"][0], (1, 10, "matthew-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 20, "matthew-11-20.json"))
        self.assertEqual(cfg["blocks"][2], (21, 28, "matthew-21-28.json"))
        self.assertTrue({"mateo", "matthew", "mt", "libro de mateo"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_matthew(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Mateo (92 preguntas, 28/28 capítulos cubiertos, 83 MULTIPLE_CHOICE, 9 TRUE_FALSE, 10 con additional_refs, 15 totales)."""
        if not self.matthew_questions:
            self.skipTest("matthew-master-input.json no disponible")
        self.assertEqual(len(self.matthew_questions), 92)
        chapter_counts = {}
        category_counts = collections.Counter()
        type_counts = collections.Counter()
        difficulty_counts = collections.Counter()
        questions_with_add_refs = 0
        total_add_refs = 0
        all_chars = []

        for qid, q in self.matthew_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 28, f"Capítulo {ch} fuera del rango 1..28 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))

            q_type = q.get("question_type", "MULTIPLE_CHOICE")
            type_counts[q_type] += 1

            if q_type == "MULTIPLE_CHOICE":
                for opt in ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]:
                    self.assertTrue(bool(str(q.get(opt, "")).strip()), f"Opción {opt} vacía en {qid}")
            elif q_type == "TRUE_FALSE":
                self.assertTrue(bool(str(q.get("opcion_a", "")).strip()), f"Opción A vacía en {qid}")
                self.assertTrue(bool(str(q.get("opcion_b", "")).strip()), f"Opción B vacía en {qid}")
                self.assertEqual(str(q.get("opcion_c", "")).strip(), "", f"Opción C no vacía en TRUE_FALSE {qid}")
                self.assertEqual(str(q.get("opcion_d", "")).strip(), "", f"Opción D no vacía en TRUE_FALSE {qid}")

            cat = q.get("category")
            category_counts[cat] += 1
            if cat == "PERSONAJES_BIBLICOS":
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")

            diff = q.get("difficulty")
            difficulty_counts[diff] += 1

            all_chars.extend(q.get("characters", []))

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)

        expected_ch_dist = {
            1: 4, 2: 3, 3: 3, 4: 3, 5: 4, 6: 3, 7: 3, 8: 3, 9: 3, 10: 3,
            11: 3, 12: 3, 13: 4, 14: 3, 15: 3, 16: 3, 17: 3, 18: 3, 19: 3, 20: 3,
            21: 3, 22: 3, 23: 3, 24: 3, 25: 4, 26: 5, 27: 5, 28: 3
        }
        self.assertEqual(chapter_counts, expected_ch_dist)
        self.assertEqual(type_counts, {"MULTIPLE_CHOICE": 83, "TRUE_FALSE": 9})
        self.assertEqual(difficulty_counts, {"Básico": 27, "Intermedio": 35, "Avanzado": 25, "Experto": 5})
        self.assertEqual(category_counts, {
            "NT_GENERAL": 11,
            "PERSONAJES_BIBLICOS": 20,
            "JESUS_PALABRAS": 35,
            "JESUS_MILAGROS": 14,
            "JESUS_PARABOLAS": 12
        })
        self.assertEqual(questions_with_add_refs, 10)
        self.assertEqual(total_add_refs, 15)

    def test_true_false_auditor_type_aware(self) -> None:
        """Verifica que el auditor trate TRUE_FALSE de manera type-aware (2 opciones válidas vs 4 opciones en MULTIPLE_CHOICE)."""
        # 1. Pregunta TRUE_FALSE canónica de Mateo (2 opciones)
        q_tf = {
            "id": "NQB-NT-MAT-TEST-01",
            "book": "Mateo",
            "chapter": 1,
            "verse_start": 23,
            "verse_end": 23,
            "reference": "Mateo 1:23",
            "category": "NT_GENERAL",
            "difficulty": "Básico",
            "question_type": "TRUE_FALSE",
            "question": "¿El nombre Emanuel significa 'Dios con nosotros'?",
            "opcion_a": "Verdadero",
            "opcion_b": "Falso",
            "opcion_c": "",
            "opcion_d": "",
            "correct_option": "A",
            "correct_answer": "Verdadero",
            "explanation": "Mateo 1:23 declara que Emanuel traducido es: Dios con nosotros."
        }
        verse_map = {23: "He aquí, una virgen concebirá y dará a luz un hijo, Y llamarás su nombre Emanuel, que traducido es: Dios con nosotros."}
        res_tf = evaluate_question(q_tf, verse_map, book_key="matthew")
        self.assertEqual(res_tf["controles_superados"]["control_distractores_invalidos"], "PASS")
        self.assertEqual(res_tf["controles_superados"]["control_sin_ambiguedad"], "PASS")

        # 2. Mutación negativa: Pregunta MULTIPLE_CHOICE con opciones C y D vacías debe dar FAIL
        q_mc_invalid = copy.deepcopy(q_tf)
        q_mc_invalid["question_type"] = "MULTIPLE_CHOICE"
        res_mc = evaluate_question(q_mc_invalid, verse_map, book_key="matthew")
        self.assertEqual(res_mc["controles_superados"]["control_distractores_invalidos"], "FAIL")
        self.assertEqual(res_mc["controles_superados"]["control_sin_ambiguedad"], "FAIL")

    def get_mark_question(self, qid: str) -> dict:
        self.assertIn(qid, self.mark_questions, f"ID '{qid}' no encontrado en mark-master-input.json")
        return copy.deepcopy(self.mark_questions[qid])

    def test_detect_book_key_mark(self) -> None:
        """Verifica detección de book_key para Marcos y sus variantes."""
        spec_mar = {"questions": [{"id": "NQB-NT-MAR-0001", "book": "Marcos"}]}
        self.assertEqual(detect_book_key(spec_mar), "mark")

        spec_alias = {"questions": [{"id": "NQB-NT-MAR-0001", "book": "marcos"}]}
        self.assertEqual(detect_book_key(spec_alias), "mark")

        spec_en = {"questions": [{"id": "NQB-NT-MAR-0001", "book": "Mark"}]}
        self.assertEqual(detect_book_key(spec_en), "mark")

        spec_mc = {"questions": [{"id": "NQB-NT-MAR-0001", "book": "mc"}]}
        self.assertEqual(detect_book_key(spec_mc), "mark")

        spec_libro = {"questions": [{"id": "NQB-NT-MAR-0001", "book": "Evangelio de Marcos"}]}
        self.assertEqual(detect_book_key(spec_libro), "mark")

    def test_mark_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Marcos: 16 capítulos, 2 bloques."""
        self.assertIn("mark", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["mark"]
        self.assertEqual(cfg["canonical_name"], "Marcos")
        self.assertEqual(cfg["api_name"], "Marcos")
        self.assertEqual(cfg["total_chapters"], 16)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertEqual(cfg["blocks"][0], (1, 8, "mark-01-08.json"))
        self.assertEqual(cfg["blocks"][1], (9, 16, "mark-09-16.json"))
        self.assertTrue({"marcos", "mark", "mc", "libro de marcos", "evangelio de marcos"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_mark(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Marcos (74 preguntas, 16/16 capítulos cubiertos, 67 MULTIPLE_CHOICE, 7 TRUE_FALSE, 9 con additional_refs, 12 totales)."""
        if not self.mark_questions:
            self.skipTest("mark-master-input.json no disponible")
        self.assertEqual(len(self.mark_questions), 74)
        chapter_counts = {}
        category_counts = collections.Counter()
        type_counts = collections.Counter()
        difficulty_counts = collections.Counter()
        questions_with_add_refs = 0
        total_add_refs = 0
        all_chars = []

        expected_add_refs_map = {
            "NQB-NT-MAR-0002": ["Malaquías 3:1", "Isaías 40:3"],
            "NQB-NT-MAR-0009": ["1 Samuel 21:1-6"],
            "NQB-NT-MAR-0029": ["Isaías 29:13"],
            "NQB-NT-MAR-0049": ["Isaías 56:7", "Jeremías 7:11"],
            "NQB-NT-MAR-0051": ["Salmos 118:22-23"],
            "NQB-NT-MAR-0053": ["Deuteronomio 6:4-5", "Levítico 19:18"],
            "NQB-NT-MAR-0054": ["Salmos 110:1"],
            "NQB-NT-MAR-0063": ["Zacarías 13:7"],
            "NQB-NT-MAR-0068": ["Salmos 22:1"],
        }

        for qid, q in self.mark_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 16, f"Capítulo {ch} fuera del rango 1..16 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))

            q_type = q.get("question_type", "MULTIPLE_CHOICE")
            type_counts[q_type] += 1

            if q_type == "MULTIPLE_CHOICE":
                for opt in ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]:
                    self.assertTrue(bool(str(q.get(opt, "")).strip()), f"Opción {opt} vacía en {qid}")
            elif q_type == "TRUE_FALSE":
                self.assertTrue(bool(str(q.get("opcion_a", "")).strip()), f"Opción A vacía en {qid}")
                self.assertTrue(bool(str(q.get("opcion_b", "")).strip()), f"Opción B vacía en {qid}")
                self.assertEqual(str(q.get("opcion_c", "")).strip(), "", f"Opción C no vacía en TRUE_FALSE {qid}")
                self.assertEqual(str(q.get("opcion_d", "")).strip(), "", f"Opción D no vacía en TRUE_FALSE {qid}")

            cat = q.get("category")
            category_counts[cat] += 1
            if cat == "PERSONAJES_BIBLICOS":
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")

            diff = q.get("difficulty")
            difficulty_counts[diff] += 1

            all_chars.extend(q.get("characters", []))

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)
                self.assertIn(qid, expected_add_refs_map)
                self.assertEqual(add_refs, expected_add_refs_map[qid])

        expected_ch_dist = {
            1: 5, 2: 4, 3: 4, 4: 5, 5: 5, 6: 5, 7: 4, 8: 5,
            9: 4, 10: 5, 11: 4, 12: 5, 13: 4, 14: 6, 15: 5, 16: 4
        }
        self.assertEqual(chapter_counts, expected_ch_dist)
        self.assertEqual(type_counts, {"MULTIPLE_CHOICE": 67, "TRUE_FALSE": 7})
        self.assertEqual(difficulty_counts, {"Básico": 10, "Intermedio": 27, "Avanzado": 28, "Experto": 9})
        self.assertEqual(category_counts, {
            "NT_GENERAL": 16,
            "PERSONAJES_BIBLICOS": 17,
            "JESUS_PALABRAS": 22,
            "JESUS_MILAGROS": 14,
            "JESUS_PARABOLAS": 5
        })
        self.assertEqual(questions_with_add_refs, 9)
        self.assertEqual(total_add_refs, 12)

    def get_luke_question(self, qid: str) -> dict:
        self.assertIn(qid, self.luke_questions, f"ID '{qid}' no encontrado en luke-master-input.json")
        return copy.deepcopy(self.luke_questions[qid])

    def test_detect_book_key_luke(self) -> None:
        """Verifica detección de book_key para Lucas y sus variantes."""
        spec_luk = {"questions": [{"id": "NQB-NT-LUC-0001", "book": "Lucas"}]}
        self.assertEqual(detect_book_key(spec_luk), "luke")

        spec_alias = {"questions": [{"id": "NQB-NT-LUC-0001", "book": "lucas"}]}
        self.assertEqual(detect_book_key(spec_alias), "luke")

        spec_en = {"questions": [{"id": "NQB-NT-LUC-0001", "book": "Luke"}]}
        self.assertEqual(detect_book_key(spec_en), "luke")

        spec_lc = {"questions": [{"id": "NQB-NT-LUC-0001", "book": "lc"}]}
        self.assertEqual(detect_book_key(spec_lc), "luke")

        spec_libro = {"questions": [{"id": "NQB-NT-LUC-0001", "book": "Evangelio de Lucas"}]}
        self.assertEqual(detect_book_key(spec_libro), "luke")

    def test_luke_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Lucas: 24 capítulos, 3 bloques."""
        self.assertIn("luke", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["luke"]
        self.assertEqual(cfg["canonical_name"], "Lucas")
        self.assertEqual(cfg["api_name"], "Lucas")
        self.assertEqual(cfg["total_chapters"], 24)
        self.assertEqual(len(cfg["blocks"]), 3)
        self.assertEqual(cfg["blocks"][0], (1, 8, "luke-01-08.json"))
        self.assertEqual(cfg["blocks"][1], (9, 16, "luke-09-16.json"))
        self.assertEqual(cfg["blocks"][2], (17, 24, "luke-17-24.json"))
        self.assertTrue({"lucas", "luke", "lc", "libro de lucas", "evangelio de lucas"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_luke(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Lucas (96 preguntas, 24/24 capítulos cubiertos, 4 por capítulo, 89 MULTIPLE_CHOICE, 7 TRUE_FALSE, 9 con additional_refs, 12 totales)."""
        if not self.luke_questions:
            self.skipTest("luke-master-input.json no disponible")
        self.assertEqual(len(self.luke_questions), 96)
        chapter_counts = {}
        category_counts = collections.Counter()
        type_counts = collections.Counter()
        difficulty_counts = collections.Counter()
        questions_with_add_refs = 0
        total_add_refs = 0
        all_chars = []

        expected_add_refs_map = {
            "NQB-NT-LUC-0004": ["1 Samuel 2:1-10"],
            "NQB-NT-LUC-0007": ["Isaías 49:6"],
            "NQB-NT-LUC-0013": ["Isaías 61:1-2"],
            "NQB-NT-LUC-0014": ["1 Reyes 17:8-16", "2 Reyes 5:1-14"],
            "NQB-NT-LUC-0043": ["Jonás 3:5-10", "1 Reyes 10:1-10"],
            "NQB-NT-LUC-0076": ["Isaías 56:7", "Jeremías 7:11"],
            "NQB-NT-LUC-0078": ["Salmos 118:22"],
            "NQB-NT-LUC-0080": ["Éxodo 3:6"],
            "NQB-NT-LUC-0094": ["Moisés y los profetas"],
        }

        for qid, q in self.luke_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 24, f"Capítulo {ch} fuera del rango 1..24 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            self.assertEqual(q.get("correct_option"), "A")
            self.assertEqual(q.get("correct_answer"), q.get("opcion_a"))

            q_type = q.get("question_type", "MULTIPLE_CHOICE")
            type_counts[q_type] += 1

            if q_type == "MULTIPLE_CHOICE":
                for opt in ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]:
                    self.assertTrue(bool(str(q.get(opt, "")).strip()), f"Opción {opt} vacía en {qid}")
            elif q_type == "TRUE_FALSE":
                self.assertTrue(bool(str(q.get("opcion_a", "")).strip()), f"Opción A vacía en {qid}")
                self.assertTrue(bool(str(q.get("opcion_b", "")).strip()), f"Opción B vacía en {qid}")
                self.assertEqual(str(q.get("opcion_c", "")).strip(), "", f"Opción C no vacía en TRUE_FALSE {qid}")
                self.assertEqual(str(q.get("opcion_d", "")).strip(), "", f"Opción D no vacía en TRUE_FALSE {qid}")

            cat = q.get("category")
            category_counts[cat] += 1
            if cat == "PERSONAJES_BIBLICOS":
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")

            diff = q.get("difficulty")
            difficulty_counts[diff] += 1

            all_chars.extend(q.get("characters", []))

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)
                self.assertIn(qid, expected_add_refs_map)
                self.assertEqual(add_refs, expected_add_refs_map[qid])

        expected_ch_dist = {i: 4 for i in range(1, 25)}
        self.assertEqual(chapter_counts, expected_ch_dist)
        self.assertEqual(type_counts, {"MULTIPLE_CHOICE": 89, "TRUE_FALSE": 7})
        self.assertEqual(difficulty_counts, {"Básico": 24, "Intermedio": 35, "Avanzado": 32, "Experto": 5})
        self.assertEqual(category_counts, {
            "NT_GENERAL": 3,
            "PERSONAJES_BIBLICOS": 33,
            "JESUS_PALABRAS": 29,
            "JESUS_MILAGROS": 11,
            "JESUS_PARABOLAS": 20
        })
        self.assertEqual(questions_with_add_refs, 9)
        self.assertEqual(total_add_refs, 12)

    def test_is_narrative_source_attribution_generic_cases(self) -> None:
        """Verifica la distinción genérica entre personajes participantes y atribuciones narrativas/fuentes."""
        # Caso 1: Atribución del narrador en opción A ("Lucas señala...")
        text_case1 = "Vuelve agradeciendo a Dios, y Lucas señala que era samaritano"
        self.assertTrue(is_narrative_source_attribution("lucas", text_case1))

        # Caso 2: Personaje bíblico participante real ("Lucas acompañó a Pablo") -> NO es atribución
        text_case2 = "Lucas acompañó a Pablo en sus viajes misioneros"
        self.assertFalse(is_narrative_source_attribution("lucas", text_case2))

        # Caso 3: Prefijo de fuente ("según Lucas...")
        text_case3 = "La ofrenda fue destacada según Lucas como un acto de fe"
        self.assertTrue(is_narrative_source_attribution("lucas", text_case3))

        # Caso 4: Generalización a otros libros y narradores ("Marcos relata...", "Mateo menciona...", "Juan presenta...")
        self.assertTrue(is_narrative_source_attribution("marcos", "Marcos relata la curación del ciego"))
        self.assertTrue(is_narrative_source_attribution("mateo", "Mateo menciona la genealogía"))
        self.assertTrue(is_narrative_source_attribution("juan", "Juan presenta el discurso del pan de vida"))
        self.assertTrue(is_narrative_source_attribution("lucas", "En el relato de Lucas sobre el buen samaritano"))
        self.assertTrue(is_narrative_source_attribution("lucas", "Como subraya Lucas en su evangelio"))

        # Caso 5: Nombre de libro/personaje sin patrón de atribución -> NO queda excluido
        self.assertFalse(is_narrative_source_attribution("samuel", "Samuel habló al pueblo con firmeza"))
        self.assertFalse(is_narrative_source_attribution("david", "David derrotó a Goliat en el valle"))

    def test_nqb_nt_luc_0068_narrative_attribution_resolved(self) -> None:
        """Verifica que NQB-NT-LUC-0068 no falle en control_nombres_propios ni control_rango_suficiente."""
        if "NQB-NT-LUC-0068" not in self.luke_questions:
            self.skipTest("NQB-NT-LUC-0068 no disponible en luke-master-input.json")

        q = self.get_luke_question("NQB-NT-LUC-0068")
        verse_map = {
            11: "Yendo Jesús a Jerusalén, pasaba entre Samaria y Galilea.",
            12: "Y al entrar en una aldea, le salieron al encuentro diez hombres leprosos, los cuales se pararon de lejos",
            13: "y alzaron la voz, diciendo: ¡Jesús, Maestro, ten misericordia de nosotros!",
            14: "Cuando él los vio, les dijo: Id, mostraos a los sacerdotes. Y aconteció que mientras iban, fueron limpiados.",
            15: "Entonces uno de ellos, viendo que había sido sanado, volvió, glorificando a Dios a gran voz,",
            16: "y se postró rostro en tierra a sus pies, dándole gracias; y éste era samaritano.",
            17: "Respondiendo Jesús, dijo: ¿No son diez los que fueron limpiados? Y los nueve, ¿dónde están?",
            18: "¿No hubo quien volviese y diese gloria a Dios sino este extranjero?",
            19: "Y le dijo: Levántate, vete; tu fe te ha salvado."
        }

        res = evaluate_question(q, verse_map, book_key="luke")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["incidencias"], [])

    def get_john_question(self, qid: str) -> dict:
        self.assertIn(qid, self.john_questions, f"ID '{qid}' no encontrado en john-master-input.json")
        return copy.deepcopy(self.john_questions[qid])

    def test_detect_book_key_john(self) -> None:
        """Verifica detección de book_key para Juan y sus variantes."""
        spec_joh = {"questions": [{"id": "NQB-NT-JUA-0001", "book": "Juan"}]}
        self.assertEqual(detect_book_key(spec_joh), "john")

        spec_alias = {"questions": [{"id": "NQB-NT-JUA-0001", "book": "juan"}]}
        self.assertEqual(detect_book_key(spec_alias), "john")

        spec_en = {"questions": [{"id": "NQB-NT-JUA-0001", "book": "John"}]}
        self.assertEqual(detect_book_key(spec_en), "john")

        spec_jn = {"questions": [{"id": "NQB-NT-JUA-0001", "book": "jn"}]}
        self.assertEqual(detect_book_key(spec_jn), "john")

        spec_libro = {"questions": [{"id": "NQB-NT-JUA-0001", "book": "Evangelio de Juan"}]}
        self.assertEqual(detect_book_key(spec_libro), "john")

    def test_john_book_config_and_aliases(self) -> None:
        """Verifica configuración canónica de Juan: 21 capítulos, 2 bloques."""
        self.assertIn("john", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["john"]
        self.assertEqual(cfg["canonical_name"], "Juan")
        self.assertEqual(cfg["api_name"], "Juan")
        self.assertEqual(cfg["total_chapters"], 21)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertEqual(cfg["blocks"][0], (1, 10, "john-01-10.json"))
        self.assertEqual(cfg["blocks"][1], (11, 21, "john-11-21.json"))
        self.assertTrue({"juan", "john", "jn", "libro de juan", "evangelio de juan"}.issubset(cfg["aliases"]))

    def test_global_canonical_id_reference_integrity_john(self) -> None:
        """Verifica consistencia de IDs, referencias y metadatos en Juan (100 preguntas, 21/21 capítulos cubiertos, 92 MULTIPLE_CHOICE, 8 TRUE_FALSE, 10 con additional_refs, 16 totales)."""
        if not self.john_questions:
            self.skipTest("john-master-input.json no disponible")
        self.assertEqual(len(self.john_questions), 100)
        chapter_counts = {}
        category_counts = collections.Counter()
        type_counts = collections.Counter()
        difficulty_counts = collections.Counter()
        questions_with_add_refs = 0
        total_add_refs = 0
        all_chars = []

        expected_add_refs_map = {
            "NQB-NT-JUA-0007": ["Salmos 69:9"],
            "NQB-NT-JUA-0011": ["Números 21:8-9"],
            "NQB-NT-JUA-0026": ["Éxodo 16:4-15"],
            "NQB-NT-JUA-0047": ["Salmos 82:6"],
            "NQB-NT-JUA-0056": ["Zacarías 9:9", "Salmos 118:25-26"],
            "NQB-NT-JUA-0059": ["Isaías 53:1", "Isaías 6:10"],
            "NQB-NT-JUA-0061": ["Salmos 41:9"],
            "NQB-NT-JUA-0072": ["Salmos 35:19", "Salmos 69:4"],
            "NQB-NT-JUA-0087": ["Salmos 22:18"],
            "NQB-NT-JUA-0089": ["Éxodo 12:46", "Números 9:12", "Salmos 34:20", "Zacarías 12:10"],
        }

        for qid, q in self.john_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            self.assertIsNotNone(ch)
            self.assertTrue(1 <= ch <= 21, f"Capítulo {ch} fuera del rango 1..21 en {qid}")
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )
            corr_opt = q.get("correct_option")
            corr_ans = q.get("correct_answer")
            if corr_opt == "A":
                self.assertEqual(corr_ans, q.get("opcion_a"))
            elif corr_opt == "B":
                self.assertEqual(corr_ans, q.get("opcion_b"))

            q_type = q.get("question_type", "MULTIPLE_CHOICE")
            type_counts[q_type] += 1

            if q_type == "MULTIPLE_CHOICE":
                self.assertEqual(corr_opt, "A")
                for opt in ["opcion_a", "opcion_b", "opcion_c", "opcion_d"]:
                    self.assertTrue(bool(str(q.get(opt, "")).strip()), f"Opción {opt} vacía en {qid}")
            elif q_type == "TRUE_FALSE":
                self.assertTrue(bool(str(q.get("opcion_a", "")).strip()), f"Opción A vacía en {qid}")
                self.assertTrue(bool(str(q.get("opcion_b", "")).strip()), f"Opción B vacía en {qid}")
                self.assertEqual(str(q.get("opcion_c", "")).strip(), "", f"Opción C no vacía en TRUE_FALSE {qid}")
                self.assertEqual(str(q.get("opcion_d", "")).strip(), "", f"Opción D no vacía en TRUE_FALSE {qid}")

            cat = q.get("category")
            category_counts[cat] += 1
            if cat == "PERSONAJES_BIBLICOS":
                self.assertGreater(len(q.get("characters", [])), 0, f"Pregunta de personajes sin characters en {qid}")

            diff = q.get("difficulty")
            difficulty_counts[diff] += 1

            all_chars.extend(q.get("characters", []))

            add_refs = q.get("additional_references", [])
            if len(add_refs) > 0:
                questions_with_add_refs += 1
                total_add_refs += len(add_refs)
                self.assertIn(qid, expected_add_refs_map)
                self.assertEqual(add_refs, expected_add_refs_map[qid])

        expected_ch_dist = {
            1: 5, 2: 4, 3: 5, 4: 5, 5: 4, 6: 6, 7: 4, 8: 6, 9: 4, 10: 5,
            11: 6, 12: 5, 13: 5, 14: 5, 15: 4, 16: 4, 17: 4, 18: 4, 19: 5, 20: 5, 21: 5
        }
        self.assertEqual(chapter_counts, expected_ch_dist)
        self.assertEqual(type_counts, {"MULTIPLE_CHOICE": 92, "TRUE_FALSE": 8})
        self.assertEqual(difficulty_counts, {"Básico": 23, "Intermedio": 39, "Avanzado": 29, "Experto": 9})
        self.assertEqual(dict(category_counts), {
            "NT_GENERAL": 7,
            "PERSONAJES_BIBLICOS": 35,
            "JESUS_PALABRAS": 50,
            "JESUS_MILAGROS": 8
        })
        self.assertEqual(category_counts.get("JESUS_PARABOLAS", 0), 0)
        self.assertEqual(questions_with_add_refs, 10)
        self.assertEqual(total_add_refs, 16)

    def test_true_false_inverted_options_order(self) -> None:
        """Verifica que TRUE_FALSE con opcion_a='Falso' y opcion_b='Verdadero' funcione correctamente sin forzar A='Verdadero'."""
        q_tf_inv = {
            "id": "NQB-NT-JUA-TEST-TF",
            "book": "Juan",
            "chapter": 10,
            "verse_start": 40,
            "verse_end": 42,
            "reference": "Juan 10:40-42",
            "category": "NT_GENERAL",
            "difficulty": "Intermedio",
            "question_type": "TRUE_FALSE",
            "question": "Indica si es verdadero o falso que Juan realizó más señales milagrosas que Jesús",
            "opcion_a": "Falso",
            "opcion_b": "Verdadero",
            "opcion_c": "",
            "opcion_d": "",
            "correct_option": "A",
            "correct_answer": "Falso",
            "explanation": "Juan no hizo señales según el texto."
        }
        verse_map = {
            40: "Y se fue de nuevo al otro lado del Jordán, al lugar donde primero había estado bautizando Juan; y se quedó allí.",
            41: "Y muchos venían a él, y decían: Juan, a la verdad, ninguna señal hizo; pero todo lo que Juan dijo de éste, era verdad.",
            42: "Y muchos creyeron en él allí."
        }
        res = evaluate_question(q_tf_inv, verse_map, book_key="john")
        self.assertEqual(res["controles_superados"]["control_distractores_invalidos"], "PASS")
        self.assertEqual(res["controles_superados"]["control_sin_ambiguedad"], "PASS")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")

    def test_is_narrative_source_attribution_john_specific(self) -> None:
        """Verifica los casos específicos de Juan: atribución narrativa vs Juan el Bautista participante."""
        # 1. "Juan narra que..." -> atribución
        self.assertTrue(is_narrative_source_attribution("juan", "Juan narra que Jesús llegó a Samaria"))

        # 2. "Juan explica que..." -> atribución
        self.assertTrue(is_narrative_source_attribution("juan", "Juan explica que esto sucedió en Betania"))

        # 3. "Juan no hizo señales..." (Juan el Bautista participante) -> NO es atribución narrativa
        self.assertFalse(is_narrative_source_attribution("juan", "Juan no hizo señales según decían los testigos"))

        # 4. "Juan el Bautista..." -> personaje
        self.assertFalse(is_narrative_source_attribution("juan", "Juan el Bautista dio testimonio del Cordero de Dios"))

        # 5. "el evangelio de Juan..." -> fuente documental
        self.assertTrue(is_narrative_source_attribution("juan", "En el evangelio de Juan encontramos siete señales"))

    def test_is_biblical_place_usage_generic_cases(self) -> None:
        """Verifica la distinción genérica entre topónimos bíblicos y homógrafos comunes (ej: Ramá vs rama)."""
        # Caso A: Sustantivo botánico en metáfora ("La rama necesita permanecer unida a la vid") -> NO lugar
        self.assertFalse(is_biblical_place_usage("rama", "La rama necesita permanecer unida a la vid"))

        # Caso B: Sustantivo botánico cuantificado ("Cada rama lleva fruto") -> NO lugar
        self.assertFalse(is_biblical_place_usage("rama", "Cada rama produce mejor si se cuida"))

        # Caso C: Topónimo bíblico acentuado y locativo ("Samuel volvió a Ramá") -> SÍ lugar
        self.assertTrue(is_biblical_place_usage("rama", "Samuel volvió a Ramá"))

        # Caso D: Topónimo bíblico con prefijo locativo sin acento ("Fue a Rama") -> SÍ lugar
        self.assertTrue(is_biblical_place_usage("rama", "Fue a Rama para consultar al vidente"))

        # Caso E: Sustantivo común con complemento ("rama de un árbol") -> NO lugar
        self.assertFalse(is_biblical_place_usage("rama", "Una rama de un árbol cayó al camino"))

    def test_nqb_nt_jua_0070_homograph_resolved(self) -> None:
        """Verifica que NQB-NT-JUA-0070 (vid y ramas) no falle en control_lugares por el término botánico 'rama'."""
        if "NQB-NT-JUA-0070" not in self.john_questions:
            self.skipTest("NQB-NT-JUA-0070 no disponible")
        q = self.get_john_question("NQB-NT-JUA-0070")
        vmap = {
            1: "Yo soy la vid verdadera, y mi Padre es el labrador.",
            2: "Todo pámpano que en mí no lleva fruto, lo quitará; y todo aquel que lleva fruto, lo limpiará, para que lleve más fruto.",
            3: "Ya vosotros estáis limpios por la palabra que os he hablado.",
            4: "Permaneced en mí, y yo en vosotros. Como el pámpano no puede llevar fruto por sí mismo, si no permanece en la vid, así tampoco vosotros, si no permanecéis en mí.",
            5: "Yo soy la vid, vosotros los pámpanos; el que permanece en mí, y yo en él, éste lleva mucho fruto; porque separados de mí nada podéis hacer.",
            6: "El que en mí no permanece, será echado fuera como pámpano, y se secará; y los recogen, y los echan en el fuego, y arden.",
            7: "Si permanecéis en mí, y mis palabras permanecen en vosotros, pedid todo lo que queréis, y os será hecho.",
            8: "En esto es glorificado mi Padre, en que llevéis mucho fruto, y seáis así mis discípulos."
        }
        res = evaluate_question(q, vmap, book_key="john")
        self.assertEqual(res["controles_superados"]["control_lugares"], "NOT_APPLICABLE")
        self.assertNotEqual(res["controles_superados"]["control_rango_suficiente"], "FAIL")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["incidencias"], [])

    def test_resolve_implicit_speaker_first_person_jesus_cases(self) -> None:
        """Verifica la resolución contextual del referente de 1ª persona en discursos de Jesús."""
        # Caso A: Categoría JESUS_PALABRAS con 'de mí' -> resuelve a Jesús
        passage_a = "el dara testimonio acerca de mi"
        vmap_a = {26: "él dará testimonio acerca de mí"}
        self.assertTrue(resolve_implicit_speaker(
            "jesus", passage_a, vmap_a, 26, ["Jesús", "discípulos"],
            book_key="john", category="JESUS_PALABRAS"
        ))

        # Caso B: Texto con 'conmigo' -> resuelve a Jesús en discurso continuo
        passage_b = "porque habeis estado conmigo desde el principio"
        vmap_b = {27: "porque habéis estado conmigo desde el principio."}
        self.assertTrue(resolve_implicit_speaker(
            "jesus", passage_b, vmap_b, 27, ["Jesús", "discípulos"],
            book_key="john", category="JESUS_PALABRAS"
        ))

        # Caso C: Pasaje con otro orador explícito -> NO resuelve a Jesús
        passage_c = "pedro dijo no lo conozco ni se que dices"
        vmap_c = {60: "Pedro dijo: No lo conozco ni sé qué dices."}
        self.assertFalse(resolve_implicit_speaker(
            "jesus", passage_c, vmap_c, 60, ["Pedro", "Jesús"],
            book_key="john", category="NT_GENERAL"
        ))

        # Caso D: Categoría no JESUS_PALABRAS sin atribución discursiva
        passage_d = "los soldados dijeron hagamos esto entre nosotros"
        vmap_d = {24: "Los soldados dijeron: Hagamos esto entre nosotros."}
        self.assertFalse(resolve_implicit_speaker(
            "jesus", passage_d, vmap_d, 24, ["soldados"],
            book_key="john", category="NT_GENERAL"
        ))

    def test_nqb_nt_jua_0073_implicit_speaker_resolved(self) -> None:
        """Verifica que NQB-NT-JUA-0073 (Juan 15:26-27) resuelva 'Jesús' como referente de 1ª persona."""
        if "NQB-NT-JUA-0073" not in self.john_questions:
            self.skipTest("NQB-NT-JUA-0073 no disponible")
        q = self.get_john_question("NQB-NT-JUA-0073")
        vmap = {
            26: "Pero cuando venga el Consolador, a quien yo os enviaré del Padre, el Espíritu de verdad, el cual procede del Padre, él dará testimonio acerca de mí;",
            27: "y vosotros daréis testimonio también, porque habéis estado conmigo desde el principio."
        }
        res = evaluate_question(q, vmap, book_key="john")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res["controles_superados"]["control_rango_suficiente"], "FAIL")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["incidencias"], [])

    # --- PRUEBAS ESPECÍFICAS DE HECHOS ---

    def get_acts_question(self, qid: str) -> dict:
        self.assertIn(qid, self.acts_questions, f"ID '{qid}' no encontrado en acts-master-input.json")
        return copy.deepcopy(self.acts_questions[qid])

    def test_detect_book_key_acts(self) -> None:
        """Verifica detección de book_key para Hechos y sus variantes."""
        spec_act = {"questions": [{"id": "NQB-NT-HEC-0001", "book": "Hechos"}]}
        self.assertEqual(detect_book_key(spec_act), "acts")

        spec_alias = {"questions": [{"id": "NQB-NT-HEC-0001", "book": "hechos"}]}
        self.assertEqual(detect_book_key(spec_alias), "acts")

        spec_en = {"questions": [{"id": "NQB-NT-HEC-0001", "book": "Acts"}]}
        self.assertEqual(detect_book_key(spec_en), "acts")

        spec_hch = {"questions": [{"id": "NQB-NT-HEC-0001", "book": "hch"}]}
        self.assertEqual(detect_book_key(spec_hch), "acts")

        spec_libro = {"questions": [{"id": "NQB-NT-HEC-0001", "book": "Hechos de los Apóstoles"}]}
        self.assertEqual(detect_book_key(spec_libro), "acts")

    def test_acts_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Hechos en BOOK_CONFIGS."""
        self.assertIn("acts", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["acts"]
        self.assertEqual(cfg["canonical_name"], "Hechos")
        self.assertEqual(cfg["api_name"], "Hechos")
        self.assertEqual(cfg["total_chapters"], 28)
        self.assertEqual(len(cfg["blocks"]), 3)
        self.assertIn("hechos", cfg["aliases"])
        self.assertIn("acts", cfg["aliases"])
        self.assertIn("hch", cfg["aliases"])
        self.assertIn("jerusalen", cfg["ambient_places"])
        self.assertIn("antioquia", cfg["ambient_places"])
        self.assertIn("roma", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_acts(self) -> None:
        """Verifica consistencia de IDs y referencias en Hechos."""
        if not self.acts_questions:
            self.skipTest("acts-master-input.json no disponible")
        for qid, q in self.acts_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_acts_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Hechos."""
        if not self.acts_questions:
            self.skipTest("acts-master-input.json no disponible")
        self.assertEqual(len(self.acts_questions), 112)
        
        # 4 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.acts_questions.values())
        self.assertEqual(len(ch_counts), 28)
        for ch in range(1, 29):
            self.assertEqual(ch_counts[ch], 4, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 4")

        # Dificultad: Básico=26, Intermedio=52, Avanzado=26, Experto=8
        diff_counts = collections.Counter(q["difficulty"] for q in self.acts_questions.values())
        self.assertEqual(diff_counts["Básico"], 26)
        self.assertEqual(diff_counts["Intermedio"], 52)
        self.assertEqual(diff_counts["Avanzado"], 26)
        self.assertEqual(diff_counts["Experto"], 8)

        # Tipos: 103 MC, 9 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.acts_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 103)
        self.assertEqual(type_counts["TRUE_FALSE"], 9)

    def test_acts_additional_references(self) -> None:
        """Verifica las 11 preguntas con 14 referencias adicionales en Hechos."""
        if not self.acts_questions:
            self.skipTest("acts-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-HEC-0004": ["Salmos 69:25", "Salmos 109:8"],
            "NQB-NT-HEC-0006": ["Joel 2:28-32"],
            "NQB-NT-HEC-0012": ["Deuteronomio 18:15-19"],
            "NQB-NT-HEC-0013": ["Salmos 118:22"],
            "NQB-NT-HEC-0026": ["Éxodo 2:14"],
            "NQB-NT-HEC-0027": ["Isaías 66:1-2"],
            "NQB-NT-HEC-0031": ["Isaías 53:7-8"],
            "NQB-NT-HEC-0051": ["Salmos 2:7", "Isaías 55:3", "Salmos 16:10"],
            "NQB-NT-HEC-0059": ["Amós 9:11-12"],
            "NQB-NT-HEC-0068": ["Isaías 42:5"],
            "NQB-NT-HEC-0112": ["Isaías 6:9-10"]
        }
        found_add_refs = {}
        for qid, q in self.acts_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 11)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 14)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_acts_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Hechos."""
        if not self.acts_questions:
            self.skipTest("acts-master-input.json no disponible")
        for qid, q in self.acts_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_acts_implicit_speaker_speech_resolution(self) -> None:
        """Verifica resolución retrospectiva del orador en discursos apostólicos de Hechos."""
        # Discurso de Esteban en Hechos 7
        vmap_esteban = {
            2: "Y Esteban dijo: Varones hermanos y padres, oíd: El Dios de la gloria apareció a nuestro padre Abraham...",
            44: "Tuvieron nuestros padres el tabernáculo del testimonio en el desierto...",
            51: "¡Duros de cerviz, e incircuncisos de corazón y de oídos! Vosotros resistís siempre al Espíritu Santo; como vuestros padres, así también vosotros.",
            52: "¿A cuál de los profetas no persiguieron vuestros padres? Y mataron a los que anunciaron de antemano la venida del Justo, de quien vosotros ahora habéis sido entregadores y matadores;",
            53: "vosotros que recibisteis la ley por disposición de ángeles, y no la guardasteis."
        }
        res_esteban = resolve_implicit_speaker(
            "esteban", "tuvieron nuestros padres el tabernaculo del testimonio y nos dieron la ley",
            vmap_esteban, 51, ["Esteban"], book_key="acts", category="PERSONAJES_BIBLICOS"
        )
        self.assertTrue(res_esteban)

    # --- PRUEBAS ESPECÍFICAS DE ROMANOS ---

    def get_romans_question(self, qid: str) -> dict:
        self.assertIn(qid, self.romans_questions, f"ID '{qid}' no encontrado en romans-master-input.json")
        return copy.deepcopy(self.romans_questions[qid])

    def test_detect_book_key_romans(self) -> None:
        """Verifica detección de book_key para Romanos y sus variantes."""
        spec_rom = {"questions": [{"id": "NQB-NT-ROM-0001", "book": "Romanos"}]}
        self.assertEqual(detect_book_key(spec_rom), "romans")

        spec_alias = {"questions": [{"id": "NQB-NT-ROM-0001", "book": "romanos"}]}
        self.assertEqual(detect_book_key(spec_alias), "romans")

        spec_en = {"questions": [{"id": "NQB-NT-ROM-0001", "book": "Romans"}]}
        self.assertEqual(detect_book_key(spec_en), "romans")

        spec_rom_short = {"questions": [{"id": "NQB-NT-ROM-0001", "book": "rom"}]}
        self.assertEqual(detect_book_key(spec_rom_short), "romans")

        spec_carta = {"questions": [{"id": "NQB-NT-ROM-0001", "book": "Carta a los Romanos"}]}
        self.assertEqual(detect_book_key(spec_carta), "romans")

    def test_romans_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Romanos en BOOK_CONFIGS."""
        self.assertIn("romans", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["romans"]
        self.assertEqual(cfg["canonical_name"], "Romanos")
        self.assertEqual(cfg["api_name"], "Romanos")
        self.assertEqual(cfg["total_chapters"], 16)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertIn("romanos", cfg["aliases"])
        self.assertIn("romans", cfg["aliases"])
        self.assertIn("rom", cfg["aliases"])
        self.assertIn("roma", cfg["ambient_places"])
        self.assertIn("cencrea", cfg["ambient_places"])
        self.assertIn("espana", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_romans(self) -> None:
        """Verifica consistencia de IDs y referencias en Romanos."""
        if not self.romans_questions:
            self.skipTest("romans-master-input.json no disponible")
        for qid, q in self.romans_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_romans_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Romanos."""
        if not self.romans_questions:
            self.skipTest("romans-master-input.json no disponible")
        self.assertEqual(len(self.romans_questions), 80)
        
        # 5 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.romans_questions.values())
        self.assertEqual(len(ch_counts), 16)
        for ch in range(1, 17):
            self.assertEqual(ch_counts[ch], 5, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 5")

        # Dificultad: Básico=22, Intermedio=27, Avanzado=26, Experto=5
        diff_counts = collections.Counter(q["difficulty"] for q in self.romans_questions.values())
        self.assertEqual(diff_counts["Básico"], 22)
        self.assertEqual(diff_counts["Intermedio"], 27)
        self.assertEqual(diff_counts["Avanzado"], 26)
        self.assertEqual(diff_counts["Experto"], 5)

        # Tipos: 71 MC, 9 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.romans_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 71)
        self.assertEqual(type_counts["TRUE_FALSE"], 9)

    def test_romans_additional_references(self) -> None:
        """Verifica las 13 preguntas con 21 referencias adicionales en Romanos."""
        if not self.romans_questions:
            self.skipTest("romans-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-ROM-0003": ["Habacuc 2:4"],
            "NQB-NT-ROM-0011": ["Salmos 14:1-3", "Salmos 53:1-3"],
            "NQB-NT-ROM-0016": ["Génesis 15:6"],
            "NQB-NT-ROM-0018": ["Salmos 32:1-2"],
            "NQB-NT-ROM-0040": ["Salmos 44:22"],
            "NQB-NT-ROM-0045": ["Oseas 2:23", "Oseas 1:10", "Isaías 10:22-23", "Isaías 1:9"],
            "NQB-NT-ROM-0048": ["Deuteronomio 30:12-14"],
            "NQB-NT-ROM-0049": ["Joel 2:32"],
            "NQB-NT-ROM-0050": ["Isaías 52:7", "Isaías 53:1"],
            "NQB-NT-ROM-0052": ["1 Reyes 19:10-18"],
            "NQB-NT-ROM-0054": ["Isaías 59:20-21"],
            "NQB-NT-ROM-0060": ["Proverbios 25:21-22"],
            "NQB-NT-ROM-0073": ["Salmos 18:49", "Deuteronomio 32:43", "Salmos 117:1", "Isaías 11:10"]
        }
        found_add_refs = {}
        for qid, q in self.romans_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 13)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 21)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_romans_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Romanos."""
        if not self.romans_questions:
            self.skipTest("romans-master-input.json no disponible")
        for qid, q in self.romans_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_romans_olive_branches_homograph(self) -> None:
        """Verifica que las ramas del olivo de Romanos 11 no se interpreten como la ciudad Ramá."""
        self.assertFalse(is_biblical_place_usage("rama", "las ramas desgajadas del olivo"))
        self.assertFalse(is_biblical_place_usage("rama", "las ramas del olivo silvestre fueron injertadas"))
        self.assertFalse(is_biblical_place_usage("rama", "la raíz sostiene a las ramas"))

    def test_romans_epistolary_attribution_pablo(self) -> None:
        """Verifica que 'Pablo afirma/argumenta...' se reconozca como atribución epistolar."""
        self.assertTrue(is_narrative_source_attribution("pablo", "Pablo argumenta que la fe precede a la circuncisión"))
        self.assertTrue(is_narrative_source_attribution("pablo", "Pablo concluye que no hay condenación para los creyentes"))
        self.assertTrue(is_narrative_source_attribution("pablo", "Según expone Pablo en la carta"))

    # --- PRUEBAS ESPECÍFICAS DE 1 CORINTIOS ---

    def get_1corinthians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.corinthians1_questions, f"ID '{qid}' no encontrado en 1corinthians-master-input.json")
        return copy.deepcopy(self.corinthians1_questions[qid])

    def test_detect_book_key_1corinthians(self) -> None:
        """Verifica detección de book_key para 1 Corintios y sus variantes."""
        spec_1co = {"questions": [{"id": "NQB-NT-1CO-0001", "book": "1 Corintios"}]}
        self.assertEqual(detect_book_key(spec_1co), "1corinthians")

        spec_alias = {"questions": [{"id": "NQB-NT-1CO-0001", "book": "1corintios"}]}
        self.assertEqual(detect_book_key(spec_alias), "1corinthians")

        spec_en = {"questions": [{"id": "NQB-NT-1CO-0001", "book": "1 Corinthians"}]}
        self.assertEqual(detect_book_key(spec_en), "1corinthians")

        spec_1co_short = {"questions": [{"id": "NQB-NT-1CO-0001", "book": "1 cor"}]}
        self.assertEqual(detect_book_key(spec_1co_short), "1corinthians")

        spec_carta = {"questions": [{"id": "NQB-NT-1CO-0001", "book": "Primera Carta a los Corintios"}]}
        self.assertEqual(detect_book_key(spec_carta), "1corinthians")

    def test_1corinthians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 1 Corintios en BOOK_CONFIGS."""
        self.assertIn("1corinthians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["1corinthians"]
        self.assertEqual(cfg["canonical_name"], "1 Corintios")
        self.assertEqual(cfg["api_name"], "1 Corintios")
        self.assertEqual(cfg["total_chapters"], 16)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertIn("1 corintios", cfg["aliases"])
        self.assertIn("1corintios", cfg["aliases"])
        self.assertIn("1 corinthians", cfg["aliases"])
        self.assertIn("corinto", cfg["ambient_places"])
        self.assertIn("efeso", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_1corinthians(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Corintios."""
        if not self.corinthians1_questions:
            self.skipTest("1corinthians-master-input.json no disponible")
        for qid, q in self.corinthians1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_1corinthians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 1 Corintios."""
        if not self.corinthians1_questions:
            self.skipTest("1corinthians-master-input.json no disponible")
        self.assertEqual(len(self.corinthians1_questions), 80)
        
        # 5 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.corinthians1_questions.values())
        self.assertEqual(len(ch_counts), 16)
        for ch in range(1, 17):
            self.assertEqual(ch_counts[ch], 5, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 5")

        # Dificultad: Básico=19, Intermedio=25, Avanzado=29, Experto=7
        diff_counts = collections.Counter(q["difficulty"] for q in self.corinthians1_questions.values())
        self.assertEqual(diff_counts["Básico"], 19)
        self.assertEqual(diff_counts["Intermedio"], 25)
        self.assertEqual(diff_counts["Avanzado"], 29)
        self.assertEqual(diff_counts["Experto"], 7)

        # Tipos: 71 MC, 9 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.corinthians1_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 71)
        self.assertEqual(type_counts["TRUE_FALSE"], 9)

    def test_1corinthians_additional_references(self) -> None:
        """Verifica las 14 preguntas con 15 referencias adicionales en 1 Corintios."""
        if not self.corinthians1_questions:
            self.skipTest("1corinthians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-1CO-0003": ["Isaías 29:14"],
            "NQB-NT-1CO-0005": ["Jeremías 9:23-24"],
            "NQB-NT-1CO-0007": ["Isaías 64:4"],
            "NQB-NT-1CO-0010": ["Isaías 40:13"],
            "NQB-NT-1CO-0015": ["Job 5:13"],
            "NQB-NT-1CO-0022": ["Éxodo 12:15"],
            "NQB-NT-1CO-0024": ["Deuteronomio 17:7"],
            "NQB-NT-1CO-0029": ["Génesis 2:24"],
            "NQB-NT-1CO-0042": ["Deuteronomio 25:4"],
            "NQB-NT-1CO-0047": ["Éxodo 32:6"],
            "NQB-NT-1CO-0049": ["Salmos 24:1"],
            "NQB-NT-1CO-0068": ["Isaías 28:11-12"],
            "NQB-NT-1CO-0073": ["Salmos 8:6"],
            "NQB-NT-1CO-0075": ["Isaías 25:8", "Oseas 13:14"]
        }
        found_add_refs = {}
        for qid, q in self.corinthians1_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 14)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 15)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_1corinthians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en 1 Corintios."""
        if not self.corinthians1_questions:
            self.skipTest("1corinthians-master-input.json no disponible")
        for qid, q in self.corinthians1_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    # --- PRUEBAS ESPECÍFICAS DE 2 CORINTIOS ---

    def get_2corinthians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.corinthians2_questions, f"ID '{qid}' no encontrado en 2corinthians-master-input.json")
        return copy.deepcopy(self.corinthians2_questions[qid])

    def test_detect_book_key_2corinthians(self) -> None:
        """Verifica detección de book_key para 2 Corintios y sus variantes."""
        spec_2co = {"questions": [{"id": "NQB-NT-2CO-0001", "book": "2 Corintios"}]}
        self.assertEqual(detect_book_key(spec_2co), "2corinthians")

        spec_alias = {"questions": [{"id": "NQB-NT-2CO-0001", "book": "2corintios"}]}
        self.assertEqual(detect_book_key(spec_alias), "2corinthians")

        spec_en = {"questions": [{"id": "NQB-NT-2CO-0001", "book": "2 Corinthians"}]}
        self.assertEqual(detect_book_key(spec_en), "2corinthians")

        spec_2co_short = {"questions": [{"id": "NQB-NT-2CO-0001", "book": "2 cor"}]}
        self.assertEqual(detect_book_key(spec_2co_short), "2corinthians")

        spec_carta = {"questions": [{"id": "NQB-NT-2CO-0001", "book": "Segunda Carta a los Corintios"}]}
        self.assertEqual(detect_book_key(spec_carta), "2corinthians")

    def test_2corinthians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 2 Corintios en BOOK_CONFIGS."""
        self.assertIn("2corinthians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["2corinthians"]
        self.assertEqual(cfg["canonical_name"], "2 Corintios")
        self.assertEqual(cfg["api_name"], "2 Corintios")
        self.assertEqual(cfg["total_chapters"], 13)
        self.assertEqual(len(cfg["blocks"]), 2)
        self.assertIn("2 corintios", cfg["aliases"])
        self.assertIn("2corintios", cfg["aliases"])
        self.assertIn("2 corinthians", cfg["aliases"])
        self.assertIn("corinto", cfg["ambient_places"])
        self.assertIn("damasco", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_2corinthians(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Corintios."""
        if not self.corinthians2_questions:
            self.skipTest("2corinthians-master-input.json no disponible")
        for qid, q in self.corinthians2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_2corinthians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 2 Corintios."""
        if not self.corinthians2_questions:
            self.skipTest("2corinthians-master-input.json no disponible")
        self.assertEqual(len(self.corinthians2_questions), 65)
        
        # 5 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.corinthians2_questions.values())
        self.assertEqual(len(ch_counts), 13)
        for ch in range(1, 14):
            self.assertEqual(ch_counts[ch], 5, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 5")

        # Dificultad: Básico=13, Intermedio=21, Avanzado=25, Experto=6
        diff_counts = collections.Counter(q["difficulty"] for q in self.corinthians2_questions.values())
        self.assertEqual(diff_counts["Básico"], 13)
        self.assertEqual(diff_counts["Intermedio"], 21)
        self.assertEqual(diff_counts["Avanzado"], 25)
        self.assertEqual(diff_counts["Experto"], 6)

        # Tipos: 53 MC, 12 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.corinthians2_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 53)
        self.assertEqual(type_counts["TRUE_FALSE"], 12)

    def test_2corinthians_additional_references(self) -> None:
        """Verifica las 10 preguntas con 11 referencias adicionales en 2 Corintios."""
        if not self.corinthians2_questions:
            self.skipTest("2corinthians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-2CO-0012": ["Jeremías 31:31-34"],
            "NQB-NT-2CO-0013": ["Éxodo 34:29-35"],
            "NQB-NT-2CO-0019": ["Salmos 116:10"],
            "NQB-NT-2CO-0026": ["Isaías 49:8"],
            "NQB-NT-2CO-0030": ["Levítico 26:12", "Ezequiel 37:27"],
            "NQB-NT-2CO-0039": ["Éxodo 16:18"],
            "NQB-NT-2CO-0043": ["Salmos 112:9"],
            "NQB-NT-2CO-0050": ["Jeremías 9:24"],
            "NQB-NT-2CO-0051": ["Génesis 3:1-5"],
            "NQB-NT-2CO-0061": ["Deuteronomio 19:15"]
        }
        found_add_refs = {}
        for qid, q in self.corinthians2_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 10)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 11)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_2corinthians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en 2 Corintios."""
        if not self.corinthians2_questions:
            self.skipTest("2corinthians-master-input.json no disponible")
        for qid, q in self.corinthians2_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    # --- PRUEBAS ESPECÍFICAS DE GÁLATAS ---

    def get_galatians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.galatians_questions, f"ID '{qid}' no encontrado en galatians-master-input.json")
        return copy.deepcopy(self.galatians_questions[qid])

    def test_detect_book_key_galatians(self) -> None:
        """Verifica detección de book_key para Gálatas y sus variantes."""
        spec_gal = {"questions": [{"id": "NQB-NT-GAL-0001", "book": "Gálatas"}]}
        self.assertEqual(detect_book_key(spec_gal), "galatians")

        spec_alias = {"questions": [{"id": "NQB-NT-GAL-0001", "book": "galatas"}]}
        self.assertEqual(detect_book_key(spec_alias), "galatians")

        spec_en = {"questions": [{"id": "NQB-NT-GAL-0001", "book": "Galatians"}]}
        self.assertEqual(detect_book_key(spec_en), "galatians")

        spec_gal_short = {"questions": [{"id": "NQB-NT-GAL-0001", "book": "gal"}]}
        self.assertEqual(detect_book_key(spec_gal_short), "galatians")

        spec_carta = {"questions": [{"id": "NQB-NT-GAL-0001", "book": "Carta a los Gálatas"}]}
        self.assertEqual(detect_book_key(spec_carta), "galatians")

    def test_galatians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Gálatas en BOOK_CONFIGS."""
        self.assertIn("galatians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["galatians"]
        self.assertEqual(cfg["canonical_name"], "Gálatas")
        self.assertEqual(cfg["api_name"], "Gálatas")
        self.assertEqual(cfg["total_chapters"], 6)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("galatas", cfg["aliases"])
        self.assertIn("gálatas", cfg["aliases"])
        self.assertIn("galatians", cfg["aliases"])
        self.assertIn("galacia", cfg["ambient_places"])
        self.assertIn("arabia", cfg["ambient_places"])
        self.assertIn("antioquia", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_galatians(self) -> None:
        """Verifica consistencia de IDs y referencias en Gálatas."""
        if not self.galatians_questions:
            self.skipTest("galatians-master-input.json no disponible")
        for qid, q in self.galatians_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_galatians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Gálatas."""
        if not self.galatians_questions:
            self.skipTest("galatians-master-input.json no disponible")
        self.assertEqual(len(self.galatians_questions), 36)
        
        # 6 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.galatians_questions.values())
        self.assertEqual(len(ch_counts), 6)
        for ch in range(1, 7):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # Dificultad: Básico=8, Intermedio=12, Avanzado=13, Experto=3
        diff_counts = collections.Counter(q["difficulty"] for q in self.galatians_questions.values())
        self.assertEqual(diff_counts["Básico"], 8)
        self.assertEqual(diff_counts["Intermedio"], 12)
        self.assertEqual(diff_counts["Avanzado"], 13)
        self.assertEqual(diff_counts["Experto"], 3)

        # Tipos: 30 MC, 6 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.galatians_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 30)
        self.assertEqual(type_counts["TRUE_FALSE"], 6)

    def test_galatians_additional_references(self) -> None:
        """Verifica las 7 preguntas con 10 referencias adicionales en Gálatas."""
        if not self.galatians_questions:
            self.skipTest("galatians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-GAL-0010": ["Romanos 3:28"],
            "NQB-NT-GAL-0014": ["Génesis 15:6"],
            "NQB-NT-GAL-0015": ["Deuteronomio 27:26", "Habacuc 2:4", "Deuteronomio 21:23"],
            "NQB-NT-GAL-0016": ["Génesis 12:7"],
            "NQB-NT-GAL-0022": ["Génesis 16:1-16", "Génesis 21:1-21"],
            "NQB-NT-GAL-0023": ["Génesis 21:1-12"],
            "NQB-NT-GAL-0028": ["Levítico 19:18"]
        }
        found_add_refs = {}
        for qid, q in self.galatians_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 7)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 10)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_galatians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Gálatas."""
        if not self.galatians_questions:
            self.skipTest("galatians-master-input.json no disponible")
        for qid, q in self.galatians_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_biblical_person_aliases_cefas_pedro(self) -> None:
        """Verifica la resolución simétrica de alias Cefas <-> Pedro y la no equivalencia automática de Simón."""
        # 1. Cefas en entidad, Pedro en pasaje -> MATCH TRUE
        self.assertTrue(person_token_matches_text("cefas", "despues de tres anos subi a jerusalen para ver a pedro"))
        self.assertTrue(person_token_matches_text("Cefas", "fui a visitar a Pedro"))

        # 2. Pedro en entidad, Cefas en pasaje -> MATCH TRUE
        self.assertTrue(person_token_matches_text("pedro", "cuando cefas vino a antioquia le resisti cara a cara"))
        self.assertTrue(person_token_matches_text("Pedro", "se reunio con Cefas"))

        # 3. Simon aislado NO debe mapear automaticamente a Pedro
        self.assertFalse(person_token_matches_text("simon", "entonces pedro tomo la palabra"))
        self.assertFalse(person_token_matches_text("pedro", "entonces simon el mago respondio"))

    def test_is_biblical_person_usage_mesa(self) -> None:
        """Verifica distinción entre el rey Mesa de Moab y sustantivos comunes como 'mesa compartida'."""
        # Sustantivo común -> False (NO PERSONA)
        self.assertFalse(is_biblical_person_usage("mesa", "la mesa compartida con gentiles"))
        self.assertFalse(is_biblical_person_usage("mesa", "su conducta no era coherente con la mesa compartida"))
        self.assertFalse(is_biblical_person_usage("mesa", "se sentaron a una mesa con los discipulos"))
        self.assertFalse(is_biblical_person_usage("mesa", "comer a la mesa con ellos"))
        self.assertFalse(is_biblical_person_usage("mesa", "estando sentados a la mesa"))
        self.assertFalse(is_biblical_person_usage("mesa", "la mesa del Señor"))

        # Personaje bíblico real -> True (PERSONA)
        self.assertTrue(is_biblical_person_usage("mesa", "Mesa rey de Moab era pastor de ovejas"))
        self.assertTrue(is_biblical_person_usage("mesa", "entonces el rey Mesa tributaba al rey de Israel"))
        self.assertTrue(is_biblical_person_usage("mesa", "Mesa, rey de Moab"))

    def test_galatians_0005_and_0009_evaluations_no_fail(self) -> None:
        """Verifica que GAL-0005 (Cefas/Pedro) y GAL-0009 (mesa compartida) no produzcan FAIL."""
        if not self.galatians_questions:
            self.skipTest("galatians-master-input.json no disponible")

        # Mock passage text de RVR1960 para Gal 1:18-20 (usa 'Pedro')
        gal1_verses = {
            18: "Después, pasados tres años, subí a Jerusalén para ver a Pedro, y permanecí con él quince días;",
            19: "pero no vi a ningún otro de los apóstoles, sino a Jacobo el hermano del Señor.",
            20: "En esto que os escribo, he aquí delante de Dios que no miento."
        }
        q5 = self.get_galatians_question("NQB-NT-GAL-0005")
        res5 = evaluate_question(q5, gal1_verses, book_key="galatians")
        self.assertNotEqual(res5["controles_superados"].get("control_nombres_propios"), "FAIL")
        self.assertNotEqual(res5["controles_superados"].get("control_rango_suficiente"), "FAIL")
        self.assertIn(res5["estado"], {"VERIFICADO", "NO_CONCLUYENTE"})

        # Mock passage text de RVR1960 para Gal 2:11-14 (usa 'Pedro' y 'comía con los gentiles')
        gal2_verses = {
            11: "Pero cuando Pedro vino a Antioquía, le resistí cara a cara, porque era de condenar.",
            12: "Pues antes que viniesen algunos de parte de Jacobo, comía con los gentiles; pero después que vinieron, se retraía y se apartaba, porque tenía miedo de los de la circuncisión.",
            13: "Y en su simulación participaban también los otros judíos, de tal manera que aun Bernabé fue también arrastrado por la hipocresía de ellos.",
            14: "Pero cuando vi que no andaban rectamente conforme a la verdad del evangelio, dije a Pedro delante de todos: Si tú, siendo judío, vives como los gentiles y no como judío, ¿por qué obligas a los gentiles a judaizar?"
        }
        q9 = self.get_galatians_question("NQB-NT-GAL-0009")
        res9 = evaluate_question(q9, gal2_verses, book_key="galatians")
        self.assertNotEqual(res9["controles_superados"].get("control_nombres_propios"), "FAIL")
        self.assertNotEqual(res9["controles_superados"].get("control_rango_suficiente"), "FAIL")
        self.assertIn(res9["estado"], {"VERIFICADO", "NO_CONCLUYENTE"})

    # --- PRUEBAS ESPECÍFICAS DE EFESIOS ---

    def get_ephesians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ephesians_questions, f"ID '{qid}' no encontrado en ephesians-master-input.json")
        return copy.deepcopy(self.ephesians_questions[qid])

    def test_detect_book_key_ephesians(self) -> None:
        """Verifica detección de book_key para Efesios y sus variantes."""
        spec_efe = {"questions": [{"id": "NQB-NT-EFE-0001", "book": "Efesios"}]}
        self.assertEqual(detect_book_key(spec_efe), "ephesians")

        spec_alias = {"questions": [{"id": "NQB-NT-EFE-0001", "book": "efesios"}]}
        self.assertEqual(detect_book_key(spec_alias), "ephesians")

        spec_en = {"questions": [{"id": "NQB-NT-EFE-0001", "book": "Ephesians"}]}
        self.assertEqual(detect_book_key(spec_en), "ephesians")

        spec_short = {"questions": [{"id": "NQB-NT-EFE-0001", "book": "efe"}]}
        self.assertEqual(detect_book_key(spec_short), "ephesians")

        spec_carta = {"questions": [{"id": "NQB-NT-EFE-0001", "book": "Carta a los Efesios"}]}
        self.assertEqual(detect_book_key(spec_carta), "ephesians")

    def test_ephesians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Efesios en BOOK_CONFIGS."""
        self.assertIn("ephesians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["ephesians"]
        self.assertEqual(cfg["canonical_name"], "Efesios")
        self.assertEqual(cfg["api_name"], "Efesios")
        self.assertEqual(cfg["total_chapters"], 6)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("efesios", cfg["aliases"])
        self.assertIn("ephesians", cfg["aliases"])
        self.assertIn("efe", cfg["aliases"])
        self.assertIn("efeso", cfg["ambient_places"])
        self.assertIn("roma", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_ephesians(self) -> None:
        """Verifica consistencia de IDs y referencias en Efesios."""
        if not self.ephesians_questions:
            self.skipTest("ephesians-master-input.json no disponible")
        for qid, q in self.ephesians_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_ephesians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Efesios."""
        if not self.ephesians_questions:
            self.skipTest("ephesians-master-input.json no disponible")
        self.assertEqual(len(self.ephesians_questions), 36)

        # 6 preguntas por capítulo
        ch_counts = collections.Counter(q["chapter"] for q in self.ephesians_questions.values())
        self.assertEqual(len(ch_counts), 6)
        for ch in range(1, 7):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # Dificultad: Básico=9, Intermedio=13, Avanzado=11, Experto=3
        diff_counts = collections.Counter(q["difficulty"] for q in self.ephesians_questions.values())
        self.assertEqual(diff_counts["Básico"], 9)
        self.assertEqual(diff_counts["Intermedio"], 13)
        self.assertEqual(diff_counts["Avanzado"], 11)
        self.assertEqual(diff_counts["Experto"], 3)

        # Tipos: 30 MC, 6 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.ephesians_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 30)
        self.assertEqual(type_counts["TRUE_FALSE"], 6)

        tf_ids = [q["id"] for q in self.ephesians_questions.values() if q.get("question_type") == "TRUE_FALSE"]
        expected_tf = ["NQB-NT-EFE-0006", "NQB-NT-EFE-0012", "NQB-NT-EFE-0018", "NQB-NT-EFE-0024", "NQB-NT-EFE-0030", "NQB-NT-EFE-0036"]
        self.assertEqual(sorted(tf_ids), sorted(expected_tf))

    def test_ephesians_additional_references(self) -> None:
        """Verifica las 9 preguntas con 12 referencias adicionales en Efesios."""
        if not self.ephesians_questions:
            self.skipTest("ephesians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-EFE-0006": ["Salmos 8:6"],
            "NQB-NT-EFE-0010": ["Isaías 57:19"],
            "NQB-NT-EFE-0020": ["Salmos 68:18"],
            "NQB-NT-EFE-0023": ["Zacarías 8:16"],
            "NQB-NT-EFE-0028": ["Génesis 2:24"],
            "NQB-NT-EFE-0029": ["Génesis 2:24"],
            "NQB-NT-EFE-0031": ["Éxodo 20:12", "Deuteronomio 5:16"],
            "NQB-NT-EFE-0032": ["Deuteronomio 10:17"],
            "NQB-NT-EFE-0034": ["Isaías 11:5", "Isaías 52:7", "Isaías 59:17"]
        }
        found_add_refs = {}
        for qid, q in self.ephesians_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 9)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 12)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_ephesians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Efesios."""
        if not self.ephesians_questions:
            self.skipTest("ephesians-master-input.json no disponible")
        for qid, q in self.ephesians_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_ephesians_0036_tiquico_and_armadura_metaphor(self) -> None:
        """Verifica que Tíquico sea reconocido como personaje real y la armadura como metáfora."""
        if not self.ephesians_questions:
            self.skipTest("ephesians-master-input.json no disponible")

        # Mock passage text de RVR1960 para Efesios 6:21-24
        efe6_verses = {
            21: "Para que también vosotros sepáis mis asuntos, y lo que hago, todo os lo hará saber Tíquico, hermano amado y fiel ministro en el Señor,",
            22: "el cual envié a vosotros para esto mismo, para que sepáis lo tocante a nosotros, y que consuele vuestros corazones.",
            23: "Paz sea a los hermanos, y amor con fe, de Dios Padre y del Señor Jesucristo.",
            24: "La gracia sea con todos los que aman a nuestro Señor Jesucristo con amor inalterable. Amén."
        }
        q36 = self.get_ephesians_question("NQB-NT-EFE-0036")
        res36 = evaluate_question(q36, efe6_verses, book_key="ephesians")
        self.assertEqual(res36["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res36["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS ESPECÍFICAS DE FILIPENSES ---

    def get_philippians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.philippians_questions, f"ID '{qid}' no encontrado en philippians-master-input.json")
        return copy.deepcopy(self.philippians_questions[qid])

    def test_detect_book_key_philippians(self) -> None:
        """Verifica detección de book_key para Filipenses y sus variantes."""
        spec_fil = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "Filipenses"}]}
        self.assertEqual(detect_book_key(spec_fil), "philippians")

        spec_alias = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "filipenses"}]}
        self.assertEqual(detect_book_key(spec_alias), "philippians")

        spec_en = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "Philippians"}]}
        self.assertEqual(detect_book_key(spec_en), "philippians")

        spec_short = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "fil"}]}
        self.assertEqual(detect_book_key(spec_short), "philippians")

        spec_carta = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "Carta a los Filipenses"}]}
        self.assertEqual(detect_book_key(spec_carta), "philippians")

        spec_epistola = {"questions": [{"id": "NQB-NT-FIL-0001", "book": "Epístola a los Filipenses"}]}
        self.assertEqual(detect_book_key(spec_epistola), "philippians")

    def test_philippians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Filipenses en BOOK_CONFIGS."""
        self.assertIn("philippians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["philippians"]
        self.assertEqual(cfg["canonical_name"], "Filipenses")
        self.assertEqual(cfg["api_name"], "Filipenses")
        self.assertEqual(cfg["total_chapters"], 4)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("filipenses", cfg["aliases"])
        self.assertIn("philippians", cfg["aliases"])
        self.assertIn("fil", cfg["aliases"])
        self.assertIn("filipos", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])
        self.assertIn("roma", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_philippians(self) -> None:
        """Verifica consistencia de IDs y referencias en Filipenses."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")
        for qid, q in self.philippians_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_philippians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Filipenses."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")
        self.assertEqual(len(self.philippians_questions), 24)

        # 6 preguntas por capítulo (4 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.philippians_questions.values())
        self.assertEqual(len(ch_counts), 4)
        for ch in range(1, 5):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # Dificultad: Básico=7, Intermedio=7, Avanzado=8, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.philippians_questions.values())
        self.assertEqual(diff_counts["Básico"], 7)
        self.assertEqual(diff_counts["Intermedio"], 7)
        self.assertEqual(diff_counts["Avanzado"], 8)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 20 MC, 4 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.philippians_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 20)
        self.assertEqual(type_counts["TRUE_FALSE"], 4)

        tf_ids = [q["id"] for q in self.philippians_questions.values() if q.get("question_type") == "TRUE_FALSE"]
        expected_tf = ["NQB-NT-FIL-0006", "NQB-NT-FIL-0012", "NQB-NT-FIL-0018", "NQB-NT-FIL-0024"]
        self.assertEqual(sorted(tf_ids), sorted(expected_tf))

    def test_philippians_additional_references(self) -> None:
        """Verifica las 5 preguntas con 6 referencias adicionales en Filipenses."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-FIL-0001": ["Hechos 16:12-40"],
            "NQB-NT-FIL-0004": ["Hechos 16:19-40"],
            "NQB-NT-FIL-0008": ["Isaías 45:23"],
            "NQB-NT-FIL-0014": ["Hechos 22:3", "Hechos 23:6"],
            "NQB-NT-FIL-0023": ["Génesis 8:21"]
        }
        found_add_refs = {}
        for qid, q in self.philippians_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 5)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 6)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_philippians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Filipenses."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")
        for qid, q in self.philippians_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_philippians_true_false_0018_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-FIL-0018 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")
        q18 = self.get_philippians_question("NQB-NT-FIL-0018")
        self.assertEqual(q18["opcion_a"].strip().lower(), "falso")
        self.assertEqual(q18["opcion_b"].strip().lower(), "verdadero")
        self.assertEqual(q18["correct_option"], "A")
        self.assertEqual(q18["correct_answer"].strip().lower(), "falso")

    def test_philippians_characters_and_safety(self) -> None:
        """Verifica reconocimiento de Epafrodito, Evodia, Síntique, Clemente y pasajes clave."""
        if not self.philippians_questions:
            self.skipTest("philippians-master-input.json no disponible")

        # Mock passage text de RVR1960 para Filipenses 2:25-30 (Epafrodito)
        fil2_verses = {
            25: "Mas tuve por necesario enviaros a Epafrodito, mi hermano y colaborador y compañero de milicia, vuestro mensajero, y ministrador de mis necesidades;",
            26: "porque tenía gran deseo de veros a todos vosotros, y gravemente se angustió porque habíais oído que había estado enfermo.",
            27: "Pues en verdad estuvo enfermo, a punto de morir; pero Dios tuvo misericordia de él, y no solamente de él, sino asimismo de mí, para que yo no tuviese tristeza sobre tristeza.",
            28: "Así que le envío con mayor solicitud, para que al verle de nuevo, os gocéis, y yo esté con menos tristeza.",
            29: "Recibidle, pues, en el Señor, con todo gozo, y tened en alta estima a los que son como él;",
            30: "porque por la obra de Cristo estuvo próximo a la muerte, exponiendo su vida para suplir lo que faltaba en vuestro servicio por mí."
        }
        q12 = self.get_philippians_question("NQB-NT-FIL-0012")
        res12 = evaluate_question(q12, fil2_verses, book_key="philippians")
        self.assertEqual(res12["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res12["estado"], "REQUIERE_CORRECCION")

        # Mock passage text de RVR1960 para Filipenses 4:2-3 (Evodia, Síntique, Clemente)
        fil4_verses = {
            2: "Ruego a Evodia y a Síntique, que sean de un mismo sentir en el Señor.",
            3: "Asimismo te ruego también a ti, compañero fiel, que ayudes a éstas que combatieron juntamente conmigo en el evangelio, con Clemente también y los demás colaboradores míos, cuyos nombres están en el libro de la vida."
        }
        q19 = self.get_philippians_question("NQB-NT-FIL-0019")
        res19 = evaluate_question(q19, fil4_verses, book_key="philippians")
        self.assertEqual(res19["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res19["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS ESPECÍFICAS DE COLOSENSES ---

    def get_colossians_question(self, qid: str) -> dict:
        self.assertIn(qid, self.colossians_questions, f"ID '{qid}' no encontrado en colossians-master-input.json")
        return copy.deepcopy(self.colossians_questions[qid])

    def test_detect_book_key_colossians(self) -> None:
        """Verifica detección de book_key para Colosenses y sus variantes."""
        spec_col = {"questions": [{"id": "NQB-NT-COL-0001", "book": "Colosenses"}]}
        self.assertEqual(detect_book_key(spec_col), "colossians")

        spec_alias = {"questions": [{"id": "NQB-NT-COL-0001", "book": "colosenses"}]}
        self.assertEqual(detect_book_key(spec_alias), "colossians")

        spec_en = {"questions": [{"id": "NQB-NT-COL-0001", "book": "Colossians"}]}
        self.assertEqual(detect_book_key(spec_en), "colossians")

        spec_short = {"questions": [{"id": "NQB-NT-COL-0001", "book": "col"}]}
        self.assertEqual(detect_book_key(spec_short), "colossians")

        spec_carta = {"questions": [{"id": "NQB-NT-COL-0001", "book": "Carta a los Colosenses"}]}
        self.assertEqual(detect_book_key(spec_carta), "colossians")

        spec_epistola = {"questions": [{"id": "NQB-NT-COL-0001", "book": "Epístola a los Colosenses"}]}
        self.assertEqual(detect_book_key(spec_epistola), "colossians")

    def test_colossians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Colosenses en BOOK_CONFIGS."""
        self.assertIn("colossians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["colossians"]
        self.assertEqual(cfg["canonical_name"], "Colosenses")
        self.assertEqual(cfg["api_name"], "Colosenses")
        self.assertEqual(cfg["total_chapters"], 4)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("colosenses", cfg["aliases"])
        self.assertIn("colossians", cfg["aliases"])
        self.assertIn("col", cfg["aliases"])
        self.assertIn("colosas", cfg["ambient_places"])
        self.assertIn("laodicea", cfg["ambient_places"])
        self.assertIn("hierapolis", cfg["ambient_places"])

    def test_global_canonical_id_reference_integrity_colossians(self) -> None:
        """Verifica consistencia de IDs y referencias en Colosenses."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")
        for qid, q in self.colossians_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_colossians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Colosenses."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")
        self.assertEqual(len(self.colossians_questions), 24)

        # 6 preguntas por capítulo (4 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.colossians_questions.values())
        self.assertEqual(len(ch_counts), 4)
        for ch in range(1, 5):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # Dificultad: Básico=7, Intermedio=7, Avanzado=8, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.colossians_questions.values())
        self.assertEqual(diff_counts["Básico"], 7)
        self.assertEqual(diff_counts["Intermedio"], 7)
        self.assertEqual(diff_counts["Avanzado"], 8)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 20 MC, 4 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.colossians_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 20)
        self.assertEqual(type_counts["TRUE_FALSE"], 4)

        tf_ids = [q["id"] for q in self.colossians_questions.values() if q.get("question_type") == "TRUE_FALSE"]
        expected_tf = ["NQB-NT-COL-0006", "NQB-NT-COL-0012", "NQB-NT-COL-0018", "NQB-NT-COL-0024"]
        self.assertEqual(sorted(tf_ids), sorted(expected_tf))

    def test_colossians_additional_references(self) -> None:
        """Verifica las 7 preguntas con 10 referencias adicionales en Colosenses."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-COL-0002": ["Filemón 1:23"],
            "NQB-NT-COL-0004": ["Juan 1:3", "Hebreos 1:3"],
            "NQB-NT-COL-0011": ["Levítico 23:2-3", "Números 28:11-15"],
            "NQB-NT-COL-0014": ["Génesis 1:26-27"],
            "NQB-NT-COL-0021": ["Efesios 6:21-22", "Filemón 1:10-12"],
            "NQB-NT-COL-0022": ["Filemón 1:23-24"],
            "NQB-NT-COL-0023": ["Filemón 1:2"]
        }
        found_add_refs = {}
        for qid, q in self.colossians_questions.items():
            refs = q.get("additional_references", [])
            if refs:
                found_add_refs[qid] = refs

        self.assertEqual(len(found_add_refs), 7)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 10)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_colossians_modes_and_categories(self) -> None:
        """Verifica la asignación de modos y categorías sin categorías de Jesús en Colosenses."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")
        for qid, q in self.colossians_questions.items():
            cat = q.get("category")
            self.assertIn(cat, {"NT_GENERAL", "PERSONAJES_BIBLICOS"})
            self.assertNotIn(cat, {"JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"})
            modes = q.get("eligible_modes", [])
            self.assertIn("NT", modes)
            self.assertIn("AMBOS", modes)
            if cat == "PERSONAJES_BIBLICOS":
                self.assertIn("PERSONAJES_NT", modes)
                self.assertIn("PERSONAJES_AMBOS", modes)
            if q.get("question_type") == "TRUE_FALSE":
                self.assertIn("VERDADERO_FALSO_NT", modes)
                self.assertIn("VERDADERO_FALSO_AMBOS", modes)

    def test_colossians_true_false_0012_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-COL-0012 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")
        q12 = self.get_colossians_question("NQB-NT-COL-0012")
        self.assertEqual(q12["opcion_a"].strip().lower(), "falso")
        self.assertEqual(q12["opcion_b"].strip().lower(), "verdadero")
        self.assertEqual(q12["correct_option"], "A")
        self.assertEqual(q12["correct_answer"].strip().lower(), "falso")

    def test_colossians_characters_and_safety(self) -> None:
        """Verifica reconocimiento de colaboradores de Colosenses y resolución de entidades."""
        if not self.colossians_questions:
            self.skipTest("colossians-master-input.json no disponible")

        # Mock passage text de RVR1960 para Colosenses 4:7-9 (Tíquico y Onésimo)
        col4_7_9 = {
            7: "Todo lo que a mí se refiere, os lo hará saber Tíquico, amado hermano y fiel ministro y consiervo en el Señor,",
            8: "el cual he enviado a vosotros para esto mismo, para que conozca lo que a vosotros se refiere, y conforte vuestros corazones,",
            9: "con Onésimo, amado y fiel hermano, que es uno de vosotros. Todo lo que acá pasa, os lo harán saber."
        }
        q21 = self.get_colossians_question("NQB-NT-COL-0021")
        res21 = evaluate_question(q21, col4_7_9, book_key="colossians")
        self.assertEqual(res21["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res21["estado"], "REQUIERE_CORRECCION")

        # Mock passage text de RVR1960 para Colosenses 4:10-14 (Aristarco, Marcos, Jesús llamado Justo, Epafras, Lucas, Demas)
        col4_10_14 = {
            10: "Aristarco, mi compañero de prisiones, os saluda, y Marcos el sobrino de Bernabé, acerca del cual habéis recibido mandamientos; si fuere a vosotros, recibidle;",
            11: "y Jesús, llamado Justo; que son los únicos de la circuncisión que me ayudan en el reino de Dios, y han sido para mí un consuelo.",
            12: "Os saluda Epafras, el cual es uno de vosotros, siervo de Cristo, siempre rogando encarecidamente por vosotros en sus oraciones, para que estéis firmes, perfectos y completos en todo lo que Dios quiere.",
            13: "Porque de él doy testimonio de que tiene gran solicitud por vosotros, y por los que están en Laodicea, y los que están en Hierápolis.",
            14: "Os saluda Lucas el médico amado, y Demas."
        }
        q22 = self.get_colossians_question("NQB-NT-COL-0022")
        res22 = evaluate_question(q22, col4_10_14, book_key="colossians")
        self.assertEqual(res22["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res22["estado"], "REQUIERE_CORRECCION")

        # Mock passage text de RVR1960 para Colosenses 4:15-17 (Ninfa, Arquipo, Laodicea)
        col4_15_17 = {
            15: "Saludad a los hermanos que están en Laodicea, y a Ninfa y a la iglesia que está en su casa.",
            16: "Cuando esta carta haya sido leída entre vosotros, haced que también se lea en la iglesia de los laodicenses, y que la de Laodicea la leáis también vosotros.",
            17: "Y decid a Arquipo: Mira que cumplas el ministerio que recibiste en el Señor."
        }
        q23 = self.get_colossians_question("NQB-NT-COL-0023")
        res23 = evaluate_question(q23, col4_15_17, book_key="colossians")
        self.assertEqual(res23["controles_superados"].get("control_nombres_propios"), "PASS")
        self.assertNotEqual(res23["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS ESPECÍFICAS DE 1 TESALONICENSES ---

    def get_thessalonians1_question(self, qid: str) -> dict:
        self.assertIn(qid, self.thessalonians1_questions, f"ID '{qid}' no encontrado en 1thessalonians-master-input.json")
        return copy.deepcopy(self.thessalonians1_questions[qid])

    def test_detect_book_key_1thessalonians(self) -> None:
        """Verifica detección de book_key para 1 Tesalonicenses y sus variantes."""
        for alias in ["1 Tesalonicenses", "1tesalonicenses", "1 Thessalonians", "1thessalonians",
                       "1 thess", "1ts", "Primera de Tesalonicenses", "Primera carta a los Tesalonicenses"]:
            spec = {"questions": [{"id": "NQB-NT-1TS-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "1thessalonians",
                             f"detect_book_key failed for alias: {alias}")

    def test_1thessalonians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 1 Tesalonicenses en BOOK_CONFIGS."""
        self.assertIn("1thessalonians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["1thessalonians"]
        self.assertEqual(cfg["canonical_name"], "1 Tesalonicenses")
        self.assertEqual(cfg["api_name"], "1Tesalonicenses")
        self.assertEqual(cfg["total_chapters"], 5)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("1 tesalonicenses", cfg["aliases"])
        self.assertIn("1thessalonians", cfg["aliases"])
        self.assertIn("1ts", cfg["aliases"])
        self.assertIn("tesalonica", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])

    def test_1thessalonians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        self.assertEqual(len(self.thessalonians1_questions), 30)

        # 6 preguntas por capítulo (5 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.thessalonians1_questions.values())
        self.assertEqual(len(ch_counts), 5)
        for ch in range(1, 6):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-1TS-0001 a NQB-NT-1TS-0030
        ids = sorted(self.thessalonians1_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-1TS-0001")
        self.assertEqual(ids[-1], "NQB-NT-1TS-0030")
        self.assertEqual(len(set(ids)), 30)

        # Dificultad: Básico=10, Intermedio=10, Avanzado=7, Experto=3
        diff_counts = collections.Counter(q["difficulty"] for q in self.thessalonians1_questions.values())
        self.assertEqual(diff_counts["Básico"], 10)
        self.assertEqual(diff_counts["Intermedio"], 10)
        self.assertEqual(diff_counts["Avanzado"], 7)
        self.assertEqual(diff_counts["Experto"], 3)

        # Tipos: 25 MC, 5 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.thessalonians1_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 25)
        self.assertEqual(type_counts["TRUE_FALSE"], 5)

        tf_ids = sorted(q["id"] for q in self.thessalonians1_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted(["NQB-NT-1TS-0006", "NQB-NT-1TS-0012", "NQB-NT-1TS-0018", "NQB-NT-1TS-0024", "NQB-NT-1TS-0030"])
        self.assertEqual(tf_ids, expected_tf)

    def test_1thessalonians_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.thessalonians1_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 24)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 6)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_1thessalonians_additional_references(self) -> None:
        """Verifica las 2 preguntas con 2 referencias adicionales en 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-1TS-0007": ["Hechos 16:22-40"],
            "NQB-NT-1TS-0011": ["Hechos 17:1-10"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.thessalonians1_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 2)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 2)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_1thessalonians_modes(self) -> None:
        """Verifica la asignación de modos en 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.thessalonians1_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 30)
        self.assertEqual(mode_counts["AMBOS"], 30)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 6)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 6)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 5)

    def test_1thessalonians_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        for qid, q in self.thessalonians1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_1thessalonians_true_false_0024_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-1TS-0024 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        q24 = self.get_thessalonians1_question("NQB-NT-1TS-0024")
        self.assertEqual(q24["opcion_a"].strip().lower(), "falso")
        self.assertEqual(q24["opcion_b"].strip().lower(), "verdadero")
        self.assertEqual(q24["correct_option"], "A")
        self.assertEqual(q24["correct_answer"].strip().lower(), "falso")

    def test_1thessalonians_epistle_epistolary_resolution(self) -> None:
        """Verifica que Pablo como autor epistolar se resuelva sin exigir token en cada versículo."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")

        # NQB-NT-1TS-0010 cubre 1 Tesalonicenses 2:9-12 — Pablo sin token en cada verso
        q10 = self.thessalonians1_questions.get("NQB-NT-1TS-0010")
        if not q10:
            self.skipTest("NQB-NT-1TS-0010 no disponible")

        ts2_9_12 = {
            9: "Porque os recordáis, hermanos, nuestro trabajo y fatiga; cómo trabajando de noche y de día, para no ser gravosos a ninguno de vosotros, os predicamos el evangelio de Dios.",
            10: "Vosotros sois testigos, y Dios también, de cuán santa, justa e irreprensiblemente nos comportamos con vosotros los creyentes;",
            11: "así como también sabéis de qué modo, como el padre a sus hijos, exhortábamos y consolábamos a cada uno de vosotros,",
            12: "y os encargábamos que anduvieseis como es digno de Dios, que os llamó a su reino y gloria."
        }
        res = evaluate_question(q10, ts2_9_12, book_key="1thessalonians")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                            f"Q NQB-NT-1TS-0010 no debe ser REQUIERE_CORRECCION: {res.get('motivos_correccion')}")

    def test_1thessalonians_characters_silvano_timoteo(self) -> None:
        """Verifica que Silvano y Timoteo estén en BIBLE_PERSONAJES."""
        self.assertIn("silvano", BIBLE_PERSONAJES)
        self.assertIn("timoteo", BIBLE_PERSONAJES)
        self.assertIn("pablo", BIBLE_PERSONAJES)

    def test_1thessalonians_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 1 Tesalonicenses."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.thessalonians1_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_1thessalonians_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 1 Tesalonicenses y los 12 libros NT anteriores."""
        if not self.thessalonians1_questions:
            self.skipTest("1thessalonians-master-input.json no disponible")
        ts_texts = {q["question"].strip() for q in self.thessalonians1_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), ts_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 1 Tesalonicenses")

    # --- PRUEBAS ESPECÍFICAS DE 2 TESALONICENSES ---

    def get_thessalonians2_question(self, qid: str) -> dict:
        self.assertIn(qid, self.thessalonians2_questions, f"ID '{qid}' no encontrado en 2thessalonians-master-input.json")
        return copy.deepcopy(self.thessalonians2_questions[qid])

    def test_detect_book_key_2thessalonians(self) -> None:
        """Verifica detección de book_key para 2 Tesalonicenses y sus variantes."""
        for alias in ["2 Tesalonicenses", "2tesalonicenses", "2 Thessalonians", "2thessalonians",
                       "2 thess", "2ts", "Segunda de Tesalonicenses", "Segunda carta a los Tesalonicenses"]:
            spec = {"questions": [{"id": "NQB-NT-2TS-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "2thessalonians",
                             f"detect_book_key failed for alias: {alias}")

    def test_2thessalonians_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 2 Tesalonicenses en BOOK_CONFIGS."""
        self.assertIn("2thessalonians", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["2thessalonians"]
        self.assertEqual(cfg["canonical_name"], "2 Tesalonicenses")
        self.assertEqual(cfg["api_name"], "2Tesalonicenses")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("2 tesalonicenses", cfg["aliases"])
        self.assertIn("2thessalonians", cfg["aliases"])
        self.assertIn("2ts", cfg["aliases"])
        self.assertIn("tesalonica", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])

    def test_2thessalonians_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        self.assertEqual(len(self.thessalonians2_questions), 18)

        # 6 preguntas por capítulo (3 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.thessalonians2_questions.values())
        self.assertEqual(len(ch_counts), 3)
        for ch in range(1, 4):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-2TS-0001 a NQB-NT-2TS-0018
        ids = sorted(self.thessalonians2_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-2TS-0001")
        self.assertEqual(ids[-1], "NQB-NT-2TS-0018")
        self.assertEqual(len(set(ids)), 18)

        # Dificultad: Básico=5, Intermedio=6, Avanzado=5, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.thessalonians2_questions.values())
        self.assertEqual(diff_counts["Básico"], 5)
        self.assertEqual(diff_counts["Intermedio"], 6)
        self.assertEqual(diff_counts["Avanzado"], 5)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 15 MC, 3 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.thessalonians2_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 15)
        self.assertEqual(type_counts["TRUE_FALSE"], 3)

        tf_ids = sorted(q["id"] for q in self.thessalonians2_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted(["NQB-NT-2TS-0006", "NQB-NT-2TS-0012", "NQB-NT-2TS-0018"])
        self.assertEqual(tf_ids, expected_tf)

    def test_2thessalonians_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.thessalonians2_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 14)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_2thessalonians_additional_references(self) -> None:
        """Verifica las 3 preguntas con 3 referencias adicionales en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-2TS-0007": ["1 Tesalonicenses 5:1-6"],
            "NQB-NT-2TS-0010": ["Mateo 24:23-27"],
            "NQB-NT-2TS-0016": ["1 Tesalonicenses 4:11-12"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.thessalonians2_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 3)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 3)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_2thessalonians_modes(self) -> None:
        """Verifica la asignación de modos en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.thessalonians2_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 18)
        self.assertEqual(mode_counts["AMBOS"], 18)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 3)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 3)

    def test_2thessalonians_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        for qid, q in self.thessalonians2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_2thessalonians_true_false_0018_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-2TS-0018 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        q18 = self.get_thessalonians2_question("NQB-NT-2TS-0018")
        self.assertEqual(q18["opcion_a"].strip().lower(), "falso")
        self.assertEqual(q18["opcion_b"].strip().lower(), "verdadero")
        self.assertEqual(q18["correct_option"], "A")
        self.assertEqual(q18["correct_answer"].strip().lower(), "falso")

    def test_2thessalonians_epistle_epistolary_resolution(self) -> None:
        """Verifica que Pablo como autor epistolar se resuelva en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")

        # 2 Tesalonicenses 3:6-9 — Mandato sobre no andar desordenadamente y ejemplo de Pablo
        ts3_6_9 = {
            6: "Pero os ordenamos, hermanos, en el nombre de nuestro Señor Jesucristo, que os apartéis de todo hermano que ande desordenadamente, y no según la enseñanza que recibisteis de nosotros.",
            7: "Porque vosotros mismos sabéis de qué manera debéis imitarnos; pues nosotros no anduvimos desordenadamente entre vosotros,",
            8: "ni comimos de balde el pan de nadie, sino que trabajamos con afán y fatiga día y noche, para no ser gravosos a ninguno de vosotros;",
            9: "no porque no tuviésemos derecho, sino por daros nosotros mismos un ejemplo para que nos imitaseis."
        }
        q15 = self.thessalonians2_questions.get("NQB-NT-2TS-0015")
        if q15:
            res = evaluate_question(q15, ts3_6_9, book_key="2thessalonians")
            self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                                f"Q NQB-NT-2TS-0015 no debe ser REQUIERE_CORRECCION: {res.get('motivos_correccion')}")

    def test_2thessalonians_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 2 Tesalonicenses."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.thessalonians2_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_2thessalonians_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 2 Tesalonicenses y los 13 libros NT anteriores."""
        if not self.thessalonians2_questions:
            self.skipTest("2thessalonians-master-input.json no disponible")
        ts_texts = {q["question"].strip() for q in self.thessalonians2_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), ts_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 2 Tesalonicenses")

    # --- PRUEBAS ESPECÍFICAS DE 1 TIMOTEO ---

    def get_timothy1_question(self, qid: str) -> dict:
        self.assertIn(qid, self.timothy1_questions, f"ID '{qid}' no encontrado en 1timothy-master-input.json")
        return copy.deepcopy(self.timothy1_questions[qid])

    def test_detect_book_key_1timothy(self) -> None:
        """Verifica detección de book_key para 1 Timoteo y sus variantes."""
        for alias in ["1 Timoteo", "1timoteo", "1 Timothy", "1timothy",
                       "1 tim", "1ti", "Primera de Timoteo", "Primera carta a Timoteo"]:
            spec = {"questions": [{"id": "NQB-NT-1TI-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "1timothy",
                             f"detect_book_key failed for alias: {alias}")

    def test_1timothy_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 1 Timoteo en BOOK_CONFIGS."""
        self.assertIn("1timothy", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["1timothy"]
        self.assertEqual(cfg["canonical_name"], "1 Timoteo")
        self.assertEqual(cfg["api_name"], "1Timoteo")
        self.assertEqual(cfg["total_chapters"], 6)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("1 timoteo", cfg["aliases"])
        self.assertIn("1timothy", cfg["aliases"])
        self.assertIn("1ti", cfg["aliases"])
        self.assertIn("efeso", cfg["ambient_places"])
        self.assertIn("macedonia", cfg["ambient_places"])

    def test_1timothy_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        self.assertEqual(len(self.timothy1_questions), 36)

        # 6 preguntas por capítulo (6 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.timothy1_questions.values())
        self.assertEqual(len(ch_counts), 6)
        for ch in range(1, 7):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-1TI-0001 a NQB-NT-1TI-0036
        ids = sorted(self.timothy1_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-1TI-0001")
        self.assertEqual(ids[-1], "NQB-NT-1TI-0036")
        self.assertEqual(len(set(ids)), 36)

        # Dificultad: Básico=11, Intermedio=12, Avanzado=10, Experto=3
        diff_counts = collections.Counter(q["difficulty"] for q in self.timothy1_questions.values())
        self.assertEqual(diff_counts["Básico"], 11)
        self.assertEqual(diff_counts["Intermedio"], 12)
        self.assertEqual(diff_counts["Avanzado"], 10)
        self.assertEqual(diff_counts["Experto"], 3)

        # Tipos: 30 MC, 6 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.timothy1_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 30)
        self.assertEqual(type_counts["TRUE_FALSE"], 6)

        tf_ids = sorted(q["id"] for q in self.timothy1_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted(["NQB-NT-1TI-0006", "NQB-NT-1TI-0012", "NQB-NT-1TI-0018", "NQB-NT-1TI-0024", "NQB-NT-1TI-0030", "NQB-NT-1TI-0036"])
        self.assertEqual(tf_ids, expected_tf)

    def test_1timothy_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.timothy1_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 28)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 8)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_1timothy_additional_references(self) -> None:
        """Verifica las 9 preguntas con 10 referencias individuales en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-1TI-0002": ["Hechos 20:29-31"],
            "NQB-NT-1TI-0005": ["Hechos 9:1-19"],
            "NQB-NT-1TI-0013": ["Tito 1:5-9"],
            "NQB-NT-1TI-0019": ["Colosenses 2:16-23"],
            "NQB-NT-1TI-0022": ["2 Timoteo 1:5-7"],
            "NQB-NT-1TI-0028": ["Deuteronomio 19:15", "Lucas 10:7"],
            "NQB-NT-1TI-0031": ["Filemón 1:15-16"],
            "NQB-NT-1TI-0033": ["Hebreos 13:5"],
            "NQB-NT-1TI-0035": ["Mateo 6:19-21"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.timothy1_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 9)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 10)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_1timothy_modes(self) -> None:
        """Verifica la asignación de modos en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.timothy1_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 36)
        self.assertEqual(mode_counts["AMBOS"], 36)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 8)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 8)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 6)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 6)

    def test_1timothy_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        for qid, q in self.timothy1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_1timothy_true_false_0036_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-1TI-0036 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        q36 = self.get_timothy1_question("NQB-NT-1TI-0036")
        self.assertEqual(q36["opcion_a"].strip().lower(), "falso")
        self.assertEqual(q36["opcion_b"].strip().lower(), "verdadero")
        self.assertEqual(q36["correct_option"], "A")
        self.assertEqual(q36["correct_answer"].strip().lower(), "falso")

    def test_1timothy_epistle_epistolary_resolution(self) -> None:
        """Verifica que Pablo y Timoteo se resuelvan en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")

        # 1 Timoteo 1:3-4 — Pablo pide a Timoteo quedarse en Éfeso
        ti1_3_4 = {
            3: "Como te rogué que te quedases en Éfeso, cuando fui a Macedonia, para que mandases a algunos que no enseñen diferente doctrina,",
            4: "ni presten atención a fábulas y genealogías interminables, que acarrean disputas más bien que edificación de Dios que es por fe, así te encargo ahora."
        }
        q2 = self.timothy1_questions.get("NQB-NT-1TI-0002")
        if q2:
            res = evaluate_question(q2, ti1_3_4, book_key="1timothy")
            self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                                f"Q NQB-NT-1TI-0002 no debe ser REQUIERE_CORRECCION: {res.get('motivos_correccion')}")

    def test_1timothy_characters_and_places(self) -> None:
        """Verifica que himeneo esté en BIBLE_PERSONAJES y efeso en BIBLE_PLACES."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES
        self.assertIn("himeneo", BIBLE_PERSONAJES)
        self.assertIn("pablo", BIBLE_PERSONAJES)
        self.assertIn("timoteo", BIBLE_PERSONAJES)
        self.assertIn("efeso", BIBLE_PLACES)

    def test_1timothy_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 1 Timoteo."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.timothy1_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_1timothy_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 1 Timoteo y los 14 libros NT anteriores."""
        if not self.timothy1_questions:
            self.skipTest("1timothy-master-input.json no disponible")
        ti_texts = {q["question"].strip() for q in self.timothy1_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), ti_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 1 Timoteo")

    # --- PRUEBAS ESPECÍFICAS DE 2 TIMOTEO ---

    def get_timothy2_question(self, qid: str) -> dict:
        self.assertIn(qid, self.timothy2_questions, f"ID '{qid}' no encontrado en 2timothy-master-input.json")
        return copy.deepcopy(self.timothy2_questions[qid])

    def test_detect_book_key_2timothy(self) -> None:
        """Verifica detección de book_key para 2 Timoteo y sus variantes."""
        for alias in ["2 Timoteo", "2timoteo", "2 Timothy", "2timothy",
                       "2 tim", "2ti", "Segunda de Timoteo", "Segunda carta a Timoteo"]:
            spec = {"questions": [{"id": "NQB-NT-2TI-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "2timothy",
                             f"detect_book_key failed for alias: {alias}")

    def test_2timothy_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 2 Timoteo en BOOK_CONFIGS."""
        self.assertIn("2timothy", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["2timothy"]
        self.assertEqual(cfg["canonical_name"], "2 Timoteo")
        self.assertEqual(cfg["api_name"], "2Timoteo")
        self.assertEqual(cfg["total_chapters"], 4)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("2 timoteo", cfg["aliases"])
        self.assertIn("2timothy", cfg["aliases"])
        self.assertIn("2ti", cfg["aliases"])
        self.assertIn("roma", cfg["ambient_places"])
        self.assertIn("mileto", cfg["ambient_places"])
        self.assertIn("troas", cfg["ambient_places"])

    def test_2timothy_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        self.assertEqual(len(self.timothy2_questions), 24)

        # 6 preguntas por capítulo (4 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.timothy2_questions.values())
        self.assertEqual(len(ch_counts), 4)
        for ch in range(1, 5):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-2TI-0001 a NQB-NT-2TI-0024
        ids = sorted(self.timothy2_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-2TI-0001")
        self.assertEqual(ids[-1], "NQB-NT-2TI-0024")
        self.assertEqual(len(set(ids)), 24)

        # Dificultad: Básico=7, Intermedio=8, Avanzado=7, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.timothy2_questions.values())
        self.assertEqual(diff_counts["Básico"], 7)
        self.assertEqual(diff_counts["Intermedio"], 8)
        self.assertEqual(diff_counts["Avanzado"], 7)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 20 MC, 4 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.timothy2_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 20)
        self.assertEqual(type_counts["TRUE_FALSE"], 4)

        tf_ids = sorted(q["id"] for q in self.timothy2_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted(["NQB-NT-2TI-0006", "NQB-NT-2TI-0012", "NQB-NT-2TI-0018", "NQB-NT-2TI-0024"])
        self.assertEqual(tf_ids, expected_tf)

    def test_2timothy_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.timothy2_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 17)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 7)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_2timothy_additional_references(self) -> None:
        """Verifica las 6 preguntas con 10 referencias individuales en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-2TI-0002": ["Hechos 16:1-3"],
            "NQB-NT-2TI-0006": ["2 Timoteo 4:19"],
            "NQB-NT-2TI-0010": ["1 Timoteo 1:20"],
            "NQB-NT-2TI-0015": ["Hechos 13:50", "Hechos 14:5-6", "Hechos 14:19"],
            "NQB-NT-2TI-0021": ["Colosenses 4:14", "Filemón 1:24"],
            "NQB-NT-2TI-0024": ["Hechos 18:2-3", "Hechos 20:4"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.timothy2_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 6)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 10)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_2timothy_modes(self) -> None:
        """Verifica la asignación de modos en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.timothy2_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 24)
        self.assertEqual(mode_counts["AMBOS"], 24)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 7)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 7)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 4)

    def test_2timothy_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        for qid, q in self.timothy2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_2timothy_true_false_neutral_semantics(self) -> None:
        """Verifica que NQB-NT-2TI-0006 y NQB-NT-2TI-0024 operen con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        for qid in ["NQB-NT-2TI-0006", "NQB-NT-2TI-0024"]:
            q = self.get_timothy2_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

    def test_2timothy_epistle_epistolary_resolution(self) -> None:
        """Verifica que Pablo y Timoteo se resuelvan en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")

        # 2 Timoteo 1:3-5 — fe no fingida en Loida y Eunice
        ti2_1_3_5 = {
            3: "Doy gracias a Dios, al cual sirvo desde mis mayores con limpia conciencia, de que sin cesar me acuerdo de ti en mis oraciones noche y día;",
            4: "deseando verte, al acordarme de tus lágrimas, para llenarme de gozo;",
            5: "trayendo a la memoria la fe no fingida que hay en ti, la cual habitó primero en tu abuela Loida, y en tu madre Eunice, y estoy seguro que en ti también."
        }
        q2 = self.timothy2_questions.get("NQB-NT-2TI-0002")
        if q2:
            res = evaluate_question(q2, ti2_1_3_5, book_key="2timothy")
            self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                                f"Q NQB-NT-2TI-0002 no debe ser REQUIERE_CORRECCION: {res.get('incidencias')}")

    def test_2timothy_characters_and_places(self) -> None:
        """Verifica que personajes y lugares de 2 Timoteo estén en sus lexicons."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES
        for p in ["loida", "eunice", "figelo", "hermogenes", "onesiforo", "fileto", "janes", "jambres", "trofimo"]:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")
        for l in ["roma", "mileto", "troas", "antioquia", "iconio", "listra"]:
            self.assertIn(l, BIBLE_PLACES, f"Falta lugar: {l}")

    def test_2timothy_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 2 Timoteo."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.timothy2_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_2timothy_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 2 Timoteo y los 15 libros NT anteriores."""
        if not self.timothy2_questions:
            self.skipTest("2timothy-master-input.json no disponible")
        ti_texts = {q["question"].strip() for q in self.timothy2_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), ti_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 2 Timoteo")

    # --- PRUEBAS ESPECÍFICAS DE TITO ---

    def get_titus_question(self, qid: str) -> dict:
        self.assertIn(qid, self.titus_questions, f"ID '{qid}' no encontrado en titus-master-input.json")
        return copy.deepcopy(self.titus_questions[qid])

    def test_detect_book_key_titus(self) -> None:
        """Verifica detección de book_key para Tito y sus variantes."""
        for alias in ["Tito", "tito", "Titus", "titus", "tit", "Epístola a Tito", "Carta a Tito"]:
            spec = {"questions": [{"id": "NQB-NT-TIT-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "titus",
                             f"detect_book_key failed for alias: {alias}")

    def test_titus_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Tito en BOOK_CONFIGS."""
        self.assertIn("titus", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["titus"]
        self.assertEqual(cfg["canonical_name"], "Tito")
        self.assertEqual(cfg["api_name"], "Tito")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("tito", cfg["aliases"])
        self.assertIn("titus", cfg["aliases"])
        self.assertIn("tit", cfg["aliases"])
        self.assertIn("creta", cfg["ambient_places"])
        self.assertIn("nicopolis", cfg["ambient_places"])
        self.assertIn("dalmacia", cfg["ambient_places"])

    def test_titus_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        self.assertEqual(len(self.titus_questions), 18)

        # 6 preguntas por capítulo (3 capítulos)
        ch_counts = collections.Counter(q["chapter"] for q in self.titus_questions.values())
        self.assertEqual(len(ch_counts), 3)
        for ch in range(1, 4):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-TIT-0001 a NQB-NT-TIT-0018
        ids = sorted(self.titus_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-TIT-0001")
        self.assertEqual(ids[-1], "NQB-NT-TIT-0018")
        self.assertEqual(len(set(ids)), 18)

        # Dificultad: Básico=5, Intermedio=6, Avanzado=5, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.titus_questions.values())
        self.assertEqual(diff_counts["Básico"], 5)
        self.assertEqual(diff_counts["Intermedio"], 6)
        self.assertEqual(diff_counts["Avanzado"], 5)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 15 MC, 3 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.titus_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 15)
        self.assertEqual(type_counts["TRUE_FALSE"], 3)

        tf_ids = sorted(q["id"] for q in self.titus_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted(["NQB-NT-TIT-0006", "NQB-NT-TIT-0012", "NQB-NT-TIT-0018"])
        self.assertEqual(tf_ids, expected_tf)

    def test_titus_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.titus_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 14)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_titus_additional_references(self) -> None:
        """Verifica las 7 preguntas con 7 referencias individuales en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-TIT-0002": ["Hechos 14:23"],
            "NQB-NT-TIT-0003": ["1 Timoteo 3:1-7"],
            "NQB-NT-TIT-0010": ["Filemón 1:15-16"],
            "NQB-NT-TIT-0011": ["Efesios 2:8-10"],
            "NQB-NT-TIT-0014": ["Efesios 2:4-9"],
            "NQB-NT-TIT-0017": ["2 Timoteo 2:23-26"],
            "NQB-NT-TIT-0018": ["Hechos 18:24-28"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.titus_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 7)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 7)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_titus_modes(self) -> None:
        """Verifica la asignación de modos en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.titus_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 18)
        self.assertEqual(mode_counts["AMBOS"], 18)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 3)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 3)

    def test_titus_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        for qid, q in self.titus_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_titus_true_false_neutral_semantics(self) -> None:
        """Verifica que TIT0006 y TIT0018 operen con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        for qid in ["NQB-NT-TIT-0006", "NQB-NT-TIT-0018"]:
            q = self.get_titus_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

    def test_titus_epistle_epistolary_resolution(self) -> None:
        """Verifica que Pablo y Tito se resuelvan en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")

        # Tito 1:5 — Por esta causa te dejé en Creta
        tit1_5 = {
            5: "Por esta causa te dejé en Creta, para que corrigieses lo deficiente, y establecieses ancianos en cada ciudad, así como yo te mandé;"
        }
        q2 = self.titus_questions.get("NQB-NT-TIT-0002")
        if q2:
            res = evaluate_question(q2, tit1_5, book_key="titus")
            self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                                f"Q NQB-NT-TIT-0002 no debe ser REQUIERE_CORRECCION: {res.get('incidencias')}")

    def test_titus_characters_and_places(self) -> None:
        """Verifica que personajes y lugares de Tito estén en sus lexicons."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES
        for p in ["pablo", "tito", "artemas", "tiquico", "zenas", "apolos"]:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")
        for l in ["creta", "nicopolis", "dalmacia"]:
            self.assertIn(l, BIBLE_PLACES, f"Falta lugar: {l}")

    def test_titus_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Tito."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.titus_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_titus_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Tito y los 16 libros NT anteriores."""
        if not self.titus_questions:
            self.skipTest("titus-master-input.json no disponible")
        tit_texts = {q["question"].strip() for q in self.titus_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), tit_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Tito")

    # --- PRUEBAS ESPECÍFICAS DE FILEMÓN ---

    def get_philemon_question(self, qid: str) -> dict:
        self.assertIn(qid, self.philemon_questions, f"ID '{qid}' no encontrado en philemon-master-input.json")
        return copy.deepcopy(self.philemon_questions[qid])

    def test_detect_book_key_philemon(self) -> None:
        """Verifica detección de book_key para Filemón y sus variantes."""
        for alias in ["Filemón", "filemon", "Filemon", "Philemon", "philemon", "phlm", "flm", "Epístola a Filemón", "Carta a Filemón"]:
            spec = {"questions": [{"id": "NQB-NT-FLM-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "philemon",
                             f"detect_book_key failed for alias: {alias}")

    def test_philemon_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Filemón en BOOK_CONFIGS."""
        self.assertIn("philemon", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["philemon"]
        self.assertEqual(cfg["canonical_name"], "Filemón")
        self.assertEqual(cfg["api_name"], "Filemon")
        self.assertEqual(cfg["total_chapters"], 1)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("filemon", cfg["aliases"])
        self.assertIn("filemón", cfg["aliases"])
        self.assertIn("philemon", cfg["aliases"])
        self.assertIn("phlm", cfg["aliases"])
        self.assertIn("flm", cfg["aliases"])
        self.assertIn("roma", cfg["ambient_places"])
        self.assertIn("colosas", cfg["ambient_places"])

    def test_philemon_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        self.assertEqual(len(self.philemon_questions), 6)

        # 6 preguntas en capítulo 1
        ch_counts = collections.Counter(q["chapter"] for q in self.philemon_questions.values())
        self.assertEqual(len(ch_counts), 1)
        self.assertEqual(ch_counts[1], 6)

        # IDs: NQB-NT-FLM-0001 a NQB-NT-FLM-0006
        ids = sorted(self.philemon_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-FLM-0001")
        self.assertEqual(ids[-1], "NQB-NT-FLM-0006")
        self.assertEqual(len(set(ids)), 6)

        # Dificultad: Básico=2, Intermedio=2, Avanzado=1, Experto=1
        diff_counts = collections.Counter(q["difficulty"] for q in self.philemon_questions.values())
        self.assertEqual(diff_counts["Básico"], 2)
        self.assertEqual(diff_counts["Intermedio"], 2)
        self.assertEqual(diff_counts["Avanzado"], 1)
        self.assertEqual(diff_counts["Experto"], 1)

        # Tipos: 5 MC, 1 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.philemon_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 5)
        self.assertEqual(type_counts["TRUE_FALSE"], 1)

        tf_ids = sorted(q["id"] for q in self.philemon_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = ["NQB-NT-FLM-0006"]
        self.assertEqual(tf_ids, expected_tf)

    def test_philemon_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.philemon_questions.values())
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        self.assertEqual(cat_counts["NT_GENERAL"], 2)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_philemon_additional_references(self) -> None:
        """Verifica las 3 preguntas con 3 referencias individuales en Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-FLM-0001": ["Colosenses 4:17"],
            "NQB-NT-FLM-0003": ["Colosenses 4:9"],
            "NQB-NT-FLM-0006": ["Colosenses 4:10-14"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.philemon_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 3)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 3)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_philemon_modes(self) -> None:
        """Verifica la asignación de modos en Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.philemon_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 6)
        self.assertEqual(mode_counts["AMBOS"], 6)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 1)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 1)

    def test_philemon_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        for qid, q in self.philemon_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_philemon_true_false_neutral_semantics(self) -> None:
        """Verifica que FLM0006 opere con semántica neutral (A=Falso, B=Verdadero, correct=A)."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        q = self.get_philemon_question("NQB-NT-FLM-0006")
        self.assertEqual(q["opcion_a"].strip().lower(), "falso", "FLM0006: opcion_a debe ser Falso")
        self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", "FLM0006: opcion_b debe ser Verdadero")
        self.assertEqual(q["correct_option"], "A", "FLM0006: correct_option debe ser A")
        self.assertEqual(q["correct_answer"].strip().lower(), "falso", "FLM0006: correct_answer debe ser Falso")

    def test_philemon_characters_and_places(self) -> None:
        """Verifica que personajes y lugares de Filemón estén en sus lexicons."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES
        for p in ["pablo", "timoteo", "filemon", "filemón", "apia", "arquipo", "onesimo", "onésimo", "epafras", "marcos", "aristarco", "demas", "lucas"]:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")
        for l in ["roma", "colosas"]:
            self.assertIn(l, BIBLE_PLACES, f"Falta lugar: {l}")

    def test_philemon_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Filemón."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.philemon_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_philemon_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Filemón y los 17 libros NT anteriores."""
        if not self.philemon_questions:
            self.skipTest("philemon-master-input.json no disponible")
        flm_texts = {q["question"].strip() for q in self.philemon_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), flm_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Filemón")

    # --- PRUEBAS ESPECÍFICAS DE HEBREOS ---

    def get_hebrews_question(self, qid: str) -> dict:
        self.assertIn(qid, self.hebrews_questions, f"ID '{qid}' no encontrado en hebrews-master-input.json")
        return copy.deepcopy(self.hebrews_questions[qid])

    def test_detect_book_key_hebrews(self) -> None:
        """Verifica detección de book_key para Hebreos y sus variantes."""
        for alias in ["Hebreos", "hebreos", "Hebrews", "hebrews", "heb", "Epístola a los Hebreos", "Carta a los Hebreos"]:
            spec = {"questions": [{"id": "NQB-NT-HEB-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "hebrews",
                             f"detect_book_key failed for alias: {alias}")

    def test_hebrews_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Hebreos en BOOK_CONFIGS."""
        self.assertIn("hebrews", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["hebrews"]
        self.assertEqual(cfg["canonical_name"], "Hebreos")
        self.assertEqual(cfg["api_name"], "Hebreos")
        self.assertEqual(cfg["total_chapters"], 13)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("hebreos", cfg["aliases"])
        self.assertIn("hebrews", cfg["aliases"])
        self.assertIn("heb", cfg["aliases"])
        self.assertIn("salem", cfg["ambient_places"])
        self.assertIn("sinai", cfg["ambient_places"])
        self.assertIn("sion", cfg["ambient_places"])
        self.assertIn("italia", cfg["ambient_places"])

    def test_hebrews_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        self.assertEqual(len(self.hebrews_questions), 78)

        # 6 preguntas en cada uno de los 13 capítulos
        ch_counts = collections.Counter(q["chapter"] for q in self.hebrews_questions.values())
        self.assertEqual(len(ch_counts), 13)
        for ch in range(1, 14):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-HEB-0001 a NQB-NT-HEB-0078
        ids = sorted(self.hebrews_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-HEB-0001")
        self.assertEqual(ids[-1], "NQB-NT-HEB-0078")
        self.assertEqual(len(set(ids)), 78)

        # Dificultad: Básico=22, Intermedio=26, Avanzado=22, Experto=8
        diff_counts = collections.Counter(q["difficulty"] for q in self.hebrews_questions.values())
        self.assertEqual(diff_counts["Básico"], 22)
        self.assertEqual(diff_counts["Intermedio"], 26)
        self.assertEqual(diff_counts["Avanzado"], 22)
        self.assertEqual(diff_counts["Experto"], 8)

        # Tipos: 65 MC, 13 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.hebrews_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 65)
        self.assertEqual(type_counts["TRUE_FALSE"], 13)

        tf_ids = sorted(q["id"] for q in self.hebrews_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted([f"NQB-NT-HEB-{i:04d}" for i in range(6, 79, 6)])
        self.assertEqual(tf_ids, expected_tf)

    def test_hebrews_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.hebrews_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 64)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 14)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_hebrews_additional_references(self) -> None:
        """Verifica las 12 preguntas con 14 referencias individuales en Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-HEB-0003": ["Salmos 2:7", "2 Samuel 7:14"],
            "NQB-NT-HEB-0014": ["Salmos 95:7-11"],
            "NQB-NT-HEB-0016": ["Números 14:1-35"],
            "NQB-NT-HEB-0026": ["Salmos 110:4"],
            "NQB-NT-HEB-0034": ["Génesis 22:16-18"],
            "NQB-NT-HEB-0037": ["Génesis 14:18-20"],
            "NQB-NT-HEB-0044": ["Jeremías 31:31-34"],
            "NQB-NT-HEB-0050": ["Levítico 16:1-34"],
            "NQB-NT-HEB-0063": ["Génesis 12:1-4", "Génesis 21:1-3"],
            "NQB-NT-HEB-0064": ["Éxodo 2:11-15"],
            "NQB-NT-HEB-0065": ["Josué 2:1-21"],
            "NQB-NT-HEB-0069": ["Génesis 25:29-34"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.hebrews_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 12)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 14)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_hebrews_modes(self) -> None:
        """Verifica la asignación de modos en Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.hebrews_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 78)
        self.assertEqual(mode_counts["AMBOS"], 78)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 14)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 14)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 13)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 13)

    def test_hebrews_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        for qid, q in self.hebrews_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_hebrews_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE: primeros 12 A=Falso/correct=A, HEB0078 A=Verdadero/correct=A."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        tf_ids = [f"NQB-NT-HEB-{i:04d}" for i in range(6, 79, 6)]
        for qid in tf_ids[:12]:
            q = self.get_hebrews_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

        # HEB0078: A=Verdadero, B=Falso, correct_option=A, correct_answer=Verdadero
        q78 = self.get_hebrews_question("NQB-NT-HEB-0078")
        self.assertEqual(q78["opcion_a"].strip().lower(), "verdadero", "HEB0078: opcion_a debe ser Verdadero")
        self.assertEqual(q78["opcion_b"].strip().lower(), "falso", "HEB0078: opcion_b debe ser Falso")
        self.assertEqual(q78["correct_option"], "A", "HEB0078: correct_option debe ser A")
        self.assertEqual(q78["correct_answer"].strip().lower(), "verdadero", "HEB0078: correct_answer debe ser Verdadero")

    def test_hebrews_author_not_attributed_to_paul(self) -> None:
        """Verifica que Hebreos no se trate como epístola paulina ni atribuya autoría a Pablo."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        # resolve_implicit_speaker no debe resolver Pablo en Hebreos
        from auditor import resolve_implicit_speaker
        verse_map = {1: "Dios, habiendo hablado muchas veces y de muchas maneras en otro tiempo a los padres por los profetas,"}
        resolved = resolve_implicit_speaker("pablo", "dios habiendo hablado...", verse_map, 1, [], book_key="hebrews")
        self.assertFalse(resolved, "Pablo no debe ser resuelto como orador implícito en Hebreos")

    def test_hebrews_characters_and_places(self) -> None:
        """Verifica que personajes y lugares de Hebreos estén en sus lexicons."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES
        expected_chars = [
            "moises", "josue", "abraham", "melquisedec", "abel", "enoc", "noe",
            "sara", "isaac", "jacob", "jose", "rahab", "gedeon", "barac", "sanson",
            "jefte", "david", "samuel", "esau", "timoteo", "aaron"
        ]
        for p in expected_chars:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")
        for l in ["salem", "sinai", "sion", "italia", "roma"]:
            self.assertIn(l, BIBLE_PLACES, f"Falta lugar: {l}")

    def test_hebrews_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Hebreos."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.hebrews_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_hebrews_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Hebreos y los 18 libros NT anteriores."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        heb_texts = {q["question"].strip() for q in self.hebrews_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), heb_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Hebreos")

    def test_hebrews_contextual_title_heb0005(self) -> None:
        """Verifica que NQB-NT-HEB-0005 resuelva 'Hijo' contextualmente sin marcar FAIL ni REQUIERE_CORRECCION."""
        if not self.hebrews_questions:
            self.skipTest("hebrews-master-input.json no disponible")
        q5 = self.get_hebrews_question("NQB-NT-HEB-0005")
        heb1_verses = {
            1: "Dios, habiendo hablado muchas veces y de muchas maneras en otro tiempo a los padres por los profetas,",
            2: "en estos postreros días nos ha hablado por el Hijo, a quien constituyó heredero de todo, y por quien asimismo hizo el universo;",
            3: "el cual, siendo el resplandor de su gloria, y la imagen misma de su sustancia, y quien sustenta todas las cosas con la palabra de su poder, habiendo efectuado la purificación de nuestros pecados por medio de sí mismo, se sentó a la diestra de la Majestad en las alturas,",
            4: "hecho tanto superior a los ángeles, cuanto heredó más excelente nombre que ellos.",
            5: "Porque ¿a cuál de los ángeles dijo jamás: Mi Hijo eres tú, Yo te he engendrado hoy, y otra vez: Yo seré a él Padre, Y él me será a mí hijo?",
            6: "Y otra vez, cuando introduce al Primogénito en el mundo, dice: Adórenle todos los ángeles de Dios.",
            7: "Ciertamente de los ángeles dice: El que hace a sus ángeles espíritus, Y a sus ministros llama de fuego.",
            8: "Mas del Hijo dice: Tu trono, oh Dios, por el siglo del siglo; Cetro de equidad es el cetro de tu reino.",
            9: "Has amado la justicia, y aborrecido la maldad, Por lo cual te ungió Dios, el Dios tuyo, Con óleo de alegría más que a tus compañeros.",
            10: "Y: Tú, oh Señor, en el principio fundaste la tierra, Y los cielos son obra de tus manos.",
            11: "Ellos perecerán, mas tú permaneces; Y todos ellos se envejecerán como una vestidura,",
            12: "Y como un vestido los envolverás, y serán mudados; Pero tú eres el mismo, Y tus años no acabarán.",
            13: "Pues, ¿a cuál de los ángeles dijo jamás: Siéntate a mi diestra, Hasta que ponga a tus enemigos por estrado de tus pies?",
            14: "¿No son todos espíritus ministradores, enviados para servicio a favor de los que serán herederos de la salvación?"
        }
        res = evaluate_question(q5, heb1_verses, book_key="hebrews")
        self.assertNotEqual(res["controles_superados"]["control_relaciones_personajes"], "FAIL",
                            f"control_relaciones_personajes no debe ser FAIL: {res.get('incidencias')}")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION",
                            f"NQB-NT-HEB-0005 no debe ser REQUIERE_CORRECCION: {res.get('incidencias')}")

    def test_contextual_title_usage_generic_positive(self) -> None:
        """Verifica que un uso de 'Hijo' como título cristológico con anclaje previo resuelva positivamente."""
        from auditor import is_contextual_title_usage
        verse_map = {
            1: "Dios nos ha hablado por el Hijo...",
            8: "Mas del Hijo dice: Tu trono, oh Dios...",
            10: "Tú, oh Señor, en el principio fundaste la tierra...",
            11: "Ellos perecerán, mas tú permaneces...",
            12: "Pero tú eres el mismo...",
        }
        text_norm = "la creacion puede cambiar pero al hijo se le atribuye permanencia"
        res = is_contextual_title_usage(
            stem="hij",
            text_norm=text_norm,
            verse_map=verse_map,
            start_verse=10,
            characters=["Jesucristo"],
            category="NT_GENERAL",
            eligible_modes=["NT", "AMBOS"]
        )
        self.assertTrue(res, "Debe resolver título cristológico con anclaje en v8")

    def test_contextual_title_usage_negative_kinship(self) -> None:
        """Verifica que una afirmación familiar real no respaldada siga fallando (regresión negativa obligatoria)."""
        from auditor import is_contextual_title_usage
        verse_map = {
            1: "Palabras de la historia...",
            5: "Y vinieron los mensajeros...",
            6: "Y vieron la ciudad...",
        }
        text_norm = "salomon era hijo de saul"
        res = is_contextual_title_usage(
            stem="hij",
            text_norm=text_norm,
            verse_map=verse_map,
            start_verse=5,
            characters=["Salomón", "Saúl"],
            category="PERSONAJES_BIBLICOS",
            eligible_modes=["NT"]
        )
        self.assertFalse(res, "No debe otorgar título a una relación de parentesco humana falsa")

        # Comprobar que evaluate_question marque FAIL en control_relaciones_personajes
        fake_q = {
            "id": "TEST-KIN-FAIL",
            "book": "Génesis",
            "chapter": 1,
            "verse_start": 5,
            "verse_end": 6,
            "reference": "Génesis 1:5-6",
            "category": "PERSONAJES_BIBLICOS",
            "characters": ["Salomón"],
            "difficulty": "Básico",
            "question_type": "MULTIPLE_CHOICE",
            "question": "¿Quién era hijo de Saúl?",
            "opcion_a": "Salomón era hijo de Saúl",
            "opcion_b": "David",
            "opcion_c": "Jonatán",
            "opcion_d": "Samuel",
            "correct_option": "A",
            "correct_answer": "Salomón era hijo de Saúl",
            "explanation": "Afirmación de prueba",
            "additional_references": [],
            "eligible_modes": ["NT"]
        }
        eval_res = evaluate_question(fake_q, verse_map, book_key="genesis")
        self.assertEqual(eval_res["controles_superados"]["control_relaciones_personajes"], "FAIL")
        self.assertEqual(eval_res["estado"], "REQUIERE_CORRECCION")

    def test_contextual_title_usage_no_anchor(self) -> None:
        """Verifica que 'Hijo' sin anclaje previo en el capítulo no otorgue título contextual."""
        from auditor import is_contextual_title_usage
        verse_map = {
            10: "Tú, oh Señor, en el principio fundaste la tierra...",
            11: "Ellos perecerán, mas tú permaneces...",
            12: "Pero tú eres el mismo...",
        }
        text_norm = "al hijo se le atribuye permanencia"
        res = is_contextual_title_usage(
            stem="hij",
            text_norm=text_norm,
            verse_map=verse_map,
            start_verse=10,
            characters=["Jesucristo"],
            category="NT_GENERAL",
            eligible_modes=["NT"]
        )
        self.assertFalse(res, "Sin versículos anteriores con anclaje, no debe conceder título")

    # --- PRUEBAS ESPECÍFICAS DE SANTIAGO ---

    def get_james_question(self, qid: str) -> dict:
        self.assertIn(qid, self.james_questions, f"ID '{qid}' no encontrado en james-master-input.json")
        return copy.deepcopy(self.james_questions[qid])

    def test_detect_book_key_james(self) -> None:
        """Verifica detección de book_key para Santiago y sus variantes."""
        for alias in ["Santiago", "santiago", "James", "james", "stg", "san", "Epístola de Santiago", "Carta de Santiago"]:
            spec = {"questions": [{"id": "NQB-NT-SAN-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "james",
                             f"detect_book_key failed for alias: {alias}")

    def test_james_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Santiago en BOOK_CONFIGS."""
        self.assertIn("james", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["james"]
        self.assertEqual(cfg["canonical_name"], "Santiago")
        self.assertEqual(cfg["api_name"], "Santiago")
        self.assertEqual(cfg["total_chapters"], 5)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("santiago", cfg["aliases"])
        self.assertIn("james", cfg["aliases"])
        self.assertIn("stg", cfg["aliases"])
        self.assertIn("san", cfg["aliases"])

    def test_james_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        self.assertEqual(len(self.james_questions), 30)

        # 6 preguntas en cada uno de los 5 capítulos
        ch_counts = collections.Counter(q["chapter"] for q in self.james_questions.values())
        self.assertEqual(len(ch_counts), 5)
        for ch in range(1, 6):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-SAN-0001 a NQB-NT-SAN-0030
        ids = sorted(self.james_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-SAN-0001")
        self.assertEqual(ids[-1], "NQB-NT-SAN-0030")
        self.assertEqual(len(set(ids)), 30)

        # Dificultad: Básico=6, Intermedio=10, Avanzado=9, Experto=5
        diff_counts = collections.Counter(q["difficulty"] for q in self.james_questions.values())
        self.assertEqual(diff_counts["Básico"], 6)
        self.assertEqual(diff_counts["Intermedio"], 10)
        self.assertEqual(diff_counts["Avanzado"], 9)
        self.assertEqual(diff_counts["Experto"], 5)

        # Tipos: 25 MC, 5 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.james_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 25)
        self.assertEqual(type_counts["TRUE_FALSE"], 5)

        tf_ids = sorted(q["id"] for q in self.james_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted([f"NQB-NT-SAN-{i:04d}" for i in [6, 12, 18, 24, 30]])
        self.assertEqual(tf_ids, expected_tf)

    def test_james_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.james_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 25)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 5)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_james_additional_references(self) -> None:
        """Verifica las 9 preguntas con 11 referencias individuales en Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-SAN-0002": ["Romanos 5:3-4"],
            "NQB-NT-SAN-0007": ["Levítico 19:15"],
            "NQB-NT-SAN-0009": ["1 Juan 3:17-18"],
            "NQB-NT-SAN-0011": ["Génesis 22:1-18"],
            "NQB-NT-SAN-0012": ["Josué 2:1-21"],
            "NQB-NT-SAN-0015": ["Proverbios 15:1"],
            "NQB-NT-SAN-0023": ["Proverbios 27:1"],
            "NQB-NT-SAN-0026": ["Job 1:20-22", "Job 2:9-10"],
            "NQB-NT-SAN-0029": ["1 Reyes 17:1", "1 Reyes 18:41-45"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.james_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 9)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 11)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_james_modes(self) -> None:
        """Verifica la asignación de modos en Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.james_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 30)
        self.assertEqual(mode_counts["AMBOS"], 30)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 5)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 5)

    def test_james_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        for qid, q in self.james_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_james_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE: SAN0012 A=Verdadero/correct=A, otros 4 A=Falso/correct=A."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        for qid in ["NQB-NT-SAN-0006", "NQB-NT-SAN-0018", "NQB-NT-SAN-0024", "NQB-NT-SAN-0030"]:
            q = self.get_james_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

        # SAN0012: A=Verdadero, B=Falso, correct_option=A, correct_answer=Verdadero
        q12 = self.get_james_question("NQB-NT-SAN-0012")
        self.assertEqual(q12["opcion_a"].strip().lower(), "verdadero", "SAN0012: opcion_a debe ser Verdadero")
        self.assertEqual(q12["opcion_b"].strip().lower(), "falso", "SAN0012: opcion_b debe ser Falso")
        self.assertEqual(q12["correct_option"], "A", "SAN0012: correct_option debe ser A")
        self.assertEqual(q12["correct_answer"].strip().lower(), "verdadero", "SAN0012: correct_answer debe ser Verdadero")

    def test_james_characters_and_epistolar_speaker(self) -> None:
        """Verifica que personajes de Santiago estén en BIBLE_PERSONAJES y resolve_implicit_speaker funcione."""
        from auditor import BIBLE_PERSONAJES, resolve_implicit_speaker
        expected_chars = ["santiago", "abraham", "rahab", "job", "elias"]
        for p in expected_chars:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")

        verse_map = {
            1: "Santiago, siervo de Dios y del Señor Jesucristo, a las doce tribus que están en la dispersión: Salud.",
            2: "Hermanos míos, tened por sumo gozo cuando os halléis en diversas pruebas,"
        }
        passage_norm = "hermanos mios tened por sumo gozo cuando os halleis en diversas pruebas"
        resolved = resolve_implicit_speaker("santiago", passage_norm, verse_map, 2, ["Santiago"], book_key="james")
        self.assertTrue(resolved, "Santiago debe resolverse como autor/remitente epistolar en Santiago")

    def test_james_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Santiago."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.james_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_james_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Santiago y los 19 libros NT anteriores."""
        if not self.james_questions:
            self.skipTest("james-master-input.json no disponible")
        san_texts = {q["question"].strip() for q in self.james_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), san_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Santiago")

    def test_is_biblical_person_usage_demas(self) -> None:
        """Verifica la desambiguación genérica entre Demas (personaje bíblico) y demás (uso común)."""
        from auditor import is_biblical_person_usage

        # TEST 1: Uso común con tilde
        self.assertFalse(
            is_biblical_person_usage("demas", "una persona humana como los demás"),
            "Uso común con tilde ('los demás') debe retornar False"
        )

        # TEST 2: Texto sin tilde
        self.assertFalse(
            is_biblical_person_usage("demas", "una persona humana como los demas"),
            "Uso común sin tilde ('los demas') debe retornar False"
        )

        # Locuciones comunes adicionales
        self.assertFalse(is_biblical_person_usage("demas", "a los demás creyentes"))
        self.assertFalse(is_biblical_person_usage("demas", "de las demás personas"))
        self.assertFalse(is_biblical_person_usage("demas", "por lo demás, hermanos míos"))
        self.assertFalse(is_biblical_person_usage("demas", "y demás cosas semejantes"))

        # TEST 3: Uso bíblico real (2 Timoteo 4:10)
        self.assertTrue(
            is_biblical_person_usage("demas", "Demas me ha desamparado, amando este mundo"),
            "Uso bíblico real con nombre 'Demas' debe retornar True"
        )

        # TEST 4: Uso bíblico real (Colosenses 4:14)
        self.assertTrue(
            is_biblical_person_usage("demas", "Lucas el médico amado, y Demas"),
            "Uso bíblico real 'Lucas el médico amado, y Demas' debe retornar True"
        )

        # TEST 5: Uso bíblico real (Filemón 1:24)
        self.assertTrue(
            is_biblical_person_usage("demas", "Te saludan ... Demas y Lucas"),
            "Uso bíblico real 'Te saludan ... Demas y Lucas' debe retornar True"
        )

    def test_regression_san_0029_demas_disambiguation(self) -> None:
        """Verifica que NQB-NT-SAN-0029 no falle por el falso positivo de Demas/demás."""
        from auditor import evaluate_question

        san29_q = {
            "id": "NQB-NT-SAN-0029",
            "book": "Santiago",
            "chapter": 5,
            "verse_start": 17,
            "verse_end": 18,
            "reference": "Santiago 5:17-18",
            "category": "PERSONAJES_BIBLICOS",
            "subcategory": "Elías y la oración",
            "characters": ["Elías"],
            "difficulty": "Avanzado",
            "question_type": "MULTIPLE_CHOICE",
            "question": "¿Qué propósito cumple el ejemplo de Elías dentro de la enseñanza sobre la oración?",
            "opcion_a": "Mostrar que una persona humana como los demás puede orar con fervor y que la oración importa",
            "opcion_b": "Convertir a Elías en garantía de que toda petición producirá el mismo fenómeno natural",
            "opcion_c": "Autorizar a creyentes actuales a controlar el clima",
            "opcion_d": "Enseñar que una oración no respondida demuestra necesariamente falta de fe",
            "correct_option": "A",
            "correct_answer": "Mostrar que una persona humana como los demás puede orar con fervor y que la oración importa",
            "explanation": "Elías ejemplifica una oración ferviente dentro del argumento de Santiago. El ejemplo no ofrece control automático del clima ni una fórmula para juzgar la fe de otras personas.",
            "additional_references": ["1 Reyes 17:1", "1 Reyes 18:41-45"],
            "eligible_modes": ["NT", "AMBOS", "PERSONAJES_NT", "PERSONAJES_AMBOS"]
        }

        # Simular verse_map completo del capítulo 5 de Santiago
        verse_map = {v: f"Versículo simulado {v}" for v in range(1, 21)}
        verse_map[17] = "Elías era hombre sujeto a pasiones semejantes a las nuestras, y oró fervientemente para que no lloviese, y no llovió sobre la tierra por tres años y seis meses."
        verse_map[18] = "Y otra vez oró, y el cielo dio lluvia, y la tierra produjo su fruto."

        eval_res = evaluate_question(san29_q, verse_map, book_key="james")

        self.assertNotEqual(eval_res["controles_superados"]["control_nombres_propios"], "FAIL",
                            "control_nombres_propios no debe ser FAIL por 'demás'")
        self.assertNotEqual(eval_res["controles_superados"]["control_rango_suficiente"], "FAIL",
                            "control_rango_suficiente no debe ser FAIL")
        self.assertNotEqual(eval_res["estado"], "REQUIERE_CORRECCION",
                            "El estado de SAN-0029 no debe ser REQUIERE_CORRECCION")

    def test_regression_demas_biblical_character_references(self) -> None:
        """Verifica que el personaje Demas sea correctamente reconocido en sus referencias bíblicas reales."""
        from auditor import evaluate_question

        # 2 Timoteo 4:10
        tim2_q = {
            "id": "TEST-2TI-0001",
            "book": "2 Timoteo",
            "chapter": 4,
            "verse_start": 10,
            "verse_end": 10,
            "reference": "2 Timoteo 4:10",
            "category": "PERSONAJES_BIBLICOS",
            "characters": ["Demas"],
            "difficulty": "Intermedio",
            "question_type": "MULTIPLE_CHOICE",
            "question": "¿Quién desamparó a Pablo por amor al mundo presente?",
            "opcion_a": "Demas",
            "opcion_b": "Lucas",
            "opcion_c": "Tito",
            "opcion_d": "Crescencio",
            "correct_option": "A",
            "correct_answer": "Demas",
            "explanation": "Demas desamparó a Pablo habiendo amado este mundo.",
            "additional_references": [],
            "eligible_modes": ["NT"]
        }
        verse_map = {v: f"Versículo simulado {v}" for v in range(1, 23)}
        verse_map[10] = "porque Demas me ha desamparado, amando este mundo, y se ha ido a Tesalónica, Crescente a Galacia, y Tito a Dalmacia."

        eval_res = evaluate_question(tim2_q, verse_map, book_key="2timothy")
        self.assertEqual(eval_res["controles_superados"]["control_nombres_propios"], "PASS",
                         "Demas debe ser detectado como personaje bíblico válido en 2 Timoteo 4:10")

    # --- PRUEBAS ESPECÍFICAS DE 1 PEDRO ---

    def get_1peter_question(self, qid: str) -> dict:
        self.assertIn(qid, self.peter1_questions, f"ID '{qid}' no encontrado en 1peter-master-input.json")
        return copy.deepcopy(self.peter1_questions[qid])

    def test_detect_book_key_1peter(self) -> None:
        """Verifica detección de book_key para 1 Pedro y sus variantes."""
        for alias in ["1 Pedro", "1pedro", "1 Peter", "1peter", "1 pe", "1pe", "Primera de Pedro", "Primera carta de Pedro", "1ª Pedro", "1ra Pedro"]:
            spec = {"questions": [{"id": "NQB-NT-1PE-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "1peter",
                             f"detect_book_key failed for alias: {alias}")

    def test_1peter_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 1 Pedro en BOOK_CONFIGS."""
        self.assertIn("1peter", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["1peter"]
        self.assertEqual(cfg["canonical_name"], "1 Pedro")
        self.assertEqual(cfg["api_name"], "1 Pedro")
        self.assertEqual(cfg["total_chapters"], 5)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("1 pedro", cfg["aliases"])
        self.assertIn("1peter", cfg["aliases"])
        self.assertIn("1pe", cfg["aliases"])
        self.assertIn("1 pe", cfg["aliases"])

    def test_1peter_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        self.assertEqual(len(self.peter1_questions), 30)

        # 6 preguntas en cada uno de los 5 capítulos
        ch_counts = collections.Counter(q["chapter"] for q in self.peter1_questions.values())
        self.assertEqual(len(ch_counts), 5)
        for ch in range(1, 6):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-1PE-0001 a NQB-NT-1PE-0030
        ids = sorted(self.peter1_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-1PE-0001")
        self.assertEqual(ids[-1], "NQB-NT-1PE-0030")
        self.assertEqual(len(set(ids)), 30)

        # Dificultad: Básico=6, Intermedio=10, Avanzado=9, Experto=5
        diff_counts = collections.Counter(q["difficulty"] for q in self.peter1_questions.values())
        self.assertEqual(diff_counts["Básico"], 6)
        self.assertEqual(diff_counts["Intermedio"], 10)
        self.assertEqual(diff_counts["Avanzado"], 9)
        self.assertEqual(diff_counts["Experto"], 5)

        # Tipos: 25 MC, 5 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.peter1_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 25)
        self.assertEqual(type_counts["TRUE_FALSE"], 5)

        tf_ids = sorted(q["id"] for q in self.peter1_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted([f"NQB-NT-1PE-{i:04d}" for i in [6, 12, 18, 24, 30]])
        self.assertEqual(tf_ids, expected_tf)

    def test_1peter_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.peter1_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 26)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_1peter_additional_references(self) -> None:
        """Verifica las 10 preguntas con 12 referencias individuales en 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-1PE-0002": ["Romanos 6:4-5"],
            "NQB-NT-1PE-0004": ["Levítico 11:44"],
            "NQB-NT-1PE-0006": ["Isaías 40:6-8"],
            "NQB-NT-1PE-0008": ["Éxodo 19:5-6", "Isaías 28:16"],
            "NQB-NT-1PE-0011": ["Isaías 53:4-6"],
            "NQB-NT-1PE-0013": ["Génesis 18:12"],
            "NQB-NT-1PE-0017": ["Génesis 6:9-22"],
            "NQB-NT-1PE-0021": ["Proverbios 10:12"],
            "NQB-NT-1PE-0026": ["Salmos 55:22"],
            "NQB-NT-1PE-0029": ["1 Tesalonicenses 1:1", "Hechos 12:12"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.peter1_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 10)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 12)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_1peter_modes(self) -> None:
        """Verifica la asignación de modos en 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.peter1_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 30)
        self.assertEqual(mode_counts["AMBOS"], 30)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 5)

    def test_1peter_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        for qid, q in self.peter1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_1peter_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE: 1PE0018 A=Verdadero/correct=A, otros 4 A=Falso/correct=A."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        for qid in ["NQB-NT-1PE-0006", "NQB-NT-1PE-0012", "NQB-NT-1PE-0024", "NQB-NT-1PE-0030"]:
            q = self.get_1peter_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

        # 1PE0018: A=Verdadero, B=Falso, correct_option=A, correct_answer=Verdadero
        q18 = self.get_1peter_question("NQB-NT-1PE-0018")
        self.assertEqual(q18["opcion_a"].strip().lower(), "verdadero", "1PE0018: opcion_a debe ser Verdadero")
        self.assertEqual(q18["opcion_b"].strip().lower(), "falso", "1PE0018: opcion_b debe ser Falso")
        self.assertEqual(q18["correct_option"], "A", "1PE0018: correct_option debe ser A")
        self.assertEqual(q18["correct_answer"].strip().lower(), "verdadero", "1PE0018: correct_answer debe ser Verdadero")

    def test_1peter_characters_places_and_epistolar_speaker(self) -> None:
        """Verifica entidades y resolve_implicit_speaker para Pedro en 1 Pedro."""
        from auditor import BIBLE_PERSONAJES, BIBLE_PLACES, resolve_implicit_speaker
        expected_chars = ["pedro", "sara", "noe", "silvano", "marcos"]
        for p in expected_chars:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")

        expected_places = ["ponto", "galacia", "capadocia", "asia", "bitinia", "babilonia"]
        for pl in expected_places:
            self.assertIn(pl, BIBLE_PLACES, f"Falta lugar: {pl}")

        verse_map = {
            1: "Pedro, apóstol de Jesucristo, a los expatriados de la dispersión en el Ponto, Galacia, Capadocia, Asia y Bitinia,",
            2: "elegidos según la presciencia de Dios Padre en santificación del Espíritu, para obedecer y ser rociados con la sangre de Jesucristo: Gracia y paz os sean multiplicadas.",
            3: "Bendito el Dios y Padre de nuestro Señor Jesucristo, que según su grande misericordia nos hizo renacer..."
        }
        passage_norm = "bendito el dios y padre de nuestro senor jesucristo que segun su grande misericordia nos hizo renacer"
        resolved = resolve_implicit_speaker("pedro", passage_norm, verse_map, 3, ["Pedro"], book_key="1peter")
        self.assertTrue(resolved, "Pedro debe resolverse como autor/remitente epistolar en 1 Pedro")

    def test_1peter_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 1 Pedro."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.peter1_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_1peter_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 1 Pedro y los 20 libros NT anteriores."""
        if not self.peter1_questions:
            self.skipTest("1peter-master-input.json no disponible")
        pe1_texts = {q["question"].strip() for q in self.peter1_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), pe1_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 1 Pedro")

    # --- PRUEBAS ESPECÍFICAS DE 2 PEDRO ---

    def get_2peter_question(self, qid: str) -> dict:
        self.assertIn(qid, self.peter2_questions, f"ID '{qid}' no encontrado en 2peter-master-input.json")
        return copy.deepcopy(self.peter2_questions[qid])

    def test_detect_book_key_2peter(self) -> None:
        """Verifica detección de book_key para 2 Pedro y sus variantes."""
        for alias in ["2 Pedro", "2pedro", "2 Peter", "2peter", "2 pe", "2pe", "Segunda de Pedro", "Segunda carta de Pedro", "2ª Pedro", "2ra Pedro"]:
            spec = {"questions": [{"id": "NQB-NT-2PE-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "2peter",
                             f"detect_book_key failed for alias: {alias}")

    def test_2peter_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 2 Pedro en BOOK_CONFIGS."""
        self.assertIn("2peter", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["2peter"]
        self.assertEqual(cfg["canonical_name"], "2 Pedro")
        self.assertEqual(cfg["api_name"], "2 Pedro")
        self.assertEqual(cfg["total_chapters"], 3)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("2 pedro", cfg["aliases"])
        self.assertIn("2peter", cfg["aliases"])
        self.assertIn("2pe", cfg["aliases"])
        self.assertIn("2 pe", cfg["aliases"])

    def test_2peter_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        self.assertEqual(len(self.peter2_questions), 18)

        # 6 preguntas en cada uno de los 3 capítulos
        ch_counts = collections.Counter(q["chapter"] for q in self.peter2_questions.values())
        self.assertEqual(len(ch_counts), 3)
        for ch in range(1, 4):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-2PE-0001 a NQB-NT-2PE-0018
        ids = sorted(self.peter2_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-2PE-0001")
        self.assertEqual(ids[-1], "NQB-NT-2PE-0018")
        self.assertEqual(len(set(ids)), 18)

        # Dificultad: Básico=5, Intermedio=6, Avanzado=5, Experto=2
        diff_counts = collections.Counter(q["difficulty"] for q in self.peter2_questions.values())
        self.assertEqual(diff_counts["Básico"], 5)
        self.assertEqual(diff_counts["Intermedio"], 6)
        self.assertEqual(diff_counts["Avanzado"], 5)
        self.assertEqual(diff_counts["Experto"], 2)

        # Tipos: 15 MC, 3 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.peter2_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 15)
        self.assertEqual(type_counts["TRUE_FALSE"], 3)

        tf_ids = sorted(q["id"] for q in self.peter2_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted([f"NQB-NT-2PE-{i:04d}" for i in [6, 12, 18]])
        self.assertEqual(tf_ids, expected_tf)

    def test_2peter_categories(self) -> None:
        """Verifica categorías sin categorías de Evangelios en 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.peter2_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 14)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

    def test_2peter_additional_references(self) -> None:
        """Verifica las 6 preguntas con 7 referencias individuales en 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-2PE-0005": ["Mateo 17:1-8"],
            "NQB-NT-2PE-0006": ["2 Timoteo 3:16"],
            "NQB-NT-2PE-0008": ["Génesis 6:9-22", "Génesis 19:15-29"],
            "NQB-NT-2PE-0009": ["Números 22:21-35"],
            "NQB-NT-2PE-0014": ["Génesis 6:5-9:17"],
            "NQB-NT-2PE-0015": ["Salmos 90:4"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.peter2_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 6)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 7)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_2peter_modes(self) -> None:
        """Verifica la asignación de modos en 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.peter2_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 18)
        self.assertEqual(mode_counts["AMBOS"], 18)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 3)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 3)

    def test_2peter_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        for qid, q in self.peter2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_2peter_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE: 2PE0018 A=Verdadero/correct=A, otros 2 A=Falso/correct=A."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        for qid in ["NQB-NT-2PE-0006", "NQB-NT-2PE-0012"]:
            q = self.get_2peter_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

        # 2PE0018: A=Verdadero, B=Falso, correct_option=A, correct_answer=Verdadero
        q18 = self.get_2peter_question("NQB-NT-2PE-0018")
        self.assertEqual(q18["opcion_a"].strip().lower(), "verdadero", "2PE0018: opcion_a debe ser Verdadero")
        self.assertEqual(q18["opcion_b"].strip().lower(), "falso", "2PE0018: opcion_b debe ser Falso")
        self.assertEqual(q18["correct_option"], "A", "2PE0018: correct_option debe ser A")
        self.assertEqual(q18["correct_answer"].strip().lower(), "verdadero", "2PE0018: correct_answer debe ser Verdadero")

    def test_2peter_characters_and_epistolar_speaker(self) -> None:
        """Verifica entidades y resolve_implicit_speaker para Pedro en 2 Pedro."""
        from auditor import BIBLE_PERSONAJES, resolve_implicit_speaker
        expected_chars = ["pedro", "noe", "lot", "balaam", "pablo", "simon"]
        for p in expected_chars:
            self.assertIn(p, BIBLE_PERSONAJES, f"Falta personaje: {p}")

        verse_map = {
            1: "Simón Pedro, siervo y apóstol de Jesucristo, a los que habéis alcanzado, por la justicia de nuestro Dios y Salvador Jesucristo, una fe igualmente preciosa que la nuestra:",
            2: "Gracia y paz os sean multiplicadas, en el conocimiento de Dios y de nuestro Señor Jesús.",
            3: "Como todas las cosas que pertenecen a la vida y a la piedad nos han sido dadas por su divino poder..."
        }
        passage_norm = "como todas las cosas que pertenecen a la vida y a la piedad nos han sido dadas por su divino poder"
        resolved = resolve_implicit_speaker("pedro", passage_norm, verse_map, 3, ["Pedro"], book_key="2peter")
        self.assertTrue(resolved, "Pedro debe resolverse como autor/remitente epistolar en 2 Pedro")

    def test_2peter_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 2 Pedro."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.peter2_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_2peter_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 2 Pedro y los 21 libros NT anteriores."""
        if not self.peter2_questions:
            self.skipTest("2peter-master-input.json no disponible")
        pe2_texts = {q["question"].strip() for q in self.peter2_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), pe2_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 2 Pedro")

    # --- PRUEBAS ESPECÍFICAS DE 1 JUAN ---

    def get_1john_question(self, qid: str) -> dict:
        self.assertIn(qid, self.john1_questions, f"ID '{qid}' no encontrado en 1john-master-input.json")
        return copy.deepcopy(self.john1_questions[qid])

    def test_detect_book_key_1john(self) -> None:
        """Verifica detección de book_key para 1 Juan y sus variantes."""
        for alias in ["1 Juan", "1juan", "1 John", "1john", "1jn", "1 jn", "Primera de Juan", "Primera carta de Juan", "1ª Juan", "1ra Juan"]:
            spec = {"questions": [{"id": "NQB-NT-1JN-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "1john",
                             f"detect_book_key failed for alias: {alias}")

    def test_1john_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 1 Juan en BOOK_CONFIGS."""
        self.assertIn("1john", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["1john"]
        self.assertEqual(cfg["canonical_name"], "1 Juan")
        self.assertEqual(cfg["api_name"], "1 Juan")
        self.assertEqual(cfg["total_chapters"], 5)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("1 juan", cfg["aliases"])
        self.assertIn("1juan", cfg["aliases"])
        self.assertIn("1jn", cfg["aliases"])
        self.assertIn("1 jn", cfg["aliases"])

    def test_1john_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        self.assertEqual(len(self.john1_questions), 30)

        # 6 preguntas en cada uno de los 5 capítulos
        ch_counts = collections.Counter(q["chapter"] for q in self.john1_questions.values())
        self.assertEqual(len(ch_counts), 5)
        for ch in range(1, 6):
            self.assertEqual(ch_counts[ch], 6, f"Capítulo {ch} tiene {ch_counts[ch]} preguntas, se esperaban 6")

        # IDs: NQB-NT-1JN-0001 a NQB-NT-1JN-0030
        ids = sorted(self.john1_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-1JN-0001")
        self.assertEqual(ids[-1], "NQB-NT-1JN-0030")
        self.assertEqual(len(set(ids)), 30)

        # Dificultad: Básico=6, Intermedio=10, Avanzado=9, Experto=5
        diff_counts = collections.Counter(q["difficulty"] for q in self.john1_questions.values())
        self.assertEqual(diff_counts["Básico"], 6)
        self.assertEqual(diff_counts["Intermedio"], 10)
        self.assertEqual(diff_counts["Avanzado"], 9)
        self.assertEqual(diff_counts["Experto"], 5)

        # Tipos: 25 MC, 5 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.john1_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 25)
        self.assertEqual(type_counts["TRUE_FALSE"], 5)

        tf_ids = sorted(q["id"] for q in self.john1_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = sorted([f"NQB-NT-1JN-{i:04d}" for i in [6, 12, 18, 24, 30]])
        self.assertEqual(tf_ids, expected_tf)

    def test_1john_categories_and_characters(self) -> None:
        """Verifica categorías y personajes específicos de 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.john1_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 26)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)
        for forbidden in ["JESUS_PALABRAS", "JESUS_MILAGROS", "JESUS_PARABOLAS"]:
            self.assertEqual(cat_counts.get(forbidden, 0), 0, f"Categoría no permitida: {forbidden}")

        pb_qs = {q["id"]: q for q in self.john1_questions.values() if q["category"] == "PERSONAJES_BIBLICOS"}
        self.assertEqual(set(pb_qs.keys()), {"NQB-NT-1JN-0004", "NQB-NT-1JN-0007", "NQB-NT-1JN-0015", "NQB-NT-1JN-0027"})
        self.assertEqual(pb_qs["NQB-NT-1JN-0004"]["characters"], ["Jesucristo"])
        self.assertEqual(pb_qs["NQB-NT-1JN-0007"]["characters"], ["Jesucristo"])
        self.assertEqual(pb_qs["NQB-NT-1JN-0015"]["characters"], ["Caín"])
        self.assertEqual(pb_qs["NQB-NT-1JN-0027"]["characters"], ["Jesucristo"])
        # Rango exacto de 1JN0027 debe ser 5:6-12
        self.assertEqual(pb_qs["NQB-NT-1JN-0027"]["verse_start"], 6)
        self.assertEqual(pb_qs["NQB-NT-1JN-0027"]["verse_end"], 12)

    def test_1john_additional_references(self) -> None:
        """Verifica las 13 preguntas con 13 referencias individuales en 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-1JN-0001": ["Juan 1:1-4"],
            "NQB-NT-1JN-0003": ["Salmos 32:5"],
            "NQB-NT-1JN-0004": ["Mateo 26:28"],
            "NQB-NT-1JN-0007": ["Hebreos 4:14-16"],
            "NQB-NT-1JN-0009": ["Juan 13:34-35"],
            "NQB-NT-1JN-0013": ["Juan 1:12"],
            "NQB-NT-1JN-0015": ["Génesis 4:1-8"],
            "NQB-NT-1JN-0016": ["Juan 15:13"],
            "NQB-NT-1JN-0018": ["Santiago 2:15-16"],
            "NQB-NT-1JN-0019": ["1 Tesalonicenses 5:20-21"],
            "NQB-NT-1JN-0021": ["Juan 3:16"],
            "NQB-NT-1JN-0027": ["Juan 3:36"],
            "NQB-NT-1JN-0028": ["Mateo 6:10"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.john1_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 13)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 13)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_1john_modes(self) -> None:
        """Verifica la asignación de modos en 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.john1_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 30)
        self.assertEqual(mode_counts["AMBOS"], 30)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 5)

    def test_1john_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        for qid, q in self.john1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_1john_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE: 1JN0030 A=Verdadero/correct=A, otros 4 A=Falso/correct=A."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        for qid in ["NQB-NT-1JN-0006", "NQB-NT-1JN-0012", "NQB-NT-1JN-0018", "NQB-NT-1JN-0024"]:
            q = self.get_1john_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), "falso", f"{qid}: opcion_a debe ser Falso")
            self.assertEqual(q["opcion_b"].strip().lower(), "verdadero", f"{qid}: opcion_b debe ser Verdadero")
            self.assertEqual(q["correct_option"], "A", f"{qid}: correct_option debe ser A")
            self.assertEqual(q["correct_answer"].strip().lower(), "falso", f"{qid}: correct_answer debe ser Falso")

        # 1JN0030: A=Verdadero, B=Falso, correct_option=A, correct_answer=Verdadero
        q30 = self.get_1john_question("NQB-NT-1JN-0030")
        self.assertEqual(q30["opcion_a"].strip().lower(), "verdadero", "1JN0030: opcion_a debe ser Verdadero")
        self.assertEqual(q30["opcion_b"].strip().lower(), "falso", "1JN0030: opcion_b debe ser Falso")
        self.assertEqual(q30["correct_option"], "A", "1JN0030: correct_option debe ser A")
        self.assertEqual(q30["correct_answer"].strip().lower(), "verdadero", "1JN0030: correct_answer debe ser Verdadero")

    def test_1john_characters_and_no_forced_speaker(self) -> None:
        """Verifica entidades bíblicas de 1 Juan y que no se fuerce speaker=Juan sin evidencia."""
        from auditor import BIBLE_PERSONAJES, resolve_implicit_speaker
        self.assertIn("cain", BIBLE_PERSONAJES)
        self.assertIn("jesucristo", BIBLE_PERSONAJES)

        verse_map = {
            1: "Lo que era desde el principio, lo que hemos oído, lo que hemos visto con nuestros ojos...",
            2: "(porque la vida fue manifestada, y la hemos visto, y testificamos...)",
            3: "lo que hemos visto y oído, eso os anunciamos..."
        }
        passage_norm = "lo que era desde el principio lo que hemos oido lo que hemos visto con nuestros ojos"
        # 1 Juan no nombra al autor Juan en el texto, por lo que no debe resolverse como Juan arbitrariamente
        resolved_juan = resolve_implicit_speaker("juan", passage_norm, verse_map, 1, ["Juan"], book_key="1john")
        self.assertFalse(resolved_juan, "No debe resolverse 'Juan' como hablante implícito en 1 Juan sin mención en el texto")

    def test_1john_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 1 Juan."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.john1_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_1john_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 1 Juan y los 22 libros NT anteriores."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        jn1_texts = {q["question"].strip() for q in self.john1_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
            PHILIPPIANS_PATH.parent / "2peter-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), jn1_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 1 Juan")

    def test_resolve_contextual_person_reference_unit(self) -> None:
        """Pruebas unitarias completas para resolve_contextual_person_reference."""
        from auditor import resolve_contextual_person_reference

        verse_map_1jn2 = {
            1: "Hijitos míos, estas cosas os escribo para que no pequéis; y si alguno hubiere pecado, abogado tenemos para con el Padre, a Jesucristo el justo.",
            2: "Y él es la propiciación por nuestros pecados; y no solamente por los nuestros, sino también por los de todo el mundo.",
            3: "Y en esto sabemos que nosotros le conocemos, si guardamos sus mandamientos.",
            4: "El que dice: Yo le conozco, y no guarda sus mandamientos, el tal es mentiroso, y la verdad no está en él;",
            5: "pero el que guarda su palabra, en éste verdaderamente el amor de Dios se ha perfeccionado; por esto sabemos que estamos en él.",
            6: "El que dice que permanece en él, debe andar como él anduvo."
        }
        raw_pass_3_6 = " ".join(verse_map_1jn2[v] for v in range(3, 7))

        # Caso positivo 1: 1 Juan 2:1-6, antecedente Jesucristo en v1, entidad cristo en v3-6
        self.assertTrue(resolve_contextual_person_reference("cristo", raw_pass_3_6, verse_map_1jn2, 3, 6))

        # Caso positivo de alias: antecedente Jesucristo, entidad Jesucristo / Cristo
        self.assertTrue(resolve_contextual_person_reference("jesucristo", raw_pass_3_6, verse_map_1jn2, 3, 6))

        # Caso negativo 1: Rango actual contiene 'él' pero no hay antecedente en versículos anteriores
        isolated_map = {3: verse_map_1jn2[3], 4: verse_map_1jn2[4], 5: verse_map_1jn2[5], 6: verse_map_1jn2[6]}
        self.assertFalse(resolve_contextual_person_reference("cristo", raw_pass_3_6, isolated_map, 3, 6))

        # Caso negativo 2: Competidor intermedio (Pedro en v2, Jesucristo en v1)
        competitor_map = {
            1: "a Jesucristo el justo.",
            2: "Y Pedro dijo a todos los oyentes...",
            3: "permanece en él y debe andar como él anduvo."
        }
        self.assertFalse(resolve_contextual_person_reference("cristo", competitor_map[3], competitor_map, 3, 3))

        # Caso negativo 3: Dos personajes distintos en el antecedente (ambigüedad)
        ambiguous_map = {
            1: "Jesucristo y Pedro estaban en el monte.",
            2: "él dijo a los discípulos..."
        }
        self.assertFalse(resolve_contextual_person_reference("cristo", ambiguous_map[2], ambiguous_map, 2, 2))

        # Caso negativo 4: start_verse <= 1 (no hay versículos anteriores en el capítulo)
        self.assertFalse(resolve_contextual_person_reference("cristo", verse_map_1jn2[1], verse_map_1jn2, 1, 1))

        # Caso negativo 5: Antecedente no respalda al personaje solicitado
        no_match_map = {
            1: "Y Abraham se levantó de mañana...",
            2: "él dijo a sus siervos..."
        }
        self.assertFalse(resolve_contextual_person_reference("moises", no_match_map[2], no_match_map, 2, 2))

    def test_1john_0008_canonical_regression(self) -> None:
        """Regresión canónica: NQB-NT-1JN-0008 resuelve 'Cristo' por correferencia anafórica."""
        if not self.john1_questions:
            self.skipTest("1john-master-input.json no disponible")
        from auditor import evaluate_question

        verse_map_1jn2 = {
            1: "Hijitos míos, estas cosas os escribo para que no pequéis; y si alguno hubiere pecado, abogado tenemos para con el Padre, a Jesucristo el justo.",
            2: "Y él es la propiciación por nuestros pecados; y no solamente por los nuestros, sino también por los de todo el mundo.",
            3: "Y en esto sabemos que nosotros le conocemos, si guardamos sus mandamientos.",
            4: "El que dice: Yo le conozco, y no guarda sus mandamientos, el tal es mentiroso, y la verdad no está en él;",
            5: "pero el que guarda su palabra, en éste verdaderamente el amor de Dios se ha perfeccionado; por esto sabemos que estamos en él.",
            6: "El que dice que permanece en él, debe andar como él anduvo."
        }
        q8 = self.get_1john_question("NQB-NT-1JN-0008")
        res = evaluate_question(q8, verse_map_1jn2, book_key="1john")

        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res["controles_superados"]["control_rango_suficiente"], "FAIL")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_non_degradation_missing_entity_with_pronoun(self) -> None:
        """Prueba de no degradación: personaje no respaldado en antecedente sigue fallando control_nombres_propios."""
        from auditor import evaluate_question

        verse_map = {
            1: "Y aconteció que cuando Moisés descendía del monte...",
            2: "él habló a toda la congregación..."
        }
        fictitious_q = {
            "id": "TEST-NO-DEG-001",
            "book": "Éxodo",
            "chapter": 34,
            "verse_start": 2,
            "verse_end": 2,
            "reference": "Éxodo 34:2",
            "category": "OT_GENERAL",
            "difficulty": "Básico",
            "question_type": "MULTIPLE_CHOICE",
            "question": "¿Qué hizo el líder al descender?",
            "opcion_a": "David dio órdenes a los sacerdotes",
            "opcion_b": "Construyó un altar de piedra",
            "opcion_c": "Envió mensajeros a Moab",
            "opcion_d": "Permaneció en silencio",
            "correct_option": "A",
            "correct_answer": "David dio órdenes a los sacerdotes",
            "explanation": "El pasaje describe los hechos.",
            "additional_references": [],
            "eligible_modes": ["AT", "AMBOS"]
        }
        res = evaluate_question(fictitious_q, verse_map, book_key="exodus")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS ESPECÍFICAS DE 2 JUAN ---

    def get_2john_question(self, qid: str) -> dict:
        self.assertIn(qid, self.john2_questions, f"ID '{qid}' no encontrado en 2john-master-input.json")
        return copy.deepcopy(self.john2_questions[qid])

    def test_detect_book_key_2john(self) -> None:
        """Verifica detección de book_key para 2 Juan y sus variantes."""
        for alias in ["2 Juan", "2juan", "2 John", "2john", "2jn", "2 jn", "Segunda de Juan", "Segunda carta de Juan", "2ª Juan", "2da Juan"]:
            spec = {"questions": [{"id": "NQB-NT-2JN-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "2john",
                             f"detect_book_key failed for alias: {alias}")

    def test_2john_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 2 Juan en BOOK_CONFIGS."""
        self.assertIn("2john", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["2john"]
        self.assertEqual(cfg["canonical_name"], "2 Juan")
        self.assertEqual(cfg["api_name"], "2 Juan")
        self.assertEqual(cfg["total_chapters"], 1)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("2 juan", cfg["aliases"])
        self.assertIn("2juan", cfg["aliases"])
        self.assertIn("2jn", cfg["aliases"])
        self.assertIn("2 jn", cfg["aliases"])

    def test_2john_author_not_forced(self) -> None:
        """Verifica que no se fuerce speaker=Juan en 2 Juan cuando el texto solo dice 'El anciano'."""
        from auditor import resolve_implicit_speaker
        verse_map = {
            1: "El anciano a la señora elegida y a sus hijos, a quienes yo amo en la verdad..."
        }
        passage_norm = "el anciano a la senora elegida y a sus hijos a quienes yo amo en la verdad"
        resolved_juan = resolve_implicit_speaker("juan", passage_norm, verse_map, 1, ["Juan"], book_key="2john")
        self.assertFalse(resolved_juan, "No debe resolverse 'Juan' como hablante implícito en 2 Juan sin mención en el texto")

    def test_2john_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        self.assertEqual(len(self.john2_questions), 6)

        # 6 preguntas en el capítulo 1
        ch_counts = collections.Counter(q["chapter"] for q in self.john2_questions.values())
        self.assertEqual(len(ch_counts), 1)
        self.assertEqual(ch_counts[1], 6)

        # IDs: NQB-NT-2JN-0001 a NQB-NT-2JN-0006
        ids = sorted(self.john2_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-2JN-0001")
        self.assertEqual(ids[-1], "NQB-NT-2JN-0006")
        self.assertEqual(len(set(ids)), 6)

        # Dificultad: Básico=2, Intermedio=2, Avanzado=1, Experto=1
        diff_counts = collections.Counter(q["difficulty"] for q in self.john2_questions.values())
        self.assertEqual(diff_counts["Básico"], 2)
        self.assertEqual(diff_counts["Intermedio"], 2)
        self.assertEqual(diff_counts["Avanzado"], 1)
        self.assertEqual(diff_counts["Experto"], 1)

        # Tipos: 5 MC, 1 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.john2_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 5)
        self.assertEqual(type_counts["TRUE_FALSE"], 1)

        tf_ids = sorted(q["id"] for q in self.john2_questions.values() if q.get("question_type") == "TRUE_FALSE")
        self.assertEqual(tf_ids, ["NQB-NT-2JN-0006"])

    def test_2john_categories_and_characters(self) -> None:
        """Verifica categorías y personajes de 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.john2_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 5)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 1)

        pb_qs = {q["id"]: q for q in self.john2_questions.values() if q["category"] == "PERSONAJES_BIBLICOS"}
        self.assertEqual(set(pb_qs.keys()), {"NQB-NT-2JN-0003"})
        self.assertEqual(pb_qs["NQB-NT-2JN-0003"]["characters"], ["Jesucristo"])

    def test_2john_additional_references(self) -> None:
        """Verifica las 3 preguntas con 3 referencias en 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-2JN-0002": ["1 Juan 5:3"],
            "NQB-NT-2JN-0003": ["1 Juan 4:2-3"],
            "NQB-NT-2JN-0004": ["1 Juan 2:24-27"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.john2_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 3)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 3)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_2john_modes(self) -> None:
        """Verifica la asignación de modos en 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.john2_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 6)
        self.assertEqual(mode_counts["AMBOS"], 6)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 1)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 1)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 1)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 1)

    def test_2john_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        for qid, q in self.john2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_2john_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE en 2 Juan: 2JN0006 A=Verdadero/correct=A."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        q6 = self.get_2john_question("NQB-NT-2JN-0006")
        self.assertEqual(q6["opcion_a"].strip().lower(), "verdadero", "2JN0006: opcion_a debe ser Verdadero")
        self.assertEqual(q6["opcion_b"].strip().lower(), "falso", "2JN0006: opcion_b debe ser Falso")
        self.assertEqual(q6["correct_option"], "A", "2JN0006: correct_option debe ser A")
        self.assertEqual(q6["correct_answer"].strip().lower(), "verdadero", "2JN0006: correct_answer debe ser Verdadero")

    def test_2john_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 2 Juan."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.john2_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_2john_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 2 Juan y los 23 libros NT anteriores."""
        if not self.john2_questions:
            self.skipTest("2john-master-input.json no disponible")
        jn2_texts = {q["question"].strip() for q in self.john2_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
            PHILIPPIANS_PATH.parent / "2peter-master-input.json",
            PHILIPPIANS_PATH.parent / "1john-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), jn2_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 2 Juan")

    # --- PRUEBAS ESPECÍFICAS DE 3 JUAN ---

    def get_3john_question(self, qid: str) -> dict:
        self.assertIn(qid, self.john3_questions, f"ID '{qid}' no encontrado en 3john-master-input.json")
        return copy.deepcopy(self.john3_questions[qid])

    def test_detect_book_key_3john(self) -> None:
        """Verifica detección de book_key para 3 Juan y sus variantes."""
        for alias in ["3 Juan", "3juan", "3 John", "3john", "3jn", "3 jn", "Tercera de Juan", "Tercera carta de Juan", "3ª Juan", "3ra Juan"]:
            spec = {"questions": [{"id": "NQB-NT-3JN-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "3john",
                             f"detect_book_key failed for alias: {alias}")

    def test_3john_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de 3 Juan en BOOK_CONFIGS."""
        self.assertIn("3john", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["3john"]
        self.assertEqual(cfg["canonical_name"], "3 Juan")
        self.assertEqual(cfg["api_name"], "3 Juan")
        self.assertEqual(cfg["total_chapters"], 1)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("3 juan", cfg["aliases"])
        self.assertIn("3juan", cfg["aliases"])
        self.assertIn("3jn", cfg["aliases"])
        self.assertIn("3 jn", cfg["aliases"])

    def test_3john_author_not_forced(self) -> None:
        """Verifica que no se fuerce speaker=Juan en 3 Juan cuando el texto solo dice 'El anciano'."""
        from auditor import resolve_implicit_speaker
        verse_map = {
            1: "El anciano a Gayo, el amado, a quien amo en la verdad."
        }
        passage_norm = "el anciano a gayo el amado a quien amo en la verdad"
        resolved_juan = resolve_implicit_speaker("juan", passage_norm, verse_map, 1, ["Juan"], book_key="3john")
        self.assertFalse(resolved_juan, "No debe resolverse 'Juan' como hablante implícito en 3 Juan sin mención en el texto")

    def test_3john_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de 3 Juan."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        self.assertEqual(len(self.john3_questions), 6)

        # 6 preguntas en el capítulo 1
        ch_counts = collections.Counter(q["chapter"] for q in self.john3_questions.values())
        self.assertEqual(len(ch_counts), 1)
        self.assertEqual(ch_counts[1], 6)

        # IDs: NQB-NT-3JN-0001 a NQB-NT-3JN-0006
        ids = sorted(self.john3_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-3JN-0001")
        self.assertEqual(ids[-1], "NQB-NT-3JN-0006")
        self.assertEqual(len(set(ids)), 6)

        # Dificultad: Básico=2, Intermedio=2, Avanzado=1, Experto=1
        diff_counts = collections.Counter(q["difficulty"] for q in self.john3_questions.values())
        self.assertEqual(diff_counts["Básico"], 2)
        self.assertEqual(diff_counts["Intermedio"], 2)
        self.assertEqual(diff_counts["Avanzado"], 1)
        self.assertEqual(diff_counts["Experto"], 1)

        # Tipos: 5 MC, 1 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.john3_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 5)
        self.assertEqual(type_counts["TRUE_FALSE"], 1)

        tf_ids = sorted(q["id"] for q in self.john3_questions.values() if q.get("question_type") == "TRUE_FALSE")
        self.assertEqual(tf_ids, ["NQB-NT-3JN-0006"])

    def test_3john_categories_and_characters(self) -> None:
        """Verifica categorías y personajes de 3 Juan (Gayo, Diótrefes, Demetrio)."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.john3_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 3)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 3)

        pb_qs = {q["id"]: q for q in self.john3_questions.values() if q["category"] == "PERSONAJES_BIBLICOS"}
        self.assertEqual(set(pb_qs.keys()), {"NQB-NT-3JN-0001", "NQB-NT-3JN-0004", "NQB-NT-3JN-0005"})
        self.assertEqual(pb_qs["NQB-NT-3JN-0001"]["characters"], ["Gayo"])
        self.assertEqual(pb_qs["NQB-NT-3JN-0004"]["characters"], ["Diótrefes"])
        self.assertEqual(pb_qs["NQB-NT-3JN-0005"]["characters"], ["Demetrio"])

    def test_3john_additional_references(self) -> None:
        """Verifica las 4 preguntas con 4 referencias en 3 Juan."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-3JN-0002": ["2 Juan 1:4"],
            "NQB-NT-3JN-0003": ["Hebreos 13:2"],
            "NQB-NT-3JN-0004": ["1 Pedro 5:3"],
            "NQB-NT-3JN-0006": ["2 Juan 1:12"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.john3_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 4)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 4)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_3john_modes(self) -> None:
        """Verifica la asignación de modos en 3 Juan."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.john3_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 6)
        self.assertEqual(mode_counts["AMBOS"], 6)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 3)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 3)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 1)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 1)

    def test_3john_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en 3 Juan."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        for qid, q in self.john3_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_3john_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE en 3 Juan: 3JN0006 A=Verdadero/correct=A."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        q6 = self.get_3john_question("NQB-NT-3JN-0006")
        self.assertEqual(q6["opcion_a"].strip().lower(), "verdadero", "3JN0006: opcion_a debe ser Verdadero")
        self.assertEqual(q6["opcion_b"].strip().lower(), "falso", "3JN0006: opcion_b debe ser Falso")
        self.assertEqual(q6["correct_option"], "A", "3JN0006: correct_option debe ser A")
        self.assertEqual(q6["correct_answer"].strip().lower(), "verdadero", "3JN0006: correct_answer debe ser Verdadero")

    def test_3john_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en 3 Juan."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.john3_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_3john_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre 3 Juan y los 24 libros NT anteriores."""
        if not self.john3_questions:
            self.skipTest("3john-master-input.json no disponible")
        jn3_texts = {q["question"].strip() for q in self.john3_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
            PHILIPPIANS_PATH.parent / "2peter-master-input.json",
            PHILIPPIANS_PATH.parent / "1john-master-input.json",
            PHILIPPIANS_PATH.parent / "2john-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), jn3_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y 3 Juan")

    # --- PRUEBAS ESPECÍFICAS DE JUDAS ---

    def get_jude_question(self, qid: str) -> dict:
        self.assertIn(qid, self.jude_questions, f"ID '{qid}' no encontrado en jude-master-input.json")
        return copy.deepcopy(self.jude_questions[qid])

    def test_detect_book_key_jude(self) -> None:
        """Verifica detección de book_key para Judas y sus variantes."""
        for alias in ["Judas", "judas", "Jude", "jude", "Jud", "jud", "Epístola de Judas", "Carta de Judas"]:
            spec = {"questions": [{"id": "NQB-NT-JUD-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "jude",
                             f"detect_book_key failed for alias: {alias}")

    def test_jude_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Judas en BOOK_CONFIGS."""
        self.assertIn("jude", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["jude"]
        self.assertEqual(cfg["canonical_name"], "Judas")
        self.assertEqual(cfg["api_name"], "Judas")
        self.assertEqual(cfg["total_chapters"], 1)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("judas", cfg["aliases"])
        self.assertIn("jude", cfg["aliases"])
        self.assertIn("jud", cfg["aliases"])

    def test_jude_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Judas."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        self.assertEqual(len(self.jude_questions), 12)

        # 12 preguntas en el capítulo 1
        ch_counts = collections.Counter(q["chapter"] for q in self.jude_questions.values())
        self.assertEqual(len(ch_counts), 1)
        self.assertEqual(ch_counts[1], 12)

        # IDs: NQB-NT-JUD-0001 a NQB-NT-JUD-0012
        ids = sorted(self.jude_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-JUD-0001")
        self.assertEqual(ids[-1], "NQB-NT-JUD-0012")
        self.assertEqual(len(set(ids)), 12)

        # Dificultad: Básico=2, Intermedio=3, Avanzado=4, Experto=3
        diff_counts = collections.Counter(q["difficulty"] for q in self.jude_questions.values())
        self.assertEqual(diff_counts["Básico"], 2)
        self.assertEqual(diff_counts["Intermedio"], 3)
        self.assertEqual(diff_counts["Avanzado"], 4)
        self.assertEqual(diff_counts["Experto"], 3)

        # Tipos: 10 MC, 2 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.jude_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 10)
        self.assertEqual(type_counts["TRUE_FALSE"], 2)

        tf_ids = sorted(q["id"] for q in self.jude_questions.values() if q.get("question_type") == "TRUE_FALSE")
        self.assertEqual(tf_ids, ["NQB-NT-JUD-0010", "NQB-NT-JUD-0012"])

    def test_jude_categories_and_characters(self) -> None:
        """Verifica categorías y personajes de Judas (Judas, Miguel, Caín/Balaam/Coré, Enoc)."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.jude_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 8)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 4)

        pb_qs = {q["id"]: q for q in self.jude_questions.values() if q["category"] == "PERSONAJES_BIBLICOS"}
        self.assertEqual(set(pb_qs.keys()), {"NQB-NT-JUD-0001", "NQB-NT-JUD-0006", "NQB-NT-JUD-0007", "NQB-NT-JUD-0009"})
        self.assertEqual(pb_qs["NQB-NT-JUD-0001"]["characters"], ["Judas"])
        self.assertEqual(pb_qs["NQB-NT-JUD-0006"]["characters"], ["Miguel"])
        self.assertEqual(set(pb_qs["NQB-NT-JUD-0007"]["characters"]), {"Caín", "Balaam", "Coré"})
        self.assertEqual(pb_qs["NQB-NT-JUD-0009"]["characters"], ["Enoc"])

    def test_jude_additional_references(self) -> None:
        """Verifica las 11 preguntas con 16 referencias en Judas."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-JUD-0001": ["Santiago 1:1"],
            "NQB-NT-JUD-0002": ["2 Pedro 2:1"],
            "NQB-NT-JUD-0003": ["Números 14:22-23", "Hebreos 3:16-19"],
            "NQB-NT-JUD-0004": ["2 Pedro 2:4"],
            "NQB-NT-JUD-0005": ["Génesis 19:4-25", "2 Pedro 2:6"],
            "NQB-NT-JUD-0006": ["Zacarías 3:2"],
            "NQB-NT-JUD-0007": ["Génesis 4:3-8", "Números 22:7", "Números 16:1-35"],
            "NQB-NT-JUD-0008": ["2 Pedro 2:17"],
            "NQB-NT-JUD-0009": ["Génesis 5:21-24"],
            "NQB-NT-JUD-0010": ["2 Pedro 3:2-3"],
            "NQB-NT-JUD-0012": ["Romanos 16:25", "Efesios 3:20-21"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.jude_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 11)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 16)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_jude_modes(self) -> None:
        """Verifica la asignación de modos en Judas."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.jude_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 12)
        self.assertEqual(mode_counts["AMBOS"], 12)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 4)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 4)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 2)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 2)

    def test_jude_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Judas."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        for qid, q in self.jude_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_jude_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE en Judas: JUD0010 (A=Falso/correct=A) y JUD0012 (A=Verdadero/correct=A)."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        q10 = self.get_jude_question("NQB-NT-JUD-0010")
        self.assertEqual(q10["opcion_a"].strip().lower(), "falso", "JUD0010: opcion_a debe ser Falso")
        self.assertEqual(q10["opcion_b"].strip().lower(), "verdadero", "JUD0010: opcion_b debe ser Verdadero")
        self.assertEqual(q10["correct_option"], "A", "JUD0010: correct_option debe ser A")
        self.assertEqual(q10["correct_answer"].strip().lower(), "falso", "JUD0010: correct_answer debe ser Falso")

        q12 = self.get_jude_question("NQB-NT-JUD-0012")
        self.assertEqual(q12["opcion_a"].strip().lower(), "verdadero", "JUD0012: opcion_a debe ser Verdadero")
        self.assertEqual(q12["opcion_b"].strip().lower(), "falso", "JUD0012: opcion_b debe ser Falso")
        self.assertEqual(q12["correct_option"], "A", "JUD0012: correct_option debe ser A")
        self.assertEqual(q12["correct_answer"].strip().lower(), "verdadero", "JUD0012: correct_answer debe ser Verdadero")

    def test_jude_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Judas."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.jude_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_jude_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Judas y los 25 libros NT anteriores."""
        if not self.jude_questions:
            self.skipTest("jude-master-input.json no disponible")
        jud_texts = {q["question"].strip() for q in self.jude_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
            PHILIPPIANS_PATH.parent / "2peter-master-input.json",
            PHILIPPIANS_PATH.parent / "1john-master-input.json",
            PHILIPPIANS_PATH.parent / "2john-master-input.json",
            PHILIPPIANS_PATH.parent / "3john-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), jud_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Judas")

    # --- PRUEBAS ESPECÍFICAS DE APOCALIPSIS ---

    def get_revelation_question(self, qid: str) -> dict:
        self.assertIn(qid, self.revelation_questions, f"ID '{qid}' no encontrado en revelation-master-input.json")
        return copy.deepcopy(self.revelation_questions[qid])

    def test_detect_book_key_revelation(self) -> None:
        """Verifica detección de book_key para Apocalipsis y sus variantes."""
        for alias in ["Apocalipsis", "apocalipsis", "Revelation", "revelation", "Rev", "rev", "Apoc", "apoc", "Apo", "apo", "Apocalipsis de Juan", "Revelacion", "Revelación"]:
            spec = {"questions": [{"id": "NQB-NT-APO-0001", "book": alias}]}
            self.assertEqual(detect_book_key(spec), "revelation",
                             f"detect_book_key failed for alias: {alias}")

    def test_revelation_book_config_and_aliases(self) -> None:
        """Verifica la configuración canónica de Apocalipsis en BOOK_CONFIGS."""
        self.assertIn("revelation", BOOK_CONFIGS)
        cfg = BOOK_CONFIGS["revelation"]
        self.assertEqual(cfg["canonical_name"], "Apocalipsis")
        self.assertEqual(cfg["api_name"], "Apocalipsis")
        self.assertEqual(cfg["total_chapters"], 22)
        self.assertEqual(len(cfg["blocks"]), 1)
        self.assertIn("apocalipsis", cfg["aliases"])
        self.assertIn("revelation", cfg["aliases"])
        self.assertIn("rev", cfg["aliases"])
        self.assertIn("apoc", cfg["aliases"])
        self.assertIn("apo", cfg["aliases"])

    def test_revelation_canonical_baseline_structure(self) -> None:
        """Verifica conteos, tipos, dificultad y distribución por capítulo de Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        self.assertEqual(len(self.revelation_questions), 66)

        # 22 capítulos, exactamente 3 preguntas cada uno
        ch_counts = collections.Counter(q["chapter"] for q in self.revelation_questions.values())
        self.assertEqual(len(ch_counts), 22)
        for ch in range(1, 23):
            self.assertEqual(ch_counts[ch], 3, f"Capítulo {ch} debe tener 3 preguntas, tiene {ch_counts[ch]}")

        # IDs: NQB-NT-APO-0001 a NQB-NT-APO-0066
        ids = sorted(self.revelation_questions.keys())
        self.assertEqual(ids[0], "NQB-NT-APO-0001")
        self.assertEqual(ids[-1], "NQB-NT-APO-0066")
        self.assertEqual(len(set(ids)), 66)

        # Dificultad: Básico=14, Intermedio=25, Avanzado=20, Experto=7
        diff_counts = collections.Counter(q["difficulty"] for q in self.revelation_questions.values())
        self.assertEqual(diff_counts["Básico"], 14)
        self.assertEqual(diff_counts["Intermedio"], 25)
        self.assertEqual(diff_counts["Avanzado"], 20)
        self.assertEqual(diff_counts["Experto"], 7)

        # Tipos: 58 MC, 8 TF
        type_counts = collections.Counter(q.get("question_type", "MULTIPLE_CHOICE") for q in self.revelation_questions.values())
        self.assertEqual(type_counts["MULTIPLE_CHOICE"], 58)
        self.assertEqual(type_counts["TRUE_FALSE"], 8)

        tf_ids = sorted(q["id"] for q in self.revelation_questions.values() if q.get("question_type") == "TRUE_FALSE")
        expected_tf = [
            "NQB-NT-APO-0003", "NQB-NT-APO-0011", "NQB-NT-APO-0015", "NQB-NT-APO-0024",
            "NQB-NT-APO-0027", "NQB-NT-APO-0045", "NQB-NT-APO-0054", "NQB-NT-APO-0063"
        ]
        self.assertEqual(tf_ids, expected_tf)

    def test_revelation_categories_and_characters(self) -> None:
        """Verifica categorías y personajes de Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        cat_counts = collections.Counter(q["category"] for q in self.revelation_questions.values())
        self.assertEqual(cat_counts["NT_GENERAL"], 53)
        self.assertEqual(cat_counts["JESUS_PALABRAS"], 8)
        self.assertEqual(cat_counts["PERSONAJES_BIBLICOS"], 5)

        jp_ids = sorted(q["id"] for q in self.revelation_questions.values() if q["category"] == "JESUS_PALABRAS")
        self.assertEqual(jp_ids, [
            "NQB-NT-APO-0003", "NQB-NT-APO-0004", "NQB-NT-APO-0005", "NQB-NT-APO-0006",
            "NQB-NT-APO-0007", "NQB-NT-APO-0008", "NQB-NT-APO-0009", "NQB-NT-APO-0066"
        ])

        pb_qs = {q["id"]: q for q in self.revelation_questions.values() if q["category"] == "PERSONAJES_BIBLICOS"}
        self.assertEqual(set(pb_qs.keys()), {
            "NQB-NT-APO-0001", "NQB-NT-APO-0002", "NQB-NT-APO-0030", "NQB-NT-APO-0035", "NQB-NT-APO-0056"
        })
        self.assertEqual(pb_qs["NQB-NT-APO-0001"]["characters"], ["Juan"])
        self.assertEqual(pb_qs["NQB-NT-APO-0002"]["characters"], ["Jesucristo", "Juan"])
        self.assertEqual(pb_qs["NQB-NT-APO-0030"]["characters"], ["Juan"])
        self.assertEqual(set(pb_qs["NQB-NT-APO-0035"]["characters"]), {"Miguel", "dragón"})
        self.assertEqual(pb_qs["NQB-NT-APO-0056"]["characters"], ["Jesucristo"])

    def test_revelation_additional_references(self) -> None:
        """Verifica las 8 preguntas con 12 referencias en Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        expected_add_refs = {
            "NQB-NT-APO-0001": ["Apocalipsis 1:9"],
            "NQB-NT-APO-0006": ["Números 25:1-3", "Números 31:16"],
            "NQB-NT-APO-0012": ["Génesis 1:1"],
            "NQB-NT-APO-0013": ["Génesis 49:9-10", "Isaías 11:1"],
            "NQB-NT-APO-0030": ["Ezequiel 3:1-3"],
            "NQB-NT-APO-0035": ["Daniel 10:13", "Judas 1:9"],
            "NQB-NT-APO-0043": ["Éxodo 15:1"],
            "NQB-NT-APO-0064": ["Génesis 2:9", "Ezequiel 47:12"],
        }
        found_add_refs = {
            qid: q["additional_references"]
            for qid, q in self.revelation_questions.items()
            if q.get("additional_references")
        }
        self.assertEqual(len(found_add_refs), 8)
        self.assertEqual(sum(len(r) for r in found_add_refs.values()), 12)
        for qid, exp_refs in expected_add_refs.items():
            self.assertEqual(found_add_refs.get(qid), exp_refs)

    def test_revelation_modes(self) -> None:
        """Verifica la asignación de modos en Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        mode_counts = collections.defaultdict(int)
        for q in self.revelation_questions.values():
            for m in q.get("eligible_modes", []):
                mode_counts[m] += 1
        self.assertEqual(mode_counts["NT"], 66)
        self.assertEqual(mode_counts["AMBOS"], 66)
        self.assertEqual(mode_counts["JESUS_PALABRAS"], 8)
        self.assertEqual(mode_counts["PERSONAJES_NT"], 5)
        self.assertEqual(mode_counts["PERSONAJES_AMBOS"], 5)
        self.assertEqual(mode_counts["VERDADERO_FALSO_NT"], 8)
        self.assertEqual(mode_counts["VERDADERO_FALSO_AMBOS"], 8)

    def test_revelation_id_reference_integrity(self) -> None:
        """Verifica consistencia de IDs y referencias en Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        for qid, q in self.revelation_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_revelation_true_false_neutral_semantics(self) -> None:
        """Verifica semántica neutral de TRUE_FALSE en Apocalipsis en las 8 preguntas."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        expected_semantics = {
            "NQB-NT-APO-0003": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0011": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0015": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0024": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0027": ("falso", "verdadero", "A", "falso"),
            "NQB-NT-APO-0045": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0054": ("verdadero", "falso", "A", "verdadero"),
            "NQB-NT-APO-0063": ("falso", "verdadero", "A", "falso"),
        }
        for qid, (exp_a, exp_b, exp_opt, exp_ans) in expected_semantics.items():
            q = self.get_revelation_question(qid)
            self.assertEqual(q["opcion_a"].strip().lower(), exp_a, f"{qid} opcion_a")
            self.assertEqual(q["opcion_b"].strip().lower(), exp_b, f"{qid} opcion_b")
            self.assertEqual(q["correct_option"], exp_opt, f"{qid} correct_option")
            self.assertEqual(q["correct_answer"].strip().lower(), exp_ans, f"{qid} correct_answer")

    def test_revelation_no_duplicates_within(self) -> None:
        """Verifica que no haya preguntas duplicadas internamente en Apocalipsis."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        questions_texts = [q["question"].strip() for q in self.revelation_questions.values()]
        self.assertEqual(len(questions_texts), len(set(questions_texts)), "Duplicados detectados internamente")

    def test_revelation_no_duplicates_cross_nt(self) -> None:
        """Verifica que no haya preguntas duplicadas entre Apocalipsis y los 26 libros NT anteriores."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        apo_texts = {q["question"].strip() for q in self.revelation_questions.values()}
        prior_nt = [
            PHILIPPIANS_PATH.parent / "matthew-master-input.json",
            PHILIPPIANS_PATH.parent / "mark-master-input.json",
            PHILIPPIANS_PATH.parent / "luke-master-input.json",
            PHILIPPIANS_PATH.parent / "john-master-input.json",
            PHILIPPIANS_PATH.parent / "acts-master-input.json",
            PHILIPPIANS_PATH.parent / "romans-master-input.json",
            PHILIPPIANS_PATH.parent / "1corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "2corinthians-master-input.json",
            PHILIPPIANS_PATH.parent / "galatians-master-input.json",
            PHILIPPIANS_PATH.parent / "ephesians-master-input.json",
            PHILIPPIANS_PATH.parent / "philippians-master-input.json",
            PHILIPPIANS_PATH.parent / "colossians-master-input.json",
            PHILIPPIANS_PATH.parent / "1thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "2thessalonians-master-input.json",
            PHILIPPIANS_PATH.parent / "1timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "2timothy-master-input.json",
            PHILIPPIANS_PATH.parent / "titus-master-input.json",
            PHILIPPIANS_PATH.parent / "philemon-master-input.json",
            PHILIPPIANS_PATH.parent / "hebrews-master-input.json",
            PHILIPPIANS_PATH.parent / "james-master-input.json",
            PHILIPPIANS_PATH.parent / "1peter-master-input.json",
            PHILIPPIANS_PATH.parent / "2peter-master-input.json",
            PHILIPPIANS_PATH.parent / "1john-master-input.json",
            PHILIPPIANS_PATH.parent / "2john-master-input.json",
            PHILIPPIANS_PATH.parent / "3john-master-input.json",
            PHILIPPIANS_PATH.parent / "jude-master-input.json",
        ]
        for prior_path in prior_nt:
            if not prior_path.exists():
                continue
            prior_data = json.loads(prior_path.read_text(encoding="utf-8"))
            prior_questions = prior_data.get("questions", []) if isinstance(prior_data, dict) else prior_data
            for pq in prior_questions:
                self.assertNotIn(pq["question"].strip(), apo_texts,
                                 f"Pregunta duplicada entre {prior_path.name} ({pq['id']}) y Apocalipsis")

    def test_revelation_no_modern_mappings(self) -> None:
        """Verifica que ninguna pregunta ni respuesta de Apocalipsis contenga mapeos a tecnologías o entidades modernas."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        prohibited = [
            "microchip", "chip", "vacuna", "código de barras", "codigo de barras",
            "código qr", "codigo qr", "inteligencia artificial", "helicóptero", "helicoptero",
            "drone", "dron", "tanque", "avión", "avion", "internet"
        ]
        for q in self.revelation_questions.values():
            full_content = (
                q["question"] + " " + q.get("opcion_a", "") + " " + q.get("opcion_b", "") + " " +
                q.get("opcion_c", "") + " " + q.get("opcion_d", "") + " " + q.get("explanation", "")
            ).lower()
            for term in prohibited:
                self.assertNotIn(term, full_content, f"Término moderno prohibido '{term}' en {q['id']}")

    def test_revelation_speaker_resolution_christ_discourse(self) -> None:
        """Verifica la resolución contextual del hablante en el discurso de Cristo (NQB-NT-APO-0008)."""
        if not self.revelation_questions:
            self.skipTest("revelation-master-input.json no disponible")
        q8 = self.get_revelation_question("NQB-NT-APO-0008")
        verse_map = {
            7: "Escribe al ángel de la iglesia en Filadelfia: Esto dice el Santo, el Verdadero, el que tiene la llave de David, el que abre y ninguno cierra, y cierra y ninguno abre:",
            8: "Yo conozco tus obras; he aquí, he puesto delante de ti una puerta abierta, la cual nadie puede cerrar; porque aunque tienes poca fuerza, has guardado mi palabra, y no has negado mi nombre.",
            9: "He aquí, yo entrego de la sinagoga de Satanás a los que se dicen ser judíos y no lo son, sino que mienten; he aquí, yo haré que vengan y se postren a tus pies, y reconozcan que yo te he amado.",
            10: "Por cuanto has guardado la palabra de mi paciencia, yo también te guardaré de la hora de la prueba que ha de venir sobre el mundo entero, para probar a los que moran sobre la tierra.",
            11: "He aquí, yo vengo pronto; retén lo que tienes, para que ninguno tome tu corona.",
            12: "Al que venciere, yo lo haré columna en el templo de mi Dios, y nunca más saldrá de allí; y escribiré sobre él el nombre de mi Dios, y el nombre de la ciudad de mi Dios, la nueva Jerusalén, la cual desciende del cielo, de mi Dios, y mi nombre nuevo.",
            13: "El que tiene oído, oiga lo que el Espíritu dice a las iglesias."
        }
        res = evaluate_question(q8, verse_map, "revelation")
        self.assertIn(res["estado"], ["VERIFICADO", "NO_CONCLUYENTE"], f"Estado inesperado para APO0008: {res['estado']}")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION", f"APO0008 no debe ser REQUIERE_CORRECCION. Incidencias: {res.get('incidencias')}")
        self.assertEqual(res["controles_superados"].get("control_nombres_propios"), "PASS")


if __name__ == "__main__":
    unittest.main()
