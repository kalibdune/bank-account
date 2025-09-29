"""
Tests for the CLI module.

This module contains tests for the BankCLI class and CLI commands,
including input parsing, output formatting, and error handling.
"""

import pytest
from decimal import Decimal, InvalidOperation
from click.testing import CliRunner
from unittest.mock import Mock, patch
import tempfile
import os

from bank_system.cli import BankCLI, cli, main
from bank_system.models import AccountType, Account
from bank_system.database import DatabaseManager
from bank_system.account_manager import AccountManager


class TestBankCLI:
    """Test BankCLI class methods."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def bank_cli(self, temp_db_path):
        """Create a BankCLI instance for testing."""
        return BankCLI(temp_db_path)

    def test_bank_cli_initialization(self, temp_db_path):
        """Test BankCLI initialization."""
        bank_cli = BankCLI(temp_db_path)

        assert isinstance(bank_cli.db_manager, DatabaseManager)
        assert isinstance(bank_cli.account_manager, AccountManager)
        assert bank_cli.db_manager.db_path == temp_db_path

    def test_bank_cli_default_initialization(self):
        """Test BankCLI with default database path."""
        bank_cli = BankCLI()
        assert bank_cli.db_manager.db_path == "bank.db"

        # Cleanup
        if os.path.exists("bank.db"):
            os.remove("bank.db")

    def test_format_currency_positive(self, bank_cli):
        """Test currency formatting with positive amount."""
        formatted = bank_cli.format_currency(Decimal('1234.56'))
        assert formatted == "1,234.56 ₽"

    def test_format_currency_zero(self, bank_cli):
        """Test currency formatting with zero amount."""
        formatted = bank_cli.format_currency(Decimal('0.00'))
        assert formatted == "0.00 ₽"

    def test_format_currency_large_amount(self, bank_cli):
        """Test currency formatting with large amount."""
        formatted = bank_cli.format_currency(Decimal('1000000.99'))
        assert formatted == "1,000,000.99 ₽"

    def test_parse_currency_simple_number(self, bank_cli):
        """Test parsing simple currency input."""
        result = bank_cli.parse_currency("123.45")
        assert result == Decimal('123.45')

    def test_parse_currency_with_ruble_symbol(self, bank_cli):
        """Test parsing currency input with ruble symbol."""
        result = bank_cli.parse_currency("123.45₽")
        assert result == Decimal('123.45')

    def test_parse_currency_with_commas(self, bank_cli):
        """Test parsing currency input with commas."""
        result = bank_cli.parse_currency("1,234.56")
        assert result == Decimal('1234.56')

    def test_parse_currency_with_spaces(self, bank_cli):
        """Test parsing currency input with spaces."""
        result = bank_cli.parse_currency("  123.45  ")
        assert result == Decimal('123.45')

    def test_parse_currency_complex_format(self, bank_cli):
        """Test parsing complex currency format."""
        result = bank_cli.parse_currency(" 1,234.56 ₽ ")
        assert result == Decimal('1234.56')

    def test_parse_currency_invalid_input(self, bank_cli):
        """Test parsing invalid currency input."""
        with pytest.raises(ValueError, match="Invalid amount"):
            bank_cli.parse_currency("abc123")

    def test_parse_currency_empty_input(self, bank_cli):
        """Test parsing empty currency input."""
        with pytest.raises(ValueError, match="Invalid amount"):
            bank_cli.parse_currency("")

    def test_parse_currency_invalid_decimal(self, bank_cli):
        """Test parsing invalid decimal format."""
        with pytest.raises(ValueError, match="Invalid amount"):
            bank_cli.parse_currency("123.45.67")


class TestCLICommands:
    """Test CLI command functions."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def runner(self):
        """Create a click test runner."""
        return CliRunner()

    def test_main_cli_group(self, runner, temp_db_path):
        """Test main CLI group command."""
        result = runner.invoke(cli, ['--db-path', temp_db_path, '--help'])
        assert result.exit_code == 0
        assert "Bank Management System CLI" in result.output

    def test_create_account_success(self, runner, temp_db_path):
        """Test successful account creation through CLI."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Иван Тестов',
            '--type', 'checking',
            '--initial-deposit', '1000.00',
            '--minimum-balance', '100.00'
        ])

        assert result.exit_code == 0
        assert "✅ Account created successfully!" in result.output
        assert "Account Number:" in result.output
        assert "Account ID:" in result.output

    def test_create_account_interactive(self, runner, temp_db_path):
        """Test interactive account creation."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account'
        ], input='Мария Петрова\nchecking\n500.00\n50.00\n')

        assert result.exit_code == 0
        assert "✅ Account created successfully!" in result.output

    def test_create_account_invalid_amount(self, runner, temp_db_path):
        """Test account creation with invalid amount."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'savings',
            '--initial-deposit', 'invalid',
            '--minimum-balance', '0.00'
        ])

        assert result.exit_code == 0
        assert "❌ Error:" in result.output

    def test_create_account_validation_error(self, runner, temp_db_path):
        """Test account creation with validation error."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', '',
            '--type', 'checking',
            '--initial-deposit', '100.00',
            '--minimum-balance', '0.00'
        ])

        assert result.exit_code == 0
        assert "❌ Error:" in result.output

    def test_show_account_success(self, runner, temp_db_path):
        """Test successful account display."""
        # First create an account
        create_result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1000.00',
            '--minimum-balance', '100.00'
        ])
        assert create_result.exit_code == 0

        # Now show the account
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'show-account',
            '--account-id', '1'
        ])

        assert result.exit_code == 0
        assert "📊 Account Details" in result.output
        assert "Test User" in result.output

    def test_show_account_not_found(self, runner, temp_db_path):
        """Test showing non-existent account."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'show-account',
            '--account-id', '999'
        ])

        assert result.exit_code == 0
        assert "❌ Account not found" in result.output

    def test_deposit_success(self, runner, temp_db_path):
        """Test successful deposit through CLI."""
        # First create an account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1000.00'
        ])

        # Make a deposit
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'deposit',
            '--account-id', '1',
            '--amount', '500.00',
            '--description', 'Test deposit'
        ])

        assert result.exit_code == 0
        assert "✅ Deposit successful!" in result.output
        assert "500.00 ₽" in result.output

    def test_deposit_interactive(self, runner, temp_db_path):
        """Test interactive deposit."""
        # First create an account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1000.00'
        ])

        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'deposit'
        ], input='1\n250.00\n')

        assert result.exit_code == 0
        assert "✅ Deposit successful!" in result.output

    def test_deposit_error(self, runner, temp_db_path):
        """Test deposit error handling."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'deposit',
            '--account-id', '999',
            '--amount', '100.00'
        ])

        assert result.exit_code == 0
        assert "❌ Error:" in result.output

    def test_withdraw_success(self, runner, temp_db_path):
        """Test successful withdrawal through CLI."""
        # First create an account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1000.00',
            '--minimum-balance', '100.00'
        ])

        # Make a withdrawal
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'withdraw',
            '--account-id', '1',
            '--amount', '300.00',
            '--description', 'Test withdrawal'
        ])

        assert result.exit_code == 0
        assert "✅ Withdrawal successful!" in result.output
        assert "300.00 ₽" in result.output

    def test_withdraw_error(self, runner, temp_db_path):
        """Test withdrawal error handling."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'withdraw',
            '--account-id', '999',
            '--amount', '100.00'
        ])

        assert result.exit_code == 0
        assert "❌ Error:" in result.output

    def test_transfer_success(self, runner, temp_db_path):
        """Test successful transfer through CLI."""
        # Create two accounts
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Source User',
            '--type', 'checking',
            '--initial-deposit', '2000.00',
            '--minimum-balance', '100.00'
        ])

        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Dest User',
            '--type', 'savings',
            '--initial-deposit', '500.00'
        ])

        # Make a transfer
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'transfer',
            '--from-account', '1',
            '--to-account', '2',
            '--amount', '800.00',
            '--description', 'Test transfer'
        ])

        assert result.exit_code == 0
        assert "✅ Transfer successful!" in result.output
        assert "800.00 ₽" in result.output

    def test_transfer_interactive(self, runner, temp_db_path):
        """Test interactive transfer."""
        # Create two accounts
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Source User',
            '--type', 'checking',
            '--initial-deposit', '2000.00'
        ])

        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Dest User',
            '--type', 'savings'
        ])

        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'transfer'
        ], input='1\n2\n500.00\n')

        assert result.exit_code == 0
        assert "✅ Transfer successful!" in result.output

    def test_transfer_error(self, runner, temp_db_path):
        """Test transfer error handling."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'transfer',
            '--from-account', '999',
            '--to-account', '888',
            '--amount', '100.00'
        ])

        assert result.exit_code == 0
        assert "❌ Error:" in result.output

    def test_balance_success(self, runner, temp_db_path):
        """Test successful balance check through CLI."""
        # First create an account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1000.00',
            '--minimum-balance', '100.00'
        ])

        # Check balance
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'balance',
            '--account-id', '1'
        ])

        assert result.exit_code == 0
        assert "💰 Account Balance" in result.output
        assert "Test User" in result.output
        assert "1,000.00 ₽" in result.output

    def test_balance_interactive(self, runner, temp_db_path):
        """Test interactive balance check."""
        # First create an account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Test User',
            '--type', 'checking',
            '--initial-deposit', '1500.00'
        ])

        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'balance'
        ], input='1\n')

        assert result.exit_code == 0
        assert "💰 Account Balance" in result.output

    def test_balance_error(self, runner, temp_db_path):
        """Test balance check error handling."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'balance',
            '--account-id', '999'
        ])

        assert result.exit_code == 0
        assert "❌ Account not found" in result.output

    def test_main_function(self):
        """Test main function."""
        # Test that main function can be called without errors
        # We can't easily test the actual execution, but we can test import
        from bank_system.cli import main
        assert callable(main)

    def test_cli_with_transactions_history(self, runner, temp_db_path):
        """Test CLI showing account with transaction history."""
        # Create account and make some transactions
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'History User',
            '--type', 'checking',
            '--initial-deposit', '1000.00'
        ])

        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'deposit',
            '--account-id', '1',
            '--amount', '200.00'
        ])

        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'withdraw',
            '--account-id', '1',
            '--amount', '150.00'
        ])

        # Show account with history
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'show-account',
            '--account-id', '1'
        ])

        assert result.exit_code == 0
        assert "📋 Recent Transactions" in result.output
        assert "withdrawal" in result.output.lower()
        assert "deposit" in result.output.lower()

    def test_cli_currency_parsing_in_commands(self, runner, temp_db_path):
        """Test currency parsing in various CLI commands."""
        # Create account
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Currency Test',
            '--type', 'checking',
            '--initial-deposit', '1,500.50',  # Test comma in amount
            '--minimum-balance', '100.00'
        ])

        # Test deposit with currency symbol
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'deposit',
            '--account-id', '1',
            '--amount', '250.75₽'
        ])

        assert result.exit_code == 0
        assert "✅ Deposit successful!" in result.output

    def test_show_account_with_all_fields(self, runner, temp_db_path):
        """Test show account command displaying all fields correctly."""
        # Create business account with all features
        runner.invoke(cli, [
            '--db-path', temp_db_path,
            'create-account',
            '--name', 'Бизнес Клиент',
            '--type', 'business',
            '--initial-deposit', '50000.00',
            '--minimum-balance', '5000.00'
        ])

        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'show-account',
            '--account-id', '1'
        ])

        assert result.exit_code == 0
        assert "Account ID: 1" in result.output
        assert "Бизнес Клиент" in result.output
        assert "business" in result.output
        assert "50,000.00 ₽" in result.output
        assert "5,000.00 ₽" in result.output
        assert "Status: Active" in result.output

    def test_cli_error_handling_with_exception(self, runner, temp_db_path):
        """Test CLI error handling when exceptions occur."""
        # This will test the generic exception handling in show_account
        with patch('bank_system.cli.BankCLI') as mock_cli_class:
            mock_instance = Mock()
            mock_instance.account_manager.get_account_summary.side_effect = Exception("Test error")
            mock_cli_class.return_value = mock_instance

            result = runner.invoke(cli, [
                '--db-path', temp_db_path,
                'show-account',
                '--account-id', '1'
            ])

            assert result.exit_code == 0
            assert "❌ Error:" in result.output
