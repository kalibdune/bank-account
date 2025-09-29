"""
Bank Management System

A comprehensive banking account management system with CLI interface.
Supports account creation, transactions, transfers, and balance inquiries.
"""

__version__ = "0.1.0"
__author__ = "Developer"
__email__ = "dev@example.com"

from .models import Account, Transaction, AccountType, TransactionType
from .database import DatabaseManager
from .account_manager import AccountManager
from .cli import main


def create_account_manager(db_path: str = "bank.db") -> AccountManager:
    """
    Create an AccountManager instance with database.

    Args:
        db_path: Path to the database file

    Returns:
        AccountManager instance
    """
    db_manager = DatabaseManager(db_path)
    return AccountManager(db_manager)


__all__ = [
    "Account",
    "Transaction",
    "AccountType",
    "TransactionType",
    "DatabaseManager",
    "AccountManager",
    "create_account_manager",
    "main"
]
