#!/usr/bin/env python3
"""Auditor semántico y textual derivado de preguntas bíblicas contra RVR1960.

Soporta auditoría modular para:
- Génesis (50 capítulos, 5 bloques)
- Éxodo (40 capítulos, 4 bloques)
- Levítico (27 capítulos, 3 bloques)
- Números (36 capítulos, 4 bloques)
y libros bíblicos adicionales.

Evalúa deterministamente los 17 controles de calidad editorial:
identidad de libro, capítulo, versículos, existencia de pasajes, respaldo
de la pregunta, validez de la opción A, inconsistencia de distractores,
alineación canónica, compatibilidad de explicación, verificación de nombres
propios, lugares, cantidades numéricas, parentescos, suficiencia de rango
y ausencia de ambigüedad.

Incluye cliente HTTP con throttling proactivo (máximo 26 peticiones/minuto,
intervalo >= 2.3s) y manejo inteligente de HTTP 429 con lectura de reset_at.

Estados por control: PASS, FAIL, NOT_APPLICABLE, UNKNOWN.
Clasificación final: VERIFICADO, REQUIERE_CORRECCION, NO_CONCLUYENTE.

El texto bíblico RVR1960 vive únicamente en memoria volátil y se libera
inmediatamente tras evaluar cada capítulo. source_text_persisted: False.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

try:
    from tools.bible_extractor.extractor import PASSAGE_URL, api_get, extract_verses, _verse_number_from_node
except ImportError:
    from extractor import PASSAGE_URL, api_get, extract_verses, _verse_number_from_node

BOOK_CONFIGS: dict[str, dict[str, Any]] = {
    "genesis": {
        "canonical_name": "Génesis",
        "api_name": "Genesis",
        "aliases": {"genesis", "génesis"},
        "total_chapters": 50,
        "blocks": [
            (1, 10, "genesis-01-10.json"),
            (11, 20, "genesis-11-20.json"),
            (21, 30, "genesis-21-30.json"),
            (31, 40, "genesis-31-40.json"),
            (41, 50, "genesis-41-50.json"),
        ],
        "default_output_dir": "build/audit/genesis",
        "ambient_places": {"canaan", "mesopotamia"},
    },
    "exodo": {
        "canonical_name": "Éxodo",
        "api_name": "Exodo",
        "aliases": {"exodo", "éxodo", "exodus"},
        "total_chapters": 40,
        "blocks": [
            (1, 10, "exodus-01-10.json"),
            (11, 20, "exodus-11-20.json"),
            (21, 30, "exodus-21-30.json"),
            (31, 40, "exodus-31-40.json"),
        ],
        "default_output_dir": "build/audit/exodus",
        "ambient_places": {"egipto"},
    },
    "levitico": {
        "canonical_name": "Levítico",
        "api_name": "Levitico",
        "aliases": {"levitico", "levítico", "leviticus"},
        "total_chapters": 27,
        "blocks": [
            (1, 10, "leviticus-01-10.json"),
            (11, 20, "leviticus-11-20.json"),
            (21, 27, "leviticus-21-27.json"),
        ],
        "default_output_dir": "build/audit/leviticus",
        "ambient_places": {"sinai", "monte sinai", "desierto", "tabernaculo", "egipto", "canaan"},
    },
    "numeros": {
        "canonical_name": "Números",
        "api_name": "Numeros",
        "aliases": {"numeros", "números", "numbers"},
        "total_chapters": 36,
        "blocks": [
            (1, 10, "numbers-01-10.json"),
            (11, 20, "numbers-11-20.json"),
            (21, 30, "numbers-21-30.json"),
            (31, 36, "numbers-31-36.json"),
        ],
        "default_output_dir": "build/audit/numbers",
        "ambient_places": {"sinai", "monte sinai", "desierto", "moab", "cades", "paran", "jordan", "canaan", "edom", "madian", "tabernaculo", "hor", "escol", "zin"},
    },
    "deuteronomio": {
        "canonical_name": "Deuteronomio",
        "api_name": "Deuteronomio",
        "aliases": {"deuteronomio", "deuteronomy"},
        "total_chapters": 34,
        "blocks": [
            (1, 10, "deuteronomy-01-10.json"),
            (11, 20, "deuteronomy-11-20.json"),
            (21, 30, "deuteronomy-21-30.json"),
            (31, 34, "deuteronomy-31-34.json"),
        ],
        "default_output_dir": "build/audit/deuteronomy",
        "ambient_places": {
            "moab", "campos de moab", "llanuras de moab", "tierra de moab", "jordan", "canaan",
            "horeb", "sinai", "monte sinai", "seir", "nebo", "monte nebo",
            "pisga", "monte pisga", "desierto", "gerizim", "monte gerizim",
            "ebal", "monte ebal", "tabernaculo", "cades", "cadesbarnea", "cades-barnea",
            "hesbon", "hesbón", "arava", "aravá", "basan", "basán", "galaad"
        },
    },
    "josue": {
        "canonical_name": "Josué",
        "api_name": "Josue",
        "aliases": {"josue", "josué", "joshua"},
        "total_chapters": 24,
        "blocks": [
            (1, 10, "joshua-01-10.json"),
            (11, 20, "joshua-11-20.json"),
            (21, 24, "joshua-21-24.json"),
        ],
        "default_output_dir": "build/audit/joshua",
        "ambient_places": {
            "canaan", "jordan", "jerico", "jericó", "gilgal", "hai", "gabaon", "gabaón",
            "hebron", "hebrón", "silo", "siquem", "monte ebal", "monte gerizim", "ebal",
            "gerizim", "desierto", "maceda", "libna", "laquis", "eglon", "debir", "hazor",
            "merom", "galaad", "basan", "basán", "timnat-sera"
        },
    },
    "jueces": {
        "canonical_name": "Jueces",
        "api_name": "Jueces",
        "aliases": {"jueces", "judges"},
        "total_chapters": 21,
        "blocks": [
            (1, 10, "judges-01-10.json"),
            (11, 20, "judges-11-20.json"),
            (21, 21, "judges-21-21.json"),
        ],
        "default_output_dir": "build/audit/judges",
        "ambient_places": {
            "canaan", "israel", "galaad", "siquem", "silo", "siló", "betel", "bet-el",
            "mizpa", "rama", "jerusalen", "jerusalén", "hebron", "hebrón", "gaza",
            "ascalon", "ascalón", "ecron", "ecrón", "tabor", "monte tabor", "cison", "cisón",
            "arava", "aravá", "jordan", "desierto", "gibea", "gabaa", "timnat", "zora",
            "estaol", "ofra", "en-dor", "endor", "meguido", "megido"
        },
    },
    "rut": {
        "canonical_name": "Rut",
        "api_name": "Rut",
        "aliases": {"rut", "ruth"},
        "total_chapters": 4,
        "blocks": [
            (1, 4, "ruth-01-04.json"),
        ],
        "default_output_dir": "build/audit/ruth",
        "ambient_places": {
            "belen", "moab", "campos de moab", "tierra de moab", "juda", "israel", "efrata"
        },
    },
    "1samuel": {
        "canonical_name": "1 Samuel",
        "api_name": "1 Samuel",
        "aliases": {"1 samuel", "1samuel", "1 sam", "1sa", "primera de samuel", "1-samuel"},
        "total_chapters": 31,
        "blocks": [
            (1, 10, "1samuel-01-10.json"),
            (11, 20, "1samuel-11-20.json"),
            (21, 31, "1samuel-21-31.json"),
        ],
        "default_output_dir": "build/audit/1samuel",
        "ambient_places": {
            "silo", "siló", "rama", "ramá", "mizpa", "gat", "asdod", "ecron", "ecrón",
            "bet-semes", "betsemes", "quiriat-jearim", "belen", "belén", "gilgal",
            "galaad", "jabes", "jabes de galaad", "nob", "adulam", "keila", "siclag",
            "en-dor", "endor", "bet-san", "bet-sán", "israel", "juda", "filistea", "filisteos",
            "gibea", "gabaa", "carmel", "en-gadi", "engadi", "guilboa", "gilboa", "monte gilboa"
        },
    },
    "2samuel": {
        "canonical_name": "2 Samuel",
        "api_name": "2 Samuel",
        "aliases": {"2 samuel", "2samuel", "2 sam", "2sa", "segunda de samuel", "2-samuel"},
        "total_chapters": 24,
        "blocks": [
            (1, 10, "2samuel-01-10.json"),
            (11, 20, "2samuel-11-20.json"),
            (21, 24, "2samuel-21-24.json"),
        ],
        "default_output_dir": "build/audit/2samuel",
        "ambient_places": {
            "siclag", "hebron", "hebrón", "jerusalen", "jerusalén", "sion", "sión", "ciudad de david",
            "gabaon", "gabaón", "belen", "belén", "jordan", "israel", "juda", "filistea", "filisteos",
            "rabá", "raba", "gesur", "tecoa", "mahanaim", "abel-bet-maaca", "aram", "siria",
            "amon", "moab", "edom", "guilboa", "gilboa", "carmel", "en-gadi", "engadi"
        },
    },
    "1kings": {
        "canonical_name": "1 Reyes",
        "api_name": "1 Reyes",
        "aliases": {"1 reyes", "1reyes", "1 kings", "1kings", "1 rey", "primera de reyes", "1-reyes", "1_reyes"},
        "total_chapters": 22,
        "blocks": [
            (1, 10, "1kings-01-10.json"),
            (11, 20, "1kings-11-20.json"),
            (21, 22, "1kings-21-22.json"),
        ],
        "default_output_dir": "build/audit/1kings",
        "ambient_places": {
            "jerusalen", "jerusalén", "sion", "sión", "tiro", "sidon", "sidón", "siquem", "bet-el", "dan",
            "samaria", "jezreel", "galaad", "quiriat-jearim", "gabaon", "gabaón", "carmel", "monte carmel",
            "horeb", "monte horeb", "sinaí", "sinai", "damasco", "siria", "aram", "israel", "juda",
            "cabul", "ezion-geber", "ezión-geber", "eziongeber", "elot", "ofir", "sarepta", "querit",
            "arroyo de querit", "ramot de galaad", "ramot", "tirse", "tirsa", "penuel", "guilboa", "gilboa"
        },
    },
    "2kings": {
        "canonical_name": "2 Reyes",
        "api_name": "2 Reyes",
        "aliases": {"2 reyes", "2reyes", "2 kings", "2kings", "2 rey", "segunda de reyes", "2-reyes", "2_reyes"},
        "total_chapters": 25,
        "blocks": [
            (1, 10, "2kings-01-10.json"),
            (11, 20, "2kings-11-20.json"),
            (21, 25, "2kings-21-25.json"),
        ],
        "default_output_dir": "build/audit/2kings",
        "ambient_places": {
            "samaria", "jerusalen", "jerusalén", "jordan", "jordán", "jerico", "jericó", "bet-el", "gilgal",
            "sunem", "monte carmel", "carmel", "damasco", "siria", "afec", "dotan", "dothan", "ramot de galaad",
            "jezreel", "israel", "juda", "moab", "edom", "tiro", "sidon", "sidón", "ninive", "nínive", "asiria",
            "babilonia", "egipto", "valle de la sal", "sela", "jocteel", "hamat", "arpat", "sefarvaim", "lisis",
            "laquis", "libna", "gaza", "ribla", "quidron", "cedron", "cedrón", "siloe", "siloé"
        },
    },
    "1chronicles": {
        "canonical_name": "1 Crónicas",
        "api_name": "1 Crónicas",
        "aliases": {
            "1 crónicas", "1 cronicas", "1crónicas", "1cronicas",
            "1 chronicles", "1chronicles", "1 cronica", "1 crón", "1 cron",
            "primera de crónicas", "primera de cronicas", "1-cronicas", "1_cronicas"
        },
        "total_chapters": 29,
        "blocks": [
            (1, 10, "1chronicles-01-10.json"),
            (11, 20, "1chronicles-11-20.json"),
            (21, 29, "1chronicles-21-29.json"),
        ],
        "default_output_dir": "build/audit/1chronicles",
        "ambient_places": {
            "jerusalen", "jerusalén", "sion", "sión", "jordan", "jordán", "hebron", "hebrón", "jebus", "jebús",
            "gabaon", "gabaón", "quiriat-jearim", "quiriatjearim", "bet-semes", "betsemes", "bet-el", "dan", "samaria", "jezreel",
            "galaad", "siquem", "belen", "belén", "carmel", "ofir", "hamat", "sihor", "afec", "dotan", "tiro", "sidon", "sidón",
            "damasco", "siria", "aram", "moab", "edom", "amon", "amón", "filistea", "gat", "gezer", "raba", "rabá",
            "guilboa", "gilboa", "moriah", "monte moriah"
        },
    },
    "2chronicles": {
        "canonical_name": "2 Crónicas",
        "api_name": "2 Crónicas",
        "aliases": {
            "2 crónicas", "2 cronicas", "2crónicas", "2cronicas",
            "2 chronicles", "2chronicles", "2 cronica", "2 crón", "2 cron",
            "segunda de crónicas", "segunda de cronicas", "2-cronicas", "2_cronicas"
        },
        "total_chapters": 36,
        "blocks": [
            (1, 10, "2chronicles-01-10.json"),
            (11, 20, "2chronicles-11-20.json"),
            (21, 30, "2chronicles-21-30.json"),
            (31, 36, "2chronicles-31-36.json"),
        ],
        "default_output_dir": "build/audit/2chronicles",
        "ambient_places": {
            "jerusalen", "jerusalén", "sion", "sión", "jordan", "jordán", "hebron", "hebrón", "gabaon", "gabaón",
            "quiriat-jearim", "quiriatjearim", "bet-semes", "betsemes", "bet-el", "dan", "samaria", "jezreel",
            "galaad", "siquem", "belen", "belén", "carmel", "ofir", "hamat", "sihor", "afec", "dotan", "tiro",
            "sidon", "sidón", "damasco", "siria", "aram", "moab", "edom", "amon", "amón", "filistea", "gat",
            "gezer", "raba", "rabá", "guilboa", "gilboa", "moriah", "monte moriah", "beraca", "valle de beraca",
            "seir", "monte seir", "libia", "etiopia", "asiria", "babilonia", "egipto", "ninive", "nínive",
            "valle de la sal", "quidron", "cedron", "cedrón", "meguido", "megido"
        },
    },
    "ezra": {
        "canonical_name": "Esdras",
        "api_name": "Esdras",
        "aliases": {
            "esdras", "ezra", "esd", "libro de esdras"
        },
        "total_chapters": 10,
        "blocks": [
            (1, 5, "ezra-01-05.json"),
            (6, 10, "ezra-06-10.json"),
        ],
        "default_output_dir": "build/audit/ezra",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "babilonia", "persia", "ecbatana", "achmetha",
            "ahava", "rio ahava", "río ahava", "casifia", "samaria", "sion", "sión", "israel",
            "siria", "fenicia", "libano", "líbano", "jope", "tiro", "sidon", "sidón",
            "asiria", "rio eufrates", "río eufrates", "mas alla del rio", "más allá del río"
        },
    },
    "nehemiah": {
        "canonical_name": "Nehemías",
        "api_name": "Nehemías",
        "aliases": {
            "nehemías", "nehemias", "nehemiah", "neh", "libro de nehemías", "libro de nehemias"
        },
        "total_chapters": 13,
        "blocks": [
            (1, 10, "nehemiah-01-10.json"),
            (11, 13, "nehemiah-11-13.json"),
        ],
        "default_output_dir": "build/audit/nehemiah",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "susa", "samaria", "sion", "sión", "babilonia", "persia",
            "elam", "rio eufrates", "río eufrates", "mas alla del rio", "más allá del río", "valle de ono",
            "ono", "opla", "ofel", "quidron", "cedron", "cedrón", "tecoa", "gabaon", "gabaón", "mizpa",
            "jericó", "jerico", "zonoa", "bet-sur", "betsur", "queila", "keila"
        },
    },
    "esther": {
        "canonical_name": "Ester",
        "api_name": "Ester",
        "aliases": {
            "ester", "esther", "est", "libro de ester", "libro de esther"
        },
        "total_chapters": 10,
        "blocks": [
            (1, 10, "esther-01-10.json"),
        ],
        "default_output_dir": "build/audit/esther",
        "ambient_places": {
            "susa", "persia", "media", "india", "etiopia", "etiopía", "babilonia", "jerusalen", "jerusalén", "juda", "judá"
        },
    },
    "job": {
        "canonical_name": "Job",
        "api_name": "Job",
        "aliases": {
            "job", "libro de job"
        },
        "total_chapters": 42,
        "blocks": [
            (1, 10, "job-01-10.json"),
            (11, 20, "job-11-20.json"),
            (21, 30, "job-21-30.json"),
            (31, 40, "job-31-40.json"),
            (41, 42, "job-41-42.json"),
        ],
        "default_output_dir": "build/audit/job",
        "ambient_places": {
            "uz", "tierra de uz", "teman", "temán", "sua", "súa", "naamat", "saba", "caldea", "ofir", "jerusalen", "jerusalén"
        },
    },
    "psalms": {
        "canonical_name": "Salmos",
        "api_name": "Salmos",
        "aliases": {
            "salmos", "salmo", "psalms", "psalm", "libro de salmos", "libro de los salmos"
        },
        "total_chapters": 150,
        "blocks": [
            (1, 10, "psalms-001-010.json"),
            (11, 20, "psalms-011-020.json"),
            (21, 30, "psalms-021-030.json"),
            (31, 40, "psalms-031-040.json"),
            (41, 50, "psalms-041-050.json"),
            (51, 60, "psalms-051-060.json"),
            (61, 70, "psalms-061-070.json"),
            (71, 80, "psalms-071-080.json"),
            (81, 90, "psalms-081-090.json"),
            (91, 100, "psalms-091-100.json"),
            (101, 110, "psalms-101-110.json"),
            (111, 120, "psalms-111-120.json"),
            (121, 130, "psalms-121-130.json"),
            (131, 140, "psalms-131-140.json"),
            (141, 150, "psalms-141-150.json"),
        ],
        "default_output_dir": "build/audit/psalms",
        "ambient_places": {
            "jerusalen", "jerusalén", "sion", "sión", "juda", "judá", "israel", "egipto", "babilonia", "sinai", "sinaí",
            "hermon", "hermón", "cades", "efrata", "galilea", "jordan", "jordán", "siria", "tiro", "sidon", "sidón",
            "filistea", "moab", "edom", "galaad", "sirion", "senir", "basan", "basán"
        },
    },
    "proverbs": {
        "canonical_name": "Proverbios",
        "api_name": "Proverbios",
        "aliases": {
            "proverbios", "proverbio", "proverbs", "proverb", "libro de proverbios", "libro de los proverbios"
        },
        "total_chapters": 31,
        "blocks": [
            (1, 10, "proverbs-01-10.json"),
            (11, 20, "proverbs-11-20.json"),
            (21, 30, "proverbs-21-30.json"),
            (31, 31, "proverbs-31.json"),
        ],
        "default_output_dir": "build/audit/proverbs",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "egipto"
        },
    },
    "ecclesiastes": {
        "canonical_name": "Eclesiastés",
        "api_name": "Eclesiastés",
        "aliases": {
            "eclesiastes", "eclesiastés", "ecclesiastes", "ecl", "ec", "libro de eclesiastes", "libro de eclesiastés"
        },
        "total_chapters": 12,
        "blocks": [
            (1, 10, "ecclesiastes-01-10.json"),
            (11, 12, "ecclesiastes-11-12.json"),
        ],
        "default_output_dir": "build/audit/ecclesiastes",
        "ambient_places": {
            "jerusalen", "jerusalén", "israel", "juda", "judá"
        },
    },
    "song_of_songs": {
        "canonical_name": "Cantar de los Cantares",
        "api_name": "Cantares",
        "aliases": {
            "cantar de los cantares", "cantar de cantares", "cantar", "cantares", "song of songs", "song of solomon", "libro de los cantares", "libro del cantar de los cantares"
        },
        "total_chapters": 8,
        "blocks": [
            (1, 8, "song-of-songs-01-08.json"),
        ],
        "default_output_dir": "build/audit/song_of_songs",
        "ambient_places": {
            "jerusalen", "jerusalén", "en-gadi", "engadi", "en gadi", "sarón", "saron", "hermón", "hermon", "senir", "amana", "tirsa", "damasco", "hesbon", "hesbón", "bat-rabim", "carmelo", "galilea", "sion", "sión"
        },
    },
    "isaiah": {
        "canonical_name": "Isaías",
        "api_name": "Isaías",
        "aliases": {
            "isaías", "isaias", "isaiah", "is", "isa", "libro de isaías", "libro de isaias"
        },
        "total_chapters": 66,
        "blocks": [
            (1, 10, "isaiah-01-10.json"),
            (11, 20, "isaiah-11-20.json"),
            (21, 30, "isaiah-21-30.json"),
            (31, 40, "isaiah-31-40.json"),
            (41, 50, "isaiah-41-50.json"),
            (51, 60, "isaiah-51-60.json"),
            (61, 66, "isaiah-61-66.json"),
        ],
        "default_output_dir": "build/audit/isaiah",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "asiria", "babilonia", "egipto", "etiopia", "etiopía",
            "moab", "damasco", "siria", "tiro", "sidon", "sidón", "filistea", "edom", "arabia", "cedar", "elam", "media", "cush",
            "tarso", "tarsis", "sinai", "sinaí", "libano", "líbano", "carmelo", "saron", "sarón", "basán", "basan"
        },
    },
    "jeremiah": {
        "canonical_name": "Jeremías",
        "api_name": "Jeremías",
        "aliases": {
            "jeremías", "jeremias", "jeremiah", "jer", "libro de jeremías", "libro de jeremias"
        },
        "total_chapters": 52,
        "blocks": [
            (1, 10, "jeremiah-01-10.json"),
            (11, 20, "jeremiah-11-20.json"),
            (21, 30, "jeremiah-21-30.json"),
            (31, 40, "jeremiah-31-40.json"),
            (41, 50, "jeremiah-41-50.json"),
            (51, 52, "jeremiah-51-52.json"),
        ],
        "default_output_dir": "build/audit/jeremiah",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "babilonia", "egipto", "anatot", "mizpa", "tahat",
            "tafnes", "migdol", "nof", "patros", "rieti", "ribla", "ramá", "rama", "tecoa", "siloh", "silo", "betel", "bet-el",
            "eufrates", "topet", "hinom", "valle de hinom", "valle de ben-hinom", "moab", "amon", "amón", "edom",
            "damasco", "hazor", "cedar", "elam"
        },
    },
    "lamentations": {
        "canonical_name": "Lamentaciones",
        "api_name": "Lamentaciones",
        "aliases": {
            "lamentaciones", "lamentations", "lam", "libro de lamentaciones", "libro de las lamentaciones"
        },
        "total_chapters": 5,
        "blocks": [
            (1, 5, "lamentations-01-05.json"),
        ],
        "default_output_dir": "build/audit/lamentations",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "edom", "uz", "egipto", "asiria"
        },
    },
    "ezekiel": {
        "canonical_name": "Ezequiel",
        "api_name": "Ezequiel",
        "aliases": {
            "ezequiel", "ezekiel", "ez", "ezeq", "libro de ezequiel"
        },
        "total_chapters": 48,
        "blocks": [
            (1, 10, "ezekiel-01-10.json"),
            (11, 20, "ezekiel-11-20.json"),
            (21, 30, "ezekiel-21-30.json"),
            (31, 40, "ezekiel-31-40.json"),
            (41, 48, "ezekiel-41-48.json"),
        ],
        "default_output_dir": "build/audit/ezekiel",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "babilonia", "caldea", "quebar", "rio quebar", "río quebar",
            "tel-abib", "telabib", "egipto", "asiria", "tiro", "sidon", "sidón", "edom", "moab", "amon", "amón", "filistea",
            "gog", "magog", "mesec", "tubal", "persia", "cus", "fut", "gomer", "togarma", "damasco", "seir", "samaria", "sodoma",
            "en-gadi", "engadi", "en-eglaim", "eneglaim"
        },
    },
    "daniel": {
        "canonical_name": "Daniel",
        "api_name": "Daniel",
        "aliases": {
            "daniel", "dan", "libro de daniel"
        },
        "total_chapters": 12,
        "blocks": [
            (1, 12, "daniel-01-12.json"),
        ],
        "default_output_dir": "build/audit/daniel",
        "ambient_places": {
            "babilonia", "caldea", "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "persia", "media", "grecia",
            "susa", "elam", "rio ulai", "río ulai", "rio hidekel", "río hidekel", "egipto", "siria"
        },
    },
    "hosea": {
        "canonical_name": "Oseas",
        "api_name": "Oseas",
        "aliases": {
            "oseas", "hosea", "os", "libro de oseas"
        },
        "total_chapters": 14,
        "blocks": [
            (1, 14, "hosea-01-14.json"),
        ],
        "default_output_dir": "build/audit/hosea",
        "ambient_places": {
            "israel", "efrain", "efraín", "juda", "judá", "jerusalen", "jerusalén", "jezreel", "bet-aven", "betaven", "guilgal", "gilgal",
            "mizpa", "tabor", "gabaa", "rama", "ramá", "samaria", "asiria", "egipto", "betel", "bet-el", "valle de acor", "acor",
            "siquem", "adma", "zeboim", "galad", "galaad", "peniel", "líbano", "libano"
        },
    },
    "joel": {
        "canonical_name": "Joel",
        "api_name": "Joel",
        "aliases": {
            "joel", "jl", "libro de joel"
        },
        "total_chapters": 3,
        "blocks": [
            (1, 3, "joel-01-03.json"),
        ],
        "default_output_dir": "build/audit/joel",
        "ambient_places": {
            "sion", "sión", "jerusalen", "jerusalén", "juda", "judá", "israel", "valle de josafat", "josafat",
            "valle de la decision", "valle de la decisión", "valle de sitim", "sitim", "tiro", "sidon", "sidón",
            "filistea", "egipto", "edom"
        },
    },
    "amos": {
        "canonical_name": "Amós",
        "api_name": "Amos",
        "aliases": {
            "amos", "amós", "am", "libro de amos", "libro de amós"
        },
        "total_chapters": 9,
        "blocks": [
            (1, 9, "amos-01-09.json"),
        ],
        "default_output_dir": "build/audit/amos",
        "ambient_places": {
            "tecoa", "tecoah", "sion", "sión", "jerusalen", "jerusalén", "damasco", "gaza", "tiro", "edom", "temán", "teman",
            "bosra", "amon", "amón", "raba", "rabá", "moab", "queriot", "juda", "judá", "israel", "asdod", "egipto",
            "samaria", "betel", "bet-el", "guilgal", "gilgal", "beerseba", "beer-seba", "calne", "hamat", "gat",
            "carmelo", "siria", "quenaan", "canan", "canaan", "caphtor", "caftor", "quir", "basán", "basan"
        },
    },
    "obadiah": {
        "canonical_name": "Abdías",
        "api_name": "Abdias",
        "aliases": {
            "abdias", "abdías", "obadiah", "ob", "libro de abdias", "libro de abdías"
        },
        "total_chapters": 1,
        "blocks": [
            (1, 1, "obadiah-01-01.json"),
        ],
        "default_output_dir": "build/audit/obadiah",
        "ambient_places": {
            "edom", "teman", "temán", "esau", "esaú", "monte de esau", "monte de esaú", "sion", "sión", "monte de sion",
            "monte de sión", "jerusalen", "jerusalén", "juda", "judá", "israel", "jacob", "jose", "josé", "negev", "negeb",
            "sefela", "filisteos", "efrain", "efraín", "samaria", "galaad", "benjamin", "benjamín", "fenicia", "sarepta",
            "sefarad", "ciudades del sur"
        },
    },
    "jonah": {
        "canonical_name": "Jonás",
        "api_name": "Jonas",
        "aliases": {
            "jonas", "jonás", "jonah", "jon", "libro de jonas", "libro de jonás"
        },
        "total_chapters": 4,
        "blocks": [
            (1, 4, "jonah-01-04.json"),
        ],
        "default_output_dir": "build/audit/jonah",
        "ambient_places": {
            "ninive", "nínive", "tarsis", "jope", "gat-hefer", "gathefer", "asiria", "mar", "mar grande"
        },
    },
    "micah": {
        "canonical_name": "Miqueas",
        "api_name": "Miqueas",
        "aliases": {
            "miqueas", "micah", "miq", "libro de miqueas"
        },
        "total_chapters": 7,
        "blocks": [
            (1, 7, "micah-01-07.json"),
        ],
        "default_output_dir": "build/audit/micah",
        "ambient_places": {
            "samaria", "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "monte de sion", "monte de sión",
            "gat", "afra", "safir", "zanan", "bet-esel", "betesel", "marot", "laquis", "moreses-gat", "moresesgat",
            "aczib", "maresah", "adulam", "belen", "belén", "efrata", "éfrata", "asiria", "nimrod", "egipto", "moab",
            "sitim", "gilgal", "galaad", "basan", "basán"
        },
    },
    "nahum": {
        "canonical_name": "Nahúm",
        "api_name": "Nahum",
        "aliases": {
            "nahum", "nahúm", "nah", "libro de nahum", "libro de nahúm"
        },
        "total_chapters": 3,
        "blocks": [
            (1, 3, "nahum-01-03.json"),
        ],
        "default_output_dir": "build/audit/nahum",
        "ambient_places": {
            "ninive", "nínive", "asiria", "juda", "judá", "israel", "elcos", "basan", "basán", "carmelo",
            "libano", "líbano", "no-amon", "no-amón", "noamon", "tebas", "etiopia", "etiopía", "egipto",
            "fut", "libia", "rio", "río", "tigris", "eufrates", "éufrates"
        },
    },
    "habakkuk": {
        "canonical_name": "Habacuc",
        "api_name": "Habacuc",
        "aliases": {
            "habacuc", "habakkuk", "hab", "libro de habacuc"
        },
        "total_chapters": 3,
        "blocks": [
            (1, 3, "habakkuk-01-03.json"),
        ],
        "default_output_dir": "build/audit/habakkuk",
        "ambient_places": {
            "caldeos", "caldea", "juda", "judá", "israel", "teman", "temán", "paran", "parán", "monte de paran",
            "monte de parán", "cusan", "cusán", "madian", "madián", "libano", "líbano", "mar", "abismo"
        },
    },
    "zephaniah": {
        "canonical_name": "Sofonías",
        "api_name": "Sofonias",
        "aliases": {
            "sofonias", "sofonías", "zephaniah", "sof", "libro de sofonias", "libro de sofonías"
        },
        "total_chapters": 3,
        "blocks": [
            (1, 3, "zephaniah-01-03.json"),
        ],
        "default_output_dir": "build/audit/zephaniah",
        "ambient_places": {
            "juda", "judá", "jerusalen", "jerusalén", "filistea", "moab", "amon", "amón", "cus", "etiopia", "etiopía",
            "asiria", "ninive", "nínive", "gaza", "ascalon", "ascalón", "asdod", "ecron", "ecrón", "quereteos",
            "canaan", "canaán", "sodoma", "gomorra", "mactes", "mactés", "puerta del pescado", "segundo barrio"
        },
    },
    "haggai": {
        "canonical_name": "Hageo",
        "api_name": "Hageo",
        "aliases": {
            "hageo", "haggai", "hag", "libro de hageo"
        },
        "total_chapters": 2,
        "blocks": [
            (1, 2, "haggai-01-02.json"),
        ],
        "default_output_dir": "build/audit/haggai",
        "ambient_places": {
            "juda", "judá", "jerusalen", "jerusalén", "monte", "egipto", "casa", "templo"
        },
    },
    "zechariah": {
        "canonical_name": "Zacarías",
        "api_name": "Zacarias",
        "aliases": {
            "zacarias", "zacarías", "zechariah", "zac", "libro de zacarias", "libro de zacarías"
        },
        "total_chapters": 14,
        "blocks": [
            (1, 14, "zechariah-01-14.json"),
        ],
        "default_output_dir": "build/audit/zechariah",
        "ambient_places": {
            "jerusalen", "jerusalén", "juda", "judá", "israel", "sion", "sión", "monte de los olivos",
            "valle de los montes", "valle de josafat", "valle de meguido", "hadadrimon", "hadadrimón",
            "babilonia", "sinar", "sinear", "damasco", "hamat", "tiro", "sidon", "sidón", "ascalon", "ascalón",
            "gaza", "ecron", "ecrón", "asdod", "filistea", "grecia", "efrain", "efraín", "galaad", "libano", "líbano",
            "asiria", "egipto", "bet-el", "betel", "mar", "eufrates", "éufrates", "geba", "rimon", "rimón"
        },
    },
    "malachi": {
        "canonical_name": "Malaquías",
        "api_name": "Malaquias",
        "aliases": {
            "malaquias", "malaquías", "malachi", "mal", "libro de malaquias", "libro de malaquías"
        },
        "total_chapters": 4,
        "blocks": [
            (1, 4, "malachi-01-04.json"),
        ],
        "default_output_dir": "build/audit/malachi",
        "ambient_places": {
            "israel", "juda", "judá", "jerusalen", "jerusalén", "edom", "horeb", "templo", "casa"
        },
    },
    "matthew": {
        "canonical_name": "Mateo",
        "api_name": "Mateo",
        "aliases": {
            "mateo", "matthew", "mt", "libro de mateo", "evangelio de mateo", "evangelio segun san mateo", "san mateo"
        },
        "total_chapters": 28,
        "blocks": [
            (1, 10, "matthew-01-10.json"),
            (11, 20, "matthew-11-20.json"),
            (21, 28, "matthew-21-28.json"),
        ],
        "default_output_dir": "build/audit/matthew",
        "ambient_places": {
            "belen", "belén", "judea", "jerusalen", "jerusalén", "egipto", "nazaret", "galilea", "jordan", "jordán",
            "desierto", "capernaum", "capernaúm", "mar de galilea", "siria", "decapolis", "decápolis", "genesaret",
            "tiro", "sidon", "sidón", "cesarea de filipo", "monte", "monte de los olivos", "betfage", "betania",
            "getsemani", "getsemaní", "golgota", "gólgota", "arimatea", "templo", "casa", "sinagoga", "posada"
        },
    },
    "mark": {
        "canonical_name": "Marcos",
        "api_name": "Marcos",
        "aliases": {
            "marcos", "mark", "mc", "libro de marcos", "evangelio de marcos", "evangelio segun san marcos", "san marcos"
        },
        "total_chapters": 16,
        "blocks": [
            (1, 8, "mark-01-08.json"),
            (9, 16, "mark-09-16.json"),
        ],
        "default_output_dir": "build/audit/mark",
        "ambient_places": {
            "judea", "jerusalen", "jerusalén", "galilea", "jordan", "jordán", "nazaret", "capernaum", "capernaúm",
            "mar de galilea", "genesaret", "gadarenos", "decapolis", "decápolis", "tiro", "sidon", "sidón", "dalmanuta",
            "betsaida", "cesarea de filipo", "monte", "monte de los olivos", "betfage", "betania", "getsemani",
            "getsemaní", "golgota", "gólgota", "arimatea", "templo", "casa", "sinagoga", "desierto", "mar", "pretorio"
        },
    },
    "luke": {
        "canonical_name": "Lucas",
        "api_name": "Lucas",
        "aliases": {
            "lucas", "luke", "lc", "libro de lucas", "evangelio de lucas", "evangelio segun san lucas", "san lucas"
        },
        "total_chapters": 24,
        "blocks": [
            (1, 8, "luke-01-08.json"),
            (9, 16, "luke-09-16.json"),
            (17, 24, "luke-17-24.json"),
        ],
        "default_output_dir": "build/audit/luke",
        "ambient_places": {
            "judea", "jerusalen", "jerusalén", "galilea", "jordan", "jordán", "nazaret", "belen", "belén",
            "capernaum", "capernaúm", "nain", "naín", "mar de galilea", "genesaret", "gadarenos", "decapolis",
            "decápolis", "tiro", "sidon", "sidón", "betsaida", "samaria", "jerico", "jericó", "betfage",
            "betania", "monte de los olivos", "emaus", "emaús", "getsemani", "getsemaní", "golgota", "gólgota",
            "calvario", "arimatea", "templo", "casa", "sinagoga", "desierto", "mar", "pretorio", "posada", "siloe", "siloé"
        },
    },
    "john": {
        "canonical_name": "Juan",
        "api_name": "Juan",
        "aliases": {
            "juan", "john", "jn", "libro de juan", "evangelio de juan", "evangelio segun san juan", "san juan"
        },
        "total_chapters": 21,
        "blocks": [
            (1, 10, "john-01-10.json"),
            (11, 21, "john-11-21.json"),
        ],
        "default_output_dir": "build/audit/john",
        "ambient_places": {
            "judea", "jerusalen", "jerusalén", "galilea", "jordan", "jordán", "betania", "cana", "caná",
            "capernaum", "capernaúm", "samaria", "sicar", "siloe", "siloé", "betesda", "tiberias",
            "mar de tiberias", "mar de galilea", "mar", "efrain", "efraín", "cedron", "cedrón", "getsemani",
            "getsemaní", "huerto", "golgota", "gólgota", "calvario", "arimatea", "templo", "casa", "sinagoga",
            "desierto", "pretorio", "gabbata", "gábata", "enon", "enón", "salim"
        },
    },
    "acts": {
        "canonical_name": "Hechos",
        "api_name": "Hechos",
        "aliases": {
            "hechos", "acts", "hch", "libro de hechos", "hechos de los apostoles", "hechos de los apóstoles", "los hechos"
        },
        "total_chapters": 28,
        "blocks": [
            (1, 9, "acts-01-09.json"),
            (10, 19, "acts-10-19.json"),
            (20, 28, "acts-20-28.json"),
        ],
        "default_output_dir": "build/audit/acts",
        "ambient_places": {
            "jerusalen", "jerusalén", "judea", "samaria", "galilea", "antioquia", "antioquía", "damasco", "tarso",
            "cesarea", "jope", "lida", "saron", "sarón", "chipre", "salamina", "pafos", "perge", "panfilia", "panfília",
            "pisidia", "antioquia de pisidia", "iconio", "listra", "derbe", "licaonia", "galacia", "frigia", "misia",
            "troas", "tróade", "samotracia", "neapolis", "neápolis", "filipos", "anfipolis", "anfípolis", "apolonia",
            "tesalonica", "tesalónica", "berea", "atenas", "corinto", "cencrea", "efeso", "éfeso", "macedonia",
            "acaya", "mileto", "rodas", "patara", "fenicia", "tiro", "ptolemaida", "ason", "asón", "mitilene",
            "quio", "quío", "samos", "trogilio", "cos", "creta", "buenos puertos", "lasea", "fenice", "clauda",
            "cauda", "adramitio", "alejandria", "alejandría", "sirte", "malta", "melita", "siracusa", "regio",
            "puteoli", "foro de apio", "tres tabernas", "roma", "italia", "espana", "españa", "cilicia", "egipto",
            "cirene", "asia", "bitinia", "ponto", "capadocia", "areopago", "areópago", "pretorio", "templo",
            "sinagoga", "carcel", "cárcel", "mar", "mar adriatico", "mar adriático", "monte de los olivos", "cedron", "cedrón"
        },
    },
    "romans": {
        "canonical_name": "Romanos",
        "api_name": "Romanos",
        "aliases": {
            "romanos", "romans", "rom", "carta a los romanos", "epistola a los romanos", "epístola a los romanos", "libro de romanos"
        },
        "total_chapters": 16,
        "blocks": [
            (1, 8, "romans-01-08.json"),
            (9, 16, "romans-09-16.json"),
        ],
        "default_output_dir": "build/audit/romans",
        "ambient_places": {
            "roma", "espana", "españa", "jerusalen", "jerusalén", "judea", "macedonia", "acaya", "cencrea",
            "ilirico", "ilírico", "sion", "sión", "sodoma", "gomorra", "egipto", "damasco", "sinai", "sinaí",
            "grecia", "gentiles", "israel", "corinto"
        },
    },
    "1corinthians": {
        "canonical_name": "1 Corintios",
        "api_name": "1 Corintios",
        "aliases": {
            "1 corintios", "1corintios", "1 corinthians", "1corinthians", "1 cor", "1cor",
            "primera corintios", "primera de corintios", "primera carta a los corintios", "i corintios"
        },
        "total_chapters": 16,
        "blocks": [
            (1, 8, "1corinthians-01-08.json"),
            (9, 16, "1corinthians-09-16.json"),
        ],
        "default_output_dir": "build/audit/1corinthians",
        "ambient_places": {
            "corinto", "efeso", "éfeso", "macedonia", "acaya", "jerusalen", "jerusalén", "galacia",
            "asia", "troas", "tróade", "filipos", "atenas", "cencrea", "roma", "desierto", "mar rojo"
        },
    },
    "2corinthians": {
        "canonical_name": "2 Corintios",
        "api_name": "2 Corintios",
        "aliases": {
            "2 corintios", "2corintios", "2 corinthians", "2corinthians", "2 cor", "2cor",
            "segunda corintios", "segunda de corintios", "segunda carta a los corintios", "ii corintios"
        },
        "total_chapters": 13,
        "blocks": [
            (1, 7, "2corinthians-01-07.json"),
            (8, 13, "2corinthians-08-13.json"),
        ],
        "default_output_dir": "build/audit/2corinthians",
        "ambient_places": {
            "corinto", "macedonia", "acaya", "troas", "tróade", "damasco", "efeso", "éfeso",
            "judea", "jerusalen", "jerusalén", "asia"
        },
    },
    "galatians": {
        "canonical_name": "Gálatas",
        "api_name": "Gálatas",
        "aliases": {
            "galatas", "gálatas", "galatians", "gal",
            "carta a los galatas", "carta a los gálatas",
            "epistola a los galatas", "epístola a los gálatas"
        },
        "total_chapters": 6,
        "blocks": [
            (1, 6, "galatians-01-06.json"),
        ],
        "default_output_dir": "build/audit/galatians",
        "ambient_places": {
            "galacia", "arabia", "damasco", "jerusalen", "jerusalén", "siria", "cilicia",
            "antioquia", "antioquía", "judea", "sinaí", "sinai"
        },
    },
}

STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "los", "que", "su", "sus",
    "un", "una", "unos", "unas", "y", "o", "en", "por", "para", "con",
    "segun", "como", "fue", "era", "es", "se", "lo", "le", "les", "ha",
    "habia", "habian", "sus", "hizo", "dijo",
    "cual", "quien", "quienes", "cuando", "donde", "por", "que", "hacia",
    "sobre", "tras", "entre", "hasta", "desde", "ante", "bajo", "cabe",
    "pero", "mas", "este", "esta", "estos", "estas", "aquel", "aquella",
    "ser", "sido", "estar", "estaba", "estaban", "tener", "tenia", "tenian",
}

# Entidades y personajes bíblicos (Génesis a 2 Crónicas)
BIBLE_PERSONAJES = {
    # Génesis
    "adan", "eva", "cain", "abel", "set", "enos", "cainan", "mahalaleel",
    "jared", "enoc", "matusalen", "lamec", "noe", "sem", "cam", "jafet",
    "canaan", "tare", "abram", "abraham", "sarai", "sara", "lot", "melquisedec",
    "agar", "ismael", "isaac", "rebeca", "laban", "betuel", "jacob", "esau",
    "lea", "raquel", "ruben", "simeon", "levi", "juda", "dan", "neftali",
    "gad", "aser", "isacar", "zabulon", "jose", "benjamin", "dina", "tamar",
    "potifar", "faraon", "asenat", "manases", "efrain", "abimelec", "eliezer",
    "cetura", "zilpa", "bilha", "potifera", "zafenat-panea", "zafenatpanea",
    "eber", "peleg", "milca", "isca", "er", "onan", "sela", "fares", "zara",
    "hezron", "hamul", "siquem", "hamor", "nemrod", "mizraim", "cuz",
    # Éxodo y Levítico
    "moises", "aaron", "miriam", "maria", "sefora", "jetro", "reuel", "gersom",
    "sipra", "fua", "jocabed", "amram", "hur", "josue", "bezaleel", "aholiab",
    "nadab", "abiu", "eleazar", "itamar", "core", "datan", "abiram",
    "misael", "elzafan", "elsafan", "uziel", "selomit", "dibri",
    # Números y Deuteronomio
    "balaam", "balac", "finees", "caleb", "hobab", "eldad", "medad",
    "zelofehad", "mahla", "noa", "hogla", "milca", "tirsa", "cozbi", "zuri", "zur",
    "og", "sehon", "sihon", "on", "eliasaf", "pagiel", "ahiezer", "ahira", "ocran",
    "enam", "helon", "amiasadai", "pedasur", "gamaliel", "zuriel", "eliseba",
    # Josué y Jueces
    "rahab", "acan", "carmi", "zabdi", "zera", "jefone", "nun",
    "adonicedec", "hoham", "piram", "jafia", "debir", "jabin", "jobab",
    "otniel", "cenaz", "acsa", "ehud", "eglon", "samgar", "debora", "débora",
    "barac", "jael", "sisara", "sísara", "heber", "lapidot", "gedeon", "gedeón",
    "joas", "jerobaal", "abimelec", "jotam", "tola", "pua", "jair", "jefte", "jefté",
    "ibzan", "elon", "abdon", "abdón", "hilel", "sanson", "sansón", "manoa",
    "dalila", "micas", "jonatan", "gersom",
    # Rut
    "rut", "noemi", "noemí", "booz", "elimelec", "mahlon", "mahlón", "quelion", "quelión",
    "orfa", "obed", "isai", "isaí", "salmon", "salmón", "aminadab", "ram", "naason",
    # 1 Samuel
    "elcana", "ana", "penina", "eli", "elí", "ofni", "icabod", "goliat", "abner",
    "ahimelec", "abiatar", "aquis", "nabal", "abigail", "agag", "nahas", "nahás",
    "cis", "mical", "merab", "abinadab", "malquisua", "malquisúa", "joab", "abisai", "doeg",
    # 2 Samuel
    "mefi-boset", "mefiboset", "is-boset", "isboset", "asael", "absalon", "absalón",
    "amnon", "amnón", "adonias", "adonías", "sarvia", "urias", "urías", "betsabe", "betsabé",
    "natan", "natán", "ahitofel", "husai", "itai", "itaí", "simei", "ziba", "siba", "barzilai",
    "quimam", "seba", "sebá", "benaia", "benaías", "amasa", "arauna", "isbi-benob",
    "saf", "elhanan", "jonadab", "hanun", "hanún", "sobac", "baana", "recab", "talmai", "ahimaas",
    # 1 Reyes, 2 Reyes, 1 Crónicas y 2 Crónicas
    "salomon", "salomón", "roboam", "jeroboam", "abiam", "abías", "abias", "asa",
    "baasa", "ela", "zimri", "omri", "acab", "ocozias", "ocozías", "josafat", "josafath",
    "ben-hadad", "benhadad", "hazael", "jehu", "jehú", "hiel", "segub", "abisag",
    "jezabel", "atalia", "atalía", "sadoc", "zabud", "adoniram", "hiram", "semer",
    "elias", "elías", "eliseo", "ahias", "ahías", "semaias", "semaías", "micaias", "micaías",
    "sedequias", "sedequías", "imla", "quenaana", "hanani", "nabot", "abdias", "abdías",
    "jaquin", "jaquín", "boaz", "saba", "reina de saba",
    "joram", "joacaz", "joas", "joás", "zacarias", "zacarías", "salum", "manahem",
    "pekaia", "pekaía", "peka", "oseas", "amasias", "amasías", "azarias", "azarías",
    "uzias", "uzías", "acaz", "ezequias", "ezequías", "manases", "manasés", "amon", "amón",
    "josias", "josías", "joacim", "eliaquim", "joaquin", "joaquín", "matanias", "matanías",
    "giezi", "hilcias", "hilcías", "safan", "safán", "hulda", "joiada", "josaba",
    "isaias", "isaías", "jonas", "jonás", "amitai", "amoz", "naaman", "naamán", "mesa",
    "pul", "tiglat-pileser", "tiglatpileser", "salmanasar", "senaquerib", "esardohon",
    "asarjaddon", "evil-merodac", "rabsaces", "rabsaris", "tartan", "tartán",
    "gedalias", "gedalías", "netanias", "netanías", "nehustan", "nehustán",
    "baal-zebub", "baalzebub", "tartac", "nisroc", "adramelec", "anamelec",
    "jasobeam", "hacmoni", "amasai", "ornan", "ornán", "heman", "hemán", "asaf", "etan", "etán",
    "quenanias", "quenanías", "jedutun", "jedutún", "pedaias", "pedaías", "zorobabel",
    "merib-baal", "meribbaal", "sealtiel", "isbaal", "satanas", "satanás", "jeconias", "jeconías",
    "sisac", "iddo", "zera", "amarias", "amarías", "zebadias", "zebadías", "jahaziel", "conanias", "conanías", "necao", "ciro", "jeremias", "jeremías",
    # Esdras, Nehemías, Ester y Job
    "esdras", "sesbasar", "mitridates", "mitrídates", "jesua", "jesúa", "hageo", "tatnai",
    "setar-boznai", "setarboznai", "dario", "darío", "artajerjes", "secanias", "secanías",
    "meremot", "jozabad", "noadias", "noadías", "serebias", "serebías", "hasabias", "hasabías",
    "jesaias", "jesaías", "ido", "rehum", "simsai", "asenapar", "asurbanipal", "bislam", "tabeel",
    "johanan", "eliasib", "josadac", "salatiel", "seraias", "jehiel", "sanbalat", "tobias", "tobías", "gesem",
    "nehemias", "nehemías", "hacalias", "hacalías", "hanani", "hananias", "hananías",
    "sebanías", "sebanias", "patahias", "patahías",
    "ester", "mardoqueo", "asuero", "vasti", "aman", "amán", "zeres", "hegai", "hege",
    "hatac", "memucan", "memucán", "harbona", "bigtan", "bigtán", "bigtana", "teres",
    "jair", "simei", "cis", "marsena", "admeta", "tarso", "carsena", "setar",
    "job", "elifaz", "bildad", "zofar", "eliu", "eliú", "baraquel", "jemima", "cesia", "keren-hapuc", "kerenhapuc",
    # Proverbios
    "agur", "lemuel",
    # Isaías
    "sebna", "merodac-baladan", "merodac-baladán", "merodacbaladan", "merodac",
    # Jeremías
    "baruc", "ebed-melec", "ebedmelec", "pasur", "recabitas",
    # Ezequiel
    "ezequiel",
    # Daniel
    "daniel", "sadrac", "mesac", "abed-nego", "abednego", "belsasar", "beltsasar", "aspenaz", "arioc", "gabriel", "miguel",
    # Oseas
    "oseas", "gomer", "jezreel", "lo-ruhama", "loruhama", "lo-ammi", "loammi", "diblaiam", "beeri",
    # Joel
    "joel", "petuel",
    # Amós
    "amos", "amós", "amasias", "amasías", "jeroboam", "uzias", "uzías", "joas", "joás",
    # Abdías
    "abdias", "abdías",
    # Jonás
    "jonas", "jonás", "amitai", "amittai", "marineros", "capitan", "capitán", "rey de ninive", "rey de nínive", "ninivitas",
    # Miqueas
    "miqueas", "morastita", "jotam", "jotám", "acaz", "ezequias", "ezequías", "gobernantes de israel", "profetas", "balac", "balaam", "beor", "omri", "acab",
    # Nahúm
    "nahum", "nahúm", "elcesita",
    # Habacuc
    "habacuc", "habakkuk",
    # Sofonías
    "sofonias", "sofonías", "josias", "josías", "cusi", "gedalias", "gedalías", "amarias", "amarías",
    # Hageo
    "hageo", "haggai", "dario", "darío", "salatiel", "sealtiel", "josadac", "jehozadac", "zorobabel", "josue", "josué",
    # Zacarías
    "zacarias", "zacarías", "berequias", "berequías", "ido", "iddó", "iddo", "satanas", "satanás", "serezer", "regem-melec", "regemmelec", "heldai", "tobias", "tobías", "jedaias", "jedaías", "hen",
    # Malaquías
    "malaquias", "malaquías", "elias", "elías",
    # Mateo, Marcos, Lucas, Juan, Hechos y Nuevo Testamento
    "herodes", "herodías", "herodias", "pilato", "poncio pilato", "barrabas", "barrabás", "caifas", "caifás",
    "anas", "anás", "jose", "josé", "maria", "maría", "maria magdalena", "maría magdalena", "salome", "salomé",
    "juan el bautista", "juan bautista", "andres", "andrés", "jacobo", "felipe", "bartolome", "bartolomé",
    "tomas", "tomás", "tadeo", "simon", "simón", "simon cananista", "simón cananista", "simon pedro", "simón pedro",
    "judas", "judas iscariote", "iscariote", "zebedeo", "alfeo", "elisabet", "jairo", "bartimeo",
    "alejandro", "rufo", "simon de cirene", "simon el leproso", "jose de arimatea", "boanerges",
    "teofilo", "teófilo", "gabriel", "simeon", "simeón", "ana", "augusto", "cirenio", "tiberio", "lisanias",
    "juana", "chuza", "susana", "zaqueo", "moises", "moisés",
    "nicodemo", "natanael", "malco",
    "matias", "matías", "bernabe", "bernabé", "ananias", "ananías", "safira", "tabita", "dorcas",
    "agabo", "roda", "juan marcos", "sergio paulo", "elimas", "barjesus", "barjesús",
    "lidia", "carcelero", "jason", "jasón", "dionisio", "damaris", "dámaris", "crispo", "sostenes", "sóstenes",
    "galion", "galión", "sceva", "esceva", "demetrio", "eutico", "tiquico", "tíquico", "trofimo", "trófimo",
    "claudio lisias", "drusila", "festo", "berenice", "tertulo", "tértulo", "julio", "publio",
    "febe", "prisca", "epeneto", "andronico", "andrónico", "junias", "amplias", "urbano", "estaquis",
    "apeles", "aristobulo", "aristóbulo", "herodion", "herodión", "narciso", "trifena", "trifosa",
    "persida", "pérsida", "asincrito", "asíncrito", "flegonte", "hermes", "patrobas", "hermas",
    "filologo", "filólogo", "julia", "nereo", "olimpas", "tercio", "gayo", "erasto", "cuarto",
    "lucio", "sosipater", "sosípater", "adan", "adán", "cristo",
    "cefas", "estefanas", "estéfanas", "cloe", "fortunato", "acaico",
    "silvano", "eva", "aretas", "belial", "satanas", "satanás", "abrahan", "abrahán",
    "lazaro", "lázaro", "marta", "cleofas", "cornelio", "saulo", "bernice", "agripa", "felix", "félix",
    "gamaliel", "tito", "silas", "apolos", "aquila", "áquila", "priscila", "filemon", "filemón", "onesimo", "onésimo",
    # Otros comunes
    "david", "saul", "samuel", "nabucodonosor", "pablo", "pedro", "juan", "jesus", "mateo", "marcos",
    "lucas", "esteban", "timoteo",
}

# Lugares, regiones y accidentes geográficos bíblicos
# Nota: La preposición común española 'sin' NO se incluye como topónimo aislado.
BIBLE_PLACES = {
    # Génesis
    "eden", "ararat", "babel", "babilonia", "ur", "haran", "betel", "bet-el", "hebron", "siquem",
    "sodoma", "gomorra", "adma", "zeboim", "bela", "zoar", "egipto", "gosen",
    "moriah", "beerseba", "beer-seba", "macpela", "mizpa", "seir", "rameses",
    "peniel", "penuel", "dotan", "dothan", "gerar", "gueral", "filistea", "ebal",
    "galaad", "guilead", "padan-aram", "padanaram", "mesopotamia", "canaan",
    "salem", "mamre", "cala", "sinar", "ofir", "havila", "caldea", "siria",
    "lahai-roi", "lahairoi", "berseba", "sucot", "efrata", "belen", "nilo",
    "eufrates", "hidekel", "pison", "gihon", "quedem", "horeb",
    "sion", "negev", "jordan", "atarot", "shiloh", "damasco",
    # Éxodo y Levítico
    "madian", "sinai", "monte sinai", "mar rojo", "mara", "elim", "desierto de sin", "refidim",
    "masa", "meriba", "etam", "pi-hahirot", "pihahirot", "baal-zefon",
    "baalzefon", "migdol", "sur", "piton", "tabernaculo", "desierto",
    # Números, Deuteronomio, Josué y Jueces
    "cades", "cades-barnea", "cadesbarnea", "paran", "desierto de paran", "zin", "desierto de zin", "moab", "campos de moab",
    "llanuras de moab", "jerico", "jericó", "arava", "aravá", "edom", "hor", "monte hor",
    "hesbon", "hesbón", "arnon", "arnón", "bamot", "pisga", "monte pisga", "peor",
    "monte peor", "tabera", "taberah", "hazelot", "hazerot", "kibrot-hataava", "horma",
    "zalmona", "punon", "obot", "abarim", "monte abarim", "nebo", "monte nebo",
    "almon-diblataim", "arba", "escol", "valle de escol", "petor",
    "gerizim", "monte gerizim", "ebal", "monte ebal", "basan", "basán", "hermon", "monte hermon",
    "sirion", "senir", "aroer", "quedemot", "salca", "edrei", "bet-peor", "betpeor",
    "sitim", "gilgal", "hai", "gabaon", "gabaón", "cefila", "beerot", "quiriat-jearim", "quiriat-arba",
    "jerusalen", "jerusalén", "jarmut", "laquis", "eglon", "eglón", "maceda", "libna", "gezer", "debir",
    "gaza", "hazor", "madon", "madón", "simron", "simrón", "acsaf", "cineret", "dor", "mizpa",
    "merom", "aguas de merom", "monte halac", "anab", "timnat-sera", "silo", "siló", "bezer", "ramot", "golan", "golán", "galilea", "cedes",
    "cison", "cisón", "monte tabor", "tabor", "ofra", "jezreel", "valle de jezreel", "harod", "fuente de harod",
    "more", "collado de more", "tabat", "abel-mehola", "sucot", "peniel", "karkor", "piraton", "timnat", "zora",
    "estaol", "ascalon", "ascalón", "ecron", "ecrón", "asdod", "gibea", "gabaa", "rama", "mizpa", "en-dor", "endor", "meguido", "megido",
    # 1 Samuel a Job
    "bet-semes", "betsemes", "jabes", "jabes de galaad", "nob", "adulam", "keila", "siclag",
    "bet-san", "bet-sán", "carmel", "en-gadi", "engadi", "guilboa", "gilboa", "monte gilboa",
    "baal-perazim", "baalperazim", "abel-bet-maaca", "tecoa", "mahanaim", "raba", "rabá", "gesur",
    "quidron", "cedron", "cedrón", "helam", "bet-rehob", "zoba", "is-tob", "meteg-ama",
    "gihon", "gihón", "cabul", "ezion-geber", "ezión-geber", "eziongeber", "elot", "ofir",
    "sarepta", "querit", "arroyo de querit", "ramot de galaad", "tirse", "samaria", "tiro", "sidon", "sidón", "tisbe",
    "sunem", "afec", "sela", "jocteel", "hamat", "arpat", "sefarvaim", "ribla", "ninive", "nínive", "asiria", "valle de la sal", "siloe", "siloé",
    "sihor", "jebus", "jebús", "beraca", "valle de beraca", "ahava", "rio ahava", "río ahava", "casifia", "ecbatana", "achmetha", "persia",
    "susa", "valle de ono", "ono", "opla", "ofel", "zonoa", "bet-sur", "betsur", "media", "india", "etiopia", "etiopía",
    "uz", "tierra de uz", "teman", "temán", "sua", "súa", "naamat", "saba"
}

# Raíces de parentesco y lemas
KINSHIP_STEMS = {
    "hij": ["hijo", "hija", "hijos", "hijas"],
    "herman": ["hermano", "hermana", "hermanos", "hermanas"],
    "padr": ["padre", "padres", "papa"],
    "madr": ["madre", "madres", "mama"],
    "espos": ["esposa", "esposo", "esposas", "mujer", "marido"],
    "sierv": ["sierva", "siervo", "siervas", "siervos", "criado", "criados", "doncella"],
    "primogenit": ["primogenito", "primogenita"],
    "sobrin": ["sobrino", "sobrina", "pariente"],
    "tio": ["tio", "tia"],
    "suegr": ["suegro", "suegra"],
    "yern": ["yerno", "nuera"],
    "niet": ["nieto", "nieta", "nietos"],
    "abuel": ["abuelo", "abuela"],
    "concubin": ["concubina", "concubinas"],
    "gemel": ["gemelos", "mellizos"],
    "primo": ["primo", "prima", "primos"],
}

# Entidades bíblicas con polisemia (persona / tribu / territorio / colectivo)
POLYSEMOUS_ENTITIES = {
    "juda", "israel", "efrain", "benjamin", "manases", "dan", "gad",
    "aser", "neftali", "zabulon", "isacar", "simeon", "moab", "edom", "amon"
}

LOCATIVE_PREFIX_PATTERN = re.compile(
    r"\b(?:en|de|a|hacia|por|desde|para|situacion de|ciudades de|reino de|tierra de|provincia de|campos de|montes de|territorio de)\s+(\w+)\b"
)

LOCATIVE_PAIR_PATTERN = re.compile(
    r"\b(\w+)\s+y\s+(?:jerusalen|samaria|sion|galilea|belen|hebron|las ciudades|los pueblos)\b"
)

COLLECTIVE_PREFIX_PATTERN = re.compile(
    r"\b(?:tribu de|casa de|hijos de|pueblo de|varones de|hombres de)\s+(\w+)\b"
)

FIRST_PERSON_DISCOURSE_MARKERS = {
    "yo", "mi", "mis", "mio", "mia", "conmigo", "me",
    "nosotros", "nosotras", "nos", "nuestro", "nuestra", "nuestros", "nuestras",
    "diremos", "hemos", "estamos", "hablamos", "somos", "hicimos", "dejamos",
    "peque", "pequemos", "dije", "clame", "ore", "estoy", "tengo", "veo"
}

SPEECH_PRAYER_VERBS = {
    "dijo", "oro", "clamo", "respondio", "hablo", "postro", "confeso", "rogo", "suplico", "exclamo", "levanto"
}


def is_locative_or_collective_entity(token: str, full_text: str, declared_characters: list[str]) -> bool:
    """Determina si un token polisémico funciona como entidad locativa, geopolítica o colectiva."""
    norm_token = normalize(token).strip()
    if norm_token not in POLYSEMOUS_ENTITIES:
        return False

    norm_chars = {normalize(c).strip() for c in (declared_characters or [])}
    if norm_token in norm_chars:
        return False

    text_norm = normalize(full_text)

    # 1. Pareja con otro topónimo conocido (ej: 'Judá y Jerusalén')
    for m in LOCATIVE_PAIR_PATTERN.finditer(text_norm):
        if m.group(1) == norm_token:
            return True

    # 2. Prefijo locativo (ej: 'en Judá', 'de Judá', 'situación de Judá', 'ciudades de Judá')
    for m in LOCATIVE_PREFIX_PATTERN.finditer(text_norm):
        if m.group(1) == norm_token:
            return True

    # 3. Prefijo colectivo / tribal (ej: 'tribu de Judá', 'pueblo de Israel', 'hombres de Judá')
    for m in COLLECTIVE_PREFIX_PATTERN.finditer(text_norm):
        if m.group(1) == norm_token:
            return True

    return False


def is_narrative_source_attribution(token: str, full_text: str, book_cfg: dict | None = None) -> bool:
    """
    Determina genéricamente si un nombre propio coincide con una atribución narrativa / fuente documental
    (ej: 'Lucas señala...', 'según Lucas...', 'el evangelio de Lucas...') y NO con un personaje participante
    dentro del pasaje bíblico.
    """
    norm_token = normalize(token).strip()
    text_norm = normalize(full_text)

    # 1. Patrón: Nombre + verbo de atribución narrativa / epistolar / relacional
    # Ej: "lucas senala", "pablo afirma", "pablo argumenta", "pablo concluye", "pablo exhorta", "pablo ensena"
    verb_pat = (
        r"\b" + re.escape(norm_token) + r"\s+"
        r"(?:senala|señala|menciona|relata|narra|describe|registra|presenta|indica|anade|añade|"
        r"observa|enfatiza|resalta|aclara|concluye|especifica|testifica|cuenta|"
        r"recuerda|destaca|explica|subraya|afirma|argumenta|pregunta|exhorta|advierte|"
        r"compara|contrasta|ensena|enseña|establece|declara|expone|escribe|saluda|recomienda)\b"
    )
    if re.search(verb_pat, text_norm):
        return True

    # 2. Patrón: Prefijo de fuente / narración + Nombre
    # Ej: "segun lucas", "segun expone pablo", "conforme a lucas", "de acuerdo con lucas", "como senala lucas"
    source_prefix_pat = (
        r"\b(?:(?:segun|según|como)\s+(?:senala|señala|relata|registra|menciona|narra|indica|describe|subraya|destaca|dice|argumenta|concluye|ensena|enseña|escribe|declara|advierte|expone|presenta)\s+|"
        r"(?:segun|según|conforme\s+a|de\s+acuerdo\s+con)\s+)"
        + re.escape(norm_token) + r"\b"
    )
    if re.search(source_prefix_pat, text_norm):
        return True

    # 3. Patrón: Expresión de documento / evangelio / relato + Nombre
    # Ej: "evangelio de lucas", "evangelio segun lucas", "relato de lucas", "narracion de lucas", "texto de lucas"
    doc_prefix_pat = (
        r"\b(?:evangelio\s+(?:de|segun|según)|relato\s+de|narracion\s+de|narración\s+de|texto\s+de|libro\s+de|carta\s+de|epistola\s+de|epístola\s+de|escrito\s+de|argumento\s+de)\s+"
        + re.escape(norm_token) + r"\b"
    )
    if re.search(doc_prefix_pat, text_norm):
        return True

    return False


def is_biblical_place_usage(token: str, full_text: str) -> bool:
    """
    Determina si un token que coincide con un topónimo de BIBLE_PLACES está siendo utilizado
    como lugar geográfico real o como sustantivo común homógrafo (ej: 'la rama de la vid' vs ciudad 'Ramá').
    """
    norm_token = normalize(token).strip()

    # Si no es un término homógrafo conocido, se acepta como lugar bíblico
    if norm_token != "rama":
        return True

    text_norm = normalize(full_text)
    raw_lower = full_text.lower()

    # 1. Patrones claros de uso locativo / geográfico
    # Ej: "en Rama", "a Ramá", "de Ramá", "desde Ramá", "hacia Ramá", "ciudad de Ramá", "tierra de Ramá"
    locative_pattern = r"\b(?:en|a|de|desde|hacia|hasta|por|ciudad\s+de|tierra\s+de|monte\s+de|montes\s+de)\s+ram[aá]\b"
    if re.search(locative_pattern, raw_lower):
        return True

    # Si aparece explícitamente acentuado como "Ramá" o "ramá" y no está precedido por determinantes botánicos
    if "ramá" in raw_lower:
        if not re.search(r"\b(?:la|una|cada|esta|aquella|las|estas|otra|ninguna)\s+ramá\b", raw_lower):
            return True

    # 2. Patrones claros de sustantivo botánico / vegetal común
    # Ej: "la rama", "una rama", "cada rama", "las ramas", "rama de la vid", "rama del arbol", "fruto de la rama", "ramas del olivo"
    common_botanical_pattern = (
        r"\b(?:la|una|cada|esta|aquella|las|estas|otra|ninguna)\s+ramas?\b|"
        r"\bramas?\s+(?:de|del|de\s+la|de\s+las|seca|secas|verde|verdes|unida|unidas|cortada|cortadas|injertada|injertadas|desgajada|desgajadas)\b|"
        r"\b(?:fruto|hojas?|injerto|injertada|vid|arbol|olivo|raiz|olivo\s+silvestre)\s+(?:de\s+la|de\s+las|de\s+una)?\s*ramas?\b|"
        r"\bramas?\s+del\s+olivo\b"
    )
    if re.search(common_botanical_pattern, text_norm):
        return False

    return False


def is_biblical_person_usage(token: str, full_text: str) -> bool:
    """
    Determina si un token que coincide con una entrada de BIBLE_PERSONAJES está siendo utilizado
    como personaje bíblico real o como sustantivo/verbo común homógrafo (ej: 'la mesa compartida' vs rey 'Mesa').
    """
    norm_token = normalize(token).strip()

    if norm_token != "mesa":
        return True

    text_norm = normalize(full_text)
    raw_lower = full_text.lower()

    # 1. Patrones claros de uso como personaje bíblico real (Rey Mesa de Moab)
    # Ej: "Mesa rey de Moab", "rey Mesa", "el rey Mesa", "Mesa, rey"
    person_pattern = (
        r"\b(?:el\s+)?rey\s+mesa\b|"
        r"\bmesa\s*,?\s*(?:rey\s+de\s+moab|el\s+moabita|moabita)\b"
    )
    if re.search(person_pattern, raw_lower):
        return True

    # 2. Patrones claros de sustantivo común (mesa como mueble o acto de compartir comida)
    # Ej: "la mesa", "una mesa", "mesa compartida", "a la mesa", "en la mesa", "sentados a la mesa", "comer a la mesa"
    common_noun_pattern = (
        r"\b(?:la|una|esta|aquella|las|estas|cada|toda|otra|de\s+la|a\s+la|en\s+la|de\s+una|a\s+una|en\s+una)\s+mesas?\b|"
        r"\bmesas?\s+(?:compartida|comun|puesta|servida|del\s+senor|de\s+los\s+senores|de\s+los\s+cambistas|de\s+dinero)\b|"
        r"\b(?:sentar\w*|sentad\w*|com\w*|serv\w*|reclin\w*|particip\w*|acerc\w*)\s+(?:a\s+la|a\s+una|en\s+la|en\s+una)?\s*mesas?\b|"
        r"\bmesas?\s+con\s+(?:otras\s+personas|creyentes|gentiles|judios|discipulos)\b"
    )
    if re.search(common_noun_pattern, text_norm):
        return False

    # Si aparece "mesa" en minúscula en el texto sin contexto de rey Mesa
    if "mesa" in raw_lower:
        return False

    return True


def resolve_implicit_speaker(
    entity_name: str,
    passage_norm: str,
    verse_map: dict[int, str],
    start_verse: int,
    characters: list[str],
    book_key: str = "",
    category: str = "",
    eligible_modes: list[str] | None = None
) -> bool:
    """Resuelve contextualmente si entity_name es el hablante/orador en primera persona del pasaje."""
    if not verse_map:
        return False

    passage_words = set(passage_norm.split())
    has_1st_person = bool(passage_words & FIRST_PERSON_DISCOURSE_MARKERS) or any(
        m in passage_norm for m in [
            "dios nuestro", "dios mio", "nuestro dios", "de mi", "a mi", "conmigo",
            "en mi", "por mi", "ante mi", "sobre mi", "hacia mi", "acerca de mi",
            "enviado por mi", "cree en mi", "venid a mi"
        ]
    )
    if not has_1st_person:
        return False

    norm_entity = normalize(entity_name).strip()
    norm_chars = {normalize(c).strip() for c in (characters or [])}

    # 1. Comprobar versículos anteriores presentes en verse_map desde el inicio del capítulo
    # Busca retrospectivamente el orador explícito más reciente introducido en el capítulo
    candidate_speakers = set()
    for v_num in range(start_verse - 1, 0, -1):
        if v_num not in verse_map:
            continue
        v_norm = normalize(verse_map[v_num])
        v_words = set(v_norm.split())

        speakers_in_v = set()
        for p in BIBLE_PERSONAJES:
            if p in v_words:
                speech_patterns = (
                    [f"{p} {v}" for v in SPEECH_PRAYER_VERBS] +
                    [f"{v} {p}" for v in SPEECH_PRAYER_VERBS] +
                    [
                        f"{p} les dijo", f"{p} le dijo", f"{p} pues dijo", f"{p} entonces dijo",
                        f"{p} respondiendo", f"{p} diciendo", f"{p} extendiendo la mano",
                        f"{p} comenzo su defensa", f"{p} comenzo a hablar", f"{p} tomo la palabra"
                    ]
                )
                if any(pat in v_norm for pat in speech_patterns):
                    speakers_in_v.add(p)
                elif any(verb in v_words for verb in SPEECH_PRAYER_VERBS) or "diciendo" in v_words or "oracion" in v_words or "defensa" in v_words:
                    if norm_chars and p in norm_chars:
                        speakers_in_v.add(p)
        if speakers_in_v:
            candidate_speakers = speakers_in_v
            break

    if candidate_speakers == {norm_entity}:
        return True
    if len(candidate_speakers) > 1 and norm_entity not in candidate_speakers:
        return False

    # 2. Continuidad discursiva en discursos y palabras de Jesús (Evangelios: Mateo, Marcos, Lucas, Juan)
    # En discursos continuos largos (ej. Juan 14-16, Mateo 5-7, etc.), Jesús habla en primera persona
    # sin repetir 'Jesús dijo' en cada segmento de versículos.
    is_gospel_book = book_key in {"matthew", "mark", "luke", "john", "mateo", "marcos", "lucas", "juan"}
    is_jesus_discourse = (
        category == "JESUS_PALABRAS"
        or (eligible_modes and "JESUS_PALABRAS" in eligible_modes)
        or (norm_entity == "jesus" and ("jesus" in norm_chars or not characters))
    )
    if is_gospel_book and norm_entity == "jesus" and is_jesus_discourse:
        # Verificar que no exista en el pasaje un orador explícito en conflicto (ej: 'Pedro dijo:', 'Pilato dijo:')
        competing_speakers = set()
        for p in BIBLE_PERSONAJES:
            if p != "jesus" and p in passage_words:
                if any(f"{p} {verb}" in passage_norm for verb in SPEECH_PRAYER_VERBS) or any(f"{verb} {p}" in passage_norm for verb in SPEECH_PRAYER_VERBS):
                    competing_speakers.add(p)
        if not competing_speakers:
            return True

    # 3. Narración autobiográfica del autor titular del libro (ej. Esdras en el libro de Esdras)
    # Solo aplicable cuando la entidad coincide con el autor titular del libro y no hay conflicto
    is_titular_author = (norm_entity == book_key or norm_entity in {"esdras", "nehemias"} and book_key in {"ezra", "nehemiah", "esdras"})
    if is_titular_author and not candidate_speakers:
        full_ch_text = " ".join(verse_map.values())
        full_ch_norm = normalize(full_ch_text)
        full_ch_words = set(full_ch_norm.split())
        has_ch_1st_person = bool(full_ch_words & {"yo", "mi", "me", "dije", "nosotros", "nuestro"})
        if has_ch_1st_person:
            return True

    return False

# Equivalencias semánticas y de dimensiones
SYNONYMS = {
    "longitud": "largo",
    "anchura": "ancho",
    "altura": "alto",
    "largo": "longitud",
    "ancho": "anchura",
    "alto": "altura",
    "arameo": "padan-aram",
    "aramea": "padan-aram",
    "nilo": "rio",
    "rio": "nilo",
    "rebanos": "ovejas",
    "rebaño": "ovejas",
    "rebaños": "ovejas",
    "ganados": "vacas",
    "ganado": "vacas",
    "ovejas": "rebanos",
    "vacas": "ganados",
    "dios": "jehova",
    "jehova": "dios",
    "sacerdote": "sacerdotes",
    "sumo sacerdote": "sacerdote",
    "decimo": "diezmo",
    "diezmo": "decimo",
    "decima": "diezmo",
    "diezmos": "decimo",
    "animal": "ganado",
    "ganado": "animal",
    "miriam": "maria",
    "maria": "miriam",
    "sihon": "sehon",
    "sehon": "sihon",
    "combatientes": "pelearon",
    "pelearon": "combatientes",
    "otoniel": "otniel",
    "otniel": "otoniel",
    "suerte": "sorteo",
    "suertes": "sorteo",
    "sorteo": "suerte",
    "sorteada": "suerte",
    "sorteadas": "suerte",
    "morase": "vivian",
    "moraban": "vivian",
    "morar": "vivir",
    "habitaban": "vivian",
    "habitar": "vivir",
    "posesion": "heredad",
    "heredad": "posesion",
    "alianza": "pacto",
    "pacto": "alianza",
    "batalla": "guerra",
    "guerra": "batalla",
    "combatir": "pelear",
    "pelear": "combatir",
    "israelitas": "israel",
    "extranjeros": "extranjero",
    "forasteros": "extranjero",
    "forastero": "extranjero",
    "sepulcro": "sepultado",
    "sepultura": "sepultado",
    "enterrado": "sepultado",
    "enterraron": "sepultaron",
    "sepultaron": "enterraron",
    "testimonio": "testigo",
    "testigo": "testimonio",
    "piedras": "piedra",
    "piedra": "piedras",
    "carros": "carro",
    "carro": "carros",
    "bosque": "boscosa",
    "boscosa": "bosque",
    "monte": "montana",
    "montana": "monte",
    "montanosa": "monte",
    # Gentilicios bíblicos y equivalencias tribales
    "benjamin": "benjamita",
    "benjamita": "benjamin",
    "benjamitas": "benjamin",
    "efrain": "efraimita",
    "efraimita": "efrain",
    "efraimitas": "efrain",
    "galaad": "galaadita",
    "galaadita": "galaad",
    "galaaditas": "galaad",
    "dan": "danita",
    "danita": "dan",
    "danitas": "dan",
    "moab": "moabita",
    "moabita": "moab",
    "moabitas": "moab",
    "amon": "amonita",
    "amonita": "amon",
    "amonitas": "amon",
    "filistea": "filisteos",
    "filisteo": "filistea",
    "filisteos": "filistea",
    "levi": "levita",
    "levita": "levi",
    "levitas": "levi",
    "canaan": "cananeo",
    "cananeo": "canaan",
    "cananeos": "canaan",
    "cananeas": "canaan",
    "israel": "israelita",
    "israelita": "israel",
    "israelitas": "israel",
    "jebus": "jebuseos",
    "jebuseo": "jebus",
    "jebuseos": "jebus",
    "amorreo": "amorreos",
    "amorreos": "amorreo",
    "heteo": "heteos",
    "heteos": "heteo",
    "heveo": "heveos",
    "heveos": "heveo",
    "ferezeo": "ferezeos",
    "ferezeos": "ferezeo",
    "gergeseo": "gergeseos",
    "gergeseos": "gergeseo",
    "geteo": "gat",
    "geteos": "gat",
    "gabaonita": "gabaon",
    "gabaonitas": "gabaon",
    "arameo": "aram",
    "arameos": "aram",
    "sirio": "siria",
    "sirios": "siria",
    "amalec": "amalecita",
    "amalecita": "amalec",
    "amalecitas": "amalec",
    "hitita": "heteo",
    "hititas": "heteos",
    "ziba": "siba",
    "siba": "ziba",
    "silonita": "silo",
    "silonitas": "silo",
    "silo": "silonita",
    "sidonio": "sidon",
    "sidonios": "sidon",
    "sidonia": "sidon",
    "sidonias": "sidon",
    "tirio": "tiro",
    "tirios": "tiro",
    "tesbita": "tisbe",
    "tesbitas": "tisbe",
    "sunamita": "sunem",
    "sunamitas": "sunem",
    "sunem": "sunamita",
    "asirio": "asiria",
    "asirios": "asiria",
    "babilonio": "babilonia",
    "babilonios": "babilonia",
    "caldeo": "caldea",
    "caldeos": "caldea",
    "samaritano": "samaria",
    "samaritanos": "samaria",
    "uzias": "azarias",
    "uzías": "azarias",
    "azarias": "uzias",
    "azarías": "uzias",
    "ornan": "arauna",
    "ornán": "arauna",
    "arauna": "ornan",
    "merib-baal": "mefi-boset",
    "meribbaal": "mefiboset",
    "mefi-boset": "merib-baal",
    "mefiboset": "merib-baal",
    "hacmonita": "hacmoni",
    "hacmonitas": "hacmoni",
    "abram": "abraham",
    "abraham": "abram",
    "isbaal": "is-boset",
    "is-boset": "isbaal",
    "libio": "libia",
    "libios": "libia",
    "etiope": "etiopia",
    "etiopes": "etiopia",
    "etíope": "etiopia",
    "etíopes": "etiopia",
    "suquieno": "suquienos",
    "suquienos": "suquieno",
    # Redención y parentesco bíblico
    "suegra": "noemi",
    "noemi": "suegra",
    "redentor": "pariente",
    "pariente": "redentor",
    "redentores": "parientes",
    "parientes": "redentores",
    "redencion": "rescate",
    "rescate": "redencion",
    "redimir": "rescatar",
    "rescatar": "redimir",
}

# Componentes de números cardinales en español
SPANISH_HUNDREDS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500, "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}

SPANISH_TENS = {
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}

SPANISH_CARDINAL_UNITS = {
    "cero": 0, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}

SPANISH_ORDINALS = {
    "primero": 1, "primer": 1, "primera": 1,
    "segundo": 2, "segunda": 2,
    "tercero": 3, "tercer": 3, "tercera": 3, "tercia": 3,
    "cuarto": 4, "cuarta": 4,
    "quinto": 5, "quinta": 5,
    "sexto": 6, "sexta": 6,
    "septimo": 7, "septima": 7,
    "octavo": 8, "octava": 8,
    "noveno": 9, "novena": 9,
    "decimo": 10, "decima": 10,
}

SPANISH_UNITS = {**SPANISH_CARDINAL_UNITS, **SPANISH_ORDINALS}

ORDINAL_CONTEXT_WORDS = {
    "ano", "anos", "mes", "meses", "dia", "dias", "parte", "partes",
    "porcion", "porciones", "vez", "veces", "generacion", "generaciones",
    "hijo", "hijos", "lugar", "lugares", "grado", "grados", "hora", "horas"
}

SPANISH_ONE_WORDS = {"uno", "un", "una"}

ALL_NUM_WORDS = set(SPANISH_HUNDREDS.keys()) | set(SPANISH_TENS.keys()) | set(SPANISH_UNITS.keys()) | SPANISH_ONE_WORDS | {"y", "mil"}


def normalize(value: str) -> str:
    """Normaliza texto para comparación insensible a tildes, mayúsculas, guiones y signos."""
    if not value:
        return ""
    value = unicodedata.normalize("NFD", str(value).casefold())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("bet-el", "betel").replace("beer-seba", "beerseba").replace("padan-aram", "padanaram")
    value = value.replace("cades-barnea", "cadesbarnea").replace("kibrot-hataava", "kibrothataava")
    value = re.sub(r"[^a-z0-9ñ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def significant_tokens(value: str) -> list[str]:
    """Extrae palabras clave significativas omitiendo stopwords."""
    return [t for t in normalize(value).split() if len(t) >= 3 and t not in STOPWORDS]


def token_matches_text(token: str, text_norm: str) -> bool:
    """Comprueba si un token coincide con el texto normalizado por coincidencia exacta, plural/singular o sinonimia bíblica."""
    if not token or not text_norm:
        return False
    if token in text_norm:
        return True
    if token in SYNONYMS and SYNONYMS[token] in text_norm:
        return True
    # Plural -> Singular (español)
    if len(token) > 4 and token.endswith("es") and token[:-2] in text_norm:
        return True
    if len(token) > 3 and token.endswith("s") and token[:-1] in text_norm:
        return True
    # Singular -> Plural (español)
    if len(token) > 3 and (token + "s") in text_norm:
        return True
    if len(token) > 3 and (token + "es") in text_norm:
        return True
    return False


BIBLICAL_PERSON_ALIASES: dict[str, set[str]] = {
    "cefas": {"pedro"},
    "pedro": {"cefas"},
}


def person_token_matches_text(entity: str, passage_norm: str) -> bool:
    """
    Comprueba si una entidad/personaje bíblico coincide con el texto normalizado,
    probando coincidencia directa o sus alias canónicos seguros (ej: Cefas <-> Pedro).
    Nota: No mapea 'simon' aislado automáticamente a Pedro.
    """
    if not entity or not passage_norm:
        return False
    norm_e = normalize(entity).strip()
    norm_p = normalize(passage_norm)
    if token_matches_text(norm_e, norm_p):
        return True
    aliases = BIBLICAL_PERSON_ALIASES.get(norm_e, set())
    for alias in aliases:
        if token_matches_text(alias, norm_p):
            return True
    return False


def detect_book_key(spec: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Detecta la clave de configuración del libro a partir de las preguntas."""
    questions = spec if isinstance(spec, list) else spec.get("questions", [])
    if questions:
        first_book = normalize(str(questions[0].get("book", "")))
        for k, cfg in BOOK_CONFIGS.items():
            if first_book in cfg["aliases"]:
                return k
    return "genesis"


def _eval_sub_1000(tokens: list[str], is_quantitative: bool = False) -> list[int]:
    """Evalúa un grupo de palabras numéricas menor a 1000 separando adecuadamente secuencias."""
    results: list[int] = []
    val = 0
    i = 0
    while i < len(tokens):
        w = tokens[i]
        if w in SPANISH_HUNDREDS:
            if val > 0:
                results.append(val)
                val = 0
            val += SPANISH_HUNDREDS[w]
            i += 1
        elif w in SPANISH_TENS:
            if val > 0 and val % 100 != 0:
                results.append(val)
                val = 0
            val += SPANISH_TENS[w]
            i += 1
            if i < len(tokens) and tokens[i] == "y" and i + 1 < len(tokens) and (tokens[i + 1] in SPANISH_UNITS or tokens[i + 1] in SPANISH_ONE_WORDS):
                u_val = SPANISH_UNITS.get(tokens[i + 1], 1)
                val += u_val
                i += 2
        elif w in SPANISH_CARDINAL_UNITS:
            if val > 0 and val % 100 != 0:
                results.append(val)
                val = 0
            val += SPANISH_CARDINAL_UNITS[w]
            results.append(val)
            val = 0
            i += 1
        elif w in SPANISH_ORDINALS:
            has_ordinal_unit_context = (
                is_quantitative
                or (i + 1 < len(tokens) and tokens[i + 1] in ORDINAL_CONTEXT_WORDS)
                or (i > 0 and tokens[i - 1] in ORDINAL_CONTEXT_WORDS)
            )
            if has_ordinal_unit_context:
                if val > 0 and val % 100 != 0:
                    results.append(val)
                    val = 0
                val += SPANISH_ORDINALS[w]
                results.append(val)
                val = 0
            i += 1
        elif w in SPANISH_ONE_WORDS:
            # Reconocer 'un/una' en números compuestos (ej. 'seiscientos un', 'ciento un')
            if val > 0 and val % 100 == 0:
                val += 1
                i += 1
            elif w == "uno" and is_quantitative:
                if val > 0:
                    results.append(val)
                    val = 0
                results.append(1)
                i += 1
            elif is_quantitative:
                if val > 0:
                    results.append(val)
                    val = 0
                results.append(1)
                i += 1
            else:
                i += 1
        else:
            i += 1
    if val > 0:
        results.append(val)
    return results


def _eval_number_tokens(tokens: list[str], is_quantitative: bool = False) -> list[int]:
    """Evalúa una secuencia contigua de palabras numéricas en español."""
    if not tokens:
        return []
    if "mil" in tokens:
        mil_indices = [i for i, w in enumerate(tokens) if w == "mil"]
        if len(mil_indices) > 1:
            results: list[int] = []
            last_end = 0
            for k in range(len(mil_indices)):
                m_idx = mil_indices[k]
                if k + 1 < len(mil_indices):
                    next_m_idx = mil_indices[k + 1]
                    sub = tokens[m_idx + 1: next_m_idx]
                    if "y" in sub:
                        y_pos = m_idx + 1 + sub.index("y")
                        chunk = tokens[last_end:y_pos]
                        results.extend(_eval_number_tokens(chunk, is_quantitative=is_quantitative))
                        last_end = y_pos + 1
                    else:
                        chunk = tokens[last_end: m_idx + 1]
                        results.extend(_eval_number_tokens(chunk, is_quantitative=is_quantitative))
                        last_end = m_idx + 1
                else:
                    chunk = tokens[last_end:]
                    results.extend(_eval_number_tokens(chunk, is_quantitative=is_quantitative))
            return results

        mil_idx = tokens.index("mil")
        th_tokens = tokens[:mil_idx]
        rem_tokens = tokens[mil_idx + 1:]
        th_vals = _eval_sub_1000(th_tokens, is_quantitative=True) if th_tokens else [1]
        rem_vals = _eval_sub_1000(rem_tokens, is_quantitative=True) if rem_tokens else [0]
        th_val = th_vals[-1] if th_vals else 1
        rem_val = rem_vals[0] if rem_vals else 0
        compound = th_val * 1000 + rem_val
        res = [compound]
        if len(th_vals) > 1:
            res = th_vals[:-1] + res
        if len(rem_vals) > 1:
            res = res + rem_vals[1:]
        return res
    return _eval_sub_1000(tokens, is_quantitative=is_quantitative)


def extract_numbers(text: str, is_quantitative_context: bool = False) -> list[int]:
    """Extrae números enteros respetando la gramática numérica en español y construcciones compuestas."""
    raw_text = str(text)
    # Limpiar citas de capítulos/versículos
    cleaned_digits_text = re.sub(r"\b\d+\s*:\s*\d+(?:-\d+)?\b", " ", raw_text)
    # Colapsar millares con punto, coma o espacio (ej. '42.360', '42,360', '42 360', '601 730', '1.000.000' -> '42360', '601730')
    cleaned_digits_text = re.sub(
        r"\b\d{1,3}(?:[.,\s]\d{3})+\b",
        lambda m: re.sub(r"[.,\s]", "", m.group(0)),
        cleaned_digits_text
    )
    cleaned_norm = normalize(cleaned_digits_text)
    numbers: list[int] = []

    # 1. Dígitos directos
    for m in re.finditer(r"\b\d+\b", cleaned_norm):
        try:
            numbers.append(int(m.group(0)))
        except ValueError:
            pass

    # 2. Contextos especiales de supresión de 'un/una' no cuantitativo
    is_fraction = bool(re.search(r"\b(?:un|una)\s+(?:mitad|tercia|tercera|tercio|cuarta|cuarto|quinta|quinto|sexta|sexto|septima|septimo|octava|octavo|novena|noveno|decima|decimo)\b", cleaned_norm))
    is_distributive = bool(re.search(r"\b(?:un|una)\s+(?:para|por|de)\b.*\b(?:otr[oa])\b", cleaned_norm))
    is_qualitative_period = bool(re.search(r"\b(?:un|una)\s+(?:ano|dia|tiempo|periodo|semana)\s+de\s+(?:reposo|jubileo|gracia|luto|fiesta|holocausto|expiacion)", cleaned_norm))

    # 3. Diezmo en contexto de proporción, fracción, vara o conteo
    if re.search(r"\b(?:diezmo|diezmos)\b", cleaned_norm):
        if is_quantitative_context or re.search(r"\b(?:cada|contar|vara|pasa|animal|porcion|parte|uno de cada|decim[oa]|fraccion|proporcion)\b", cleaned_norm):
            numbers.append(10)

    # 4. División por mitad / dos partes
    if re.search(r"\b(?:por\s+mitad|en\s+mitad|mitades)\b", cleaned_norm):
        numbers.append(2)

    # 5. Palabras numéricas compuestas (ej. 'seiscientos un mil setecientos treinta' -> 601730)
    words = cleaned_norm.split()
    current_num_tokens = []
    for idx, w in enumerate(words):
        if w in {"un", "una"}:
            prev_w = words[idx - 1] if idx > 0 else ""
            next_w = words[idx + 1] if idx + 1 < len(words) else ""
            is_part_of_compound = (next_w == "mil") or (prev_w in SPANISH_HUNDREDS) or (prev_w == "y")
            if is_part_of_compound:
                current_num_tokens.append(w)
            elif is_quantitative_context and not (is_qualitative_period or is_distributive or is_fraction):
                current_num_tokens.append(w)
            else:
                if current_num_tokens:
                    numbers.extend(_eval_number_tokens(current_num_tokens, is_quantitative=is_quantitative_context))
                    current_num_tokens = []
        elif w in ALL_NUM_WORDS:
            current_num_tokens.append(w)
        else:
            if current_num_tokens:
                numbers.extend(_eval_number_tokens(current_num_tokens, is_quantitative=is_quantitative_context))
                current_num_tokens = []
    if current_num_tokens:
        numbers.extend(_eval_number_tokens(current_num_tokens, is_quantitative=is_quantitative_context))

    # 6. Captura de ordinales y fracciones si están presentes
    for w in words:
        if w in SPANISH_UNITS and SPANISH_UNITS[w] > 1:
            numbers.append(SPANISH_UNITS[w])

    return sorted(set(numbers))


def parse_additional_ref(ref_str: str, default_chapter: int) -> tuple[int, list[int]]:
    """Extrae capítulo y versículos de una referencia adicional multilibro."""
    m = re.search(r"(?:[A-Za-zÁÉÍÓÚáéíóúñÑ]+\s+)?(?:(\d+)[:.])?(\d+)(?:-(\d+))?", str(ref_str), re.IGNORECASE)
    if not m:
        return default_chapter, []
    ch = int(m.group(1)) if m.group(1) else default_chapter
    start_v = int(m.group(2))
    end_v = int(m.group(3)) if m.group(3) else start_v
    return ch, list(range(start_v, end_v + 1))


def extract_verses_robust(payload: Any) -> dict[int, str]:
    """Extrae versículos indexados por número de forma determinista."""
    verse_map: dict[int, str] = {}
    if not isinstance(payload, dict):
        return verse_map

    verses_list = payload.get("verses")
    if not verses_list and isinstance(payload.get("data"), dict):
        verses_list = payload["data"].get("verses")

    if isinstance(verses_list, list) and len(verses_list) > 0:
        for idx, item in enumerate(verses_list, start=1):
            if isinstance(item, dict):
                v_num = _verse_number_from_node(item) or idx
                text = item.get("text") or item.get("verse") or ""
                if isinstance(text, str) and text.strip():
                    verse_map[v_num] = text.strip()
        if verse_map:
            return verse_map

    verses = extract_verses(payload)
    for v in verses:
        try:
            num = int(v.get("verse_number", 0))
            txt = str(v.get("text", "")).strip()
            if num > 0 and txt:
                verse_map[num] = txt
        except (ValueError, TypeError):
            continue
    return verse_map


def split_composite_answer(answer_str: str) -> list[str]:
    """Descompone respuestas compuestas unidas por comas, 'y', 'e', preservando construcciones correlativas."""
    if re.search(r"\b(?:un|una|uno)\b.*\b(?:y|e)\s+otr[oa]\b", answer_str, re.IGNORECASE):
        return [answer_str.strip()]
    raw = re.split(r"[,;]|\s+y\s+|\s+e\s+", answer_str)
    parts = [p.strip() for p in raw if p.strip()]
    return parts if len(parts) > 1 else [answer_str.strip()]


def evaluate_question(
    q: dict[str, Any],
    verse_map: dict[int, str],
    book_key: str = "genesis",
) -> dict[str, Any]:
    """Evalúa una pregunta contra el pasaje en memoria aplicando los 17 controles rigurosamente."""
    book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])

    qid = str(q.get("id", "")).strip()
    book = str(q.get("book", "")).strip()
    chapter = int(q.get("chapter", 0))
    start = int(q.get("verse_start", 0))
    end = int(q.get("verse_end", start))
    ref_str = str(q.get("reference", "")).strip()

    prompt = str(q.get("question", "")).strip()
    opcion_a = str(q.get("opcion_a", "")).strip()
    opcion_b = str(q.get("opcion_b", "")).strip()
    opcion_c = str(q.get("opcion_c", "")).strip()
    opcion_d = str(q.get("opcion_d", "")).strip()
    correct_opt = str(q.get("correct_option", "")).strip().upper()
    correct_ans = str(q.get("correct_answer", "")).strip()
    explanation = str(q.get("explanation", "")).strip()
    q_type = str(q.get("question_type", "MULTIPLE_CHOICE")).strip().upper()
    is_true_false = q_type in {"TRUE_FALSE", "VERDADERO_FALSO", "TF", "VF"}

    characters = q.get("characters", [])
    if isinstance(characters, str):
        characters = [c.strip() for c in characters.split(";") if c.strip()]

    additional_refs = q.get("additional_references", [])
    if isinstance(additional_refs, str):
        additional_refs = [r.strip() for r in additional_refs.split(";") if r.strip()]

    controls: dict[str, str] = {}
    incidencias: list[str] = []
    correcciones_sugeridas: list[dict[str, Any]] = []

    # 1. Control Libro
    if normalize(book) in book_cfg["aliases"]:
        controls["control_libro"] = "PASS"
    else:
        controls["control_libro"] = "FAIL"
        incidencias.append(f"Libro no correspondiente: '{book}' (esperado '{book_cfg['canonical_name']}')")

    # 2. Control Capítulo
    if 1 <= chapter <= book_cfg["total_chapters"]:
        controls["control_capitulo"] = "PASS"
    else:
        controls["control_capitulo"] = "FAIL"
        incidencias.append(f"Capítulo fuera de rango 1-{book_cfg['total_chapters']}: {chapter}")

    # 3. Control Versículo Inicio
    if start >= 1:
        controls["control_versiculo_inicio"] = "PASS"
    else:
        controls["control_versiculo_inicio"] = "FAIL"
        incidencias.append(f"Versículo inicio inválido: {start}")

    # 4. Control Versículo Fin
    if end >= start:
        controls["control_versiculo_fin"] = "PASS"
    else:
        controls["control_versiculo_fin"] = "FAIL"
        incidencias.append(f"Versículo fin ({end}) menor que inicio ({start})")

    # 5. Control Formato Referencia
    expected_ref_suffix = f"{chapter}:{start}" if start == end else f"{chapter}:{start}-{end}"
    if bool(re.search(r"[:\s]" + re.escape(expected_ref_suffix) + r"$", ref_str)) or (f"{chapter}:{start}" in ref_str):
        controls["control_referencia_formato"] = "PASS"
    else:
        controls["control_referencia_formato"] = "FAIL"
        incidencias.append(f"Referencia '{ref_str}' no coincide con capítulo {chapter} y versículos {start}-{end}")

    # 6. Control Existencia Referencia (rango principal + additional_references en el mismo capítulo)
    main_verses = list(range(start, end + 1)) if start <= end else [start]
    all_required_verses = list(main_verses)
    for add_ref in additional_refs:
        add_ch, add_v_list = parse_additional_ref(add_ref, chapter)
        if add_ch == chapter:
            all_required_verses.extend(add_v_list)

    all_required_verses_unique = sorted(set(all_required_verses))
    if verse_map and all(v in verse_map for v in all_required_verses_unique):
        controls["control_referencia_existencia"] = "PASS"
    else:
        if not verse_map:
            controls["control_referencia_existencia"] = "UNKNOWN"
            incidencias.append(f"Capítulo {chapter} no disponible temporalmente desde ApiBiblia (posible rate limit o error de red)")
        else:
            controls["control_referencia_existencia"] = "FAIL"
            missing_v = [v for v in all_required_verses_unique if v not in verse_map]
            incidencias.append(f"Versículos faltantes en el capítulo: {missing_v}")

    # Contexto cuantitativo o de proporción/fracción de la pregunta
    has_count_context = bool(re.search(
        r"¿?\s*cuant[oa]s?\b|\bcuant[oa]s?\b|\bnumero\s+de\b|\bcantidad\s+de\b|\btotal\s+de\b|\bcuantas?\s+veces\b|\bcontar\b|\bvara\b|\bdecim[oa]\b|\bdiezmo\b|\bque\s+parte\b|\bque\s+porcion\b|\bque\s+fraccion\b|\bfraccion\b|\bproporcion\b|\bporcentaje\b|\bmitad\b|\btercia\b|\btercera\b|\bcuarta\b|\bquinta\b|\bdecima\s+parte\b",
        normalize(prompt)
    ))

    # Construir pasaje integral en memoria
    passage = " ".join(verse_map.get(v, "") for v in all_required_verses_unique) if verse_map else ""
    passage_norm = normalize(passage)
    passage_nums = set(extract_numbers(passage, is_quantitative_context=has_count_context))
    passage_hash = hashlib.sha256(passage.encode("utf-8")).hexdigest() if controls["control_referencia_existencia"] == "PASS" else None

    # Si no hay pasaje disponible por fallo de API, todos los controles de texto son UNKNOWN
    if not verse_map:
        for c_name in (
            "control_soporte_pregunta", "control_opcion_a_correcta", "control_distractores_invalidos",
            "control_respuesta_coincide_a", "control_explicacion_compatible", "control_nombres_propios",
            "control_lugares", "control_numeros_cantidades", "control_relaciones_personajes",
            "control_rango_suficiente", "control_sin_ambiguedad"
        ):
            controls[c_name] = "UNKNOWN"
        return {
            "id": qid,
            "reference": ref_str,
            "chapter": chapter,
            "verse_start": start,
            "verse_end": end,
            "estado": "NO_CONCLUYENTE",
            "controles_superados": controls,
            "incidencias": incidencias,
            "correcciones_sugeridas": correcciones_sugeridas,
            "hash_sha256_pasaje": None,
            "source_text_persisted": False,
        }

    # 7. Control Soporte de Pregunta
    q_toks = significant_tokens(prompt)
    if not q_toks:
        controls["control_soporte_pregunta"] = "UNKNOWN"
    else:
        matching_q_toks = [t for t in q_toks if token_matches_text(t, passage_norm)]
        coverage_q = len(matching_q_toks) / len(q_toks)
        if coverage_q >= 0.15 or len(matching_q_toks) >= 1:
            controls["control_soporte_pregunta"] = "PASS"
        else:
            controls["control_soporte_pregunta"] = "UNKNOWN"

    # 8. Control Opción A Correcta
    parts_a = split_composite_answer(opcion_a)
    missing_parts = []
    for part in parts_a:
        part_toks = significant_tokens(part)
        part_norm = normalize(part)
        part_nums = extract_numbers(part, is_quantitative_context=has_count_context)

        if part_nums:
            nums_matched = all(n in passage_nums for n in part_nums)
            non_num_toks = [t for t in part_toks if not t.isdigit()]
            text_matched = True if not non_num_toks else any(token_matches_text(t, passage_norm) for t in non_num_toks)
            if nums_matched and text_matched:
                continue
            missing_parts.append(part)
        else:
            if part_norm and (
                part_norm in passage_norm
                or any(token_matches_text(t, passage_norm) for t in part_toks)
            ):
                continue
            missing_parts.append(part)

    if not missing_parts:
        controls["control_opcion_a_correcta"] = "PASS"
    else:
        opt_a_nums = extract_numbers(opcion_a, is_quantitative_context=has_count_context)
        conflicting_num = any(n not in passage_nums for n in opt_a_nums if opt_a_nums and passage_nums)
        if conflicting_num:
            controls["control_opcion_a_correcta"] = "FAIL"
            incidencias.append(f"Contradicción numérica objetiva en Opción A: {opt_a_nums} vs {sorted(passage_nums)}")
        else:
            controls["control_opcion_a_correcta"] = "UNKNOWN"

    # 9. Control Distractores Inválidos
    distractor_conflicts: list[str] = []
    distractors_to_check = [opcion_b] if is_true_false else [opcion_b, opcion_c, opcion_d]
    for d_text in distractors_to_check:
        d_norm = normalize(d_text)
        if not d_norm:
            distractor_conflicts.append("Distractor vacío")
            continue
        if d_norm == normalize(opcion_a):
            distractor_conflicts.append(f"Distractor idéntico a opción A: '{d_text}'")
            continue

        d_nums = extract_numbers(d_text, is_quantitative_context=has_count_context)
        opt_a_nums = extract_numbers(opcion_a, is_quantitative_context=has_count_context)
        if d_nums and opt_a_nums and set(d_nums) == passage_nums and set(opt_a_nums) != passage_nums:
            distractor_conflicts.append(f"Distractor con datos correctos frente a Opción A incorrecta: '{d_text}'")

    if is_true_false and (opcion_c.strip() or opcion_d.strip()):
        distractor_conflicts.append(f"Pregunta TRUE_FALSE contiene contenido en opcion_c u opcion_d ('{opcion_c}', '{opcion_d}')")

    if distractor_conflicts:
        controls["control_distractores_invalidos"] = "FAIL"
        incidencias.extend(distractor_conflicts)
    else:
        controls["control_distractores_invalidos"] = "PASS"

    # 10. Control Respuesta Coincide con Opción A
    ans_aligned = (correct_opt == "A") and (normalize(correct_ans) == normalize(opcion_a))
    if ans_aligned:
        controls["control_respuesta_coincide_a"] = "PASS"
    else:
        controls["control_respuesta_coincide_a"] = "FAIL"
        incidencias.append(f"Desalineación: correct_option='{correct_opt}', correct_answer='{correct_ans}', opcion_a='{opcion_a}'")
        correcciones_sugeridas.append({
            "id": qid,
            "campo": "correct_option / correct_answer",
            "valor_actual": f"{correct_opt} / {correct_ans}",
            "valor_recomendado": f"A / {opcion_a}",
            "motivo": "Alineación canónica con Opción A",
            "referencia": ref_str,
        })

    # 11. Control Explicación Compatible
    exp_cleaned = re.sub(r"\b(?:[A-Za-zÁÉÍÓÚáéíóúñÑ]+\s+)?\d+\s*:\s*\d+(?:-\d+)?\b", " ", explanation, flags=re.IGNORECASE)
    exp_toks = significant_tokens(exp_cleaned)
    if not exp_toks:
        controls["control_explicacion_compatible"] = "UNKNOWN"
    else:
        matching_exp_toks = [t for t in exp_toks if token_matches_text(t, passage_norm)]
        exp_coverage = len(matching_exp_toks) / len(exp_toks)
        exp_nums = extract_numbers(exp_cleaned, is_quantitative_context=has_count_context)
        conflicting_nums = [n for n in exp_nums if n not in passage_nums and n > 2]

        if conflicting_nums and controls["control_opcion_a_correcta"] == "FAIL":
            controls["control_explicacion_compatible"] = "FAIL"
            incidencias.append(f"La explicación contiene datos numéricos contradictorios: {conflicting_nums}")
        elif exp_coverage >= 0.12 or len(matching_exp_toks) >= 2:
            controls["control_explicacion_compatible"] = "PASS"
        else:
            controls["control_explicacion_compatible"] = "UNKNOWN"

    # 12. Control Nombres Propios
    entities_in_opt_a = set()
    for word in normalize(opcion_a).split():
        if word in BIBLE_PERSONAJES and is_biblical_person_usage(word, opcion_a):
            if is_locative_or_collective_entity(word, opcion_a, characters):
                continue
            if is_narrative_source_attribution(word, opcion_a, book_cfg):
                continue
            entities_in_opt_a.add(word)

    entities_in_prompt = set()
    for word in normalize(prompt).split():
        if word in BIBLE_PERSONAJES and is_biblical_person_usage(word, prompt):
            if is_locative_or_collective_entity(word, prompt, characters):
                continue
            if is_narrative_source_attribution(word, prompt, book_cfg):
                continue
            entities_in_prompt.add(word)

    if entities_in_opt_a:
        missing_entities = [
            n for n in entities_in_opt_a
            if not person_token_matches_text(n, passage_norm) and n not in entities_in_prompt
        ]
        if not missing_entities:
            controls["control_nombres_propios"] = "PASS"
        else:
            # Resolución anafórica / contextual / hablante implícito:
            context_resolved = []
            if verse_map:
                full_ch_text = " ".join(verse_map.values())
                full_ch_norm = normalize(full_ch_text)
                ANAPHORIC_MARKERS = [
                    "hombre", "aquel hombre", "este hombre", "el hombre",
                    "mujer", "aquella mujer", "esta mujer", "la mujer",
                    "varon", "aquel varon", "el varon",
                    "suegra", "suegro", "padre", "madre", "marido", "esposo", "esposa",
                    "hijo", "hija", "hermano", "hermana", "pariente", "tio", "tia",
                    "redentor", "rescatador"
                ]
                has_anaphora = any(m in passage_norm for m in ANAPHORIC_MARKERS)
                if has_anaphora:
                    for n in missing_entities:
                        if person_token_matches_text(n, full_ch_norm) and (not characters or any(n == normalize(c) for c in characters)):
                            context_resolved.append(n)

                # Resolución de hablante implícito en 1ª persona
                for n in missing_entities:
                    if n not in context_resolved and resolve_implicit_speaker(
                        n, passage_norm, verse_map, start, characters, book_key,
                        category=str(q.get("category", "")).strip(), eligible_modes=q.get("eligible_modes")
                    ):
                        context_resolved.append(n)

            unresolved = [n for n in missing_entities if n not in context_resolved]
            if not unresolved:
                controls["control_nombres_propios"] = "PASS"
            else:
                controls["control_nombres_propios"] = "FAIL"
                incidencias.append(f"Personaje bíblico en opción A no respaldado en el pasaje ni resuelto contextualmente: {unresolved}")
    elif entities_in_prompt:
        matching_prompt_ent = [
            n for n in entities_in_prompt
            if person_token_matches_text(n, passage_norm)
        ]
        if matching_prompt_ent:
            controls["control_nombres_propios"] = "PASS"
        else:
            controls["control_nombres_propios"] = "NOT_APPLICABLE" if not characters else "PASS"
    elif characters:
        matching_chars = [
            c for c in characters
            if person_token_matches_text(normalize(c), passage_norm)
        ]
        if matching_chars:
            controls["control_nombres_propios"] = "PASS"
        else:
            controls["control_nombres_propios"] = "NOT_APPLICABLE"
    else:
        controls["control_nombres_propios"] = "NOT_APPLICABLE"

    # 13. Control Lugares (con contextualización de marco geográfico ambiental e hidrográfico)
    opt_a_toks = {w for w in normalize(opcion_a).split() if w in BIBLE_PLACES and is_biblical_place_usage(w, opcion_a)}
    prompt_toks = {w for w in normalize(prompt).split() if w in BIBLE_PLACES and is_biblical_place_usage(w, prompt)}
    detected_places = opt_a_toks | prompt_toks
    ambient_places = book_cfg.get("ambient_places", set())

    if not detected_places:
        controls["control_lugares"] = "NOT_APPLICABLE"
    else:
        missing_places = []
        for pl in detected_places:
            if token_matches_text(pl, passage_norm):
                continue
            if pl == "nilo" and ("rio" in passage_norm or "aguas" in passage_norm):
                continue
            if pl in ambient_places and pl not in opt_a_toks:
                continue
            if pl in ambient_places and pl in opt_a_toks and not any(p in opt_a_toks for p in BIBLE_PLACES if p not in ambient_places):
                # Si el único lugar en opción A es el marco ambiental del libro
                continue
            missing_places.append(pl)

        if not missing_places:
            controls["control_lugares"] = "PASS"
        elif any(pl in opt_a_toks for pl in missing_places):
            controls["control_lugares"] = "FAIL"
            incidencias.append(f"Lugar en opción A no coincide con el pasaje: {missing_places}")
        else:
            controls["control_lugares"] = "UNKNOWN"

    # 14. Control Números y Cantidades
    opt_a_nums = extract_numbers(opcion_a, is_quantitative_context=has_count_context)
    prompt_nums = extract_numbers(prompt, is_quantitative_context=has_count_context)
    target_nums = set(opt_a_nums) | set(prompt_nums)

    if not target_nums:
        controls["control_numeros_cantidades"] = "NOT_APPLICABLE"
    else:
        composite_count = len(parts_a)
        prompt_nums_clean = [n for n in prompt_nums if n != composite_count]

        missing_opt_nums = [n for n in opt_a_nums if n not in passage_nums]
        missing_nums = [n for n in (set(opt_a_nums) | set(prompt_nums_clean)) if n not in passage_nums]
        if missing_opt_nums:
            if passage_nums:
                controls["control_numeros_cantidades"] = "FAIL"
                incidencias.append(f"Cantidad numérica en opción A ({missing_opt_nums}) no coincide con el pasaje ({sorted(passage_nums)})")
            elif has_count_context:
                controls["control_numeros_cantidades"] = "FAIL"
                incidencias.append(f"Pregunta cuantitativa requiere cantidad ({missing_opt_nums}) no hallada en el pasaje")
            else:
                # Pregunta cualitativa sin números en el pasaje
                resolved = True
                for n in missing_opt_nums:
                    if n in {2, 3}:
                        chars_in_passage = [c for c in characters if person_token_matches_text(normalize(c), passage_norm)]
                        if len(chars_in_passage) >= n:
                            continue
                    resolved = False
                    break
                if resolved:
                    controls["control_numeros_cantidades"] = "PASS"
                else:
                    controls["control_numeros_cantidades"] = "UNKNOWN"
        elif not missing_nums or all(n in passage_nums for n in opt_a_nums):
            controls["control_numeros_cantidades"] = "PASS"
        else:
            controls["control_numeros_cantidades"] = "UNKNOWN"

    # 15. Control Relaciones de Personajes
    kin_detected_stems = set()
    all_text_norm = normalize(f"{opcion_a} {prompt}")
    for stem, words in KINSHIP_STEMS.items():
        if any(w in all_text_norm.split() for w in words):
            kin_detected_stems.add(stem)

    is_comparative = bool(re.search(r"\b(?:como|semejante|compar[oa]|figura|imagen|metafora|alusion)\b", all_text_norm))

    if not kin_detected_stems:
        controls["control_relaciones_personajes"] = "NOT_APPLICABLE"
    else:
        missing_stems = []
        for stem in kin_detected_stems:
            words = KINSHIP_STEMS[stem]
            if not any(w in passage_norm.split() for w in words):
                if is_comparative and stem in {"padr", "hij"} and any(w in passage_norm.split() for w in ["hombre", "hijo", "hija", "padre", "madre"]):
                    continue
                missing_stems.append(stem)

        if not missing_stems:
            controls["control_relaciones_personajes"] = "PASS"
        elif is_comparative:
            controls["control_relaciones_personajes"] = "PASS" if any(w in passage_norm.split() for w in ["hijo", "hija", "padre", "madre", "hombre"]) else "UNKNOWN"
        elif any(any(w in normalize(opcion_a).split() for w in KINSHIP_STEMS[stem]) for stem in missing_stems):
            controls["control_relaciones_personajes"] = "FAIL"
            incidencias.append(f"Relación/parentesco en opción A no tiene respaldo en el pasaje: {missing_stems}")
        else:
            controls["control_relaciones_personajes"] = "UNKNOWN"

    # 16. Control Rango Suficiente
    evidence_missing_outside = []
    if controls["control_nombres_propios"] == "FAIL":
        evidence_missing_outside.append("personaje bíblico ausente")
    if controls["control_numeros_cantidades"] == "FAIL":
        evidence_missing_outside.append("cantidad numérica no hallada")
    if controls["control_lugares"] == "FAIL":
        evidence_missing_outside.append("lugar no hallado")

    if evidence_missing_outside:
        controls["control_rango_suficiente"] = "FAIL"
        incidencias.append(f"El rango versicular actual no contiene la evidencia requerida para: {', '.join(evidence_missing_outside)}")
    elif controls["control_opcion_a_correcta"] == "PASS" and controls["control_soporte_pregunta"] == "PASS":
        controls["control_rango_suficiente"] = "PASS"
    else:
        controls["control_rango_suficiente"] = "UNKNOWN"

    # 17. Control Sin Ambigüedad
    expected_unique = 2 if is_true_false else 4
    unique_options = len({normalize(x) for x in (opcion_a, opcion_b, opcion_c, opcion_d) if x}) == expected_unique
    if not unique_options:
        controls["control_sin_ambiguedad"] = "FAIL"
        incidencias.append("Existen opciones duplicadas o ambiguas")
    elif controls["control_distractores_invalidos"] == "PASS":
        controls["control_sin_ambiguedad"] = "PASS"
    else:
        controls["control_sin_ambiguedad"] = "UNKNOWN"

    # Clasificación final estricta
    has_fail = any(v == "FAIL" for v in controls.values())
    has_unknown = any(v == "UNKNOWN" for v in controls.values())

    if has_fail:
        estado = "REQUIERE_CORRECCION"
    elif has_unknown:
        estado = "NO_CONCLUYENTE"
    else:
        estado = "VERIFICADO"

    return {
        "id": qid,
        "reference": ref_str,
        "chapter": chapter,
        "verse_start": start,
        "verse_end": end,
        "estado": estado,
        "controles_superados": controls,
        "total_pass": sum(1 for v in controls.values() if v == "PASS"),
        "total_fail": sum(1 for v in controls.values() if v == "FAIL"),
        "total_unknown": sum(1 for v in controls.values() if v == "UNKNOWN"),
        "total_not_applicable": sum(1 for v in controls.values() if v == "NOT_APPLICABLE"),
        "total_controles": len(controls),
        "incidencias": incidencias,
        "correcciones_sugeridas": correcciones_sugeridas,
        "hash_sha256_pasaje": passage_hash,
        "source_text_persisted": False,
    }


def run_audit(
    spec: dict[str, Any] | list[dict[str, Any]],
    fetch_chapter_fn: Callable[[str, int], dict[int, str]],
    output_dir: Path,
    rate_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el pipeline completo de auditoría agrupando dinámicamente por capítulo."""
    if isinstance(spec, list):
        raw_questions = spec
    elif isinstance(spec, dict):
        raw_questions = spec.get("questions", [])
    else:
        raw_questions = []

    book_key = detect_book_key(spec)
    book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])
    canonical_book_name = book_cfg["canonical_name"]
    api_book_name = book_cfg["api_name"]

    # Agrupación dinámica por capítulo
    questions_by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for q in raw_questions:
        ch = int(q.get("chapter", 0))
        questions_by_chapter[ch].append(q)

    present_chapters = sorted(questions_by_chapter.keys())
    all_results: list[dict[str, Any]] = []
    correcciones_totales: list[dict[str, Any]] = []
    revision_manual: list[dict[str, Any]] = []
    controles_distribution: dict[str, dict[str, int]] = defaultdict(lambda: Counter())

    successful_fetches: list[int] = []
    failed_fetches: list[int] = []

    print(f"Libro canónico: {canonical_book_name} (API: {api_book_name})", flush=True)
    print(f"Preguntas a auditar: {len(raw_questions)}", flush=True)
    print(f"Capítulos detectados ({len(present_chapters)}): {present_chapters[:10]}...{present_chapters[-5:] if len(present_chapters)>10 else ''}", flush=True)

    for idx, chapter in enumerate(present_chapters, start=1):
        ch_questions = questions_by_chapter[chapter]
        print(f"[{idx}/{len(present_chapters)}] Auditando {canonical_book_name} {chapter} ({len(ch_questions)} preguntas)...", flush=True)
        verse_map = fetch_chapter_fn(api_book_name, chapter)

        if verse_map:
            successful_fetches.append(chapter)
        else:
            failed_fetches.append(chapter)

        for q in ch_questions:
            res = evaluate_question(q, verse_map, book_key=book_key)
            all_results.append(res)
            for c_name, c_state in res["controles_superados"].items():
                controles_distribution[c_name][c_state] += 1

            if res["correcciones_sugeridas"]:
                correcciones_totales.extend(res["correcciones_sugeridas"])
            if res["estado"] in {"REQUIERE_CORRECCION", "NO_CONCLUYENTE"}:
                revision_manual.append({
                    "id": res["id"],
                    "reference": res["reference"],
                    "estado": res["estado"],
                    "incidencias": res["incidencias"],
                    "controles_fallidos_o_dudosos": {k: v for k, v in res["controles_superados"].items() if v in {"FAIL", "UNKNOWN"}},
                    "correcciones_sugeridas": res["correcciones_sugeridas"],
                })

        if isinstance(verse_map, dict):
            verse_map.clear()
        del verse_map

    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = book_cfg.get("blocks", [])

    for start_ch, end_ch, filename in blocks:
        block_results = [r for r in all_results if start_ch <= r.get("chapter", 0) <= end_ch]
        block_payload = {
            "schema_version": f"quizbible-rvr1960-audit-block-v1",
            "book": canonical_book_name,
            "chapter_range": f"{start_ch:02d}-{end_ch:02d}",
            "questions_count": len(block_results),
            "verified_count": sum(1 for r in block_results if r["estado"] == "VERIFICADO"),
            "review_required_count": sum(1 for r in block_results if r["estado"] == "REQUIERE_CORRECCION"),
            "inconclusive_count": sum(1 for r in block_results if r["estado"] == "NO_CONCLUYENTE"),
            "source_text_persisted": False,
            "results": block_results,
        }
        (output_dir / filename).write_text(json.dumps(block_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    correcciones_payload = {
        "schema_version": "quizbible-audit-corrections-v1",
        "total_correcciones": len(correcciones_totales),
        "source_text_persisted": False,
        "correcciones": correcciones_totales,
    }
    (output_dir / "correcciones-aplicadas.json").write_text(json.dumps(correcciones_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    revision_payload = {
        "schema_version": "quizbible-manual-review-v1",
        "total_pendientes": len(revision_manual),
        "source_text_persisted": False,
        "pendientes": revision_manual,
    }
    (output_dir / "revision-manual-pendiente.json").write_text(json.dumps(revision_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    controles_stats = {
        c_name: {
            "PASS": counts.get("PASS", 0),
            "FAIL": counts.get("FAIL", 0),
            "UNKNOWN": counts.get("UNKNOWN", 0),
            "NOT_APPLICABLE": counts.get("NOT_APPLICABLE", 0),
        }
        for c_name, counts in controles_distribution.items()
    }

    total_q = len(all_results)
    verif_c = sum(1 for r in all_results if r["estado"] == "VERIFICADO")
    req_corr_c = sum(1 for r in all_results if r["estado"] == "REQUIERE_CORRECCION")
    inconc_c = sum(1 for r in all_results if r["estado"] == "NO_CONCLUYENTE")

    rm = rate_metrics or {}
    attempts_total = rm.get("http_request_attempts_total", len(present_chapters))
    rate_retries = rm.get("rate_limit_retries", 0)

    summary = {
        "schema_version": "quizbible-rvr1960-audit-summary-v1",
        "source": "ApiBiblia API RVR1960",
        "book": canonical_book_name,
        "total_questions": total_q,
        "chapters_present_in_bank": len(present_chapters),
        "successful_chapter_fetches": len(successful_fetches),
        "failed_chapter_fetches": len(failed_fetches),
        "failed_chapters": failed_fetches,
        "chapters_covered": len(successful_fetches),
        "textual_coverage_complete": (len(successful_fetches) == book_cfg["total_chapters"] and len(failed_fetches) == 0),
        "chapter_coverage_complete_1_max": present_chapters == list(range(1, book_cfg["total_chapters"] + 1)),
        "http_request_attempts_total": attempts_total,
        "rate_limit_retries": rate_retries,
        "verified_count": verif_c,
        "requires_correction_count": req_corr_c,
        "inconclusive_count": inconc_c,
        "verification_rate": round(verif_c / total_q * 100, 2) if total_q else 0.0,
        "controls_distribution": controles_stats,
        "source_text_persisted": False,
    }
    (output_dir / "resumen-general.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nAuditoría finalizada:", flush=True)
    print(f"- Libro: {canonical_book_name}", flush=True)
    print(f"- Total preguntas: {total_q}", flush=True)
    print(f"- VERIFICADO: {verif_c}", flush=True)
    print(f"- REQUIERE_CORRECCION: {req_corr_c}", flush=True)
    print(f"- NO_CONCLUYENTE: {inconc_c}", flush=True)
    print(f"- Capítulos obtenidos: {len(successful_fetches)}/{book_cfg['total_chapters']}", flush=True)
    print(f"- Cobertura textual completa: {summary['textual_coverage_complete']}", flush=True)
    print(f"- Texto bíblico persistido: False", flush=True)
    return summary


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Auditor bíblico semántico derivado contra RVR1960")
        parser.add_argument("--input", default="tools/bible_extractor/genesis-master-input.json", help="Archivo de entrada")
        parser.add_argument("--output-dir", default=None, help="Directorio de salidas derivadas")
        parser.add_argument("--version", default="RVR1960", help="Versión bíblica (RVR1960)")
        parser.add_argument("--offline-fixture", default=None, help="Archivo JSON con fixtures simulados")
        args = parser.parse_args()

        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: No se encontró el archivo de entrada '{input_path}'.", file=sys.stderr)
            return 1

        spec = json.loads(input_path.read_text(encoding="utf-8"))
        book_key = detect_book_key(spec)
        book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])

        output_dir_str = args.output_dir or book_cfg["default_output_dir"]
        output_dir = Path(output_dir_str)

        if args.offline_fixture:
            fixture_data = json.loads(Path(args.offline_fixture).read_text(encoding="utf-8"))

            def fetch_mock(book: str, chapter: int) -> dict[int, str]:
                return {int(k): str(v) for k, v in fixture_data.get(str(chapter), {}).items()}

            run_audit(spec, fetch_mock, output_dir)
            return 0

        api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
        if not api_key:
            print("Falta APIBIBLIA_API_KEY en las variables de entorno. Para pruebas locales use --offline-fixture.", file=sys.stderr)
            return 2

        rate_metrics = {
            "http_request_attempts_total": 0,
            "rate_limit_retries": 0,
        }
        last_request_time = [0.0]
        min_interval = 2.3

        def fetch_apibiblia(api_book_name: str, chapter: int) -> dict[int, str]:
            query = urllib.parse.urlencode({"ref": f"{api_book_name} {chapter}", "version": args.version})
            url = f"{PASSAGE_URL}?{query}"

            max_retries = 4
            for attempt in range(1, max_retries + 1):
                elapsed = time.time() - last_request_time[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

                rate_metrics["http_request_attempts_total"] += 1
                last_request_time[0] = time.time()

                try:
                    status, payload = api_get(url, api_key)
                    if status == 200:
                        verse_map = extract_verses_robust(payload)
                        del payload
                        return verse_map

                    print(f"ApiBiblia HTTP {status} para {api_book_name} {chapter} (intento {attempt}/{max_retries})", file=sys.stderr, flush=True)

                except Exception as exc:
                    err_msg = str(exc)
                    if "429" in err_msg or "Rate" in err_msg or "RATE_LIMIT" in err_msg:
                        rate_metrics["rate_limit_retries"] += 1
                        print(f"Rate limit detectado en capítulo {chapter}. Esperando 62s para reset de ventana (intento {attempt}/{max_retries})...", file=sys.stderr, flush=True)
                        time.sleep(62.0)
                    else:
                        print(f"Aviso consultando {api_book_name} {chapter} (intento {attempt}/{max_retries}): {exc}", file=sys.stderr, flush=True)
                        if attempt == max_retries:
                            print(f"Error definitivo obteniendo {api_book_name} {chapter}. Se continuará.", file=sys.stderr, flush=True)
                            return {}
                        time.sleep(3.0 * attempt)

            return {}

        run_audit(spec, fetch_apibiblia, output_dir, rate_metrics=rate_metrics)
        return 0

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
