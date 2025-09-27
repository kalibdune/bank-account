"""
Account manager for the bank management system.

This module contains the business logic for managing bank accounts and transactions.
"""

import uuid
from decimal import Decimal
from typing import List, Optional, Tuple
from datetime import datetime

from .models import Account, Transaction, AccountType, TransactionType
from .database import DatabaseManager


class AccountManager:
    """Manages bank account operations and business logic."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize account manager with database."""
        self.db = db_manager

    def generate_account_number(self) -> str:
        """Generate a unique account number."""
        # Format: BANK-YYYYMMDD-XXXX (where XXXX is random)
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"BANK-{date_str}-{unique_id}"

    def create_account(self, customer_name: str, account_type: AccountType,
                      initial_deposit: Decimal = Decimal('0.00'),
                      minimum_balance: Decimal = Decimal('0.00')) -> Optional[Account]:
        """Create a new bank account."""
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name cannot be empty")

        if initial_deposit < 0:
            raise ValueError("Initial deposit cannot be negative")

        if minimum_balance < 0:
            raise ValueError("Minimum balance cannot be negative")

        if initial_deposit < minimum_balance:
            raise ValueError("Initial deposit must be at least the minimum balance")

        # Generate unique account number
        account_number = self.generate_account_number()

        # Ensure account number is unique
        while self.db.get_account_by_number(account_number):
            account_number = self.generate_account_number()

        # Create account object
        account = Account(
            account_number=account_number,
            customer_name=customer_name.strip(),
            account_type=account_type,
            balance=initial_deposit,
            minimum_balance=minimum_balance,
            created_at=datetime.now(),
            is_active=True
        )

        # Save to database
        account_id = self.db.create_account(account)
        if account_id:
            account.account_id = account_id

            # Record initial deposit if > 0
            if initial_deposit > 0:
                self.record_transaction(
                    account.account_id,
                    TransactionType.DEPOSIT,
                    initial_deposit,
                    "Initial deposit",
                    initial_deposit
                )

            return account

        return None

    def get_account(self, account_id: int) -> Optional[Account]:
        """Get account by ID."""
        return self.db.get_account(account_id)

    def get_account_by_number(self, account_number: str) -> Optional[Account]:
        """Get account by account number."""
        return self.db.get_account_by_number(account_number)

    def deposit(self, account_id: int, amount: Decimal, description: str = "") -> bool:
        """Deposit money to an account."""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")

        if not account.is_active:
            raise ValueError("Account is not active")

        # Update balance
        new_balance = account.balance + amount
        if self.db.update_account_balance(account_id, new_balance):
            # Record transaction
            self.record_transaction(
                account_id,
                TransactionType.DEPOSIT,
                amount,
                description or f"Deposit of {amount} RUB",
                new_balance
            )
            return True

        return False

    def withdraw(self, account_id: int, amount: Decimal, description: str = "") -> bool:
        """Withdraw money from an account."""
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")

        if not account.is_active:
            raise ValueError("Account is not active")

        # Check if withdrawal is possible
        if not account.can_withdraw(amount):
            raise ValueError(f"Insufficient funds. Available: {account.balance - account.minimum_balance} RUB")

        # Update balance
        new_balance = account.balance - amount
        if self.db.update_account_balance(account_id, new_balance):
            # Record transaction
            self.record_transaction(
                account_id,
                TransactionType.WITHDRAWAL,
                amount,
                description or f"Withdrawal of {amount} RUB",
                new_balance
            )
            return True

        return False

    def transfer(self, from_account_id: int, to_account_id: int, amount: Decimal,
                description: str = "") -> bool:
        """Transfer money between accounts."""
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")

        from_account = self.db.get_account(from_account_id)
        to_account = self.db.get_account(to_account_id)

        if not from_account:
            raise ValueError("Source account not found")
        if not to_account:
            raise ValueError("Destination account not found")

        if not from_account.is_active:
            raise ValueError("Source account is not active")
        if not to_account.is_active:
            raise ValueError("Destination account is not active")

        # Check if transfer is possible
        if not from_account.can_withdraw(amount):
            raise ValueError(f"Insufficient funds in source account. Available: {from_account.balance - from_account.minimum_balance} RUB")

        # Perform transfer
        from_new_balance = from_account.balance - amount
        to_new_balance = to_account.balance + amount

        # Update both accounts
        if (self.db.update_account_balance(from_account_id, from_new_balance) and
            self.db.update_account_balance(to_account_id, to_new_balance)):

            # Record transactions for both accounts
            transfer_desc = description or f"Transfer to account {to_account.account_number}"
            receive_desc = description or f"Transfer from account {from_account.account_number}"

            self.record_transaction(
                from_account_id,
                TransactionType.TRANSFER_OUT,
                amount,
                transfer_desc,
                from_new_balance,
                to_account_id
            )

            self.record_transaction(
                to_account_id,
                TransactionType.TRANSFER_IN,
                amount,
                receive_desc,
                to_new_balance,
                from_account_id
            )

            return True

        return False

    def get_balance(self, account_id: int) -> Optional[Decimal]:
        """Get account balance."""
        account = self.db.get_account(account_id)
        return account.balance if account else None

    def get_account_history(self, account_id: int, limit: int = 10) -> List[Transaction]:
        """Get account transaction history."""
        return self.db.get_account_transactions(account_id, limit)

    def deactivate_account(self, account_id: int) -> bool:
        """Deactivate an account."""
        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")

        if account.balance != Decimal('0.00'):
            raise ValueError("Cannot deactivate account with non-zero balance")

        return self.db.deactivate_account(account_id)

    def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        return self.db.get_all_accounts()

    def calculate_total_deposits(self, account_id: int) -> Decimal:
        """Calculate total deposits for an account."""
        transactions = self.db.get_account_transactions(account_id, limit=1000)
        total = Decimal('0.00')

        for transaction in transactions:
            if transaction.transaction_type in [TransactionType.DEPOSIT, TransactionType.TRANSFER_IN]:
                total += transaction.amount

        return total

    def calculate_total_withdrawals(self, account_id: int) -> Decimal:
        """Calculate total withdrawals for an account."""
        transactions = self.db.get_account_transactions(account_id, limit=1000)
        total = Decimal('0.00')

        for transaction in transactions:
            if transaction.transaction_type in [TransactionType.WITHDRAWAL, TransactionType.TRANSFER_OUT]:
                total += transaction.amount

        return total

    def get_account_summary(self, account_id: int) -> Optional[dict]:
        """Get comprehensive account summary."""
        account = self.db.get_account(account_id)
        if not account:
            return None

        total_deposits = self.calculate_total_deposits(account_id)
        total_withdrawals = self.calculate_total_withdrawals(account_id)
        recent_transactions = self.get_account_history(account_id, 5)

        return {
            'account': account,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'available_balance': account.balance - account.minimum_balance,
            'recent_transactions': recent_transactions
        }

    def record_transaction(self, account_id: int, transaction_type: TransactionType,
                          amount: Decimal, description: str, balance_after: Decimal,
                          related_account_id: Optional[int] = None) -> Optional[int]:
        """Record a transaction in the database."""
        transaction = Transaction(
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            timestamp=datetime.now(),
            balance_after=balance_after,
            related_account_id=related_account_id
        )

        return self.db.create_transaction(transaction)
