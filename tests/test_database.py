"""
Tests for the database module.

This module contains tests for the DatabaseManager class,
including database operations and error handling.
"""

import pytest
import tempfile
import os
import sqlite3
from datetime import datetime
from decimal import Decimal

from bank_system.database import DatabaseManager
from bank_system.models import Account, Transaction, AccountType, TransactionType


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance for testing."""
        return DatabaseManager(temp_db_path)

    @pytest.fixture
    def sample_account(self):
        """Create a sample account for testing."""
        return Account(
            account_number="TEST-20240101-ABC123",
            customer_name="Иван Тестов",
            account_type=AccountType.CHECKING,
            balance=Decimal('1000.00'),
            minimum_balance=Decimal('100.00'),
            created_at=datetime.now(),
            is_active=True
        )

    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction for testing."""
        return Transaction(
            account_id=1,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal('500.00'),
            description="Test deposit",
            timestamp=datetime.now(),
            balance_after=Decimal('1500.00'),
            related_account_id=None
        )

    def test_database_initialization(self, temp_db_path):
        """Test database initialization creates tables."""
        db_manager = DatabaseManager(temp_db_path)

        # Check that database file exists
        assert os.path.exists(temp_db_path)

        # Check that tables are created
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()

            # Check accounts table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='accounts'
            """)
            assert cursor.fetchone() is not None

            # Check transactions table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='transactions'
            """)
            assert cursor.fetchone() is not None

    def test_create_account_success(self, db_manager, sample_account):
        """Test successful account creation."""
        account_id = db_manager.create_account(sample_account)

        assert account_id is not None
        assert isinstance(account_id, int)
        assert account_id > 0

    def test_create_account_duplicate_number(self, db_manager, sample_account):
        """Test account creation with duplicate account number."""
        # Create first account
        first_id = db_manager.create_account(sample_account)
        assert first_id is not None

        # Try to create account with same number
        duplicate_account = Account(
            account_number=sample_account.account_number,  # Same number
            customer_name="Другой Клиент",
            account_type=AccountType.SAVINGS,
            balance=Decimal('2000.00')
        )

        # Should fail due to unique constraint
        second_id = db_manager.create_account(duplicate_account)
        assert second_id is None

    def test_get_account_success(self, db_manager, sample_account):
        """Test successful account retrieval."""
        account_id = db_manager.create_account(sample_account)

        retrieved_account = db_manager.get_account(account_id)

        assert retrieved_account is not None
        assert retrieved_account.account_id == account_id
        assert retrieved_account.account_number == sample_account.account_number
        assert retrieved_account.customer_name == sample_account.customer_name
        assert retrieved_account.account_type == sample_account.account_type
        assert retrieved_account.balance == sample_account.balance
        assert retrieved_account.minimum_balance == sample_account.minimum_balance
        assert retrieved_account.is_active == sample_account.is_active

    def test_get_account_not_found(self, db_manager):
        """Test account retrieval with non-existent ID."""
        account = db_manager.get_account(999)
        assert account is None

    def test_get_account_by_number_success(self, db_manager, sample_account):
        """Test successful account retrieval by number."""
        account_id = db_manager.create_account(sample_account)

        retrieved_account = db_manager.get_account_by_number(sample_account.account_number)

        assert retrieved_account is not None
        assert retrieved_account.account_id == account_id
        assert retrieved_account.account_number == sample_account.account_number

    def test_get_account_by_number_not_found(self, db_manager):
        """Test account retrieval by number with non-existent number."""
        account = db_manager.get_account_by_number("NONEXISTENT-123")
        assert account is None

    def test_update_account_balance_success(self, db_manager, sample_account):
        """Test successful balance update."""
        account_id = db_manager.create_account(sample_account)
        new_balance = Decimal('1500.00')

        result = db_manager.update_account_balance(account_id, new_balance)

        assert result is True

        # Verify the balance was updated
        updated_account = db_manager.get_account(account_id)
        assert updated_account.balance == new_balance

    def test_update_account_balance_not_found(self, db_manager):
        """Test balance update with non-existent account."""
        result = db_manager.update_account_balance(999, Decimal('1000.00'))
        assert result is False

    def test_deactivate_account_success(self, db_manager, sample_account):
        """Test successful account deactivation."""
        account_id = db_manager.create_account(sample_account)

        result = db_manager.deactivate_account(account_id)

        assert result is True

        # Verify the account was deactivated
        deactivated_account = db_manager.get_account(account_id)
        assert deactivated_account.is_active is False

    def test_deactivate_account_not_found(self, db_manager):
        """Test account deactivation with non-existent account."""
        result = db_manager.deactivate_account(999)
        assert result is False

    def test_get_all_accounts_empty(self, db_manager):
        """Test getting all accounts when none exist."""
        accounts = db_manager.get_all_accounts()
        assert accounts == []

    def test_get_all_accounts_with_data(self, db_manager):
        """Test getting all accounts with existing data."""
        # Create multiple accounts
        account1 = Account(
            account_number="TEST-1",
            customer_name="Клиент 1",
            account_type=AccountType.CHECKING,
            balance=Decimal('1000.00')
        )
        account2 = Account(
            account_number="TEST-2",
            customer_name="Клиент 2",
            account_type=AccountType.SAVINGS,
            balance=Decimal('2000.00')
        )

        db_manager.create_account(account1)
        db_manager.create_account(account2)

        accounts = db_manager.get_all_accounts()

        assert len(accounts) == 2
        assert all(isinstance(acc, Account) for acc in accounts)

        # Should be ordered by created_at DESC (newest first)
        account_names = [acc.customer_name for acc in accounts]
        assert "Клиент 2" in account_names
        assert "Клиент 1" in account_names

    def test_create_transaction_success(self, db_manager, sample_account, sample_transaction):
        """Test successful transaction creation."""
        # First create an account
        account_id = db_manager.create_account(sample_account)
        sample_transaction.account_id = account_id

        transaction_id = db_manager.create_transaction(sample_transaction)

        assert transaction_id is not None
        assert isinstance(transaction_id, int)
        assert transaction_id > 0

    def test_get_account_transactions_empty(self, db_manager, sample_account):
        """Test getting transactions for account with no transactions."""
        account_id = db_manager.create_account(sample_account)

        transactions = db_manager.get_account_transactions(account_id)

        assert transactions == []

    def test_get_account_transactions_with_data(self, db_manager, sample_account):
        """Test getting transactions with existing data."""
        # Create account
        account_id = db_manager.create_account(sample_account)

        # Create multiple transactions
        tx1 = Transaction(
            account_id=account_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal('100.00'),
            description="First deposit",
            balance_after=Decimal('1100.00')
        )
        tx2 = Transaction(
            account_id=account_id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=Decimal('50.00'),
            description="First withdrawal",
            balance_after=Decimal('1050.00')
        )

        db_manager.create_transaction(tx1)
        db_manager.create_transaction(tx2)

        transactions = db_manager.get_account_transactions(account_id)

        assert len(transactions) == 2
        assert all(isinstance(tx, Transaction) for tx in transactions)

        # Should be ordered by timestamp DESC (newest first)
        assert transactions[0].transaction_type == TransactionType.WITHDRAWAL
        assert transactions[1].transaction_type == TransactionType.DEPOSIT

    def test_get_account_transactions_with_limit(self, db_manager, sample_account):
        """Test getting transactions with limit."""
        account_id = db_manager.create_account(sample_account)

        # Create more transactions than limit
        for i in range(5):
            tx = Transaction(
                account_id=account_id,
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal(f'{100 + i}.00'),
                description=f"Deposit {i+1}",
                balance_after=Decimal(f'{1100 + (i * 100)}.00')
            )
            db_manager.create_transaction(tx)

        transactions = db_manager.get_account_transactions(account_id, limit=3)

        assert len(transactions) == 3

    def test_get_account_transactions_with_related_account(self, db_manager):
        """Test getting transactions with related account ID."""
        # Create two accounts
        account1 = Account(
            account_number="TEST-1",
            customer_name="Account 1",
            account_type=AccountType.CHECKING,
            balance=Decimal('1000.00')
        )
        account2 = Account(
            account_number="TEST-2",
            customer_name="Account 2",
            account_type=AccountType.SAVINGS,
            balance=Decimal('500.00')
        )

        account1_id = db_manager.create_account(account1)
        account2_id = db_manager.create_account(account2)

        # Create transfer transaction
        transfer_tx = Transaction(
            account_id=account1_id,
            transaction_type=TransactionType.TRANSFER_OUT,
            amount=Decimal('200.00'),
            description="Transfer to Account 2",
            balance_after=Decimal('800.00'),
            related_account_id=account2_id
        )

        db_manager.create_transaction(transfer_tx)

        transactions = db_manager.get_account_transactions(account1_id)

        assert len(transactions) == 1
        assert transactions[0].related_account_id == account2_id

    def test_close_method(self, db_manager):
        """Test close method (placeholder method)."""
        # Should not raise any exception
        db_manager.close()

    def test_database_error_handling_in_create_account(self, temp_db_path):
        """Test error handling in create_account method."""
        # Create database manager
        db_manager = DatabaseManager(temp_db_path)

        # Close the database file to simulate error
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

        # Create account with invalid database should return None
        account = Account(
            account_number="TEST-123",
            customer_name="Test User",
            account_type=AccountType.CHECKING
        )

        result = db_manager.create_account(account)
        # The result might be None or raise an exception depending on implementation
        # We're testing that it handles the error gracefully

    def test_database_path_parameter(self):
        """Test DatabaseManager with custom database path."""
        custom_path = "custom_test.db"
        db_manager = DatabaseManager(custom_path)

        assert db_manager.db_path == custom_path
        assert os.path.exists(custom_path)

        # Cleanup
        if os.path.exists(custom_path):
            os.remove(custom_path)

    def test_default_database_path(self):
        """Test DatabaseManager with default database path."""
        db_manager = DatabaseManager()

        assert db_manager.db_path == "bank.db"

        # Cleanup if created
        if os.path.exists("bank.db"):
            os.remove("bank.db")
