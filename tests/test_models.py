"""
Tests for the models module.

This module contains tests for the Account and Transaction models,
including their methods and validation logic.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from bank_system.models import Account, Transaction, AccountType, TransactionType


class TestAccountType:
    """Test AccountType enum."""

    def test_account_types(self):
        """Test all account type values."""
        assert AccountType.CHECKING.value == "checking"
        assert AccountType.SAVINGS.value == "savings"
        assert AccountType.BUSINESS.value == "business"


class TestTransactionType:
    """Test TransactionType enum."""

    def test_transaction_types(self):
        """Test all transaction type values."""
        assert TransactionType.DEPOSIT.value == "deposit"
        assert TransactionType.WITHDRAWAL.value == "withdrawal"
        assert TransactionType.TRANSFER_IN.value == "transfer_in"
        assert TransactionType.TRANSFER_OUT.value == "transfer_out"


class TestAccount:
    """Test Account model."""

    def test_account_default_initialization(self):
        """Test account creation with default values."""
        account = Account()

        assert account.account_id is None
        assert account.account_number is None
        assert account.customer_name == ""
        assert account.account_type == AccountType.CHECKING
        assert account.balance == Decimal('0.00')
        assert account.is_active is True
        assert account.minimum_balance == Decimal('0.00')
        assert isinstance(account.created_at, datetime)

    def test_account_custom_initialization(self):
        """Test account creation with custom values."""
        test_time = datetime.now()
        account = Account(
            account_id=123,
            account_number="TEST-123",
            customer_name="Тест Пользователь",
            account_type=AccountType.SAVINGS,
            balance=Decimal('5000.00'),
            created_at=test_time,
            is_active=False,
            minimum_balance=Decimal('1000.00')
        )

        assert account.account_id == 123
        assert account.account_number == "TEST-123"
        assert account.customer_name == "Тест Пользователь"
        assert account.account_type == AccountType.SAVINGS
        assert account.balance == Decimal('5000.00')
        assert account.created_at == test_time
        assert account.is_active is False
        assert account.minimum_balance == Decimal('1000.00')

    def test_account_balance_decimal_conversion(self):
        """Test automatic conversion of balance to Decimal."""
        # Test with string input
        account = Account(balance="1500.50")
        assert account.balance == Decimal('1500.50')
        assert isinstance(account.balance, Decimal)

        # Test with float input
        account = Account(balance=2500.75)
        assert account.balance == Decimal('2500.75')
        assert isinstance(account.balance, Decimal)

        # Test with int input
        account = Account(balance=3000)
        assert account.balance == Decimal('3000.00')
        assert isinstance(account.balance, Decimal)

    def test_account_minimum_balance_decimal_conversion(self):
        """Test automatic conversion of minimum_balance to Decimal."""
        # Test with string input
        account = Account(minimum_balance="500.00")
        assert account.minimum_balance == Decimal('500.00')
        assert isinstance(account.minimum_balance, Decimal)

        # Test with float input
        account = Account(minimum_balance=750.25)
        assert account.minimum_balance == Decimal('750.25')
        assert isinstance(account.minimum_balance, Decimal)

    def test_can_withdraw_with_no_minimum_balance(self):
        """Test withdrawal check with no minimum balance requirement."""
        account = Account(balance=Decimal('1000.00'))

        assert account.can_withdraw(Decimal('500.00')) is True
        assert account.can_withdraw(Decimal('1000.00')) is True
        assert account.can_withdraw(Decimal('1000.01')) is False

    def test_can_withdraw_with_minimum_balance(self):
        """Test withdrawal check with minimum balance requirement."""
        account = Account(
            balance=Decimal('1000.00'),
            minimum_balance=Decimal('200.00')
        )

        assert account.can_withdraw(Decimal('500.00')) is True
        assert account.can_withdraw(Decimal('800.00')) is True
        assert account.can_withdraw(Decimal('800.01')) is False
        assert account.can_withdraw(Decimal('1000.00')) is False

    def test_can_withdraw_decimal_conversion(self):
        """Test can_withdraw with automatic Decimal conversion."""
        account = Account(balance=Decimal('1000.00'))

        # Test with string
        assert account.can_withdraw("500.00") is True

        # Test with float
        assert account.can_withdraw(750.50) is True

        # Test with int
        assert account.can_withdraw(250) is True

    def test_deposit_success(self):
        """Test successful deposit operation."""
        account = Account(balance=Decimal('1000.00'))

        result = account.deposit(Decimal('500.00'))

        assert result is True
        assert account.balance == Decimal('1500.00')

    def test_deposit_decimal_conversion(self):
        """Test deposit with automatic Decimal conversion."""
        account = Account(balance=Decimal('1000.00'))

        # Test with string
        result = account.deposit("300.50")
        assert result is True
        assert account.balance == Decimal('1300.50')

        # Test with float
        result = account.deposit(150.25)
        assert result is True
        assert account.balance == Decimal('1450.75')

    def test_deposit_zero_amount(self):
        """Test deposit with zero amount."""
        account = Account(balance=Decimal('1000.00'))

        result = account.deposit(Decimal('0.00'))

        assert result is False
        assert account.balance == Decimal('1000.00')

    def test_deposit_negative_amount(self):
        """Test deposit with negative amount."""
        account = Account(balance=Decimal('1000.00'))

        result = account.deposit(Decimal('-100.00'))

        assert result is False
        assert account.balance == Decimal('1000.00')

    def test_withdraw_success(self):
        """Test successful withdrawal operation."""
        account = Account(balance=Decimal('1000.00'))

        result = account.withdraw(Decimal('300.00'))

        assert result is True
        assert account.balance == Decimal('700.00')

    def test_withdraw_with_minimum_balance(self):
        """Test withdrawal respecting minimum balance."""
        account = Account(
            balance=Decimal('1000.00'),
            minimum_balance=Decimal('200.00')
        )

        # Should succeed
        result = account.withdraw(Decimal('500.00'))
        assert result is True
        assert account.balance == Decimal('500.00')

        # Should fail (would go below minimum)
        result = account.withdraw(Decimal('400.00'))
        assert result is False
        assert account.balance == Decimal('500.00')

    def test_withdraw_decimal_conversion(self):
        """Test withdraw with automatic Decimal conversion."""
        account = Account(balance=Decimal('1000.00'))

        # Test with string
        result = account.withdraw("200.50")
        assert result is True
        assert account.balance == Decimal('799.50')

    def test_withdraw_zero_amount(self):
        """Test withdrawal with zero amount."""
        account = Account(balance=Decimal('1000.00'))

        result = account.withdraw(Decimal('0.00'))

        assert result is False
        assert account.balance == Decimal('1000.00')

    def test_withdraw_negative_amount(self):
        """Test withdrawal with negative amount."""
        account = Account(balance=Decimal('1000.00'))

        result = account.withdraw(Decimal('-100.00'))

        assert result is False
        assert account.balance == Decimal('1000.00')

    def test_withdraw_insufficient_funds(self):
        """Test withdrawal with insufficient funds."""
        account = Account(balance=Decimal('500.00'))

        result = account.withdraw(Decimal('600.00'))

        assert result is False
        assert account.balance == Decimal('500.00')


class TestTransaction:
    """Test Transaction model."""

    def test_transaction_default_initialization(self):
        """Test transaction creation with default values."""
        transaction = Transaction()

        assert transaction.transaction_id is None
        assert transaction.account_id == 0
        assert transaction.transaction_type == TransactionType.DEPOSIT
        assert transaction.amount == Decimal('0.00')
        assert transaction.description == ""
        assert isinstance(transaction.timestamp, datetime)
        assert transaction.balance_after == Decimal('0.00')
        assert transaction.related_account_id is None

    def test_transaction_custom_initialization(self):
        """Test transaction creation with custom values."""
        test_time = datetime.now()
        transaction = Transaction(
            transaction_id=456,
            account_id=123,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=Decimal('250.00'),
            description="Test withdrawal",
            timestamp=test_time,
            balance_after=Decimal('750.00'),
            related_account_id=789
        )

        assert transaction.transaction_id == 456
        assert transaction.account_id == 123
        assert transaction.transaction_type == TransactionType.WITHDRAWAL
        assert transaction.amount == Decimal('250.00')
        assert transaction.description == "Test withdrawal"
        assert transaction.timestamp == test_time
        assert transaction.balance_after == Decimal('750.00')
        assert transaction.related_account_id == 789

    def test_transaction_amount_decimal_conversion(self):
        """Test automatic conversion of amount to Decimal."""
        # Test with string
        transaction = Transaction(amount="123.45")
        assert transaction.amount == Decimal('123.45')
        assert isinstance(transaction.amount, Decimal)

        # Test with float
        transaction = Transaction(amount=678.90)
        assert transaction.amount == Decimal('678.90')
        assert isinstance(transaction.amount, Decimal)

        # Test with int
        transaction = Transaction(amount=1000)
        assert transaction.amount == Decimal('1000.00')
        assert isinstance(transaction.amount, Decimal)

    def test_transaction_balance_after_decimal_conversion(self):
        """Test automatic conversion of balance_after to Decimal."""
        # Test with string
        transaction = Transaction(balance_after="999.99")
        assert transaction.balance_after == Decimal('999.99')
        assert isinstance(transaction.balance_after, Decimal)

        # Test with float
        transaction = Transaction(balance_after=1234.56)
        assert transaction.balance_after == Decimal('1234.56')
        assert isinstance(transaction.balance_after, Decimal)

    def test_transaction_all_types(self):
        """Test transaction creation with all transaction types."""
        for txn_type in TransactionType:
            transaction = Transaction(transaction_type=txn_type)
            assert transaction.transaction_type == txn_type
