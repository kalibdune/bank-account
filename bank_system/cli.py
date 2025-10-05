"""
CLI interface for the bank management system.

This module provides a command-line interface for managing bank accounts and transactions.
"""

import click
from decimal import Decimal, InvalidOperation
from typing import Optional
import os
import sys

from .models import AccountType, TransactionType
from .database import DatabaseManager
from .account_manager import AccountManager


class BankCLI:
    """CLI wrapper for bank operations."""

    def __init__(self, db_path: str = "bank.db"):
        """Initialize CLI with database."""
        self.db_manager = DatabaseManager(db_path)
        self.account_manager = AccountManager(self.db_manager)

    def format_currency(self, amount: Decimal) -> str:
        """Format currency for display."""
        return f"{amount:,.2f} ₽"

    def parse_currency(self, amount_str: str) -> Decimal:
        """Parse currency input."""
        try:
            # Remove ₽ and commas
            clean_str = amount_str.replace('₽', '').replace(',', '').strip()
            return Decimal(clean_str)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid amount: {amount_str}")


@click.group()
@click.option('--db-path', default='bank.db', help='Database file path')
@click.pass_context
def cli(ctx, db_path):
    """Bank Management System CLI"""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = BankCLI(db_path)


@cli.command()
@click.option('--name', prompt='Customer name', help='Customer full name')
@click.option('--type', 'account_type',
              type=click.Choice(['checking', 'savings', 'business']),
              prompt='Account type', help='Type of account')
@click.option('--initial-deposit', default='0.00',
              prompt='Initial deposit', help='Initial deposit amount')
@click.option('--minimum-balance', default='0.00',
              prompt='Minimum balance', help='Minimum balance requirement')
@click.pass_context
def create_account(ctx, name, account_type, initial_deposit, minimum_balance):
    """Create a new bank account."""
    bank_cli = ctx.obj['cli']

    try:
        initial_amount = bank_cli.parse_currency(initial_deposit)
        min_balance = bank_cli.parse_currency(minimum_balance)
        acc_type = AccountType(account_type)

        account = bank_cli.account_manager.create_account(
            customer_name=name,
            account_type=acc_type,
            initial_deposit=initial_amount,
            minimum_balance=min_balance
        )

        if account:
            click.echo(f"✅ Account created successfully!")
            click.echo(f"Account Number: {account.account_number}")
            click.echo(f"Account ID: {account.account_id}")
            click.echo(f"Customer: {account.customer_name}")
            click.echo(f"Type: {account.account_type.value}")
            click.echo(f"Balance: {bank_cli.format_currency(account.balance)}")
            click.echo(f"Minimum Balance: {bank_cli.format_currency(account.minimum_balance)}")
        else:
            click.echo("❌ Failed to create account", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.pass_context
def show_account(ctx, account_id):
    """Show account details."""
    bank_cli = ctx.obj['cli']

    try:
        summary = bank_cli.account_manager.get_account_summary(account_id)
        if not summary:
            click.echo("❌ Account not found", err=True)
            return

        account = summary['account']
        click.echo(f"\n📊 Account Details")
        click.echo(f"{'='*50}")
        click.echo(f"Account ID: {account.account_id}")
        click.echo(f"Account Number: {account.account_number}")
        click.echo(f"Customer: {account.customer_name}")
        click.echo(f"Type: {account.account_type.value}")
        click.echo(f"Balance: {bank_cli.format_currency(account.balance)}")
        click.echo(f"Minimum Balance: {bank_cli.format_currency(account.minimum_balance)}")
        click.echo(f"Available Balance: {bank_cli.format_currency(summary['available_balance'])}")
        click.echo(f"Status: {'Active' if account.is_active else 'Inactive'}")
        click.echo(f"Frozen: {'Yes' if account.is_frozen else 'No'}")
        if account.daily_withdrawal_limit:
            click.echo(f"Daily Withdrawal Limit: {bank_cli.format_currency(account.daily_withdrawal_limit)}")
        else:
            click.echo(f"Daily Withdrawal Limit: Unlimited")
        click.echo(f"Interest Rate: {account.interest_rate}% per year")
        click.echo(f"Created: {account.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        click.echo(f"\n💰 Transaction Summary")
        click.echo(f"Total Deposits: {bank_cli.format_currency(summary['total_deposits'])}")
        click.echo(f"Total Withdrawals: {bank_cli.format_currency(summary['total_withdrawals'])}")

        if summary['recent_transactions']:
            click.echo(f"\n📋 Recent Transactions")
            click.echo(f"{'Type':<15} {'Amount':<15} {'Balance':<15} {'Date':<20} {'Description'}")
            click.echo(f"{'-'*85}")
            for txn in summary['recent_transactions']:
                click.echo(
                    f"{txn.transaction_type.value:<15} "
                    f"{bank_cli.format_currency(txn.amount):<15} "
                    f"{bank_cli.format_currency(txn.balance_after):<15} "
                    f"{txn.timestamp.strftime('%Y-%m-%d %H:%M'):<20} "
                    f"{txn.description}"
                )

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--amount', prompt='Deposit amount', help='Amount to deposit')
@click.option('--description', default='', help='Transaction description')
@click.pass_context
def deposit(ctx, account_id, amount, description):
    """Deposit money to an account."""
    bank_cli = ctx.obj['cli']

    try:
        deposit_amount = bank_cli.parse_currency(amount)

        if bank_cli.account_manager.deposit(account_id, deposit_amount, description):
            new_balance = bank_cli.account_manager.get_balance(account_id)
            click.echo(f"✅ Deposit successful!")
            click.echo(f"Amount: {bank_cli.format_currency(deposit_amount)}")
            click.echo(f"New Balance: {bank_cli.format_currency(new_balance)}")
        else:
            click.echo("❌ Deposit failed", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--amount', prompt='Withdrawal amount', help='Amount to withdraw')
@click.option('--description', default='', help='Transaction description')
@click.pass_context
def withdraw(ctx, account_id, amount, description):
    """Withdraw money from an account."""
    bank_cli = ctx.obj['cli']

    try:
        withdraw_amount = bank_cli.parse_currency(amount)

        if bank_cli.account_manager.withdraw(account_id, withdraw_amount, description):
            new_balance = bank_cli.account_manager.get_balance(account_id)
            click.echo(f"✅ Withdrawal successful!")
            click.echo(f"Amount: {bank_cli.format_currency(withdraw_amount)}")
            click.echo(f"New Balance: {bank_cli.format_currency(new_balance)}")
        else:
            click.echo("❌ Withdrawal failed", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--from-account', type=int, prompt='From Account ID', help='Source account ID')
@click.option('--to-account', type=int, prompt='To Account ID', help='Destination account ID')
@click.option('--amount', prompt='Transfer amount', help='Amount to transfer')
@click.option('--description', default='', help='Transfer description')
@click.pass_context
def transfer(ctx, from_account, to_account, amount, description):
    """Transfer money between accounts."""
    bank_cli = ctx.obj['cli']

    try:
        transfer_amount = bank_cli.parse_currency(amount)

        if bank_cli.account_manager.transfer(from_account, to_account, transfer_amount, description):
            from_balance = bank_cli.account_manager.get_balance(from_account)
            to_balance = bank_cli.account_manager.get_balance(to_account)

            click.echo(f"✅ Transfer successful!")
            click.echo(f"Amount: {bank_cli.format_currency(transfer_amount)}")
            click.echo(f"From Account {from_account} Balance: {bank_cli.format_currency(from_balance)}")
            click.echo(f"To Account {to_account} Balance: {bank_cli.format_currency(to_balance)}")
        else:
            click.echo("❌ Transfer failed", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.pass_context
def balance(ctx, account_id):
    """Check account balance."""
    bank_cli = ctx.obj['cli']

    try:
        account = bank_cli.account_manager.get_account(account_id)
        if not account:
            click.echo("❌ Account not found", err=True)
            return

        click.echo(f"\n💰 Account Balance")
        click.echo(f"Account: {account.account_number}")
        click.echo(f"Customer: {account.customer_name}")
        click.echo(f"Current Balance: {bank_cli.format_currency(account.balance)}")
        click.echo(f"Available Balance: {bank_cli.format_currency(account.balance - account.minimum_balance)}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--reason', default='', help='Reason for freezing')
@click.pass_context
def freeze_account(ctx, account_id, reason):
    """Freeze an account to prevent transactions."""
    bank_cli = ctx.obj['cli']

    try:
        if bank_cli.account_manager.freeze_account(account_id, reason):
            click.echo(f"✅ Account {account_id} has been frozen")
            if reason:
                click.echo(f"Reason: {reason}")
        else:
            click.echo("❌ Failed to freeze account", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--reason', default='', help='Reason for unfreezing')
@click.pass_context
def unfreeze_account(ctx, account_id, reason):
    """Unfreeze an account to allow transactions."""
    bank_cli = ctx.obj['cli']

    try:
        if bank_cli.account_manager.unfreeze_account(account_id, reason):
            click.echo(f"✅ Account {account_id} has been unfrozen")
            if reason:
                click.echo(f"Reason: {reason}")
        else:
            click.echo("❌ Failed to unfreeze account", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--limit', prompt='Daily withdrawal limit (or "none" for unlimited)', help='Daily withdrawal limit')
@click.pass_context
def set_withdrawal_limit(ctx, account_id, limit):
    """Set daily withdrawal limit for an account."""
    bank_cli = ctx.obj['cli']

    try:
        if limit.lower() in ['none', 'unlimited', '']:
            limit_amount = None
        else:
            limit_amount = bank_cli.parse_currency(limit)

        if bank_cli.account_manager.set_daily_withdrawal_limit(account_id, limit_amount):
            if limit_amount:
                click.echo(f"✅ Daily withdrawal limit set to {bank_cli.format_currency(limit_amount)}")
            else:
                click.echo(f"✅ Daily withdrawal limit removed (unlimited)")
        else:
            click.echo("❌ Failed to set withdrawal limit", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--year', type=int, prompt='Year', help='Year for statement')
@click.option('--month', type=int, prompt='Month', help='Month for statement (1-12)')
@click.pass_context
def monthly_statement(ctx, account_id, year, month):
    """Get monthly statement for an account."""
    bank_cli = ctx.obj['cli']

    try:
        if month < 1 or month > 12:
            click.echo("❌ Month must be between 1 and 12", err=True)
            return

        statement = bank_cli.account_manager.get_monthly_statement(account_id, year, month)
        if not statement:
            click.echo("❌ Account not found", err=True)
            return

        account = statement['account']
        click.echo(f"\n📄 Monthly Statement - {statement['period']}")
        click.echo(f"{'='*60}")
        click.echo(f"Account: {account.account_number} ({account.customer_name})")
        click.echo(f"Period: {statement['period']}")
        click.echo(f"\n💰 Balance Summary")
        click.echo(f"Opening Balance: {bank_cli.format_currency(statement['opening_balance'])}")
        click.echo(f"Closing Balance: {bank_cli.format_currency(statement['closing_balance'])}")
        click.echo(f"Net Change: {bank_cli.format_currency(statement['net_change'])}")
        
        click.echo(f"\n📊 Transaction Summary")
        click.echo(f"Total Transactions: {statement['transaction_count']}")
        click.echo(f"Deposits: {bank_cli.format_currency(statement['total_deposits'])}")
        click.echo(f"Withdrawals: {bank_cli.format_currency(statement['total_withdrawals'])}")
        click.echo(f"Transfers In: {bank_cli.format_currency(statement['total_transfers_in'])}")
        click.echo(f"Transfers Out: {bank_cli.format_currency(statement['total_transfers_out'])}")
        click.echo(f"Interest Earned: {bank_cli.format_currency(statement['total_interest'])}")
        click.echo(f"Fees: {bank_cli.format_currency(statement['total_fees'])}")

        if statement['transactions']:
            click.echo(f"\n📋 Transaction Details")
            click.echo(f"{'Date':<12} {'Type':<15} {'Amount':<15} {'Balance':<15} {'Description'}")
            click.echo(f"{'-'*85}")
            for txn in statement['transactions']:
                click.echo(
                    f"{txn.timestamp.strftime('%Y-%m-%d'):<12} "
                    f"{txn.transaction_type.value:<15} "
                    f"{bank_cli.format_currency(txn.amount):<15} "
                    f"{bank_cli.format_currency(txn.balance_after):<15} "
                    f"{txn.description}"
                )

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.pass_context
def calculate_interest(ctx, account_id):
    """Calculate and apply interest to a savings account."""
    bank_cli = ctx.obj['cli']

    try:
        interest = bank_cli.account_manager.calculate_interest(account_id)
        if interest is not None:
            if interest > 0:
                click.echo(f"✅ Interest calculated and applied!")
                click.echo(f"Interest Amount: {bank_cli.format_currency(interest)}")
                new_balance = bank_cli.account_manager.get_balance(account_id)
                click.echo(f"New Balance: {bank_cli.format_currency(new_balance)}")
            else:
                click.echo("ℹ️ No interest to calculate (rate is 0% or insufficient time passed)")
        else:
            click.echo("❌ Failed to calculate interest", err=True)

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--from-account', type=int, prompt='From Account ID', help='Source account ID')
@click.option('--transfers', prompt='Transfer list (format: "account_id:amount,account_id:amount")',
              help='Comma-separated list of transfers')
@click.option('--description', default='', help='Transfer description')
@click.pass_context
def bulk_transfer(ctx, from_account, transfers, description):
    """Transfer money to multiple accounts at once."""
    bank_cli = ctx.obj['cli']

    try:
        # Parse transfer list
        transfer_list = []
        for transfer_str in transfers.split(','):
            parts = transfer_str.strip().split(':')
            if len(parts) != 2:
                click.echo(f"❌ Invalid transfer format: {transfer_str}", err=True)
                return
            
            to_account_id = int(parts[0])
            amount = bank_cli.parse_currency(parts[1])
            transfer_list.append({
                'to_account_id': to_account_id,
                'amount': amount
            })

        result = bank_cli.account_manager.bulk_transfer(from_account, transfer_list, description)
        
        click.echo(f"\n📊 Bulk Transfer Results")
        click.echo(f"{'='*50}")
        click.echo(f"Total Amount: {bank_cli.format_currency(result['total_amount'])}")
        click.echo(f"Successful Transfers: {result['successful_count']}")
        click.echo(f"Failed Transfers: {result['failed_count']}")
        
        if result['successful_transfers']:
            click.echo(f"\n✅ Successful Transfers:")
            for transfer in result['successful_transfers']:
                click.echo(f"  Account {transfer['to_account_id']}: {bank_cli.format_currency(transfer['amount'])}")
        
        if result['failed_transfers']:
            click.echo(f"\n❌ Failed Transfers:")
            for transfer in result['failed_transfers']:
                click.echo(f"  Account {transfer['to_account_id']}: {bank_cli.format_currency(transfer['amount'])} - {transfer['error']}")

    except (ValueError, IndexError) as e:
        click.echo(f"❌ Error: {e}", err=True)


@cli.command()
@click.option('--account-id', type=int, prompt='Account ID', help='Account ID')
@click.option('--days', default=30, help='Number of days for statistics (default: 30)')
@click.pass_context
def account_stats(ctx, account_id, days):
    """Get detailed account statistics."""
    bank_cli = ctx.obj['cli']

    try:
        stats = bank_cli.account_manager.get_account_statistics(account_id, days)
        if not stats:
            click.echo("❌ Account not found", err=True)
            return

        account = stats['account']
        click.echo(f"\n📈 Account Statistics - Last {days} Days")
        click.echo(f"{'='*60}")
        click.echo(f"Account: {account.account_number} ({account.customer_name})")
        click.echo(f"Current Balance: {bank_cli.format_currency(account.balance)}")
        
        click.echo(f"\n📊 Transaction Activity")
        click.echo(f"Total Transactions: {stats['total_transactions']}")
        
        click.echo(f"\n💰 Deposits")
        click.echo(f"  Count: {stats['deposits']['count']}")
        click.echo(f"  Total: {bank_cli.format_currency(stats['deposits']['total'])}")
        if stats['deposits']['count'] > 0:
            click.echo(f"  Average: {bank_cli.format_currency(stats['deposits']['average'])}")
        
        click.echo(f"\n💸 Withdrawals")
        click.echo(f"  Count: {stats['withdrawals']['count']}")
        click.echo(f"  Total: {bank_cli.format_currency(stats['withdrawals']['total'])}")
        if stats['withdrawals']['count'] > 0:
            click.echo(f"  Average: {bank_cli.format_currency(stats['withdrawals']['average'])}")
        
        click.echo(f"\n🔄 Transfers")
        click.echo(f"  Incoming: {stats['transfers_in']['count']} ({bank_cli.format_currency(stats['transfers_in']['total'])})")
        click.echo(f"  Outgoing: {stats['transfers_out']['count']} ({bank_cli.format_currency(stats['transfers_out']['total'])})")
        
        if stats['interest']['total'] > 0:
            click.echo(f"\n💎 Interest Earned: {bank_cli.format_currency(stats['interest']['total'])}")
        
        if stats['fees']['total'] > 0:
            click.echo(f"\n💳 Fees: {bank_cli.format_currency(stats['fees']['total'])}")
        
        click.echo(f"\n🏆 Records")
        if stats['largest_deposit'] > 0:
            click.echo(f"Largest Deposit: {bank_cli.format_currency(stats['largest_deposit'])}")
        if stats['largest_withdrawal'] > 0:
            click.echo(f"Largest Withdrawal: {bank_cli.format_currency(stats['largest_withdrawal'])}")
        
        if stats['most_active_day']:
            click.echo(f"Most Active Day: {stats['most_active_day'][0]} ({stats['most_active_day'][1]} transactions)")

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
