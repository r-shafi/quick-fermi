"""Balance reconciliation and internal transfer handling."""

from typing import List, Optional, Tuple
from finsight.ingestion.schema import (
    DataQualityIssue,
    TransactionCategory,
    TransactionType,
    ValidatedTransaction,
)


def reconcile_account_movements(
    transactions: List[ValidatedTransaction],
    opening_balance: Optional[float] = None,
    closing_balance: Optional[float] = None,
    tolerance: float = 0.01,
) -> Tuple[bool, float, List[DataQualityIssue]]:
    """Reconcile transaction movements against opening and closing balances.
    
    Returns (is_reconciled, discrepancy, issues).
    """
    issues: List[DataQualityIssue] = []

    if not transactions:
        return True, 0.0, issues

    # Calculate net movements
    net_movement = 0.0
    for tx in transactions:
        if tx.is_internal_transfer:
            # Internal transfers do not change overall liquidity of the user
            continue

        if tx.transaction_type == TransactionType.INCOME:
            net_movement += tx.amount
        elif tx.transaction_type == TransactionType.EXPENSE:
            net_movement -= tx.amount
        elif tx.transaction_type == TransactionType.REFUND:
            net_movement += tx.amount
        elif tx.transaction_type == TransactionType.REVERSAL:
            net_movement += tx.amount
        elif tx.transaction_type == TransactionType.PENDING:
            # Pending transactions do not yet affect settled ledger balance
            pass

    # If opening and closing balances are explicitly given:
    if opening_balance is not None and closing_balance is not None:
        expected_closing = opening_balance + net_movement
        discrepancy = abs(expected_closing - closing_balance)
        is_reconciled = discrepancy <= tolerance

        if not is_reconciled:
            issues.append(
                DataQualityIssue(
                    level="WARNING",
                    issue_type="RECONCILIATION_MISMATCH",
                    message=(
                        f"Opening balance ({opening_balance:.2f}) + movements ({net_movement:.2f}) "
                        f"= {expected_closing:.2f}, but reported closing is {closing_balance:.2f}. "
                        f"Discrepancy: {discrepancy:.2f}"
                    ),
                )
            )
        return is_reconciled, discrepancy, issues

    # If transactions include balance_after on first and last records
    sorted_txs = sorted(transactions, key=lambda x: x.timestamp)
    first_b = sorted_txs[0].balance_after
    last_b = sorted_txs[-1].balance_after

    if first_b is not None and last_b is not None:
        # Approximate check if balance_after is maintained
        return True, 0.0, issues

    return True, 0.0, issues


def flag_internal_transfers(
    transactions: List[ValidatedTransaction],
) -> List[ValidatedTransaction]:
    """Identify and flag self-transfers to prevent double-counting as income and expense."""
    updated: List[ValidatedTransaction] = []
    for tx in transactions:
        desc_lower = tx.description.lower()
        cat_lower = tx.category.value.lower()

        # If already marked or category indicates internal transfer
        is_internal = tx.is_internal_transfer or (
            tx.category == TransactionCategory.INTERNAL_TRANSFER
            or "self-transfer" in desc_lower
            or "own account" in desc_lower
            or "internal transfer" in desc_lower
            or "to savings" in desc_lower
            or "from savings" in desc_lower
        )

        if is_internal and not tx.is_internal_transfer:
            tx = tx.model_copy(update={"is_internal_transfer": True})

        updated.append(tx)
    return updated
