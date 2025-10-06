"""
Tests for extended AccountManager functionality.

This module contains comprehensive tests for the new AccountManager methods,
including freeze/unfreeze, daily limits, interest calculation, bulk transfers,
monthly statements, and account statistics.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

from bank_system.account_manager import AccountManager
from bank_system.database import DatabaseManager
from bank_system.models import Account, Transaction, AccountType, TransactionType


class TestAccountManagerExtended:
    """Test extended AccountManager functionality."""

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

    @pytest.fixture
    def sample_account(self, account_manager):
        """Create a sample account for testing."""
        return account_manager.create_account(
            customer_name="Тест Расширенный",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('2000.00'),
            minimum_balance=Decimal('200.00')
        )

    @pytest.fixture
    def savings_account(self, account_manager):
        """Create a savings account with interest rate for testing."""
        account = account_manager.create_account(
            customer_name="Сберегательный Счет",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('10000.00'),
            minimum_balance=Decimal('1000.00')
        )
        return account

    # Freeze/Unfreeze Account Tests
    def test_freeze_account_success(self, account_manager, sample_account):
        """Test successful account freezing."""
        result = account_manager.freeze_account(sample_account.account_id, "Security check")
        assert result is True

        # Verify account is frozen
        account = account_manager.get_account(sample_account.account_id)
        assert account.is_frozen is True

        # Verify transaction was recorded
        transactions = account_manager.get_account_history(sample_account.account_id, limit=1)
        assert len(transactions) > 0
        freeze_tx = transactions[0]
        assert freeze_tx.transaction_type == TransactionType.FEE
        assert "frozen" in freeze_tx.description.lower()

    def test_freeze_account_not_found(self, account_manager):
        """Test freezing non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.freeze_account(999, "Test")

    def test_freeze_account_already_frozen(self, account_manager, sample_account):
        """Test freezing already frozen account."""
        # First freeze
        account_manager.freeze_account(sample_account.account_id, "First freeze")
        
        # Try to freeze again
        with pytest.raises(ValueError, match="Account is already frozen"):
            account_manager.freeze_account(sample_account.account_id, "Second freeze")

    def test_freeze_inactive_account(self, account_manager):
        """Test freezing inactive account."""
        # Create and deactivate account
        account = account_manager.create_account(
            customer_name="Inactive Test",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('0.00'),
            minimum_balance=Decimal('0.00')
        )
        account_manager.deactivate_account(account.account_id)

        with pytest.raises(ValueError, match="Cannot freeze inactive account"):
            account_manager.freeze_account(account.account_id, "Test")

    def test_unfreeze_account_success(self, account_manager, sample_account):
        """Test successful account unfreezing."""
        # First freeze the account
        account_manager.freeze_account(sample_account.account_id, "Security check")
        
        # Then unfreeze it
        result = account_manager.unfreeze_account(sample_account.account_id, "Check completed")
        assert result is True

        # Verify account is unfrozen
        account = account_manager.get_account(sample_account.account_id)
        assert account.is_frozen is False

        # Verify transaction was recorded
        transactions = account_manager.get_account_history(sample_account.account_id, limit=1)
        unfreeze_tx = transactions[0]
        assert unfreeze_tx.transaction_type == TransactionType.FEE
        assert "unfrozen" in unfreeze_tx.description.lower()

    def test_unfreeze_account_not_found(self, account_manager):
        """Test unfreezing non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.unfreeze_account(999, "Test")

    def test_unfreeze_account_not_frozen(self, account_manager, sample_account):
        """Test unfreezing account that is not frozen."""
        with pytest.raises(ValueError, match="Account is not frozen"):
            account_manager.unfreeze_account(sample_account.account_id, "Test")

    # Daily Withdrawal Limit Tests
    def test_set_daily_withdrawal_limit_success(self, account_manager, sample_account):
        """Test setting daily withdrawal limit."""
        limit = Decimal('5000.00')
        result = account_manager.set_daily_withdrawal_limit(sample_account.account_id, limit)
        assert result is True

        # Verify limit was set
        account = account_manager.get_account(sample_account.account_id)
        assert account.daily_withdrawal_limit == limit

        # Verify transaction was recorded
        transactions = account_manager.get_account_history(sample_account.account_id, limit=1)
        limit_tx = transactions[0]
        assert limit_tx.transaction_type == TransactionType.FEE
        assert "5000.00 RUB" in limit_tx.description

    def test_set_daily_withdrawal_limit_none(self, account_manager, sample_account):
        """Test removing daily withdrawal limit."""
        # First set a limit
        account_manager.set_daily_withdrawal_limit(sample_account.account_id, Decimal('3000.00'))
        
        # Then remove it
        result = account_manager.set_daily_withdrawal_limit(sample_account.account_id, None)
        assert result is True

        # Verify limit was removed
        account = account_manager.get_account(sample_account.account_id)
        assert account.daily_withdrawal_limit is None

        # Verify transaction was recorded
        transactions = account_manager.get_account_history(sample_account.account_id, limit=1)
        limit_tx = transactions[0]
        assert "unlimited" in limit_tx.description.lower()

    def test_set_daily_withdrawal_limit_not_found(self, account_manager):
        """Test setting limit on non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.set_daily_withdrawal_limit(999, Decimal('1000.00'))

    def test_set_daily_withdrawal_limit_negative(self, account_manager, sample_account):
        """Test setting negative daily withdrawal limit."""
        with pytest.raises(ValueError, match="Daily withdrawal limit cannot be negative"):
            account_manager.set_daily_withdrawal_limit(sample_account.account_id, Decimal('-1000.00'))

    def test_withdraw_with_daily_limit_enforcement(self, account_manager, sample_account):
        """Test withdrawal with daily limit enforcement."""
        # Set daily limit
        daily_limit = Decimal('1000.00')
        account_manager.set_daily_withdrawal_limit(sample_account.account_id, daily_limit)

        # First withdrawal should succeed
        result = account_manager.withdraw(sample_account.account_id, Decimal('600.00'))
        assert result is True

        # Second withdrawal that would exceed limit should fail
        with pytest.raises(ValueError, match="Daily withdrawal limit exceeded"):
            account_manager.withdraw(sample_account.account_id, Decimal('500.00'))

        # Smaller withdrawal within remaining limit should succeed
        result = account_manager.withdraw(sample_account.account_id, Decimal('300.00'))
        assert result is True

    def test_withdraw_frozen_account(self, account_manager, sample_account):
        """Test withdrawal from frozen account."""
        # Freeze the account
        account_manager.freeze_account(sample_account.account_id, "Test freeze")

        # Withdrawal should fail
        with pytest.raises(ValueError, match="Account is frozen"):
            account_manager.withdraw(sample_account.account_id, Decimal('100.00'))

    # Interest Calculation Tests
    def test_calculate_interest_success(self, account_manager):
        """Test successful interest calculation."""
        # Create account with interest rate first (without mocking)
        account = account_manager.create_account(
            customer_name="Interest Test",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('10000.00')
        )
        
        # Ensure account was created successfully
        assert account is not None, "Account creation failed"
        
        # Store creation time before patching
        creation_time = datetime.now()
        
        # Manually set interest rate and last calculation using database connection
        import sqlite3
        with sqlite3.connect(account_manager.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts
                SET interest_rate = ?, last_interest_calculation = ?
                WHERE account_id = ?
            """, (2.5, creation_time, account.account_id))
            conn.commit()

        # Now patch datetime for the interest calculation
        with patch('bank_system.account_manager.datetime') as mock_datetime:
            # Mock current time to be 30 days after account creation
            current_time = creation_time + timedelta(days=30)
            mock_datetime.now.return_value = current_time
            
            # Calculate interest
            interest = account_manager.calculate_interest(account.account_id)
        
        # Verify interest was calculated (2.5% annual rate for 30 days)
        expected_interest = Decimal('10000.00') * Decimal('2.5') * Decimal('30') / Decimal('365') / Decimal('100')
        expected_interest = expected_interest.quantize(Decimal('0.01'))
        
        assert interest == expected_interest
        assert interest > 0

        # Verify balance was updated
        new_balance = account_manager.get_balance(account.account_id)
        assert new_balance == Decimal('10000.00') + interest

    def test_calculate_interest_account_not_found(self, account_manager):
        """Test interest calculation on non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.calculate_interest(999)

    def test_calculate_interest_inactive_account(self, account_manager):
        """Test interest calculation on inactive account."""
        account = account_manager.create_account(
            customer_name="Inactive Interest",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('0.00'),
            minimum_balance=Decimal('0.00')
        )
        account_manager.deactivate_account(account.account_id)

        with pytest.raises(ValueError, match="Account is not active"):
            account_manager.calculate_interest(account.account_id)

    def test_calculate_interest_zero_rate(self, account_manager, sample_account):
        """Test interest calculation with zero interest rate."""
        interest = account_manager.calculate_interest(sample_account.account_id)
        assert interest == Decimal('0.00')

    @patch('bank_system.account_manager.datetime')
    def test_calculate_interest_insufficient_time(self, mock_datetime, account_manager, sample_account):
        """Test interest calculation when insufficient time has passed."""
        # Mock current time to be same as creation time
        creation_time = datetime.now()
        mock_datetime.now.return_value = creation_time

        interest = account_manager.calculate_interest(sample_account.account_id)
        assert interest == Decimal('0.00')

    # Monthly Statement Tests
    def test_get_monthly_statement_success(self, account_manager, sample_account):
        """Test getting monthly statement."""
        # Create some transactions in October 2024
        test_date = datetime(2024, 10, 15)
        
        with patch('bank_system.account_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_date
            
            # Make some transactions
            account_manager.deposit(sample_account.account_id, Decimal('500.00'), "October deposit")
            account_manager.withdraw(sample_account.account_id, Decimal('300.00'), "October withdrawal")

        # Get monthly statement
        statement = account_manager.get_monthly_statement(sample_account.account_id, 2024, 10)
        
        assert statement is not None
        assert statement['account'].account_id == sample_account.account_id
        assert statement['period'] == "2024-10"
        assert 'opening_balance' in statement
        assert 'closing_balance' in statement
        assert 'total_deposits' in statement
        assert 'total_withdrawals' in statement
        assert 'transactions' in statement

    def test_get_monthly_statement_account_not_found(self, account_manager):
        """Test getting statement for non-existent account."""
        statement = account_manager.get_monthly_statement(999, 2024, 10)
        assert statement is None

    def test_get_monthly_statement_no_transactions(self, account_manager, sample_account):
        """Test getting statement with no transactions."""
        statement = account_manager.get_monthly_statement(sample_account.account_id, 2024, 12)
        
        assert statement is not None
        assert statement['transaction_count'] == 0
        assert statement['total_deposits'] == Decimal('0.00')
        assert statement['total_withdrawals'] == Decimal('0.00')

    # Bulk Transfer Tests
    def test_bulk_transfer_success(self, account_manager):
        """Test successful bulk transfer."""
        # Create source account
        source_account = account_manager.create_account(
            customer_name="Source Bulk",
            account_type=AccountType.BUSINESS,
            initial_deposit=Decimal('10000.00'),
            minimum_balance=Decimal('1000.00')
        )
        
        # Create destination accounts
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

        # Prepare transfers
        transfers = [
            {'to_account_id': dest1.account_id, 'amount': Decimal('2000.00')},
            {'to_account_id': dest2.account_id, 'amount': Decimal('1500.00')}
        ]

        # Execute bulk transfer
        result = account_manager.bulk_transfer(source_account.account_id, transfers, "Salary payments")

        assert result['successful_count'] == 2
        assert result['failed_count'] == 0
        assert result['total_amount'] == Decimal('3500.00')

        # Verify balances
        source_balance = account_manager.get_balance(source_account.account_id)
        dest1_balance = account_manager.get_balance(dest1.account_id)
        dest2_balance = account_manager.get_balance(dest2.account_id)

        assert source_balance == Decimal('6500.00')  # 10000 - 3500
        assert dest1_balance == Decimal('2500.00')   # 500 + 2000
        assert dest2_balance == Decimal('2500.00')   # 1000 + 1500

    def test_bulk_transfer_empty_list(self, account_manager, sample_account):
        """Test bulk transfer with empty transfer list."""
        with pytest.raises(ValueError, match="Transfer list cannot be empty"):
            account_manager.bulk_transfer(sample_account.account_id, [], "Test")

    def test_bulk_transfer_insufficient_funds(self, account_manager, sample_account):
        """Test bulk transfer with insufficient funds."""
        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.CHECKING
        )

        transfers = [
            {'to_account_id': dest_account.account_id, 'amount': Decimal('5000.00')}
        ]

        with pytest.raises(ValueError, match="Insufficient funds"):
            account_manager.bulk_transfer(sample_account.account_id, transfers, "Test")

    def test_bulk_transfer_frozen_source_account(self, account_manager, sample_account):
        """Test bulk transfer from frozen source account."""
        # Freeze source account
        account_manager.freeze_account(sample_account.account_id, "Test freeze")

        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.CHECKING
        )

        transfers = [
            {'to_account_id': dest_account.account_id, 'amount': Decimal('100.00')}
        ]

        with pytest.raises(ValueError, match="Source account is frozen"):
            account_manager.bulk_transfer(sample_account.account_id, transfers, "Test")

    def test_bulk_transfer_invalid_destination(self, account_manager, sample_account):
        """Test bulk transfer with invalid destination account."""
        transfers = [
            {'to_account_id': 999, 'amount': Decimal('100.00')}
        ]

        with pytest.raises(ValueError, match="Destination account 999 not found"):
            account_manager.bulk_transfer(sample_account.account_id, transfers, "Test")

    def test_bulk_transfer_same_account(self, account_manager, sample_account):
        """Test bulk transfer to same account."""
        transfers = [
            {'to_account_id': sample_account.account_id, 'amount': Decimal('100.00')}
        ]

        with pytest.raises(ValueError, match="Cannot transfer to the same account"):
            account_manager.bulk_transfer(sample_account.account_id, transfers, "Test")

    # Account Statistics Tests
    def test_get_account_statistics_success(self, account_manager, sample_account):
        """Test getting account statistics."""
        # Create some transactions
        account_manager.deposit(sample_account.account_id, Decimal('1000.00'), "Large deposit")
        account_manager.withdraw(sample_account.account_id, Decimal('500.00'), "Large withdrawal")
        account_manager.deposit(sample_account.account_id, Decimal('200.00'), "Small deposit")

        stats = account_manager.get_account_statistics(sample_account.account_id, days=30)

        assert stats is not None
        assert stats['account'].account_id == sample_account.account_id
        assert stats['period_days'] == 30
        assert stats['total_transactions'] > 0
        assert 'deposits' in stats
        assert 'withdrawals' in stats
        assert 'largest_deposit' in stats
        assert 'largest_withdrawal' in stats

        # Check deposit statistics
        # Note: sample_account has initial_deposit of 2000.00, so largest_deposit should be 2000.00
        assert stats['deposits']['count'] >= 2
        assert stats['deposits']['total'] >= Decimal('1200.00')
        assert stats['largest_deposit'] == Decimal('2000.00')  # Initial deposit from fixture

        # Check withdrawal statistics
        assert stats['withdrawals']['count'] >= 1
        assert stats['largest_withdrawal'] == Decimal('500.00')

    def test_get_account_statistics_account_not_found(self, account_manager):
        """Test getting statistics for non-existent account."""
        stats = account_manager.get_account_statistics(999, days=30)
        assert stats is None

    def test_get_account_statistics_no_transactions(self, account_manager):
        """Test getting statistics for account with no transactions."""
        account = account_manager.create_account(
            customer_name="No Transactions",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('0.00')
        )

        stats = account_manager.get_account_statistics(account.account_id, days=30)

        assert stats is not None
        assert stats['total_transactions'] == 0
        assert stats['deposits']['count'] == 0
        assert stats['withdrawals']['count'] == 0
        assert stats['largest_deposit'] == Decimal('0.00')
        assert stats['largest_withdrawal'] == Decimal('0.00')

    def test_get_account_statistics_custom_period(self, account_manager, sample_account):
        """Test getting statistics for custom period."""
        # Create transactions
        account_manager.deposit(sample_account.account_id, Decimal('100.00'))
        
        # Get statistics for 7 days
        stats = account_manager.get_account_statistics(sample_account.account_id, days=7)
        
        assert stats is not None
        assert stats['period_days'] == 7