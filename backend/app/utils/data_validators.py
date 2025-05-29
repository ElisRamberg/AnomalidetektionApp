"""Data validation utilities for transaction data."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .exceptions import ValidationError


class TransactionDataValidator:
    """Validator for transaction data quality and consistency."""

    def __init__(self):
        # Common patterns for validation
        self.account_id_pattern = re.compile(r"^[A-Z0-9]{3,20}$")
        self.transaction_id_pattern = re.compile(r"^[A-Z0-9\-_]{1,50}$")

        # Date formats to try for parsing
        self.date_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ]

    def validate_transaction_batch(
        self, transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a batch of transactions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Validation result with errors and warnings
        """
        result = {
            "valid": True,
            "total_transactions": len(transactions),
            "valid_transactions": 0,
            "invalid_transactions": 0,
            "errors": [],
            "warnings": [],
            "transaction_errors": {},
            "summary": {},
        }

        if not transactions:
            result["valid"] = False
            result["errors"].append("No transactions provided")
            return result

        # Validate each transaction
        for i, transaction in enumerate(transactions):
            tx_errors = self.validate_single_transaction(transaction)

            if tx_errors["errors"]:
                result["invalid_transactions"] += 1
                result["transaction_errors"][i] = tx_errors
                result["errors"].extend(
                    [f"Transaction {i}: {err}" for err in tx_errors["errors"]]
                )
            else:
                result["valid_transactions"] += 1

            if tx_errors["warnings"]:
                result["warnings"].extend(
                    [f"Transaction {i}: {warn}" for warn in tx_errors["warnings"]]
                )

        # Batch-level validation
        batch_validation = self._validate_batch_consistency(transactions)
        result["errors"].extend(batch_validation["errors"])
        result["warnings"].extend(batch_validation["warnings"])

        # Overall validity
        result["valid"] = len(result["errors"]) == 0

        # Create summary
        result["summary"] = self._create_validation_summary(transactions, result)

        return result

    def validate_single_transaction(
        self, transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a single transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Validation result for the transaction
        """
        errors = []
        warnings = []

        # Required fields validation
        required_fields = ["amount", "timestamp", "account_id"]
        for field in required_fields:
            if field not in transaction:
                errors.append(f"Missing required field: {field}")
            elif transaction[field] is None:
                errors.append(f"Required field '{field}' is null")

        # If required fields are missing, return early
        if errors:
            return {"errors": errors, "warnings": warnings}

        # Amount validation
        amount_validation = self._validate_amount(transaction.get("amount"))
        errors.extend(amount_validation["errors"])
        warnings.extend(amount_validation["warnings"])

        # Timestamp validation
        timestamp_validation = self._validate_timestamp(transaction.get("timestamp"))
        errors.extend(timestamp_validation["errors"])
        warnings.extend(timestamp_validation["warnings"])

        # Account ID validation
        account_validation = self._validate_account_id(transaction.get("account_id"))
        errors.extend(account_validation["errors"])
        warnings.extend(account_validation["warnings"])

        # Transaction ID validation (if present)
        if "id" in transaction or "transaction_id" in transaction:
            tx_id = transaction.get("id") or transaction.get("transaction_id")
            id_validation = self._validate_transaction_id(tx_id)
            errors.extend(id_validation["errors"])
            warnings.extend(id_validation["warnings"])

        # Description validation (if present)
        if "description" in transaction:
            desc_validation = self._validate_description(transaction.get("description"))
            warnings.extend(desc_validation["warnings"])

        return {"errors": errors, "warnings": warnings}

    def _validate_amount(self, amount: Any) -> Dict[str, List[str]]:
        """Validate transaction amount."""
        errors = []
        warnings = []

        if amount is None:
            errors.append("Amount cannot be null")
            return {"errors": errors, "warnings": warnings}

        # Try to convert to Decimal for precise validation
        try:
            if isinstance(amount, str):
                # Remove currency symbols and spaces
                cleaned_amount = re.sub(r"[^\d.-]", "", amount)
                decimal_amount = Decimal(cleaned_amount)
            else:
                decimal_amount = Decimal(str(amount))

            # Validate amount constraints
            if decimal_amount == 0:
                warnings.append("Zero amount transaction")
            elif decimal_amount < 0:
                warnings.append("Negative amount transaction")
            elif decimal_amount > Decimal("1000000"):  # 1 million
                warnings.append("Very large amount transaction")

            # Check decimal places
            if decimal_amount.as_tuple().exponent < -2:
                warnings.append("Amount has more than 2 decimal places")

        except (InvalidOperation, ValueError, TypeError):
            errors.append(f"Invalid amount format: {amount}")

        return {"errors": errors, "warnings": warnings}

    def _validate_timestamp(self, timestamp: Any) -> Dict[str, List[str]]:
        """Validate transaction timestamp."""
        errors = []
        warnings = []

        if timestamp is None:
            errors.append("Timestamp cannot be null")
            return {"errors": errors, "warnings": warnings}

        parsed_date = None

        # If already a datetime object
        if isinstance(timestamp, (datetime, date)):
            parsed_date = timestamp
        elif isinstance(timestamp, str):
            # Try to parse string timestamp
            for date_format in self.date_formats:
                try:
                    parsed_date = datetime.strptime(timestamp, date_format)
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                errors.append(f"Invalid timestamp format: {timestamp}")
                return {"errors": errors, "warnings": warnings}
        else:
            errors.append(f"Unsupported timestamp type: {type(timestamp)}")
            return {"errors": errors, "warnings": warnings}

        # Validate date range
        current_date = datetime.now()
        if parsed_date > current_date:
            warnings.append("Future timestamp detected")
        elif parsed_date.year < 2000:
            warnings.append("Very old timestamp detected")

        return {"errors": errors, "warnings": warnings}

    def _validate_account_id(self, account_id: Any) -> Dict[str, List[str]]:
        """Validate account identifier."""
        errors = []
        warnings = []

        if account_id is None:
            errors.append("Account ID cannot be null")
            return {"errors": errors, "warnings": warnings}

        account_str = str(account_id).strip()

        if not account_str:
            errors.append("Account ID cannot be empty")
        elif len(account_str) < 3:
            warnings.append("Account ID is very short")
        elif len(account_str) > 50:
            warnings.append("Account ID is very long")

        # Check for suspicious patterns
        if account_str.lower() in ["test", "demo", "example"]:
            warnings.append("Account ID appears to be a test account")

        return {"errors": errors, "warnings": warnings}

    def _validate_transaction_id(self, transaction_id: Any) -> Dict[str, List[str]]:
        """Validate transaction identifier."""
        errors = []
        warnings = []

        if transaction_id is None:
            return {"errors": errors, "warnings": warnings}  # Optional field

        tx_id_str = str(transaction_id).strip()

        if not tx_id_str:
            warnings.append("Empty transaction ID")
        elif len(tx_id_str) > 100:
            warnings.append("Transaction ID is very long")

        return {"errors": errors, "warnings": warnings}

    def _validate_description(self, description: Any) -> Dict[str, List[str]]:
        """Validate transaction description."""
        warnings = []

        if description is None:
            return {"warnings": warnings}  # Optional field

        desc_str = str(description).strip()

        if not desc_str:
            warnings.append("Empty description")
        elif len(desc_str) > 1000:
            warnings.append("Very long description")

        # Check for suspicious content
        suspicious_words = ["test", "dummy", "fake", "sample"]
        if any(word in desc_str.lower() for word in suspicious_words):
            warnings.append("Description contains test-like content")

        return {"warnings": warnings}

    def _validate_batch_consistency(
        self, transactions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Validate consistency across the batch of transactions."""
        errors = []
        warnings = []

        if len(transactions) < 2:
            return {"errors": errors, "warnings": warnings}

        # Check for duplicate transaction IDs
        tx_ids = []
        for tx in transactions:
            tx_id = tx.get("id") or tx.get("transaction_id")
            if tx_id:
                tx_ids.append(str(tx_id))

        if len(tx_ids) != len(set(tx_ids)):
            errors.append("Duplicate transaction IDs detected")

        # Check timestamp ordering
        timestamps = []
        for tx in transactions:
            if "timestamp" in tx:
                try:
                    parsed_ts = self._parse_timestamp(tx["timestamp"])
                    if parsed_ts:
                        timestamps.append(parsed_ts)
                except:
                    continue

        if len(timestamps) > 1:
            if timestamps != sorted(timestamps):
                warnings.append("Transactions are not chronologically ordered")

        # Check for account diversity
        accounts = set()
        for tx in transactions:
            if "account_id" in tx:
                accounts.add(str(tx["account_id"]))

        if len(accounts) == 1 and len(transactions) > 100:
            warnings.append("All transactions belong to a single account")

        return {"errors": errors, "warnings": warnings}

    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Helper to parse timestamp."""
        if isinstance(timestamp, (datetime, date)):
            return timestamp
        elif isinstance(timestamp, str):
            for date_format in self.date_formats:
                try:
                    return datetime.strptime(timestamp, date_format)
                except ValueError:
                    continue
        return None

    def _create_validation_summary(
        self, transactions: List[Dict[str, Any]], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create validation summary statistics."""
        summary = {
            "total_transactions": len(transactions),
            "valid_transactions": result["valid_transactions"],
            "invalid_transactions": result["invalid_transactions"],
            "validation_rate": (
                result["valid_transactions"] / len(transactions) if transactions else 0
            ),
            "error_count": len(result["errors"]),
            "warning_count": len(result["warnings"]),
        }

        # Analyze data characteristics
        if transactions:
            amounts = []
            accounts = set()
            timestamps = []

            for tx in transactions:
                # Collect amounts
                if "amount" in tx and tx["amount"] is not None:
                    try:
                        amounts.append(float(tx["amount"]))
                    except:
                        pass

                # Collect accounts
                if "account_id" in tx:
                    accounts.add(str(tx["account_id"]))

                # Collect timestamps
                if "timestamp" in tx:
                    parsed_ts = self._parse_timestamp(tx["timestamp"])
                    if parsed_ts:
                        timestamps.append(parsed_ts)

            if amounts:
                summary["amount_stats"] = {
                    "min": min(amounts),
                    "max": max(amounts),
                    "avg": sum(amounts) / len(amounts),
                    "count": len(amounts),
                }

            summary["unique_accounts"] = len(accounts)

            if timestamps:
                summary["date_range"] = {
                    "start": min(timestamps).isoformat(),
                    "end": max(timestamps).isoformat(),
                    "span_days": (max(timestamps) - min(timestamps)).days,
                }

        return summary


class DataQualityChecker:
    """Advanced data quality checking for transaction datasets."""

    def __init__(self):
        self.validator = TransactionDataValidator()

    def check_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Comprehensive data quality check for transaction DataFrame.

        Args:
            df: Transaction DataFrame

        Returns:
            Data quality report
        """
        report = {
            "overall_quality": "good",
            "quality_score": 0.0,
            "issues": [],
            "recommendations": [],
            "statistics": {},
        }

        if df.empty:
            report["overall_quality"] = "poor"
            report["issues"].append("Dataset is empty")
            return report

        # Check completeness
        completeness = self._check_completeness(df)
        report["statistics"]["completeness"] = completeness

        # Check consistency
        consistency = self._check_consistency(df)
        report["statistics"]["consistency"] = consistency

        # Check validity
        validity = self._check_validity(df)
        report["statistics"]["validity"] = validity

        # Check uniqueness
        uniqueness = self._check_uniqueness(df)
        report["statistics"]["uniqueness"] = uniqueness

        # Calculate overall quality score
        scores = [
            completeness.get("score", 0),
            consistency.get("score", 0),
            validity.get("score", 0),
            uniqueness.get("score", 0),
        ]
        report["quality_score"] = sum(scores) / len(scores)

        # Determine overall quality
        if report["quality_score"] >= 0.8:
            report["overall_quality"] = "excellent"
        elif report["quality_score"] >= 0.6:
            report["overall_quality"] = "good"
        elif report["quality_score"] >= 0.4:
            report["overall_quality"] = "fair"
        else:
            report["overall_quality"] = "poor"

        # Collect issues and recommendations
        for stat in report["statistics"].values():
            if "issues" in stat:
                report["issues"].extend(stat["issues"])
            if "recommendations" in stat:
                report["recommendations"].extend(stat["recommendations"])

        return report

    def _check_completeness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data completeness."""
        result = {"score": 1.0, "issues": [], "recommendations": []}

        total_cells = len(df) * len(df.columns)
        missing_cells = df.isnull().sum().sum()
        completeness_rate = (total_cells - missing_cells) / total_cells

        result["completeness_rate"] = completeness_rate
        result["missing_values"] = missing_cells
        result["score"] = completeness_rate

        if completeness_rate < 0.95:
            result["issues"].append(f"Dataset has {completeness_rate:.1%} completeness")
            result["recommendations"].append("Review and handle missing values")

        # Check specific columns
        required_cols = ["amount", "timestamp", "account_id"]
        for col in required_cols:
            if col in df.columns:
                missing_pct = df[col].isnull().mean()
                if missing_pct > 0:
                    result["issues"].append(
                        f"Required column '{col}' has {missing_pct:.1%} missing values"
                    )

        return result

    def _check_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data consistency."""
        result = {"score": 1.0, "issues": [], "recommendations": []}

        # Check timestamp consistency
        if "timestamp" in df.columns:
            # Should be in chronological order ideally
            ts_series = pd.to_datetime(df["timestamp"], errors="coerce")
            if ts_series.isnull().any():
                inconsistent_count = ts_series.isnull().sum()
                result["issues"].append(
                    f"{inconsistent_count} timestamps could not be parsed"
                )
                result["score"] *= 0.9

        # Check amount consistency (should be numeric)
        if "amount" in df.columns:
            numeric_amounts = pd.to_numeric(df["amount"], errors="coerce")
            if numeric_amounts.isnull().any():
                non_numeric = numeric_amounts.isnull().sum()
                result["issues"].append(f"{non_numeric} amounts are not numeric")
                result["score"] *= 0.9

        return result

    def _check_validity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data validity."""
        result = {"score": 1.0, "issues": [], "recommendations": []}

        # Check for negative amounts
        if "amount" in df.columns:
            negative_amounts = (pd.to_numeric(df["amount"], errors="coerce") < 0).sum()
            if negative_amounts > 0:
                result["issues"].append(
                    f"{negative_amounts} transactions have negative amounts"
                )
                result["score"] *= 0.95

        # Check for future dates
        if "timestamp" in df.columns:
            ts_series = pd.to_datetime(df["timestamp"], errors="coerce")
            future_dates = (ts_series > datetime.now()).sum()
            if future_dates > 0:
                result["issues"].append(
                    f"{future_dates} transactions have future timestamps"
                )
                result["score"] *= 0.98

        return result

    def _check_uniqueness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check data uniqueness."""
        result = {"score": 1.0, "issues": [], "recommendations": []}

        # Check for duplicate rows
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            result["issues"].append(f"{duplicate_rows} duplicate rows found")
            result["recommendations"].append("Remove duplicate transactions")
            result["score"] *= 0.9

        # Check for duplicate transaction IDs
        id_cols = ["id", "transaction_id", "external_transaction_id"]
        for col in id_cols:
            if col in df.columns:
                duplicates = df[col].duplicated().sum()
                if duplicates > 0:
                    result["issues"].append(f"{duplicates} duplicate values in {col}")
                    result["score"] *= 0.9

        return result
