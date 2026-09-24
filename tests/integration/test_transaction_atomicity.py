"""
q:transaction had no atomicity at all.

begin/commit/rollback only set flags on a dict — no BEGIN, no COMMIT, no
ROLLBACK ever reached the database, and each q:query inside the block opened
its own pooled connection and autocommitted. So a bank transfer whose second
leg failed left the first leg (the debit) committed and the money gone, while
the framework printed "rolled back".

Reported by two audit dimensions; reproduced here with a real sqlite file
before and after the fix.
"""

import sqlite3

import pytest

from quantum.runtime.database_service import DatabaseService, QueryExecutionError


@pytest.fixture
def bank(tmp_path):
    db = tmp_path / "bank.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
    con.executemany("INSERT INTO accounts VALUES (?, ?)", [(1, 1000), (2, 1000)])
    con.commit()
    con.close()

    svc = DatabaseService(local_datasources={
        "bank": {"driver": "sqlite", "database": str(db)}
    })
    return svc, db


def _balances(db):
    con = sqlite3.connect(str(db))
    rows = dict(con.execute("SELECT id, balance FROM accounts").fetchall())
    con.close()
    return rows


class TestAtomicity:
    def test_a_failed_transfer_rolls_back_the_debit(self, bank):
        svc, db = bank
        tx = svc.begin_transaction("bank")
        try:
            # debit account 1 — succeeds
            svc.execute_query("bank", "UPDATE accounts SET balance = balance - 500 WHERE id = 1")
            # credit account 2 — fails: no such column
            svc.execute_query("bank", "UPDATE accounts SET nope = balance + 500 WHERE id = 2")
            svc.commit_transaction(tx)
        except QueryExecutionError:
            svc.rollback_transaction(tx)

        # The debit must be gone. Before the fix, account 1 was 500.
        assert _balances(db) == {1: 1000, 2: 1000}, "the debit was not rolled back — money lost"

    def test_a_successful_transfer_commits_both_legs(self, bank):
        svc, db = bank
        tx = svc.begin_transaction("bank")
        svc.execute_query("bank", "UPDATE accounts SET balance = balance - 500 WHERE id = 1")
        svc.execute_query("bank", "UPDATE accounts SET balance = balance + 500 WHERE id = 2")
        svc.commit_transaction(tx)
        assert _balances(db) == {1: 500, 2: 1500}

    def test_a_committed_transaction_survives_a_new_connection(self, bank):
        """The commit must be durable, not just visible on the same handle."""
        svc, db = bank
        tx = svc.begin_transaction("bank")
        svc.execute_query("bank", "UPDATE accounts SET balance = 4242 WHERE id = 1")
        svc.commit_transaction(tx)
        # _balances opens a brand-new sqlite connection.
        assert _balances(db)[1] == 4242

    def test_an_uncommitted_write_is_not_visible_outside(self, bank):
        """Mid-transaction, an outside reader must not see the pending write —
        proof the write really is inside an open transaction, not autocommitted."""
        svc, db = bank
        tx = svc.begin_transaction("bank")
        svc.execute_query("bank", "UPDATE accounts SET balance = 7 WHERE id = 1")
        # A separate connection should still see the old value.
        assert _balances(db)[1] == 1000
        svc.rollback_transaction(tx)
        assert _balances(db)[1] == 1000

    def test_queries_outside_a_transaction_still_autocommit(self, bank):
        """The transaction path must not change standalone behaviour."""
        svc, db = bank
        svc.execute_query("bank", "UPDATE accounts SET balance = 123 WHERE id = 2")
        assert _balances(db)[2] == 123
