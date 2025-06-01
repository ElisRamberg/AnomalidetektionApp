#!/usr/bin/env python3
"""
Smoke test for SimpleCSVProcessor.
Run from project root with `python test_simple_processor.py`.
"""

import sys

# Ensure backend code is importable (must come before app imports)
sys.path.insert(0, "backend")

from datetime import datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from app.services.simple_processor import SimpleCSVProcessor  # noqa: E402


def main():
    processor = SimpleCSVProcessor()
    upload_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    file_path = "test_data/example_transactions.csv"

    print(
        f"🧪 Testing SimpleCSVProcessor on {file_path} " f"with upload_id {upload_id}"
    )
    txns = processor.process_csv_file(file_path, upload_id)
    print(f"✅ Processed {len(txns)} transactions.")

    # Basic assertions
    assert len(txns) == 5, f"Expected 5 transactions, got {len(txns)}"

    # Inspect first transaction
    t0 = txns[0]
    print("First transaction:", t0)

    # Field checks
    assert t0.amount == Decimal("100.50"), f"Amount mismatch: {t0.amount}"
    assert t0.account_id == "ACC001", f"Account ID mismatch: {t0.account_id}"
    assert isinstance(
        t0.timestamp, datetime
    ), f"Timestamp is not datetime: {type(t0.timestamp)}"

    print("🎉 All basic checks passed.")


if __name__ == "__main__":
    main()
