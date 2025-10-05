"""
Account manager for the bank management system.

This module contains the business logic for managing bank accounts and transactions.
"""

import uuid
from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timedelta

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

        if account.is_frozen:
            raise ValueError("Account is frozen")

        # Check if withdrawal is possible
        if not account.can_withdraw(amount):
            raise ValueError(f"Insufficient funds. Available: {account.balance - account.minimum_balance} RUB")

        # Check daily withdrawal limit
        if account.daily_withdrawal_limit is not None:
            today_withdrawals = self.db.get_daily_withdrawals(account_id, datetime.now())
            if not account.is_within_daily_limit(amount, today_withdrawals):
                raise ValueError(f"Daily withdrawal limit exceeded. Limit: {account.daily_withdrawal_limit} RUB, Today's withdrawals: {today_withdrawals} RUB")

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

    def freeze_account(self, account_id: int, reason: str = "") -> bool:
        """Заморозить счет (временно заблокировать операции)."""
        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        
        if account.is_frozen:
            raise ValueError("Account is already frozen")
        
        if not account.is_active:
            raise ValueError("Cannot freeze inactive account")
        
        # Обновляем статус заморозки в базе данных
        success = self.db.freeze_account(account_id, True)
        if success:
            # Записываем транзакцию о заморозке
            self.record_transaction(
                account_id,
                TransactionType.FEE,
                Decimal('0.00'),
                f"Account frozen: {reason}" if reason else "Account frozen",
                account.balance
            )
        
        return success

    def unfreeze_account(self, account_id: int, reason: str = "") -> bool:
        """Разморозить счет."""
        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        
        if not account.is_frozen:
            raise ValueError("Account is not frozen")
        
        # Обновляем статус заморозки в базе данных
        success = self.db.freeze_account(account_id, False)
        if success:
            # Записываем транзакцию о разморозке
            self.record_transaction(
                account_id,
                TransactionType.FEE,
                Decimal('0.00'),
                f"Account unfrozen: {reason}" if reason else "Account unfrozen",
                account.balance
            )
        
        return success

    def set_daily_withdrawal_limit(self, account_id: int, limit: Optional[Decimal]) -> bool:
        """Установить дневной лимит на снятие средств."""
        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        
        if limit is not None and limit < 0:
            raise ValueError("Daily withdrawal limit cannot be negative")
        
        success = self.db.set_daily_withdrawal_limit(account_id, limit)
        if success:
            limit_str = f"{limit} RUB" if limit else "unlimited"
            self.record_transaction(
                account_id,
                TransactionType.FEE,
                Decimal('0.00'),
                f"Daily withdrawal limit set to {limit_str}",
                account.balance
            )
        
        return success

    def get_monthly_statement(self, account_id: int, year: int, month: int) -> Optional[dict]:
        """Получить месячную выписку по счету."""
        account = self.db.get_account(account_id)
        if not account:
            return None
        
        # Получаем транзакции за месяц
        transactions = self.db.get_monthly_transactions(account_id, year, month)
        
        # Рассчитываем статистику
        opening_balance = Decimal('0.00')
        closing_balance = account.balance
        total_deposits = Decimal('0.00')
        total_withdrawals = Decimal('0.00')
        total_transfers_in = Decimal('0.00')
        total_transfers_out = Decimal('0.00')
        total_interest = Decimal('0.00')
        total_fees = Decimal('0.00')
        
        if transactions:
            # Начальный баланс = текущий баланс - все изменения за месяц
            for txn in transactions:
                if txn.transaction_type == TransactionType.DEPOSIT:
                    total_deposits += txn.amount
                elif txn.transaction_type == TransactionType.WITHDRAWAL:
                    total_withdrawals += txn.amount
                elif txn.transaction_type in [TransactionType.TRANSFER_IN, TransactionType.BULK_TRANSFER_IN]:
                    total_transfers_in += txn.amount
                elif txn.transaction_type in [TransactionType.TRANSFER_OUT, TransactionType.BULK_TRANSFER_OUT]:
                    total_transfers_out += txn.amount
                elif txn.transaction_type == TransactionType.INTEREST:
                    total_interest += txn.amount
                elif txn.transaction_type == TransactionType.FEE:
                    total_fees += txn.amount
            
            # Рассчитываем начальный баланс
            net_change = (total_deposits + total_transfers_in + total_interest) - (total_withdrawals + total_transfers_out + total_fees)
            opening_balance = closing_balance - net_change
        
        return {
            'account': account,
            'period': f"{year}-{month:02d}",
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_transfers_in': total_transfers_in,
            'total_transfers_out': total_transfers_out,
            'total_interest': total_interest,
            'total_fees': total_fees,
            'net_change': closing_balance - opening_balance,
            'transactions': transactions,
            'transaction_count': len(transactions)
        }

    def calculate_interest(self, account_id: int) -> Optional[Decimal]:
        """Рассчитать и начислить проценты на остаток (для сберегательных счетов)."""
        account = self.db.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        
        if not account.is_active:
            raise ValueError("Account is not active")
        
        if account.interest_rate <= 0:
            return Decimal('0.00')
        
        # Рассчитываем проценты с последнего начисления или с даты создания счета
        last_calculation = account.last_interest_calculation or account.created_at
        now = datetime.now()
        
        # Если прошло меньше дня, не начисляем проценты
        days_passed = (now - last_calculation).days
        if days_passed < 1:
            return Decimal('0.00')
        
        # Рассчитываем проценты: (баланс * годовая_ставка * дни) / 365
        daily_rate = account.interest_rate / Decimal('365')
        interest_amount = account.balance * daily_rate * Decimal(str(days_passed)) / Decimal('100')
        
        # Округляем до копеек
        interest_amount = interest_amount.quantize(Decimal('0.01'))
        
        if interest_amount > 0:
            # Начисляем проценты
            new_balance = account.balance + interest_amount
            if self.db.update_account_balance(account_id, new_balance):
                # Обновляем дату последнего начисления
                self.db.update_interest_calculation(account_id, now)
                
                # Записываем транзакцию
                self.record_transaction(
                    account_id,
                    TransactionType.INTEREST,
                    interest_amount,
                    f"Interest accrued for {days_passed} days at {account.interest_rate}% annual rate",
                    new_balance
                )
                
                return interest_amount
        
        return Decimal('0.00')

    def bulk_transfer(self, from_account_id: int, transfers: List[dict], description: str = "") -> dict:
        """Массовый перевод на несколько счетов.
        
        Args:
            from_account_id: ID счета-источника
            transfers: Список словарей с ключами 'to_account_id' и 'amount'
            description: Описание операции
            
        Returns:
            Словарь с результатами операции
        """
        if not transfers:
            raise ValueError("Transfer list cannot be empty")
        
        from_account = self.db.get_account(from_account_id)
        if not from_account:
            raise ValueError("Source account not found")
        
        if not from_account.is_active:
            raise ValueError("Source account is not active")
        
        if from_account.is_frozen:
            raise ValueError("Source account is frozen")
        
        # Рассчитываем общую сумму
        total_amount = Decimal('0.00')
        validated_transfers = []
        
        for transfer in transfers:
            to_account_id = transfer.get('to_account_id')
            amount = Decimal(str(transfer.get('amount', 0)))
            
            if amount <= 0:
                raise ValueError(f"Transfer amount must be positive for account {to_account_id}")
            
            if to_account_id == from_account_id:
                raise ValueError("Cannot transfer to the same account")
            
            to_account = self.db.get_account(to_account_id)
            if not to_account:
                raise ValueError(f"Destination account {to_account_id} not found")
            
            if not to_account.is_active:
                raise ValueError(f"Destination account {to_account_id} is not active")
            
            total_amount += amount
            validated_transfers.append({
                'to_account_id': to_account_id,
                'to_account': to_account,
                'amount': amount
            })
        
        # Проверяем достаточность средств
        if not from_account.can_withdraw(total_amount):
            raise ValueError(f"Insufficient funds. Required: {total_amount} RUB, Available: {from_account.balance - from_account.minimum_balance} RUB")
        
        # Выполняем переводы
        successful_transfers = []
        failed_transfers = []
        
        for transfer in validated_transfers:
            try:
                to_account_id = transfer['to_account_id']
                to_account = transfer['to_account']
                amount = transfer['amount']
                
                # Обновляем балансы
                from_new_balance = from_account.balance - amount
                to_new_balance = to_account.balance + amount
                
                if (self.db.update_account_balance(from_account_id, from_new_balance) and
                    self.db.update_account_balance(to_account_id, to_new_balance)):
                    
                    # Записываем транзакции
                    transfer_desc = description or f"Bulk transfer to account {to_account.account_number}"
                    receive_desc = description or f"Bulk transfer from account {from_account.account_number}"
                    
                    self.record_transaction(
                        from_account_id,
                        TransactionType.BULK_TRANSFER_OUT,
                        amount,
                        transfer_desc,
                        from_new_balance,
                        to_account_id
                    )
                    
                    self.record_transaction(
                        to_account_id,
                        TransactionType.BULK_TRANSFER_IN,
                        amount,
                        receive_desc,
                        to_new_balance,
                        from_account_id
                    )
                    
                    successful_transfers.append({
                        'to_account_id': to_account_id,
                        'amount': amount,
                        'status': 'success'
                    })
                    
                    # Обновляем баланс источника для следующей итерации
                    from_account.balance = from_new_balance
                    
                else:
                    failed_transfers.append({
                        'to_account_id': to_account_id,
                        'amount': amount,
                        'status': 'failed',
                        'error': 'Database update failed'
                    })
                    
            except Exception as e:
                failed_transfers.append({
                    'to_account_id': transfer['to_account_id'],
                    'amount': transfer['amount'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'total_amount': total_amount,
            'successful_count': len(successful_transfers),
            'failed_count': len(failed_transfers),
            'successful_transfers': successful_transfers,
            'failed_transfers': failed_transfers
        }

    def get_account_statistics(self, account_id: int, days: int = 30) -> Optional[dict]:
        """Получить детальную статистику по счету за указанный период."""
        account = self.db.get_account(account_id)
        if not account:
            return None
        
        # Получаем все транзакции за период
        all_transactions = self.db.get_account_transactions(account_id, limit=1000)
        
        # Фильтруем транзакции за последние N дней
        cutoff_date = datetime.now() - timedelta(days=days)
        period_transactions = [
            txn for txn in all_transactions
            if txn.timestamp >= cutoff_date
        ]
        
        # Инициализируем счетчики
        stats = {
            'account': account,
            'period_days': days,
            'total_transactions': len(period_transactions),
            'deposits': {'count': 0, 'total': Decimal('0.00'), 'average': Decimal('0.00')},
            'withdrawals': {'count': 0, 'total': Decimal('0.00'), 'average': Decimal('0.00')},
            'transfers_in': {'count': 0, 'total': Decimal('0.00'), 'average': Decimal('0.00')},
            'transfers_out': {'count': 0, 'total': Decimal('0.00'), 'average': Decimal('0.00')},
            'interest': {'count': 0, 'total': Decimal('0.00')},
            'fees': {'count': 0, 'total': Decimal('0.00')},
            'daily_activity': {},
            'largest_deposit': Decimal('0.00'),
            'largest_withdrawal': Decimal('0.00'),
            'most_active_day': None,
            'balance_trend': []
        }
        
        # Анализируем транзакции
        daily_counts = {}
        
        for txn in period_transactions:
            day_key = txn.timestamp.date().isoformat()
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
            
            if txn.transaction_type == TransactionType.DEPOSIT:
                stats['deposits']['count'] += 1
                stats['deposits']['total'] += txn.amount
                if txn.amount > stats['largest_deposit']:
                    stats['largest_deposit'] = txn.amount
                    
            elif txn.transaction_type == TransactionType.WITHDRAWAL:
                stats['withdrawals']['count'] += 1
                stats['withdrawals']['total'] += txn.amount
                if txn.amount > stats['largest_withdrawal']:
                    stats['largest_withdrawal'] = txn.amount
                    
            elif txn.transaction_type in [TransactionType.TRANSFER_IN, TransactionType.BULK_TRANSFER_IN]:
                stats['transfers_in']['count'] += 1
                stats['transfers_in']['total'] += txn.amount
                
            elif txn.transaction_type in [TransactionType.TRANSFER_OUT, TransactionType.BULK_TRANSFER_OUT]:
                stats['transfers_out']['count'] += 1
                stats['transfers_out']['total'] += txn.amount
                
            elif txn.transaction_type == TransactionType.INTEREST:
                stats['interest']['count'] += 1
                stats['interest']['total'] += txn.amount
                
            elif txn.transaction_type == TransactionType.FEE:
                stats['fees']['count'] += 1
                stats['fees']['total'] += txn.amount
        
        # Рассчитываем средние значения
        if stats['deposits']['count'] > 0:
            stats['deposits']['average'] = stats['deposits']['total'] / stats['deposits']['count']
        
        if stats['withdrawals']['count'] > 0:
            stats['withdrawals']['average'] = stats['withdrawals']['total'] / stats['withdrawals']['count']
        
        if stats['transfers_in']['count'] > 0:
            stats['transfers_in']['average'] = stats['transfers_in']['total'] / stats['transfers_in']['count']
        
        if stats['transfers_out']['count'] > 0:
            stats['transfers_out']['average'] = stats['transfers_out']['total'] / stats['transfers_out']['count']
        
        # Находим самый активный день
        if daily_counts:
            stats['most_active_day'] = max(daily_counts.items(), key=lambda x: x[1])
            stats['daily_activity'] = daily_counts
        
        # Тренд баланса (последние 10 транзакций)
        recent_transactions = period_transactions[:10]
        stats['balance_trend'] = [
            {
                'date': txn.timestamp.isoformat(),
                'balance': txn.balance_after,
                'change': txn.amount if txn.transaction_type in [
                    TransactionType.DEPOSIT, TransactionType.TRANSFER_IN,
                    TransactionType.BULK_TRANSFER_IN, TransactionType.INTEREST
                ] else -txn.amount
            }
            for txn in recent_transactions
        ]
        
        return stats
