import io
import os
import sqlite3
import tempfile
import unittest
from collections.abc import Callable, Iterator
from unittest.mock import MagicMock, patch

from ibanpl import (
    MIN_BANK_RECORDS, b_dbop, bank_base_update, bank_j_iterator,
    bank_list_update, bank_update, chk_iban, sql_get_all_bank_no,
    sql_get_all_jorg, validate_bank_data)


class _FailingCursorProxy:
    """Cursor wrapper that raises on executemany() calls whose SQL matches
    should_fail, otherwise delegates to the real cursor. Used to simulate a
    database error partway through a multi-statement transaction."""

    def __init__(self, real_cursor: sqlite3.Cursor,
                should_fail: Callable[[str], bool]) -> None:
        self._c = real_cursor
        self._should_fail = should_fail

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        return self._c.execute(sql, *args)

    def executemany(self, sql: str, seq: object) -> sqlite3.Cursor:
        if self._should_fail(sql):
            raise sqlite3.OperationalError("simulated failure")
        return self._c.executemany(sql, seq)

    def close(self) -> None:
        self._c.close()


class _ProxyConnection:
    """Connection wrapper whose cursor() hands out a _FailingCursorProxy."""

    def __init__(self, real_con: sqlite3.Connection,
                should_fail: Callable[[str], bool]) -> None:
        self._con = real_con
        self._should_fail = should_fail

    def cursor(self) -> _FailingCursorProxy:
        return _FailingCursorProxy(self._con.cursor(), self._should_fail)

    def commit(self) -> None:
        self._con.commit()

    def rollback(self) -> None:
        self._con.rollback()

    def close(self) -> None:
        self._con.close()


class ChkIbanTests(unittest.TestCase):
    VALID_UNFORMATTED = "61109010140000071219812874"
    VALID_FORMATTED = "61 1090 1014 0000 0712 1981 2874"

    def assert_valid(self, number: str, formatted: str = VALID_FORMATTED) -> None:
        ok, msg, result = chk_iban(number)
        self.assertTrue(ok)
        self.assertEqual(msg, "Numer prawidłowy")
        self.assertEqual(result, formatted)

    def assert_invalid(self, number: str,
                       expected_msg_prefix: str | None = None) -> str:
        ok, msg, _ = chk_iban(number)
        self.assertFalse(ok)
        if expected_msg_prefix is not None:
            self.assertTrue(msg.startswith(expected_msg_prefix))
        return msg

    def test_valid_unformatted_number(self) -> None:
        self.assert_valid(self.VALID_UNFORMATTED)

    def test_valid_number_already_formatted_with_spaces(self) -> None:
        self.assert_valid(self.VALID_FORMATTED)

    def test_valid_number_with_dashes(self) -> None:
        self.assert_valid("61-1090-1014-0000-0712-1981-2874")

    def test_second_valid_number(self) -> None:
        self.assert_valid(
            "27114020040000300201355387",
            "27 1140 2004 0000 3002 0135 5387",
        )

    def test_wrong_checksum(self) -> None:
        self.assert_invalid(
            "11109010140000071219812874", "Błąd w numerze")

    def test_too_short(self) -> None:
        msg = self.assert_invalid("6110901014000007121981287")
        self.assertEqual(msg, "Powinno być 26 znaków jest 25")

    def test_too_long(self) -> None:
        msg = self.assert_invalid("611090101400000712198128744")
        self.assertEqual(msg, "Powinno być 26 znaków jest 27")

    def test_empty_string(self) -> None:
        msg = self.assert_invalid("")
        self.assertEqual(msg, "Powinno być 26 znaków jest 0")

    def test_invalid_character(self) -> None:
        self.assert_invalid(
            "6110901O140000071219812874", "Nieprawidłowy znak")

    def test_already_prefixed_with_pl_is_rejected(self) -> None:
        # chk_iban always prepends "PL" itself, so a caller-supplied prefix
        # doubles up and pushes the length check to fail.
        msg = self.assert_invalid("PL" + self.VALID_UNFORMATTED)
        self.assertEqual(msg, "Powinno być 26 znaków jest 28")


class ValidateBankDataTests(unittest.TestCase):
    def make_line(self, bank_id: int = 1010, unit_id: int = 2025,
                 field: int | None = None, value: str | None = None) -> str:
        """Build one plewibnra.txt-format line: 32 tab-separated fields,
        with field 4 encoding the 4-digit bank id and 4-digit unit id."""
        fields = ["x"] * 32
        fields[4] = "{0:04d}{1:04d}".format(bank_id, unit_id)
        if field is not None:
            fields[field] = value
        return "\t".join(fields) + "\n"

    def make_content(self, n_lines: int, **kwargs: int | str | None) -> io.StringIO:
        return io.StringIO(self.make_line(**kwargs) * n_lines)

    def test_valid_data_returns_none(self) -> None:
        content = self.make_content(MIN_BANK_RECORDS)
        self.assertIsNone(validate_bank_data(content))

    def test_valid_data_rewinds_content_to_starting_position(self) -> None:
        content = self.make_content(MIN_BANK_RECORDS)
        pos = content.tell()
        validate_bank_data(content)
        self.assertEqual(content.tell(), pos)

    def test_rewinds_to_original_offset_not_zero(self) -> None:
        prefix = "prefix-junk\n"
        content = io.StringIO(prefix + self.make_line() * MIN_BANK_RECORDS)
        content.readline()
        pos = content.tell()
        self.assertNotEqual(pos, 0)
        validate_bank_data(content)
        self.assertEqual(content.tell(), pos)

    def test_empty_content_is_incomplete(self) -> None:
        content = io.StringIO("")
        msg = validate_bank_data(content)
        self.assertEqual(
            msg,
            "Pobrane dane o bankach wyglądają na niekompletne "
            "(otrzymano 0 rekordów)",
        )

    def test_below_minimum_record_count_is_incomplete(self) -> None:
        content = self.make_content(MIN_BANK_RECORDS - 1)
        msg = validate_bank_data(content)
        self.assertEqual(
            msg,
            "Pobrane dane o bankach wyglądają na niekompletne "
            "(otrzymano {0} rekordów)".format(MIN_BANK_RECORDS - 1),
        )

    def test_line_with_too_few_fields_is_rejected(self) -> None:
        lines = [self.make_line() for _ in range(5)]
        lines[2] = "a\tb\tc\n"
        content = io.StringIO("".join(lines))
        msg = validate_bank_data(content)
        self.assertEqual(
            msg,
            "Nieprawidłowy format pobranych danych o bankach (linia 3)")

    def test_line_with_short_bank_unit_field_is_rejected(self) -> None:
        lines = [self.make_line() for _ in range(5)]
        lines[1] = self.make_line(field=4, value="1010")
        content = io.StringIO("".join(lines))
        msg = validate_bank_data(content)
        self.assertEqual(
            msg,
            "Nieprawidłowy format pobranych danych o bankach (linia 2)")

    def test_line_with_non_numeric_bank_unit_field_is_rejected(self) -> None:
        lines = [self.make_line() for _ in range(3)]
        lines[0] = self.make_line(field=4, value="abcd2025")
        content = io.StringIO("".join(lines))
        msg = validate_bank_data(content)
        self.assertEqual(
            msg,
            "Nieprawidłowy format pobranych danych o bankach (linia 1)")

    def test_malformed_line_rewinds_content_to_starting_position(self) -> None:
        lines = [self.make_line() for _ in range(3)]
        lines[0] = "a\tb\n"
        content = io.StringIO("".join(lines))
        pos = content.tell()
        validate_bank_data(content)
        self.assertEqual(content.tell(), pos)


class BankBaseUpdateTests(unittest.TestCase):
    """Exercises bank_base_update() against a real (temp-file) sqlite
    database rather than mocks, since the behavior under test -- that a
    failure partway through leaves the database untouched -- is exactly
    the kind of thing a mock can't prove; only a real transaction can."""

    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)  # b_dbop() creates the schema fresh
        patcher = patch("ibanpl.b_dbop",
                        side_effect=lambda db_file_name=None:
                            b_dbop(self.db_path))
        self.addCleanup(patcher.stop)
        patcher.start()

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def seed(self) -> None:
        con = b_dbop(self.db_path)
        con.execute("insert into bank values (?,?,?)",
                    (9999, "EXISTING BANK", "EB"))
        con.execute(
            "insert into jorg (id, oid, j_org_name) values (1, 9999, 'seed')")
        con.commit()
        con.close()

    def read_tables(self) -> tuple[list, list]:
        con = sqlite3.connect(self.db_path)
        bank_rows = con.execute("select * from bank").fetchall()
        jorg_rows = con.execute(
            "select id, oid, j_org_name from jorg").fetchall()
        con.close()
        return bank_rows, jorg_rows

    def make_content(self, n_lines: int = MIN_BANK_RECORDS,
                     bank_id_start: int = 1000,
                     unit_id: int = 1) -> io.StringIO:
        lines = []
        for i in range(n_lines):
            fields = ["x"] * 32
            fields[4] = "{0:04d}{1:04d}".format(bank_id_start + i, unit_id)
            lines.append("\t".join(fields) + "\n")
        return io.StringIO("".join(lines))

    def test_successful_update_replaces_both_tables(self) -> None:
        self.seed()
        result = bank_base_update(self.make_content())
        self.assertIsNone(result)
        bank_rows, jorg_rows = self.read_tables()
        self.assertEqual(len(bank_rows), MIN_BANK_RECORDS)
        self.assertEqual(len(jorg_rows), MIN_BANK_RECORDS)

    def test_invalid_data_leaves_database_untouched(self) -> None:
        self.seed()
        before = self.read_tables()
        # Too few records to pass validate_bank_data's completeness check.
        result = bank_base_update(self.make_content(n_lines=1))
        self.assertIsNotNone(result)
        self.assertEqual(self.read_tables(), before)

    def test_db_error_after_jorg_write_rolls_back_both_tables(self) -> None:
        """A failure in the *second* write (bank), after the *first* write
        (jorg) already succeeded within the same transaction, must undo
        both -- proving this is one atomic transaction, not two separate
        commits like the code used to do."""
        self.seed()
        before = self.read_tables()

        with patch("ibanpl.b_dbop",
                   side_effect=lambda db_file_name=None:
                       _ProxyConnection(
                           b_dbop(self.db_path),
                           should_fail=lambda sql: "insert into bank" in sql)):
            result = bank_base_update(self.make_content())

        self.assertEqual(result, "simulated failure")
        self.assertEqual(self.read_tables(), before)

    def test_iterator_error_rolls_back_both_tables(self) -> None:
        """A plain (non-sqlite3.Error) exception raised while iterating
        bank_j_iterator mid-executemany() must still roll back cleanly."""
        self.seed()
        before = self.read_tables()

        def broken_j_iterator(content: io.StringIO,
                              bdict: dict) -> Iterator[tuple]:
            for i, item in enumerate(bank_j_iterator(content, bdict)):
                if i == 5:
                    raise ValueError("simulated parsing bug")
                yield item

        with patch("ibanpl.bank_j_iterator", side_effect=broken_j_iterator):
            result = bank_base_update(self.make_content())

        self.assertEqual(result, "simulated parsing bug")
        self.assertEqual(self.read_tables(), before)

    def test_failed_update_does_not_prevent_a_later_clean_one(self) -> None:
        self.seed()

        with patch("ibanpl.b_dbop",
                   side_effect=lambda db_file_name=None:
                       _ProxyConnection(b_dbop(self.db_path),
                                        should_fail=lambda sql: True)):
            failed_result = bank_base_update(self.make_content())
        self.assertIsNotNone(failed_result)

        clean_result = bank_base_update(self.make_content())
        self.assertIsNone(clean_result)
        bank_rows, jorg_rows = self.read_tables()
        self.assertEqual(len(bank_rows), MIN_BANK_RECORDS)
        self.assertEqual(len(jorg_rows), MIN_BANK_RECORDS)


class BankListUpdateTests(unittest.TestCase):
    @patch("ibanpl.bank_base_update")
    @patch("ibanpl.get_url_response")
    def test_no_response_returns_error_without_processing(
            self, mock_get_response, mock_base_update) -> None:
        mock_get_response.return_value = None
        result = bank_list_update()
        self.assertEqual(
            result, "Nie udało się pobrać danych o bankach z serwera NBP")
        mock_base_update.assert_not_called()

    @patch("ibanpl.bank_base_update")
    @patch("ibanpl.get_url_response")
    def test_read_error_is_caught_and_response_is_closed(
            self, mock_get_response, mock_base_update) -> None:
        mock_response = MagicMock()
        mock_response.read.side_effect = OSError("boom")
        mock_get_response.return_value = mock_response
        result = bank_list_update()
        self.assertTrue(
            result.startswith("Błąd podczas przetwarzania pobranych danych:"))
        mock_response.close.assert_called_once()
        mock_base_update.assert_not_called()

    @patch("ibanpl.bank_base_update")
    @patch("ibanpl.get_url_response")
    def test_success_decodes_and_delegates_to_bank_base_update(
            self, mock_get_response, mock_base_update) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = "zawartość".encode("cp852")
        mock_get_response.return_value = mock_response
        mock_base_update.return_value = None
        result = bank_list_update()
        self.assertIsNone(result)
        mock_response.close.assert_called_once()
        mock_base_update.assert_called_once()
        content_arg = mock_base_update.call_args[0][0]
        self.assertIsInstance(content_arg, io.StringIO)
        self.assertEqual(content_arg.getvalue(), "zawartość")

    @patch("ibanpl.bank_base_update")
    @patch("ibanpl.get_url_response")
    def test_bank_base_update_error_is_propagated(
            self, mock_get_response, mock_base_update) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"data"
        mock_get_response.return_value = mock_response
        mock_base_update.return_value = "some db error"
        result = bank_list_update()
        self.assertEqual(result, "some db error")


class BankUpdateTests(unittest.TestCase):
    @patch("ibanpl.logger")
    @patch("ibanpl.chk_avail_update")
    @patch("ibanpl.bank_list_update")
    def test_prints_error_when_avail_check_fails(
            self, mock_list_update, mock_avail, mock_logger) -> None:
        mock_avail.return_value = (False, "nie udało się połączyć")
        bank_update()
        mock_logger.error.assert_called_once_with(
            "błąd podczas sprawdzania aktualizacji: %s", "nie udało się połączyć")
        mock_list_update.assert_not_called()

    @patch("ibanpl.logger")
    @patch("ibanpl.chk_avail_update")
    @patch("ibanpl.bank_list_update")
    def test_prints_success_when_update_succeeds(
            self, mock_list_update, mock_avail, mock_logger) -> None:
        mock_avail.return_value = (True, "some prompt")
        mock_list_update.return_value = None
        bank_update()
        mock_logger.info.assert_called_once_with("lista została uaktualniona")

    @patch("ibanpl.logger")
    @patch("ibanpl.chk_avail_update")
    @patch("ibanpl.bank_list_update")
    def test_prints_error_when_update_fails(
            self, mock_list_update, mock_avail, mock_logger) -> None:
        mock_avail.return_value = (True, "some prompt")
        mock_list_update.return_value = "boom"
        bank_update()
        mock_logger.error.assert_called_once_with("blad przy aktualizacji: %s", "boom")


class SqlGetAllTests(unittest.TestCase):
    """ibanpl-specific helpers absent from pyfaktury's fk/banknum.py --
    the GTK UI lists banks and branches through them."""

    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)  # b_dbop() creates the schema fresh
        con = b_dbop(self.db_path)
        con.executemany("insert into bank values (?,?,?)",
                        [(9999, "BANK A", "A"), (1010, "BANK B", "B")])
        # jorg: id = branch number, oid = bank number
        con.executemany(
            "insert into jorg (id, oid, j_org_name) values (?,?,?)",
            [(2, 9999, "u2"), (1, 9999, "u1"), (5, 1010, "u5")])
        con.commit()
        con.close()
        patcher = patch("ibanpl.b_dbop",
                        side_effect=lambda db_file_name=None:
                            b_dbop(self.db_path))
        self.addCleanup(patcher.stop)
        patcher.start()

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_sql_get_all_bank_no_returns_ids_ordered(self) -> None:
        rows, error_info = sql_get_all_bank_no()
        self.assertIsNone(error_info)
        self.assertEqual(rows, [(1010,), (9999,)])

    def test_sql_get_all_jorg_returns_branch_ids_of_bank(self) -> None:
        rows, error_info = sql_get_all_jorg(9999)
        self.assertIsNone(error_info)
        self.assertEqual(rows, [(1,), (2,)])

    def test_sql_get_all_jorg_no_branches_returns_empty(self) -> None:
        rows, error_info = sql_get_all_jorg(5555)
        self.assertIsNone(error_info)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
