"""
Bank Management System

A comprehensive banking account management system with CLI interface.
Supports account creation, transactions, transfers, and balance inquiries.
"""

__version__ = "0.1.0"
__author__ = "Developer"
__email__ = "dev@example.com"

from .models import Account, Transaction
from .database import DatabaseManager
from .account_manager import AccountManager
from .cli import main

__all__ = [
    "Account",
    "Transaction",
    "DatabaseManager",
    "AccountManager",
    "main"
]
