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


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
