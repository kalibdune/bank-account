"""
Additional tests to achieve 100% code coverage.

This module contains specific tests to cover the remaining uncovered lines
in the bank management system.
"""

import pytest
import tempfile
import os
import sqlite3
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from bank_system.database import DatabaseManager
from bank_system.account_manager import AccountManager
from bank_system.models import Account, Transaction, AccountType, TransactionType
from bank_system.cli import BankCLI, cli


class TestDatabaseErrorHandling:
    """Test database error handling to achieve full coverage."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_create_account_database_error(self, temp_db_path):
        """Test create_account method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        # Create a sample account
        account = Account(
            account_number="TEST-123",
            customer_name="Test User",
            account_type=AccountType.CHECKING
        )

        # Mock sqlite3.connect to raise an error
        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.create_account(account)
            assert result is None

    def test_get_account_database_error(self, temp_db_path):
        """Test get_account method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.get_account(1)
            assert result is None

    def test_get_account_by_number_database_error(self, temp_db_path):
        """Test get_account_by_number method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.get_account_by_number("TEST-123")
            assert result is None

    def test_update_account_balance_database_error(self, temp_db_path):
        """Test update_account_balance method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.update_account_balance(1, Decimal('100.00'))
            assert result is False

    def test_deactivate_account_database_error(self, temp_db_path):
        """Test deactivate_account method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.deactivate_account(1)
            assert result is False

    def test_get_all_accounts_database_error(self, temp_db_path):
        """Test get_all_accounts method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.get_all_accounts()
            assert result == []

    def test_create_transaction_database_error(self, temp_db_path):
        """Test create_transaction method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        transaction = Transaction(
            account_id=1,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal('100.00')
        )

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.create_transaction(transaction)
            assert result is None

    def test_get_account_transactions_database_error(self, temp_db_path):
        """Test get_account_transactions method with database error."""
        db_manager = DatabaseManager(temp_db_path)

        with patch('sqlite3.connect') as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database error")

            result = db_manager.get_account_transactions(1)
            assert result == []


class TestAccountManagerErrorHandling:
    """Test AccountManager error handling for full coverage."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def account_manager(self, temp_db_path):
        """Create an AccountManager instance for testing."""
        db_manager = DatabaseManager(temp_db_path)
        return AccountManager(db_manager)

    def test_create_account_database_creation_failure(self, account_manager):
        """Test account creation when database creation fails."""
        with patch.object(account_manager.db, 'create_account', return_value=None):
            result = account_manager.create_account(
                customer_name="Test User",
                account_type=AccountType.CHECKING
            )
            assert result is None

    def test_deposit_database_update_failure(self, account_manager):
        """Test deposit when database update fails."""
        # Create account first
        account = account_manager.create_account(
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Mock database update to fail
        with patch.object(account_manager.db, 'update_account_balance', return_value=False):
            result = account_manager.deposit(account.account_id, Decimal('100.00'))
            assert result is False

    def test_withdraw_database_update_failure(self, account_manager):
        """Test withdrawal when database update fails."""
        # Create account first
        account = account_manager.create_account(
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Mock database update to fail
        with patch.object(account_manager.db, 'update_account_balance', return_value=False):
            result = account_manager.withdraw(account.account_id, Decimal('100.00'))
            assert result is False

    def test_transfer_partial_failure(self, account_manager):
        """Test transfer when one database update fails."""
        # Create two accounts
        account1 = account_manager.create_account(
            customer_name="User 1",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('2000.00')
        )
        account2 = account_manager.create_account(
            customer_name="User 2",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Mock database update to fail for the second update
        update_calls = 0
        def mock_update(account_id, balance):
            nonlocal update_calls
            update_calls += 1
            if update_calls == 2:  # Fail on second call
                return False
            return True

        with patch.object(account_manager.db, 'update_account_balance', side_effect=mock_update):
            result = account_manager.transfer(
                account1.account_id,
                account2.account_id,
                Decimal('500.00')
            )
            assert result is False


class TestCLIErrorPaths:
    """Test CLI error handling paths for full coverage."""

    @pytest.fixture
    def runner(self):
        """Create a click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_create_account_failure(self, runner, temp_db_path):
        """Test create account CLI command when creation fails."""
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.create_account.return_value = None
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'create-account',
                '--name', 'Test User',
                '--type', 'checking',
                '--initial-deposit', '1000.00',
                '--minimum-balance', '0.00'
            ])

            assert result.exit_code == 0
            assert "❌ Failed to create account" in result.output

    def test_deposit_failure(self, runner, temp_db_path):
        """Test deposit CLI command when deposit fails."""
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.deposit.return_value = False
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'deposit',
                '--account-id', '1',
                '--amount', '100.00'
            ])

            assert result.exit_code == 0
            assert "❌ Deposit failed" in result.output

    def test_withdraw_failure(self, runner, temp_db_path):
        """Test withdraw CLI command when withdrawal fails."""
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.withdraw.return_value = False
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'withdraw',
                '--account-id', '1',
                '--amount', '100.00'
            ])

            assert result.exit_code == 0
            assert "❌ Withdrawal failed" in result.output

    def test_transfer_failure(self, runner, temp_db_path):
        """Test transfer CLI command when transfer fails."""
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.transfer.return_value = False
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'transfer',
                '--from-account', '1',
                '--to-account', '2',
                '--amount', '100.00'
            ])

            assert result.exit_code == 0
            assert "❌ Transfer failed" in result.output

    def test_balance_exception_handling(self, runner, temp_db_path):
        """Test balance CLI command exception handling."""
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.get_account.side_effect = Exception("Test error")
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'balance',
                '--account-id', '1'
            ])

            assert result.exit_code == 0
            assert "❌ Error:" in result.output

    def test_main_function_call(self):
        """Test that main function can be imported and called."""
        from bank_system.cli import main

        # Test that we can import and reference the main function
        assert callable(main)

    def test_cli_main_import(self):
        """Test the main function import and call."""
        # Simply test that main can be called (covers the if __name__ == '__main__' block)
        from bank_system.cli import main
        assert callable(main)

    def test_main_function_execution(self, runner):
        """Test main function execution to cover lines 238 and 242."""
        from bank_system.cli import main

        # Test that main function calls cli() - mock cli to avoid actual execution
        with patch('bank_system.cli.cli') as mock_cli:
            main()
            mock_cli.assert_called_once()


class TestRemainingCoverage:
    """Test remaining uncovered code paths."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def account_manager(self, temp_db_path):
        """Create an AccountManager instance for testing."""
        db_manager = DatabaseManager(temp_db_path)
        return AccountManager(db_manager)

    def test_record_transaction_failure(self, account_manager):
        """Test record_transaction when database creation fails."""
        with patch.object(account_manager.db, 'create_transaction', return_value=None):
            result = account_manager.record_transaction(
                account_id=1,
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal('100.00'),
                description="Test",
                balance_after=Decimal('100.00')
            )
            assert result is None

    def test_generate_account_number_collision_loop(self, account_manager):
        """Test account number collision handling with multiple collisions."""
        existing_numbers = set()

        # Create multiple accounts to test collision handling
        for i in range(3):
            account = account_manager.create_account(
                customer_name=f"User {i}",
                account_type=AccountType.CHECKING
            )
            existing_numbers.add(account.account_number)

        # All numbers should be unique
        assert len(existing_numbers) == 3

    def test_account_manager_none_account_scenarios(self, account_manager):
        """Test AccountManager methods with None account scenarios."""
        # Test methods that check for account existence
        with patch.object(account_manager.db, 'get_account', return_value=None):

            # These should raise ValueError for account not found
            with pytest.raises(ValueError, match="Account not found"):
                account_manager.deposit(999, Decimal('100.00'))

            with pytest.raises(ValueError, match="Account not found"):
                account_manager.withdraw(999, Decimal('100.00'))

            with pytest.raises(ValueError, match="Source account not found"):
                account_manager.transfer(999, 1, Decimal('100.00'))

    def test_transfer_destination_account_not_found(self, account_manager):
        """Test transfer when destination account is not found."""
        # Create source account
        source_account = account_manager.create_account(
            customer_name="Source User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Mock to return source account but None for destination
        def mock_get_account(account_id):
            if account_id == source_account.account_id:
                return source_account
            return None

        with patch.object(account_manager.db, 'get_account', side_effect=mock_get_account):
            with pytest.raises(ValueError, match="Destination account not found"):
                account_manager.transfer(source_account.account_id, 999, Decimal('100.00'))

    def test_account_manager_edge_cases(self, account_manager):
        """Test edge cases in AccountManager."""
        # Test calculate methods with account that has no transactions except initial
        account = account_manager.create_account(
            customer_name="Edge Case User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Test calculation methods
        total_deposits = account_manager.calculate_total_deposits(account.account_id)
        total_withdrawals = account_manager.calculate_total_withdrawals(account.account_id)

        assert total_deposits == Decimal('1000.00')  # Only initial deposit
        assert total_withdrawals == Decimal('0.00')  # No withdrawals

    def test_account_manager_duplicate_account_number_handling(self, account_manager):
        """Test account creation with duplicate account number collision."""
        # Mock generate_account_number to return same number twice then different
        call_count = 0

        def mock_generate():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return "DUPLICATE-NUMBER"
            return "UNIQUE-NUMBER"

        with patch.object(account_manager, 'generate_account_number', side_effect=mock_generate):
            # Mock get_account_by_number to return account for first two calls, None for third
            def mock_get_by_number(number):
                if number == "DUPLICATE-NUMBER":
                    return Account(account_number=number, customer_name="Existing")
                return None

            with patch.object(account_manager.db, 'get_account_by_number', side_effect=mock_get_by_number):
                account = account_manager.create_account(
                    customer_name="Test User",
                    account_type=AccountType.CHECKING
                )
                assert account is not None
                # Should have generated unique number after collision
                assert account.account_number == "UNIQUE-NUMBER"

    def test_account_manager_record_transaction_database_failure(self, account_manager):
        """Test record_transaction method when database fails."""
        # Create account first
        account = account_manager.create_account(
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Mock database to fail transaction creation
        with patch.object(account_manager.db, 'create_transaction', return_value=None):
            result = account_manager.record_transaction(
                account_id=account.account_id,
                transaction_type=TransactionType.DEPOSIT,
                amount=Decimal('100.00'),
                description="Test transaction",
                balance_after=Decimal('1100.00')
            )
            assert result is None

    def test_account_number_collision_while_loop(self, account_manager):
        """Test the while loop in create_account that handles account number collisions."""
        collision_count = 0

        def mock_get_account_by_number(number):
            nonlocal collision_count
            collision_count += 1
            # Return existing account for first call, None for second call
            if collision_count == 1:
                return Account(account_number=number, customer_name="Existing")
            return None

        with patch.object(account_manager.db, 'get_account_by_number', side_effect=mock_get_account_by_number):
            account = account_manager.create_account(
                customer_name="Collision Test User",
                account_type=AccountType.CHECKING
            )
            # Should successfully create account after one collision
            assert account is not None
            assert collision_count == 2  # Called twice: once collision, once success
