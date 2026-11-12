import csv
import zipfile
import io
import logging
from datetime import datetime

import unicodedata

from fii_analyzer.ingestion.upsert import insert_data

logger = logging.getLogger(__name__)

def extract_data(data):
    zip_buffer = io.BytesIO(data.content)
    year = datetime.now().year

    with zipfile.ZipFile(zip_buffer) as zip_file:
        list_of_files = zip_file.namelist()
        logger.info("Found %d files in ZIP", len(list_of_files))

        for file in list_of_files:
            with zip_file.open(file) as f:
                match file:
                    case file if file == f"inf_mensal_fii_ativo_passivo_{year}.csv":
                        try:
                            data = build_data(f, year)
                            insert_data(file, data, year)
                        except Exception:
                            logger.exception("Failed to process %s", file)
                            continue

                    case file if file == f"inf_mensal_fii_complemento_{year}.csv":
                        try:
                            data = build_data(f, year)
                            insert_data(file, data, year)
                        except Exception:
                            logger.exception("Failed to process %s", file)
                            continue

                    case file if file == f"inf_mensal_fii_geral_{year}.csv":
                        try:
                            data = build_data(f, year)
                            insert_data(file, data, year)
                        except Exception:
                            logger.exception("Failed to process %s", file)
                            continue


def build_data(file, year):
    rows = []
    encoding = "cp1252" if file.name != f"inf_mensal_fii_ativo_passivo_{year}.csv" else "utf-8"
    text_file = io.TextIOWrapper(file, encoding=encoding)
    data = csv.DictReader(text_file, delimiter=";")

    for row in data:
        cleaned = {
            strip_accents(key.lower()): (value if value != "" else None)
            for key, value in row.items()
        }
        cleaned["cnpj_fundo"] = cleaned.pop("cnpj_fundo_classe")

        if file.name == f"inf_mensal_fii_geral_{year}.csv":
            cleaned["nome_fundo"] = cleaned.pop("nome_fundo_classe")

        rows.append(cleaned)

    logger.info("Parsed %d rows from %s", len(rows), file.name)
    return rows


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
