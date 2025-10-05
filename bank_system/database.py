"""
Database manager for the bank management system.

This module handles all database operations using SQLite.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from .models import Account, Transaction, AccountType, TransactionType


class DatabaseManager:
    """Manages database operations for the banking system."""

    def __init__(self, db_path: str = "bank.db"):
        """Initialize database manager."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_number TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                    minimum_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_frozen BOOLEAN DEFAULT 0,
                    daily_withdrawal_limit DECIMAL(15,2),
                    interest_rate DECIMAL(5,4) DEFAULT 0.0000,
                    last_interest_calculation TIMESTAMP
                )
            """)
            
            # Add new columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE accounts ADD COLUMN is_frozen BOOLEAN DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE accounts ADD COLUMN daily_withdrawal_limit DECIMAL(15,2)")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE accounts ADD COLUMN interest_rate DECIMAL(5,4) DEFAULT 0.0000")
            except sqlite3.OperationalError:
                pass  # Column already exists
                
            try:
                cursor.execute("ALTER TABLE accounts ADD COLUMN last_interest_calculation TIMESTAMP")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Create transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    balance_after DECIMAL(15,2) NOT NULL,
                    related_account_id INTEGER,
                    FOREIGN KEY (account_id) REFERENCES accounts (account_id),
                    FOREIGN KEY (related_account_id) REFERENCES accounts (account_id)
                )
            """)

            conn.commit()

    def create_account(self, account: Account) -> Optional[int]:
        """Create a new account in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO accounts (account_number, customer_name, account_type,
                                        balance, minimum_balance, created_at, is_active,
                                        is_frozen, daily_withdrawal_limit, interest_rate, last_interest_calculation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account.account_number,
                    account.customer_name,
                    account.account_type.value,
                    float(account.balance),
                    float(account.minimum_balance),
                    account.created_at,
                    account.is_active,
                    account.is_frozen,
                    float(account.daily_withdrawal_limit) if account.daily_withdrawal_limit else None,
                    float(account.interest_rate),
                    account.last_interest_calculation
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Error creating account: {e}")
            return None

    def get_account(self, account_id: int) -> Optional[Account]:
        """Get account by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT account_id, account_number, customer_name, account_type,
                           balance, minimum_balance, created_at, is_active,
                           is_frozen, daily_withdrawal_limit, interest_rate, last_interest_calculation
                    FROM accounts WHERE account_id = ?
                """, (account_id,))

                row = cursor.fetchone()
                if row:
                    return Account(
                        account_id=row[0],
                        account_number=row[1],
                        customer_name=row[2],
                        account_type=AccountType(row[3]),
                        balance=Decimal(str(row[4])),
                        minimum_balance=Decimal(str(row[5])),
                        created_at=datetime.fromisoformat(row[6]),
                        is_active=bool(row[7]),
                        is_frozen=bool(row[8]) if row[8] is not None else False,
                        daily_withdrawal_limit=Decimal(str(row[9])) if row[9] is not None else None,
                        interest_rate=Decimal(str(row[10])) if row[10] is not None else Decimal('0.00'),
                        last_interest_calculation=datetime.fromisoformat(row[11]) if row[11] else None
                    )
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Error getting account: {e}")
            return None

    def get_account_by_number(self, account_number: str) -> Optional[Account]:
        """Get account by account number."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT account_id, account_number, customer_name, account_type,
                           balance, minimum_balance, created_at, is_active,
                           is_frozen, daily_withdrawal_limit, interest_rate, last_interest_calculation
                    FROM accounts WHERE account_number = ?
                """, (account_number,))

                row = cursor.fetchone()
                if row:
                    return Account(
                        account_id=row[0],
                        account_number=row[1],
                        customer_name=row[2],
                        account_type=AccountType(row[3]),
                        balance=Decimal(str(row[4])),
                        minimum_balance=Decimal(str(row[5])),
                        created_at=datetime.fromisoformat(row[6]),
                        is_active=bool(row[7]),
                        is_frozen=bool(row[8]) if row[8] is not None else False,
                        daily_withdrawal_limit=Decimal(str(row[9])) if row[9] is not None else None,
                        interest_rate=Decimal(str(row[10])) if row[10] is not None else Decimal('0.00'),
                        last_interest_calculation=datetime.fromisoformat(row[11]) if row[11] else None
                    )
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Error getting account by number: {e}")
            return None

    def update_account_balance(self, account_id: int, new_balance: Decimal) -> bool:
        """Update account balance."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET balance = ? WHERE account_id = ?
                """, (float(new_balance), account_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating balance: {e}")
            return False

    def deactivate_account(self, account_id: int) -> bool:
        """Deactivate an account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET is_active = 0 WHERE account_id = ?
                """, (account_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error deactivating account: {e}")
            return False

    def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        accounts = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT account_id, account_number, customer_name, account_type,
                           balance, minimum_balance, created_at, is_active,
                           is_frozen, daily_withdrawal_limit, interest_rate, last_interest_calculation
                    FROM accounts ORDER BY created_at DESC
                """)

                for row in cursor.fetchall():
                    accounts.append(Account(
                        account_id=row[0],
                        account_number=row[1],
                        customer_name=row[2],
                        account_type=AccountType(row[3]),
                        balance=Decimal(str(row[4])),
                        minimum_balance=Decimal(str(row[5])),
                        created_at=datetime.fromisoformat(row[6]),
                        is_active=bool(row[7]),
                        is_frozen=bool(row[8]) if row[8] is not None else False,
                        daily_withdrawal_limit=Decimal(str(row[9])) if row[9] is not None else None,
                        interest_rate=Decimal(str(row[10])) if row[10] is not None else Decimal('0.00'),
                        last_interest_calculation=datetime.fromisoformat(row[11]) if row[11] else None
                    ))
        except sqlite3.Error as e:
            self.logger.error(f"Error getting all accounts: {e}")

        return accounts

    def create_transaction(self, transaction: Transaction) -> Optional[int]:
        """Create a new transaction record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (account_id, transaction_type, amount,
                                            description, timestamp, balance_after, related_account_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction.account_id,
                    transaction.transaction_type.value,
                    float(transaction.amount),
                    transaction.description,
                    transaction.timestamp,
                    float(transaction.balance_after),
                    transaction.related_account_id
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Error creating transaction: {e}")
            return None

    def get_account_transactions(self, account_id: int, limit: int = 10) -> List[Transaction]:
        """Get transactions for an account."""
        transactions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT transaction_id, account_id, transaction_type, amount,
                           description, timestamp, balance_after, related_account_id
                    FROM transactions
                    WHERE account_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (account_id, limit))

                for row in cursor.fetchall():
                    transactions.append(Transaction(
                        transaction_id=row[0],
                        account_id=row[1],
                        transaction_type=TransactionType(row[2]),
                        amount=Decimal(str(row[3])),
                        description=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        balance_after=Decimal(str(row[6])),
                        related_account_id=row[7]
                    ))
        except sqlite3.Error as e:
            self.logger.error(f"Error getting transactions: {e}")

        return transactions

    def freeze_account(self, account_id: int, is_frozen: bool) -> bool:
        """Freeze or unfreeze an account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET is_frozen = ? WHERE account_id = ?
                """, (is_frozen, account_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating freeze status: {e}")
            return False

    def set_daily_withdrawal_limit(self, account_id: int, limit: Optional[Decimal]) -> bool:
        """Set daily withdrawal limit for an account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET daily_withdrawal_limit = ? WHERE account_id = ?
                """, (float(limit) if limit else None, account_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error setting daily withdrawal limit: {e}")
            return False

    def update_interest_calculation(self, account_id: int, last_calculation: datetime) -> bool:
        """Update last interest calculation timestamp."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET last_interest_calculation = ? WHERE account_id = ?
                """, (last_calculation, account_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating interest calculation: {e}")
            return False

    def get_monthly_transactions(self, account_id: int, year: int, month: int) -> List[Transaction]:
        """Get transactions for a specific month."""
        transactions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Get transactions for the specified month
                cursor.execute("""
                    SELECT transaction_id, account_id, transaction_type, amount,
                           description, timestamp, balance_after, related_account_id
                    FROM transactions
                    WHERE account_id = ?
                    AND strftime('%Y', timestamp) = ?
                    AND strftime('%m', timestamp) = ?
                    ORDER BY timestamp ASC
                """, (account_id, str(year), f"{month:02d}"))

                for row in cursor.fetchall():
                    transactions.append(Transaction(
                        transaction_id=row[0],
                        account_id=row[1],
                        transaction_type=TransactionType(row[2]),
                        amount=Decimal(str(row[3])),
                        description=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        balance_after=Decimal(str(row[6])),
                        related_account_id=row[7]
                    ))
        except sqlite3.Error as e:
            self.logger.error(f"Error getting monthly transactions: {e}")

        return transactions

    def get_daily_withdrawals(self, account_id: int, date: datetime) -> Decimal:
        """Get total withdrawals for a specific day."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE account_id = ?
                    AND transaction_type IN ('withdrawal', 'transfer_out', 'bulk_transfer_out')
                    AND DATE(timestamp) = DATE(?)
                """, (account_id, date.date()))
                
                result = cursor.fetchone()
                return Decimal(str(result[0])) if result else Decimal('0.00')
        except sqlite3.Error as e:
            self.logger.error(f"Error getting daily withdrawals: {e}")
            return Decimal('0.00')

    def close(self):
        """Close database connections (placeholder for cleanup if needed)."""
        pass
