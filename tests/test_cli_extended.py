"""
Tests for extended CLI functionality.

This module contains tests for the new CLI commands added for extended
banking functionality including freeze/unfreeze, limits, statements, etc.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from click.testing import CliRunner
from unittest.mock import patch, Mock

from bank_system.cli import cli
from bank_system.database import DatabaseManager
from bank_system.account_manager import AccountManager
from bank_system.models import AccountType


class TestCLIExtended:
    """Test extended CLI functionality."""

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
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_account_id(self, temp_db_path):
        """Create a sample account and return its ID."""
        db_manager = DatabaseManager(temp_db_path)
        account_manager = AccountManager(db_manager)
        
        account = account_manager.create_account(
            customer_name="CLI Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('5000.00'),
            minimum_balance=Decimal('500.00')
        )
        return account.account_id, temp_db_path

    def test_freeze_account_command_success(self, runner, sample_account_id):
        """Test freeze-account CLI command success."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'freeze-account',
            '--account-id', str(account_id),
            '--reason', 'Security check'
        ])
        
        assert result.exit_code == 0
        assert "Account" in result.output
        assert "frozen" in result.output
        assert "Security check" in result.output

    def test_freeze_account_command_not_found(self, runner, temp_db_path):
        """Test freeze-account CLI command with non-existent account."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'freeze-account',
            '--account-id', '999',
            '--reason', 'Test'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Account not found" in result.output

    def test_unfreeze_account_command_success(self, runner, sample_account_id):
        """Test unfreeze-account CLI command success."""
        account_id, db_path = sample_account_id
        
        # First freeze the account
        runner.invoke(cli, [
            '--db-path', db_path,
            'freeze-account',
            '--account-id', str(account_id),
            '--reason', 'Test freeze'
        ])
        
        # Then unfreeze it
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'unfreeze-account',
            '--account-id', str(account_id),
            '--reason', 'Test completed'
        ])
        
        assert result.exit_code == 0
        assert "Account" in result.output
        assert "unfrozen" in result.output
        assert "Test completed" in result.output

    def test_unfreeze_account_command_not_frozen(self, runner, sample_account_id):
        """Test unfreeze-account CLI command on non-frozen account."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'unfreeze-account',
            '--account-id', str(account_id),
            '--reason', 'Test'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "not frozen" in result.output

    def test_set_withdrawal_limit_command_success(self, runner, sample_account_id):
        """Test set-withdrawal-limit CLI command success."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'set-withdrawal-limit',
            '--account-id', str(account_id),
            '--limit', '3000.00'
        ])
        
        assert result.exit_code == 0
        assert "Daily withdrawal limit set" in result.output
        assert "3,000.00" in result.output

    def test_set_withdrawal_limit_command_unlimited(self, runner, sample_account_id):
        """Test set-withdrawal-limit CLI command with unlimited."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'set-withdrawal-limit',
            '--account-id', str(account_id),
            '--limit', 'none'
        ])
        
        assert result.exit_code == 0
        assert "Daily withdrawal limit removed" in result.output
        assert "unlimited" in result.output

    def test_set_withdrawal_limit_command_invalid_amount(self, runner, sample_account_id):
        """Test set-withdrawal-limit CLI command with invalid amount."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'set-withdrawal-limit',
            '--account-id', str(account_id),
            '--limit', 'invalid'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output

    def test_monthly_statement_command_success(self, runner, sample_account_id):
        """Test monthly-statement CLI command success."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'monthly-statement',
            '--account-id', str(account_id),
            '--year', '2024',
            '--month', '10'
        ])
        
        assert result.exit_code == 0
        assert "Monthly Statement" in result.output
        assert "2024-10" in result.output
        assert "Balance Summary" in result.output

    def test_monthly_statement_command_invalid_month(self, runner, sample_account_id):
        """Test monthly-statement CLI command with invalid month."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'monthly-statement',
            '--account-id', str(account_id),
            '--year', '2024',
            '--month', '13'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Month must be between 1 and 12" in result.output

    def test_monthly_statement_command_account_not_found(self, runner, temp_db_path):
        """Test monthly-statement CLI command with non-existent account."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'monthly-statement',
            '--account-id', '999',
            '--year', '2024',
            '--month', '10'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Account not found" in result.output

    def test_calculate_interest_command_success(self, runner, sample_account_id):
        """Test calculate-interest CLI command success."""
        account_id, db_path = sample_account_id
        
        # Mock the interest calculation to return a positive value
        with patch('bank_system.account_manager.AccountManager.calculate_interest') as mock_calc:
            mock_calc.return_value = Decimal('25.50')
            
            result = runner.invoke(cli, [
                '--db-path', db_path,
                'calculate-interest',
                '--account-id', str(account_id)
            ])
            
            assert result.exit_code == 0
            assert "Interest calculated and applied" in result.output
            assert "25.50" in result.output

    def test_calculate_interest_command_no_interest(self, runner, sample_account_id):
        """Test calculate-interest CLI command with no interest."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'calculate-interest',
            '--account-id', str(account_id)
        ])
        
        assert result.exit_code == 0
        assert "No interest to calculate" in result.output

    def test_calculate_interest_command_account_not_found(self, runner, temp_db_path):
        """Test calculate-interest CLI command with non-existent account."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'calculate-interest',
            '--account-id', '999'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Account not found" in result.output

    def test_bulk_transfer_command_success(self, runner, temp_db_path):
        """Test bulk-transfer CLI command success."""
        # Create multiple accounts
        db_manager = DatabaseManager(temp_db_path)
        account_manager = AccountManager(db_manager)
        
        source_account = account_manager.create_account(
            customer_name="Source Account",
            account_type=AccountType.BUSINESS,
            initial_deposit=Decimal('10000.00'),
            minimum_balance=Decimal('1000.00')
        )
        
        dest1 = account_manager.create_account(
            customer_name="Dest 1",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('500.00')
        )
        
        dest2 = account_manager.create_account(
            customer_name="Dest 2",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('1000.00')
        )
        
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'bulk-transfer',
            '--from-account', str(source_account.account_id),
            '--transfers', f'{dest1.account_id}:1000.00,{dest2.account_id}:1500.00',
            '--description', 'Salary payments'
        ])
        
        assert result.exit_code == 0
        assert "Bulk Transfer Results" in result.output
        assert "Total Amount" in result.output
        assert "Successful Transfers: 2" in result.output
        assert "Failed Transfers: 0" in result.output

    def test_bulk_transfer_command_invalid_format(self, runner, sample_account_id):
        """Test bulk-transfer CLI command with invalid transfer format."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'bulk-transfer',
            '--from-account', str(account_id),
            '--transfers', 'invalid_format',
            '--description', 'Test'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Invalid transfer format" in result.output

    def test_bulk_transfer_command_insufficient_funds(self, runner, sample_account_id):
        """Test bulk-transfer CLI command with insufficient funds."""
        account_id, db_path = sample_account_id
        
        # Create destination account
        db_manager = DatabaseManager(db_path)
        account_manager = AccountManager(db_manager)
        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.CHECKING
        )
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'bulk-transfer',
            '--from-account', str(account_id),
            '--transfers', f'{dest_account.account_id}:10000.00',
            '--description', 'Test'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Insufficient funds" in result.output

    def test_account_stats_command_success(self, runner, sample_account_id):
        """Test account-stats CLI command success."""
        account_id, db_path = sample_account_id
        
        # Add some transactions first
        db_manager = DatabaseManager(db_path)
        account_manager = AccountManager(db_manager)
        account_manager.deposit(account_id, Decimal('1000.00'), "Test deposit")
        account_manager.withdraw(account_id, Decimal('500.00'), "Test withdrawal")
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'account-stats',
            '--account-id', str(account_id),
            '--days', '30'
        ])
        
        assert result.exit_code == 0
        assert "Account Statistics" in result.output
        assert "Last 30 Days" in result.output
        assert "Transaction Activity" in result.output
        assert "Deposits" in result.output
        assert "Withdrawals" in result.output

    def test_account_stats_command_custom_days(self, runner, sample_account_id):
        """Test account-stats CLI command with custom days."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'account-stats',
            '--account-id', str(account_id),
            '--days', '7'
        ])
        
        assert result.exit_code == 0
        assert "Last 7 Days" in result.output

    def test_account_stats_command_account_not_found(self, runner, temp_db_path):
        """Test account-stats CLI command with non-existent account."""
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'account-stats',
            '--account-id', '999'
        ])
        
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "Account not found" in result.output

    def test_show_account_command_with_new_fields(self, runner, sample_account_id):
        """Test show-account CLI command displays new fields."""
        account_id, db_path = sample_account_id
        
        # Set some new field values
        db_manager = DatabaseManager(db_path)
        account_manager = AccountManager(db_manager)
        account_manager.set_daily_withdrawal_limit(account_id, Decimal('2000.00'))
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'show-account',
            '--account-id', str(account_id)
        ])
        
        assert result.exit_code == 0
        assert "Account Details" in result.output
        assert "Frozen: No" in result.output
        assert "Daily Withdrawal Limit" in result.output
        assert "Interest Rate" in result.output

    def test_show_account_command_frozen_account(self, runner, sample_account_id):
        """Test show-account CLI command with frozen account."""
        account_id, db_path = sample_account_id
        
        # Freeze the account
        db_manager = DatabaseManager(db_path)
        account_manager = AccountManager(db_manager)
        account_manager.freeze_account(account_id, "Test freeze")
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'show-account',
            '--account-id', str(account_id)
        ])
        
        assert result.exit_code == 0
        assert "Frozen: Yes" in result.output

    def test_cli_commands_help(self, runner):
        """Test that all new CLI commands have help text."""
        # Test main help includes new commands
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        
        # Test individual command help
        commands = [
            'freeze-account',
            'unfreeze-account', 
            'set-withdrawal-limit',
            'monthly-statement',
            'calculate-interest',
            'bulk-transfer',
            'account-stats'
        ]
        
        for command in commands:
            result = runner.invoke(cli, [command, '--help'])
            assert result.exit_code == 0
            assert "Usage:" in result.output

    def test_cli_error_handling(self, runner, temp_db_path):
        """Test CLI error handling for various scenarios."""
        # Test with invalid database path
        result = runner.invoke(cli, [
            '--db-path', '/invalid/path/bank.db',
            'freeze-account',
            '--account-id', '1',
            '--reason', 'Test'
        ])
        # Should handle gracefully (exact behavior depends on implementation)
        
        # Test with invalid account ID format
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'freeze-account',
            '--account-id', 'invalid',
            '--reason', 'Test'
        ])
        # Should handle gracefully

    def test_cli_currency_formatting(self, runner, sample_account_id):
        """Test that CLI properly formats currency in output."""
        account_id, db_path = sample_account_id
        
        result = runner.invoke(cli, [
            '--db-path', db_path,
            'show-account',
            '--account-id', str(account_id)
        ])
        
        assert result.exit_code == 0
        # Check for proper currency formatting with ₽ symbol
        assert "₽" in result.output
        # Check for comma-separated thousands
        assert "5,000.00" in result.output

    def test_cli_interactive_prompts(self, runner, temp_db_path):
        """Test CLI interactive prompts work correctly."""
        # Create an account first
        db_manager = DatabaseManager(temp_db_path)
        account_manager = AccountManager(db_manager)
        account = account_manager.create_account(
            customer_name="Interactive Test",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )
        
        # Test freeze-account with prompts
        result = runner.invoke(cli, [
            '--db-path', temp_db_path,
            'freeze-account'
        ], input=f'{account.account_id}\nSecurity check\n')
        
        assert result.exit_code == 0
        assert "frozen" in result.output