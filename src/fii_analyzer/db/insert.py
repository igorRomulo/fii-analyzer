import logging
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fii_analyzer.db.model import engine

logger = logging.getLogger(__name__)
BATCH_SIZE = 1000

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(OperationalError)
)
def _execute_batch(conn, stmt):
    try:
        conn.execute(stmt)
        conn.commit()
    except OperationalError:
        conn.rollback()
        raise

def insert_data_in_database(model, data):
    EXCLUDED_FROM_UPDATE = ["created_at", "updated_at"]
    table = model.__table__
    pk_columns = [col.name for col in table.primary_key.columns]
    num_batches = (len(data) + BATCH_SIZE - 1)
    non_pk_columns = [
        col.name for col in table.columns
        if col.name not in pk_columns and col.name not in EXCLUDED_FROM_UPDATE
    ]

    logger.info("Inserting %d rows into %s in %d batches", len(data), table.name, num_batches)

    with engine.connect() as conn:
        for i in range(0, len(data), BATCH_SIZE):
            batch_num = i
            batch_data = data[i : i + BATCH_SIZE]
            stmt = pg_insert(table).values(batch_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=pk_columns,
                set_={
                    col: stmt.excluded[col]
                    for col in non_pk_columns
                } | {"updated_at": func.now()},
            )
            _execute_batch(conn, stmt)
            logger.info("Batch %d/%d: %d rows committed", batch_num, num_batches, len(batch_data))