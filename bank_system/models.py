"""
Data models for the bank management system.

This module contains the core data structures used throughout the application.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class AccountType(Enum):
    """Types of bank accounts."""
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS = "business"


class TransactionType(Enum):
    """Types of transactions."""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    INTEREST = "interest"
    FEE = "fee"
    BULK_TRANSFER_OUT = "bulk_transfer_out"
    BULK_TRANSFER_IN = "bulk_transfer_in"


@dataclass
class Account:
    """Represents a bank account."""

    account_id: Optional[int] = None
    account_number: Optional[str] = None
    customer_name: str = ""
    account_type: AccountType = AccountType.CHECKING
    balance: Decimal = Decimal('0.00')
    created_at: Optional[datetime] = None
    is_active: bool = True
    minimum_balance: Decimal = Decimal('0.00')
    is_frozen: bool = False
    daily_withdrawal_limit: Optional[Decimal] = None
    interest_rate: Decimal = Decimal('0.00')  # Annual interest rate as percentage
    last_interest_calculation: Optional[datetime] = None

    def __post_init__(self):
        """Initialize account after creation."""
        if self.created_at is None:
            self.created_at = datetime.now()

        # Ensure balance is a Decimal
        if not isinstance(self.balance, Decimal):
            self.balance = Decimal(str(self.balance))

        if not isinstance(self.minimum_balance, Decimal):
            self.minimum_balance = Decimal(str(self.minimum_balance))
            
        if not isinstance(self.interest_rate, Decimal):
            self.interest_rate = Decimal(str(self.interest_rate))
            
        if self.daily_withdrawal_limit is not None and not isinstance(self.daily_withdrawal_limit, Decimal):
            self.daily_withdrawal_limit = Decimal(str(self.daily_withdrawal_limit))

    def can_withdraw(self, amount: Decimal) -> bool:
        """Check if withdrawal is possible without going below minimum balance."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if self.is_frozen:
            return False
            
        return self.balance - amount >= self.minimum_balance
    
    def is_within_daily_limit(self, amount: Decimal, daily_withdrawals: Decimal) -> bool:
        """Check if withdrawal is within daily limit."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if not isinstance(daily_withdrawals, Decimal):
            daily_withdrawals = Decimal(str(daily_withdrawals))
            
        if self.daily_withdrawal_limit is None:
            return True
            
        return daily_withdrawals + amount <= self.daily_withdrawal_limit

    def withdraw(self, amount: Decimal) -> bool:
        """Withdraw money from account."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            return False

        if not self.can_withdraw(amount):
            return False

        self.balance -= amount
        return True

    def deposit(self, amount: Decimal) -> bool:
        """Deposit money to account."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        if amount <= 0:
            return False

        self.balance += amount
        return True


@dataclass
class Transaction:
    """Represents a bank transaction."""

    transaction_id: Optional[int] = None
    account_id: int = 0
    transaction_type: TransactionType = TransactionType.DEPOSIT
    amount: Decimal = Decimal('0.00')
    description: str = ""
    timestamp: Optional[datetime] = None
    balance_after: Decimal = Decimal('0.00')
    related_account_id: Optional[int] = None  # For transfers

    def __post_init__(self):
        """Initialize transaction after creation."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Ensure amounts are Decimals
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))

        if not isinstance(self.balance_after, Decimal):
            self.balance_after = Decimal(str(self.balance_after))
