import csv
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List

from ..models.transaction import Transaction


class SimpleCSVProcessor:
    """
    Simple processor that reads a CSV file and maps each row to a Transaction.
    """

    def process_csv_file(
        self,
        file_path: str,
        upload_id: str,
    ) -> List[Transaction]:
        """
        Read the CSV at file_path and parse each row.
        Return a list of Transaction objects.

        Args:
            file_path: Path to the CSV file
            upload_id: UUID string of the FileUpload record
        Returns:
            List of unsaved Transaction model instances
        """
        transactions: List[Transaction] = []
        with open(
            file_path,
            mode="r",
            newline="",
            encoding="utf-8",
        ) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Parse JSON fields
                raw_data = json.loads(row.get("raw_data") or "{}")
                processed_data = json.loads(row.get("processed_data") or "{}")

                # Parse amount
                amount = Decimal(row["amount"])

                # Parse timestamp (handle 'Z' UTC marker)
                ts_str = row["timestamp"]
                iso_ts = ts_str.replace("Z", "+00:00")
                timestamp = datetime.fromisoformat(iso_ts)

                txn = Transaction(
                    upload_id=uuid.UUID(upload_id),
                    external_transaction_id=row.get("external_transaction_id"),
                    amount=amount,
                    timestamp=timestamp,
                    account_id=row.get("account_id"),
                    description=row.get("description"),
                    category=row.get("category"),
                    reference=row.get("reference"),
                    raw_data=raw_data,
                    processed_data=processed_data,
                    day_of_week=row.get("day_of_week"),
                    hour_of_day=row.get("hour_of_day"),
                    is_weekend=row.get("is_weekend"),
                    month=row.get("month"),
                    quarter=row.get("quarter"),
                )
                transactions.append(txn)
        return transactions
