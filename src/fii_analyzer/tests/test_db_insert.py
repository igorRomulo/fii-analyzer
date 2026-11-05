from unittest.mock import MagicMock, patch, call

import pytest

from fii_analyzer.db.insert import insert_data_in_database, BATCH_SIZE


class TestInsertDataInDatabase:
    def _make_mock_model(self):
        pk_col = MagicMock()
        pk_col.name = "id"

        non_pk_col = MagicMock()
        non_pk_col.name = "value"

        created_col = MagicMock()
        created_col.name = "created_at"

        updated_col = MagicMock()
        updated_col.name = "updated_at"

        table = MagicMock()
        table.name = "test_table"
        table.primary_key.columns = [pk_col]
        table.columns = [pk_col, non_pk_col, created_col, updated_col]

        model = MagicMock()
        model.__table__ = table
        return model

    @patch("fii_analyzer.db.insert.engine")
    @patch("fii_analyzer.db.insert.pg_insert")
    def test_single_batch(self, mock_pg_insert, mock_engine):
        model = self._make_mock_model()
        data = [{"id": i, "value": f"v{i}"} for i in range(5)]

        mock_stmt = MagicMock()
        mock_pg_insert.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt
        mock_stmt.excluded = {"value": "excluded_value", "updated_at": "excluded_updated"}

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        insert_data_in_database(model, data)

        mock_pg_insert.assert_called_once()

    @patch("fii_analyzer.db.insert.engine")
    @patch("fii_analyzer.db.insert.pg_insert")
    def test_multiple_batches(self, mock_pg_insert, mock_engine):
        model = self._make_mock_model()
        data = [{"id": i, "value": f"v{i}"} for i in range(BATCH_SIZE + 5)]

        mock_stmt = MagicMock()
        mock_pg_insert.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt
        mock_stmt.excluded = {"value": "excluded_value", "updated_at": "excluded_updated"}

        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        insert_data_in_database(model, data)

        assert mock_pg_insert.call_count == 2

    def test_excludes_timestamp_columns_from_update(self):
        model = self._make_mock_model()
        table = model.__table__
        pk_columns = [col.name for col in table.primary_key.columns]
        excluded = ["created_at", "updated_at"]

        non_pk_columns = [
            col.name for col in table.columns
            if col.name not in pk_columns and col.name not in excluded
        ]
        assert "created_at" not in non_pk_columns
        assert "updated_at" not in non_pk_columns
        assert "value" in non_pk_columns
