"""
Core business logic tests - 8 most important tests for banking system.

These tests cover the essential functionality that must work correctly
for the banking system to be reliable and secure.
"""

import pytest
import tempfile
import os
from decimal import Decimal

from bank_system.account_manager import AccountManager
from bank_system.database import DatabaseManager
from bank_system.models import Account, AccountType, TransactionType


class TestCoreBankingLogic:
    """Core banking business logic tests."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def account_manager(self, temp_db):
        """Create an AccountManager instance for testing."""
        db_manager = DatabaseManager(temp_db)
        return AccountManager(db_manager)

    def test_create_account_with_initial_deposit(self, account_manager):
        """
        Test 1: Account creation with initial deposit.
        Critical: Must correctly create account and set initial balance.
        """
        account = account_manager.create_account(
            customer_name="Иван Петров",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('10000.00'),
            minimum_balance=Decimal('1000.00')
        )

        assert account is not None
        assert account.customer_name == "Иван Петров"
        assert account.balance == Decimal('10000.00')
        assert account.minimum_balance == Decimal('1000.00')
        assert account.is_active is True

    def test_deposit_increases_balance_correctly(self, account_manager):
        """
        Test 2: Deposit operation must correctly increase balance.
        Critical: Financial calculations must be precise.
        """
        account = account_manager.create_account(
            customer_name="Мария Сидорова",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('5000.00')
        )

        # Make deposit
        result = account_manager.deposit(
            account.account_id,
            Decimal('3000.00'),
            "Зарплата"
        )

        assert result is True
        new_balance = account_manager.get_balance(account.account_id)
        assert new_balance == Decimal('8000.00')

    def test_withdrawal_respects_minimum_balance(self, account_manager):
        """
        Test 3: Withdrawal must respect minimum balance constraint.
        Critical: Prevents overdrafts and maintains account integrity.
        """
        account = account_manager.create_account(
            customer_name="Алексей Козлов",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('15000.00'),
            minimum_balance=Decimal('2000.00')
        )

        # Try to withdraw amount that would go below minimum balance
        with pytest.raises(ValueError, match="Insufficient funds"):
            account_manager.withdraw(
                account.account_id,
                Decimal('14000.00')  # Would leave only 1000, below 2000 minimum
            )

        # Verify balance unchanged
        balance = account_manager.get_balance(account.account_id)
        assert balance == Decimal('15000.00')

    def test_successful_withdrawal_within_limits(self, account_manager):
        """
        Test 4: Valid withdrawal must work correctly.
        Critical: Legitimate withdrawals must be processed accurately.
        """
        account = account_manager.create_account(
            customer_name="Елена Волкова",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('20000.00'),
            minimum_balance=Decimal('3000.00')
        )

        # Withdraw within limits
        result = account_manager.withdraw(
            account.account_id,
            Decimal('10000.00'),
            "Покупка автомобиля"
        )

        assert result is True
        new_balance = account_manager.get_balance(account.account_id)
        assert new_balance == Decimal('10000.00')

    def test_transfer_between_accounts(self, account_manager):
        """
        Test 5: Transfer between accounts must work correctly.
        Critical: Money must be moved accurately without loss or duplication.
        """
        # Create source account
        source_account = account_manager.create_account(
            customer_name="Дмитрий Попов",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('25000.00'),
            minimum_balance=Decimal('1000.00')
        )

        # Create destination account
        dest_account = account_manager.create_account(
            customer_name="Анна Морозова",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('5000.00')
        )

        # Perform transfer
        result = account_manager.transfer(
            from_account_id=source_account.account_id,
            to_account_id=dest_account.account_id,
            amount=Decimal('8000.00'),
            description="Перевод другу"
        )

        assert result is True

        # Verify balances
        source_balance = account_manager.get_balance(source_account.account_id)
        dest_balance = account_manager.get_balance(dest_account.account_id)

        assert source_balance == Decimal('17000.00')  # 25000 - 8000
        assert dest_balance == Decimal('13000.00')    # 5000 + 8000

    def test_transfer_respects_source_account_limits(self, account_manager):
        """
        Test 6: Transfer must not allow source account to go below minimum balance.
        Critical: Prevents unauthorized overdrafts during transfers.
        """
        source_account = account_manager.create_account(
            customer_name="Сергей Белов",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('12000.00'),
            minimum_balance=Decimal('5000.00')
        )

        dest_account = account_manager.create_account(
            customer_name="Татьяна Зеленская",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('3000.00')
        )

        # Try transfer that would violate minimum balance
        with pytest.raises(ValueError, match="Insufficient funds in source account"):
            account_manager.transfer(
                from_account_id=source_account.account_id,
                to_account_id=dest_account.account_id,
                amount=Decimal('10000.00')  # Would leave only 2000, below 5000 minimum
            )

    def test_account_deactivation_requires_zero_balance(self, account_manager):
        """
        Test 7: Account deactivation must require zero balance.
        Critical: Prevents loss of customer funds.
        """
        account = account_manager.create_account(
            customer_name="Николай Смирнов",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1500.00')
        )

        # Try to deactivate account with balance
        with pytest.raises(ValueError, match="Cannot deactivate account with non-zero balance"):
            account_manager.deactivate_account(account.account_id)

        # Withdraw all money first
        account_manager.withdraw(account.account_id, Decimal('1500.00'))

        # Now deactivation should work
        result = account_manager.deactivate_account(account.account_id)
        assert result is True

    def test_transaction_history_tracking(self, account_manager):
        """
        Test 8: Transaction history must be accurately recorded.
        Critical: Audit trail for all financial operations.
        """
        account = account_manager.create_account(
            customer_name="Ольга Кузнецова",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('8000.00')
        )

        # Perform multiple operations
        account_manager.deposit(account.account_id, Decimal('2000.00'), "Доплата")
        account_manager.withdraw(account.account_id, Decimal('1500.00'), "Покупки")

        # Check transaction history
        transactions = account_manager.get_account_history(account.account_id, limit=10)

        # Should have 3 transactions: initial deposit + deposit + withdrawal
        assert len(transactions) == 3

        # Check transaction types and amounts (newest first)
        assert transactions[0].transaction_type == TransactionType.WITHDRAWAL
        assert transactions[0].amount == Decimal('1500.00')
        assert transactions[1].transaction_type == TransactionType.DEPOSIT
        assert transactions[1].amount == Decimal('2000.00')
        assert transactions[2].transaction_type == TransactionType.DEPOSIT
        assert transactions[2].amount == Decimal('8000.00')  # Initial deposit
