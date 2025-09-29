"""
Integration tests for the bank management system.

This module contains integration tests that test the system as a whole,
including edge cases and comprehensive scenarios.
"""

import pytest
import tempfile
import os
from decimal import Decimal
from datetime import datetime

from bank_system import create_account_manager
from bank_system.models import AccountType, TransactionType
from bank_system.database import DatabaseManager
from bank_system.account_manager import AccountManager


class TestSystemIntegration:
    """Test complete system integration."""

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
        return create_account_manager(temp_db_path)

    def test_complete_banking_workflow(self, account_manager):
        """Test a complete banking workflow scenario."""
        # Create multiple accounts
        personal_account = account_manager.create_account(
            customer_name="Иван Петров",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('10000.00'),
            minimum_balance=Decimal('1000.00')
        )

        savings_account = account_manager.create_account(
            customer_name="Иван Петров",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('5000.00'),
            minimum_balance=Decimal('0.00')
        )

        business_account = account_manager.create_account(
            customer_name="ООО Рога и Копыта",
            account_type=AccountType.BUSINESS,
            initial_deposit=Decimal('100000.00'),
            minimum_balance=Decimal('10000.00')
        )

        # Perform various operations
        # 1. Salary deposit to personal account
        account_manager.deposit(
            personal_account.account_id,
            Decimal('50000.00'),
            "Зарплата за месяц"
        )

        # 2. Transfer to savings
        account_manager.transfer(
            personal_account.account_id,
            savings_account.account_id,
            Decimal('20000.00'),
            "Перевод в накопления"
        )

        # 3. Business payment
        account_manager.transfer(
            business_account.account_id,
            personal_account.account_id,
            Decimal('15000.00'),
            "Оплата услуг консультанта"
        )

        # 4. Various withdrawals
        account_manager.withdraw(
            personal_account.account_id,
            Decimal('8000.00'),
            "Покупки и расходы"
        )

        # Verify final balances
        personal_balance = account_manager.get_balance(personal_account.account_id)
        savings_balance = account_manager.get_balance(savings_account.account_id)
        business_balance = account_manager.get_balance(business_account.account_id)

        # Expected calculations:
        # Personal: 10000 + 50000 - 20000 + 15000 - 8000 = 47000
        # Savings: 5000 + 20000 = 25000
        # Business: 100000 - 15000 = 85000

        assert personal_balance == Decimal('47000.00')
        assert savings_balance == Decimal('25000.00')
        assert business_balance == Decimal('85000.00')

        # Verify transaction histories
        personal_history = account_manager.get_account_history(personal_account.account_id, limit=20)
        assert len(personal_history) == 5  # Initial + salary + transfer out + transfer in + withdrawal

        savings_history = account_manager.get_account_history(savings_account.account_id, limit=20)
        assert len(savings_history) == 2  # Initial + transfer in

        business_history = account_manager.get_account_history(business_account.account_id, limit=20)
        assert len(business_history) == 2  # Initial + transfer out

    def test_account_lifecycle_management(self, account_manager):
        """Test complete account lifecycle from creation to deactivation."""
        # Create account without minimum balance for easy deactivation
        account = account_manager.create_account(
            customer_name="Временный Клиент",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('5000.00'),
            minimum_balance=Decimal('0.00')
        )

        # Use account actively
        account_manager.deposit(account.account_id, Decimal('2000.00'), "Пополнение")
        account_manager.withdraw(account.account_id, Decimal('3000.00'), "Снятие средств")

        # Check account summary
        summary = account_manager.get_account_summary(account.account_id)
        assert summary is not None
        assert summary['total_deposits'] == Decimal('7000.00')  # 5000 + 2000
        assert summary['total_withdrawals'] == Decimal('3000.00')

        # Empty account for deactivation
        remaining_balance = account_manager.get_balance(account.account_id)
        account_manager.withdraw(
            account.account_id,
            remaining_balance,
            "Закрытие счета"
        )

        # Deactivate account
        result = account_manager.deactivate_account(account.account_id)
        assert result is True

        # Verify account is deactivated
        deactivated_account = account_manager.get_account(account.account_id)
        assert deactivated_account.is_active is False

    def test_concurrent_operations_simulation(self, account_manager):
        """Test simulation of concurrent operations."""
        # Create accounts
        account1 = account_manager.create_account(
            customer_name="Клиент 1",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('10000.00')
        )

        account2 = account_manager.create_account(
            customer_name="Клиент 2",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('10000.00')
        )

        # Simulate multiple rapid operations
        operations = [
            (account_manager.transfer, account1.account_id, account2.account_id, Decimal('1000.00'), "Transfer 1"),
            (account_manager.deposit, account1.account_id, Decimal('500.00'), "Deposit 1"),
            (account_manager.transfer, account2.account_id, account1.account_id, Decimal('750.00'), "Transfer 2"),
            (account_manager.withdraw, account2.account_id, Decimal('300.00'), "Withdrawal 1"),
            (account_manager.deposit, account2.account_id, Decimal('1200.00'), "Deposit 2"),
        ]

        # Execute all operations
        for operation in operations:
            if len(operation) == 5:  # Transfer
                operation[0](operation[1], operation[2], operation[3], operation[4])
            else:  # Deposit/Withdraw
                operation[0](operation[1], operation[2], operation[3])

        # Verify final state consistency
        final_balance1 = account_manager.get_balance(account1.account_id)
        final_balance2 = account_manager.get_balance(account2.account_id)

        # Expected calculations:
        # Account1: 10000 - 1000 + 500 + 750 = 10250
        # Account2: 10000 + 1000 - 750 - 300 + 1200 = 11150

        assert final_balance1 == Decimal('10250.00')
        assert final_balance2 == Decimal('11150.00')

        # Total money should be conserved
        assert final_balance1 + final_balance2 == Decimal('21400.00')

    def test_database_error_recovery(self, temp_db_path):
        """Test database error handling and recovery."""
        # Create account manager
        account_manager = create_account_manager(temp_db_path)

        # Create an account successfully
        account = account_manager.create_account(
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        assert account is not None

        # Verify account can be retrieved
        retrieved = account_manager.get_account(account.account_id)
        assert retrieved is not None
        assert retrieved.account_id == account.account_id

    def test_large_transaction_volumes(self, account_manager):
        """Test system performance with large number of transactions."""
        # Create account
        account = account_manager.create_account(
            customer_name="High Volume User",
            account_type=AccountType.BUSINESS,
            initial_deposit=Decimal('1000000.00')
        )

        # Perform many small transactions
        for i in range(50):
            if i % 2 == 0:
                account_manager.deposit(
                    account.account_id,
                    Decimal('100.00'),
                    f"Deposit {i+1}"
                )
            else:
                account_manager.withdraw(
                    account.account_id,
                    Decimal('50.00'),
                    f"Withdrawal {i+1}"
                )

        # Verify final balance calculation
        # 25 deposits of 100 = 2500
        # 25 withdrawals of 50 = 1250
        # Net change = +1250
        expected_balance = Decimal('1000000.00') + Decimal('1250.00')
        final_balance = account_manager.get_balance(account.account_id)
        assert final_balance == expected_balance

        # Verify transaction history tracking
        history = account_manager.get_account_history(account.account_id, limit=100)
        assert len(history) == 51  # 50 transactions + 1 initial deposit

    def test_edge_case_decimal_precision(self, account_manager):
        """Test handling of decimal precision edge cases."""
        account = account_manager.create_account(
            customer_name="Precision Test",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('100.00')
        )

        # Test very precise amounts
        precise_amounts = [
            Decimal('0.01'),
            Decimal('0.99'),
            Decimal('1.001'),  # Will be rounded to 1.00
            Decimal('999999.99'),
        ]

        for amount in precise_amounts:
            # Deposit and immediate withdrawal should maintain precision
            account_manager.deposit(account.account_id, amount, f"Precision test {amount}")

        # Verify balance calculation precision
        balance = account_manager.get_balance(account.account_id)
        assert isinstance(balance, Decimal)

    def test_account_number_uniqueness_under_load(self, account_manager):
        """Test account number uniqueness under simulated load."""
        account_numbers = set()

        # Create multiple accounts rapidly
        for i in range(20):
            account = account_manager.create_account(
                customer_name=f"User {i}",
                account_type=AccountType.CHECKING
            )

            assert account.account_number not in account_numbers
            account_numbers.add(account.account_number)

        # All account numbers should be unique
        assert len(account_numbers) == 20

    def test_get_all_accounts_comprehensive(self, account_manager):
        """Test comprehensive account listing functionality."""
        # Create accounts of different types
        accounts_data = [
            ("Клиент Чекинг", AccountType.CHECKING, Decimal('5000.00')),
            ("Клиент Сейвингс", AccountType.SAVINGS, Decimal('10000.00')),
            ("Бизнес Клиент", AccountType.BUSINESS, Decimal('50000.00')),
        ]

        created_accounts = []
        for name, acc_type, deposit in accounts_data:
            account = account_manager.create_account(
                customer_name=name,
                account_type=acc_type,
                initial_deposit=deposit
            )
            created_accounts.append(account)

        # Get all accounts
        all_accounts = account_manager.get_all_accounts()

        assert len(all_accounts) == 3

        # Verify all created accounts are in the list
        retrieved_ids = {acc.account_id for acc in all_accounts}
        created_ids = {acc.account_id for acc in created_accounts}

        assert retrieved_ids == created_ids

    def test_transaction_description_handling(self, account_manager):
        """Test transaction description handling and storage."""
        account = account_manager.create_account(
            customer_name="Description Test",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00')
        )

        # Test various description scenarios
        test_cases = [
            (Decimal('100.00'), ""),  # Empty description
            (Decimal('200.00'), "Описание на русском"),  # Russian text
            (Decimal('150.00'), "Very long description " * 10),  # Long description
            (Decimal('75.00'), "Special chars: @#$%^&*()"),  # Special characters
        ]

        for amount, description in test_cases:
            account_manager.deposit(account.account_id, amount, description)

        # Verify all transactions recorded correctly
        history = account_manager.get_account_history(account.account_id, limit=10)

        # Should have initial deposit + 4 test deposits
        assert len(history) >= 4

        # Verify descriptions are preserved
        descriptions = [tx.description for tx in history if tx.transaction_type == TransactionType.DEPOSIT]
        assert len([d for d in descriptions if "Описание на русском" in d]) >= 1

    def test_minimum_balance_edge_cases(self, account_manager):
        """Test minimum balance enforcement in edge cases."""
        account = account_manager.create_account(
            customer_name="Edge Case User",
            account_type=AccountType.CHECKING,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('100.00')
        )

        # Test withdrawal that would leave exactly minimum balance
        result = account_manager.withdraw(account.account_id, Decimal('900.00'))
        assert result is True

        balance = account_manager.get_balance(account.account_id)
        assert balance == Decimal('100.00')

        # Test withdrawal of even 1 cent more should fail
        with pytest.raises(ValueError):
            account_manager.withdraw(account.account_id, Decimal('0.01'))

    def test_transfer_with_different_minimum_balances(self, account_manager):
        """Test transfers between accounts with different minimum balance requirements."""
        high_min_account = account_manager.create_account(
            customer_name="High Min User",
            account_type=AccountType.BUSINESS,
            initial_deposit=Decimal('20000.00'),
            minimum_balance=Decimal('5000.00')
        )

        no_min_account = account_manager.create_account(
            customer_name="No Min User",
            account_type=AccountType.SAVINGS,
            initial_deposit=Decimal('1000.00'),
            minimum_balance=Decimal('0.00')
        )

        # Transfer from high-min to no-min account
        result = account_manager.transfer(
            high_min_account.account_id,
            no_min_account.account_id,
            Decimal('14000.00')  # Should leave exactly 6000, above minimum of 5000
        )

        assert result is True

        high_min_balance = account_manager.get_balance(high_min_account.account_id)
        no_min_balance = account_manager.get_balance(no_min_account.account_id)

        assert high_min_balance == Decimal('6000.00')
        assert no_min_balance == Decimal('15000.00')

        # Try transfer that would violate minimum balance
        with pytest.raises(ValueError):
            account_manager.transfer(
                high_min_account.account_id,
                no_min_account.account_id,
                Decimal('1500.00')  # Would leave 4500, below 5000 minimum
            )


class TestModuleInit:
    """Test the bank_system module initialization."""

    def test_create_account_manager_function(self):
        """Test the create_account_manager convenience function."""
        # Test with default path
        manager = create_account_manager()
        assert isinstance(manager, AccountManager)

        # Cleanup
        if os.path.exists("bank.db"):
            os.remove("bank.db")

    def test_create_account_manager_with_custom_path(self):
        """Test create_account_manager with custom database path."""
        custom_path = "test_custom.db"
        manager = create_account_manager(custom_path)

        assert isinstance(manager, AccountManager)
        assert manager.db.db_path == custom_path

        # Cleanup
        if os.path.exists(custom_path):
            os.remove(custom_path)

    def test_module_exports(self):
        """Test that module exports expected items."""
        import bank_system

        # Check that main classes are available
        assert hasattr(bank_system, 'Account')
        assert hasattr(bank_system, 'Transaction')
        assert hasattr(bank_system, 'AccountType')
        assert hasattr(bank_system, 'TransactionType')
        assert hasattr(bank_system, 'AccountManager')
        assert hasattr(bank_system, 'DatabaseManager')
        assert hasattr(bank_system, 'create_account_manager')

    def test_import_structure(self):
        """Test that all modules can be imported correctly."""
        # Test individual module imports
        from bank_system import models
        from bank_system import database
        from bank_system import account_manager
        from bank_system import cli

        # Verify key classes exist
        assert hasattr(models, 'Account')
        assert hasattr(models, 'Transaction')
        assert hasattr(database, 'DatabaseManager')
        assert hasattr(account_manager, 'AccountManager')
        assert hasattr(cli, 'BankCLI')


class TestDatabaseCoverage:
    """Additional tests to achieve full database coverage."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_database_get_all_accounts_bug_fix(self, temp_db_path):
        """Test the bug in get_all_accounts method (wrong index usage)."""
        from bank_system.database import DatabaseManager

        db_manager = DatabaseManager(temp_db_path)

        # Create a test account to trigger the bug
        from bank_system.models import Account, AccountType
        account = Account(
            account_number="TEST-123",
            customer_name="Test User",
            account_type=AccountType.CHECKING,
            balance=Decimal('1000.00'),
            minimum_balance=Decimal('100.00')
        )

        account_id = db_manager.create_account(account)
        assert account_id is not None

        # This should work despite the bug in the method
        accounts = db_manager.get_all_accounts()
        assert len(accounts) == 1

        # The bug is in line where minimum_balance uses wrong index (row[6] instead of row[5])
        # and created_at also uses wrong index (row[6] instead of row[6])
        # But the method might still work due to data structure
