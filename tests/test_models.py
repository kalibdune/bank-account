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
        assert TransactionType.INTEREST.value == "interest"
        assert TransactionType.FEE.value == "fee"
        assert TransactionType.BULK_TRANSFER_IN.value == "bulk_transfer_in"
        assert TransactionType.BULK_TRANSFER_OUT.value == "bulk_transfer_out"


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
        assert account.is_frozen is False
        assert account.daily_withdrawal_limit is None
        assert account.interest_rate == Decimal('0.00')
        assert account.last_interest_calculation is None
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
            minimum_balance=Decimal('1000.00'),
            is_frozen=True,
            daily_withdrawal_limit=Decimal('5000.00'),
            interest_rate=Decimal('2.5'),
            last_interest_calculation=test_time
        )

        assert account.account_id == 123
        assert account.account_number == "TEST-123"
        assert account.customer_name == "Тест Пользователь"
        assert account.account_type == AccountType.SAVINGS
        assert account.balance == Decimal('5000.00')
        assert account.created_at == test_time
        assert account.is_active is False
        assert account.minimum_balance == Decimal('1000.00')
        assert account.is_frozen is True
        assert account.daily_withdrawal_limit == Decimal('5000.00')
        assert account.interest_rate == Decimal('2.5')
        assert account.last_interest_calculation == test_time

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


class TestAccountNewFields:
    """Test new fields and methods in Account model."""

    def test_account_new_fields_default_values(self):
        """Test new fields have correct default values."""
        account = Account()
        
        assert account.is_frozen is False
        assert account.daily_withdrawal_limit is None
        assert account.interest_rate == Decimal('0.00')
        assert account.last_interest_calculation is None

    def test_account_new_fields_custom_values(self):
        """Test new fields with custom values."""
        test_time = datetime.now()
        account = Account(
            is_frozen=True,
            daily_withdrawal_limit=Decimal('10000.00'),
            interest_rate=Decimal('3.5'),
            last_interest_calculation=test_time
        )
        
        assert account.is_frozen is True
        assert account.daily_withdrawal_limit == Decimal('10000.00')
        assert account.interest_rate == Decimal('3.5')
        assert account.last_interest_calculation == test_time

    def test_account_interest_rate_decimal_conversion(self):
        """Test automatic conversion of interest_rate to Decimal."""
        # Test with string
        account = Account(interest_rate="2.75")
        assert account.interest_rate == Decimal('2.75')
        assert isinstance(account.interest_rate, Decimal)

        # Test with float
        account = Account(interest_rate=4.25)
        assert account.interest_rate == Decimal('4.25')
        assert isinstance(account.interest_rate, Decimal)

        # Test with int
        account = Account(interest_rate=5)
        assert account.interest_rate == Decimal('5.00')
        assert isinstance(account.interest_rate, Decimal)

    def test_account_daily_withdrawal_limit_decimal_conversion(self):
        """Test automatic conversion of daily_withdrawal_limit to Decimal."""
        # Test with string
        account = Account(daily_withdrawal_limit="5000.00")
        assert account.daily_withdrawal_limit == Decimal('5000.00')
        assert isinstance(account.daily_withdrawal_limit, Decimal)

        # Test with float
        account = Account(daily_withdrawal_limit=7500.50)
        assert account.daily_withdrawal_limit == Decimal('7500.50')
        assert isinstance(account.daily_withdrawal_limit, Decimal)

        # Test with int
        account = Account(daily_withdrawal_limit=10000)
        assert account.daily_withdrawal_limit == Decimal('10000.00')
        assert isinstance(account.daily_withdrawal_limit, Decimal)

    def test_can_withdraw_frozen_account(self):
        """Test withdrawal check on frozen account."""
        account = Account(
            balance=Decimal('1000.00'),
            is_frozen=True
        )
        
        # Should not be able to withdraw from frozen account
        assert account.can_withdraw(Decimal('100.00')) is False
        assert account.can_withdraw(Decimal('500.00')) is False

    def test_can_withdraw_unfrozen_account(self):
        """Test withdrawal check on unfrozen account."""
        account = Account(
            balance=Decimal('1000.00'),
            is_frozen=False
        )
        
        # Should be able to withdraw from unfrozen account
        assert account.can_withdraw(Decimal('100.00')) is True
        assert account.can_withdraw(Decimal('500.00')) is True

    def test_is_within_daily_limit_no_limit(self):
        """Test daily limit check when no limit is set."""
        account = Account(daily_withdrawal_limit=None)
        
        # Should always return True when no limit is set
        assert account.is_within_daily_limit(Decimal('1000.00'), Decimal('0.00')) is True
        assert account.is_within_daily_limit(Decimal('5000.00'), Decimal('2000.00')) is True

    def test_is_within_daily_limit_with_limit(self):
        """Test daily limit check with limit set."""
        account = Account(daily_withdrawal_limit=Decimal('5000.00'))
        
        # Test within limit
        assert account.is_within_daily_limit(Decimal('1000.00'), Decimal('2000.00')) is True
        assert account.is_within_daily_limit(Decimal('2000.00'), Decimal('3000.00')) is True
        
        # Test at limit
        assert account.is_within_daily_limit(Decimal('1000.00'), Decimal('4000.00')) is True
        
        # Test over limit
        assert account.is_within_daily_limit(Decimal('2000.00'), Decimal('4000.00')) is False
        assert account.is_within_daily_limit(Decimal('6000.00'), Decimal('0.00')) is False

    def test_is_within_daily_limit_decimal_conversion(self):
        """Test daily limit check with automatic Decimal conversion."""
        account = Account(daily_withdrawal_limit=Decimal('5000.00'))
        
        # Test with string inputs
        assert account.is_within_daily_limit("1000.00", "2000.00") is True
        
        # Test with float inputs
        assert account.is_within_daily_limit(1500.50, 2500.25) is True
        
        # Test with int inputs
        assert account.is_within_daily_limit(1000, 3000) is True


class TestTransactionNewTypes:
    """Test new transaction types."""

    def test_new_transaction_types_creation(self):
        """Test creation of transactions with new types."""
        # Test INTEREST transaction
        interest_tx = Transaction(transaction_type=TransactionType.INTEREST)
        assert interest_tx.transaction_type == TransactionType.INTEREST
        
        # Test FEE transaction
        fee_tx = Transaction(transaction_type=TransactionType.FEE)
        assert fee_tx.transaction_type == TransactionType.FEE
        
        # Test BULK_TRANSFER_IN transaction
        bulk_in_tx = Transaction(transaction_type=TransactionType.BULK_TRANSFER_IN)
        assert bulk_in_tx.transaction_type == TransactionType.BULK_TRANSFER_IN
        
        # Test BULK_TRANSFER_OUT transaction
        bulk_out_tx = Transaction(transaction_type=TransactionType.BULK_TRANSFER_OUT)
        assert bulk_out_tx.transaction_type == TransactionType.BULK_TRANSFER_OUT

    def test_all_transaction_types_count(self):
        """Test that we have all expected transaction types."""
        expected_types = {
            'deposit', 'withdrawal', 'transfer_in', 'transfer_out',
            'interest', 'fee', 'bulk_transfer_in', 'bulk_transfer_out'
        }
        
        actual_types = {txn_type.value for txn_type in TransactionType}
        assert actual_types == expected_types
        assert len(TransactionType) == 8
