"""Deduplication logic for incoming transaction streams."""

import hashlib
from typing import List, Set, Tuple
from finsight.ingestion.schema import DataQualityIssue, ValidatedTransaction


def compute_content_hash(tx: ValidatedTransaction) -> str:
    """Compute a deterministic hash for transaction content matching."""
    components = [
        tx.account_id,
        tx.timestamp.isoformat(),
        f"{tx.amount:.4f}",
        tx.currency,
        tx.transaction_type.value,
        str(tx.counterparty or ""),
        str(tx.description or "")[:32],
    ]
    raw = "|".join(components).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def deduplicate_transactions(
    transactions: List[ValidatedTransaction],
) -> Tuple[List[ValidatedTransaction], List[DataQualityIssue]]:
    """Deduplicate transactions by ID and by exact content hash.
    
    Policy: Keep the first occurrence, flag duplicates as WARNING issues.
    """
    seen_ids: Set[str] = set()
    seen_hashes: Set[str] = set()
    unique_txs: List[ValidatedTransaction] = []
    issues: List[DataQualityIssue] = []

    for idx, tx in enumerate(transactions):
        # Check transaction ID
        if tx.transaction_id in seen_ids:
            issues.append(
                DataQualityIssue(
                    level="WARNING",
                    issue_type="DUPLICATE_TRANSACTION_ID",
                    message=f"Duplicate transaction ID '{tx.transaction_id}' detected. Retaining first occurrence.",
                    row_index=idx,
                    transaction_id=tx.transaction_id,
                )
            )
            continue

        # Check content hash
        c_hash = compute_content_hash(tx)
        if c_hash in seen_hashes:
            issues.append(
                DataQualityIssue(
                    level="WARNING",
                    issue_type="DUPLICATE_CONTENT_HASH",
                    message=f"Duplicate content detected for transaction ID '{tx.transaction_id}'. Retaining first occurrence.",
                    row_index=idx,
                    transaction_id=tx.transaction_id,
                )
            )
            continue

        seen_ids.add(tx.transaction_id)
        seen_hashes.add(c_hash)
        unique_txs.append(tx)

    return unique_txs, issues
