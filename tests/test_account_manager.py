"""
Tests for the account_manager module.

This module contains comprehensive tests for the AccountManager class,
including business logic, validation, and error handling.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from unittest.mock import Mock, patch

from bank_system.account_manager import AccountManager
from bank_system.database import DatabaseManager
from bank_system.models import Account, Transaction, AccountType, TransactionType


class TestAccountManager:
    """Test AccountManager class."""

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
            customer_name="Тест Клиент",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('100.00')
        )

    def test_generate_account_number_format(self, account_manager):
        """Test account number generation format."""
        account_number = account_manager.generate_account_number()

        assert isinstance(account_number, str)
        assert account_number.startswith("BANK-")
        assert len(account_number.split("-")) == 3

        # Check date format (BANK-YYYYMMDD-XXXX)
        parts = account_number.split("-")
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # 8-character UUID part

    def test_generate_account_number_uniqueness(self, account_manager):
        """Test that generated account numbers are unique."""
        numbers = set()
        for _ in range(10):
            number = account_manager.generate_account_number()
            assert number not in numbers
            numbers.add(number)

    def test_create_account_success(self, account_manager):
        """Test successful account creation."""
        account = account_manager.create_account(
            customer_name="Иван Петров",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('5000.00'),
            minimum_balance=Decimal('500.00')
        )

        assert account is not None
        assert account.customer_name == "Иван Петров"
        assert account.account_type == AccountType.SAVINGS
        assert account.balance == Decimal('5000.00')
        assert account.minimum_balance == Decimal('500.00')
        assert account.is_active is True
        assert account.account_id is not None

    def test_create_account_empty_name(self, account_manager):
        """Test account creation with empty customer name."""
        with pytest.raises(ValueError, match="Customer name cannot be empty"):
            account_manager.create_account(
                customer_name="",
                account_type=AccountType.CHECKING
            )

    def test_create_account_whitespace_name(self, account_manager):
        """Test account creation with whitespace-only name."""
        with pytest.raises(ValueError, match="Customer name cannot be empty"):
            account_manager.create_account(
                customer_name="   ",
                account_type=AccountType.CHECKING
            )

    def test_create_account_negative_initial_deposit(self, account_manager):
        """Test account creation with negative initial deposit."""
        with pytest.raises(ValueError, match="Initial deposit cannot be negative"):
            account_manager.create_account(
                customer_name="Test User",
                account_type=AccountType.CHECKING,
                initial_deposit=Decimal('-100.00')
            )

    def test_create_account_negative_minimum_balance(self, account_manager):
        """Test account creation with negative minimum balance."""
        with pytest.raises(ValueError, match="Minimum balance cannot be negative"):
            account_manager.create_account(
                customer_name="Test User",
                account_type=AccountType.CHECKING,
                minimum_balance=Decimal('-50.00')
            )

    def test_create_account_initial_deposit_below_minimum(self, account_manager):
        """Test account creation with initial deposit below minimum balance."""
        with pytest.raises(ValueError, match="Initial deposit must be at least the minimum balance"):
            account_manager.create_account(
                customer_name="Test User",
                account_type=AccountType.CHECKING,
                initial_deposit=Decimal('100.00'),
                minimum_balance=Decimal('200.00')
            )

    def test_create_account_trims_whitespace(self, account_manager):
        """Test that account creation trims customer name whitespace."""
        account = account_manager.create_account(
            customer_name="  Иван Петров  ",
            account_type=AccountType.CHECKING
        )

        assert account.customer_name == "Иван Петров"

    def test_create_account_with_zero_initial_deposit(self, account_manager):
        """Test account creation with zero initial deposit."""
        account = account_manager.create_account(
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('0.00')
        )

        assert account is not None
        assert account.balance == Decimal('0.00')

        # Should not create initial deposit transaction
        transactions = account_manager.get_account_history(account.account_id)
        assert len(transactions) == 0

    def test_deposit_success(self, account_manager, sample_account):
        """Test successful deposit."""
        result = account_manager.deposit(
            sample_account.account_id,
            Decimal('500.00'),
            "Test deposit"
        )

        assert result is True
        new_balance = account_manager.get_balance(sample_account.account_id)
        assert new_balance == Decimal('1500.00')

    def test_deposit_zero_amount(self, account_manager, sample_account):
        """Test deposit with zero amount."""
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account_manager.deposit(sample_account.account_id, Decimal('0.00'))

    def test_deposit_negative_amount(self, account_manager, sample_account):
        """Test deposit with negative amount."""
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            account_manager.deposit(sample_account.account_id, Decimal('-100.00'))

    def test_deposit_nonexistent_account(self, account_manager):
        """Test deposit to non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.deposit(999, Decimal('100.00'))

    def test_deposit_inactive_account(self, account_manager):
        """Test deposit to inactive account."""
        # Create account without minimum balance for easy deactivation
        account = account_manager.create_account(
            customer_name="Test Inactive",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('0.00')
        )

        # Empty and deactivate the account
        account_manager.withdraw(account.account_id, Decimal('1000.00'))
        account_manager.deactivate_account(account.account_id)

        with pytest.raises(ValueError, match="Account is not active"):
            account_manager.deposit(account.account_id, Decimal('100.00'))

    def test_withdraw_success(self, account_manager, sample_account):
        """Test successful withdrawal."""
        result = account_manager.withdraw(
            sample_account.account_id,
            Decimal('300.00'),
            "Test withdrawal"
        )

        assert result is True
        new_balance = account_manager.get_balance(sample_account.account_id)
        assert new_balance == Decimal('700.00')

    def test_withdraw_zero_amount(self, account_manager, sample_account):
        """Test withdrawal with zero amount."""
        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            account_manager.withdraw(sample_account.account_id, Decimal('0.00'))

    def test_withdraw_negative_amount(self, account_manager, sample_account):
        """Test withdrawal with negative amount."""
        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            account_manager.withdraw(sample_account.account_id, Decimal('-100.00'))

    def test_withdraw_insufficient_funds(self, account_manager, sample_account):
        """Test withdrawal with insufficient funds."""
        with pytest.raises(ValueError, match="Insufficient funds"):
            account_manager.withdraw(sample_account.account_id, Decimal('1000.00'))

    def test_withdraw_nonexistent_account(self, account_manager):
        """Test withdrawal from non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.withdraw(999, Decimal('100.00'))

    def test_withdraw_inactive_account(self, account_manager):
        """Test withdrawal from inactive account."""
        # Create account without minimum balance for easy deactivation
        account = account_manager.create_account(
            customer_name="Test Inactive Withdraw",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('0.00')
        )

        # Empty and deactivate the account
        account_manager.withdraw(account.account_id, Decimal('1000.00'))
        account_manager.deactivate_account(account.account_id)

        with pytest.raises(ValueError, match="Account is not active"):
            account_manager.withdraw(account.account_id, Decimal('50.00'))

    def test_transfer_success(self, account_manager):
        """Test successful transfer between accounts."""
        # Create two accounts
        source_account = account_manager.create_account(
            customer_name="Source Account",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('2000.00'),
            minimum_balance=Decimal('100.00')
        )
        dest_account = account_manager.create_account(
            customer_name="Destination Account",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('500.00')
        )

        result = account_manager.transfer(
            source_account.account_id,
            dest_account.account_id,
            Decimal('800.00'),
            "Test transfer"
        )

        assert result is True

        source_balance = account_manager.get_balance(source_account.account_id)
        dest_balance = account_manager.get_balance(dest_account.account_id)

        assert source_balance == Decimal('1200.00')
        assert dest_balance == Decimal('1300.00')

    def test_transfer_zero_amount(self, account_manager, sample_account):
        """Test transfer with zero amount."""
        dest_account = account_manager.create_account(
            customer_name="Dest Account",
            account_type=AccountType.SAVINGS
        )

        with pytest.raises(ValueError, match="Transfer amount must be positive"):
            account_manager.transfer(
                sample_account.account_id,
                dest_account.account_id,
                Decimal('0.00')
            )

    def test_transfer_same_account(self, account_manager, sample_account):
        """Test transfer to same account."""
        with pytest.raises(ValueError, match="Cannot transfer to the same account"):
            account_manager.transfer(
                sample_account.account_id,
                sample_account.account_id,
                Decimal('100.00')
            )

    def test_transfer_nonexistent_source_account(self, account_manager, sample_account):
        """Test transfer from non-existent source account."""
        with pytest.raises(ValueError, match="Source account not found"):
            account_manager.transfer(999, sample_account.account_id, Decimal('100.00'))

    def test_transfer_nonexistent_dest_account(self, account_manager, sample_account):
        """Test transfer to non-existent destination account."""
        with pytest.raises(ValueError, match="Destination account not found"):
            account_manager.transfer(sample_account.account_id, 999, Decimal('100.00'))

    def test_transfer_insufficient_funds(self, account_manager):
        """Test transfer with insufficient funds in source account."""
        source_account = account_manager.create_account(
            customer_name="Source",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('500.00'),
            minimum_balance=Decimal('200.00')
        )
        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.SAVINGS
        )

        with pytest.raises(ValueError, match="Insufficient funds in source account"):
            account_manager.transfer(
                source_account.account_id,
                dest_account.account_id,
                Decimal('400.00')  # Would leave only 100, below 200 minimum
            )

    def test_transfer_inactive_source_account(self, account_manager):
        """Test transfer from inactive source account."""
        source_account = account_manager.create_account(
            customer_name="Source",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('0.00'),
            minimum_balance=Decimal('0.00')
        )
        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.SAVINGS
        )

        # Deactivate source account
        account_manager.deactivate_account(source_account.account_id)

        with pytest.raises(ValueError, match="Source account is not active"):
            account_manager.transfer(
                source_account.account_id,
                dest_account.account_id,
                Decimal('100.00')
            )

    def test_transfer_inactive_dest_account(self, account_manager, sample_account):
        """Test transfer to inactive destination account."""
        dest_account = account_manager.create_account(
            customer_name="Dest",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('0.00'),
            minimum_balance=Decimal('0.00')
        )

        # Deactivate destination account
        account_manager.deactivate_account(dest_account.account_id)

        with pytest.raises(ValueError, match="Destination account is not active"):
            account_manager.transfer(
                sample_account.account_id,
                dest_account.account_id,
                Decimal('100.00')
            )

    def test_get_account_success(self, account_manager, sample_account):
        """Test successful account retrieval."""
        retrieved_account = account_manager.get_account(sample_account.account_id)

        assert retrieved_account is not None
        assert retrieved_account.account_id == sample_account.account_id

    def test_get_account_not_found(self, account_manager):
        """Test account retrieval with non-existent ID."""
        account = account_manager.get_account(999)
        assert account is None

    def test_get_account_by_number_success(self, account_manager, sample_account):
        """Test successful account retrieval by number."""
        retrieved_account = account_manager.get_account_by_number(sample_account.account_number)

        assert retrieved_account is not None
        assert retrieved_account.account_number == sample_account.account_number

    def test_get_balance_success(self, account_manager, sample_account):
        """Test successful balance retrieval."""
        balance = account_manager.get_balance(sample_account.account_id)
        assert balance == Decimal('1000.00')

    def test_get_balance_nonexistent_account(self, account_manager):
        """Test balance retrieval for non-existent account."""
        balance = account_manager.get_balance(999)
        assert balance is None

    def test_deactivate_account_success(self, account_manager):
        """Test successful account deactivation."""
        # Create account without minimum balance for easy deactivation
        account = account_manager.create_account(
            customer_name="Test Deactivate",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('0.00')
        )

        # Empty the account
        account_manager.withdraw(account.account_id, Decimal('1000.00'))

        result = account_manager.deactivate_account(account.account_id)
        assert result is True

    def test_deactivate_account_with_balance(self, account_manager, sample_account):
        """Test account deactivation with non-zero balance."""
        with pytest.raises(ValueError, match="Cannot deactivate account with non-zero balance"):
            account_manager.deactivate_account(sample_account.account_id)

    def test_deactivate_nonexistent_account(self, account_manager):
        """Test deactivation of non-existent account."""
        with pytest.raises(ValueError, match="Account not found"):
            account_manager.deactivate_account(999)

    def test_get_all_accounts(self, account_manager, sample_account):
        """Test getting all accounts."""
        # Create another account
        account_manager.create_account(
            customer_name="Another Client",
            account_type=AccountType.SAVINGS
        )

        accounts = account_manager.get_all_accounts()
        assert len(accounts) >= 2

    def test_calculate_total_deposits(self, account_manager, sample_account):
        """Test calculation of total deposits."""
        # Make some deposits
        account_manager.deposit(sample_account.account_id, Decimal('200.00'))
        account_manager.deposit(sample_account.account_id, Decimal('300.00'))

        total_deposits = account_manager.calculate_total_deposits(sample_account.account_id)
        # Initial deposit + two additional deposits
        assert total_deposits == Decimal('1500.00')

    def test_calculate_total_withdrawals(self, account_manager, sample_account):
        """Test calculation of total withdrawals."""
        # Make some withdrawals
        account_manager.withdraw(sample_account.account_id, Decimal('150.00'))
        account_manager.withdraw(sample_account.account_id, Decimal('250.00'))

        total_withdrawals = account_manager.calculate_total_withdrawals(sample_account.account_id)
        assert total_withdrawals == Decimal('400.00')

    def test_calculate_totals_with_transfers(self, account_manager):
        """Test calculation of totals including transfers."""
        # Create two accounts
        account1 = account_manager.create_account(
            customer_name="Account 1",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('2000.00'),
            minimum_balance=Decimal('100.00')
        )
        account2 = account_manager.create_account(
            customer_name="Account 2",
            account_type=AccountType.SAVINGS
        )

        # Transfer from account1 to account2
        account_manager.transfer(account1.account_id, account2.account_id, Decimal('500.00'))

        # Check totals for account1 (outgoing transfer counts as withdrawal)
        total_deposits_1 = account_manager.calculate_total_deposits(account1.account_id)
        total_withdrawals_1 = account_manager.calculate_total_withdrawals(account1.account_id)

        assert total_deposits_1 == Decimal('2000.00')  # Initial deposit
        assert total_withdrawals_1 == Decimal('500.00')  # Transfer out

        # Check totals for account2 (incoming transfer counts as deposit)
        total_deposits_2 = account_manager.calculate_total_deposits(account2.account_id)
        total_withdrawals_2 = account_manager.calculate_total_withdrawals(account2.account_id)

        assert total_deposits_2 == Decimal('500.00')  # Transfer in
        assert total_withdrawals_2 == Decimal('0.00')

    def test_get_account_summary(self, account_manager, sample_account):
        """Test getting comprehensive account summary."""
        # Make some transactions
        account_manager.deposit(sample_account.account_id, Decimal('200.00'))
        account_manager.withdraw(sample_account.account_id, Decimal('150.00'))

        summary = account_manager.get_account_summary(sample_account.account_id)

        assert summary is not None
        assert 'account' in summary
        assert 'total_deposits' in summary
        assert 'total_withdrawals' in summary
        assert 'available_balance' in summary
        assert 'recent_transactions' in summary

        assert summary['account'].account_id == sample_account.account_id
        assert summary['total_deposits'] == Decimal('1200.00')  # 1000 + 200
        assert summary['total_withdrawals'] == Decimal('150.00')
        assert summary['available_balance'] == Decimal('950.00')  # 1050 - 100 minimum

    def test_get_account_summary_nonexistent(self, account_manager):
        """Test getting summary for non-existent account."""
        summary = account_manager.get_account_summary(999)
        assert summary is None

    def test_record_transaction(self, account_manager, sample_account):
        """Test transaction recording."""
        transaction_id = account_manager.record_transaction(
            sample_account.account_id,
            TransactionType.DEPOSIT,
            Decimal('100.00'),
            "Manual transaction",
            Decimal('1100.00')
        )

        assert transaction_id is not None

        # Verify transaction was recorded
        transactions = account_manager.get_account_history(sample_account.account_id)
        manual_tx = next((tx for tx in transactions if tx.description == "Manual transaction"), None)
        assert manual_tx is not None
        assert manual_tx.amount == Decimal('100.00')

    def test_get_account_history_with_limit(self, account_manager, sample_account):
        """Test getting account history with custom limit."""
        # Create multiple transactions
        for i in range(5):
            account_manager.deposit(sample_account.account_id, Decimal('10.00'))

        transactions = account_manager.get_account_history(sample_account.account_id, limit=3)
        assert len(transactions) <= 3

    @patch('bank_system.account_manager.uuid.uuid4')
    def test_generate_account_number_collision_handling(self, mock_uuid, account_manager):
        """Test handling of account number collisions."""
        # Mock uuid to return the same value twice
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value="12345678-1234-5678-9012-123456789012")

        # Create first account to cause collision
        first_account = account_manager.create_account(
            customer_name="First User",
            account_type=AccountType.CHECKING
        )

        # Reset mock to return different value on second call
        mock_uuid.return_value.__str__ = Mock(return_value="87654321-4321-8765-2109-876543210987")

        # Create second account - should get different number
        second_account = account_manager.create_account(
            customer_name="Second User",
            account_type=AccountType.CHECKING
        )

        assert first_account.account_number != second_account.account_number
