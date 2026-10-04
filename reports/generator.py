from datetime import datetime, UTC
import hashlib
import json
import logging
import os
import sqlite3

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


class ComplianceReportGenerator:
    """Aggregates ledger transactions, runs health verifications, and exports regulatory audit trail reports."""

    def __init__(self, db_path: str = "omniaudit.db", output_dir: str = "reports"):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _verify_chain_integrity(self) -> bool:
        """Internal cryptographic check ensuring logs haven't been altered out-of-band."""
        if not os.path.exists(self.db_path):
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT decision_id, parent_id, decision, confidence, cryptographic_hash FROM audit_ledger ORDER BY sequence_id ASC"
            )
            rows = cursor.fetchall()

            expected_prev_hash = "GENESIS_BLOCK_00000000000000000000000000000000"
            for row in rows:
                dec_id, p_id, dec, conf, stored_hash = row
                payload = (
                    f"{dec_id}|{p_id}|{dec}|{conf}|{expected_prev_hash}"
                )
                calculated_hash = hashlib.sha256(
                    payload.encode("utf-8")
                ).hexdigest()

                if calculated_hash != stored_hash:
                    return False
                expected_prev_hash = stored_hash
        return True

    def generate_json_compliance_package(
        self, filename: str = "regulatory_compliance_report.json"
    ) -> str:
        """Compiles the entire immutable trail into a formalized audit ledger package."""
        logging.info("Building regulatory compliance report payload...")

        # 1. Validate data integrity profile prior to packaging
        integrity_status = self._verify_chain_integrity()

        records = []
        critical_flags_count = 0

        if os.path.exists(self.db_path):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT decision_id, parent_id, decision, confidence, timestamp, metadata, audit_flags, cryptographic_hash FROM audit_ledger"
                )
                for row in cursor.fetchall():
                    flags = json.loads(row[6])
                    if any(
                        f in flags
                        for f in [
                            "POLICY_VIOLATION_ALERT",
                            "LOW_CONFIDENCE_WARNING",
                        ]
                    ):
                        critical_flags_count += 1

                    records.append(
                        {
                            "decision_id": row[0],
                            "parent_id": row[1],
                            "decision_block": row[2],
                            "model_certainty": row[3],
                            "timestamp_utc": row[4],
                            "environment_metadata": json.loads(row[5]),
                            "compliance_flags": flags,
                            "cryptographic_signature": row[7],
                        }
                    )

        # 2. Structure metadata packet matching corporate governance frameworks
        report_payload = {
            "report_metadata": {
                "framework_version": "AegisAudit Governance Engine v1.0",
                # Fixed: Using standard timezone-aware format
                "export_timestamp": datetime.now(UTC).isoformat(),
                "cryptographic_chain_verified": integrity_status,
                "total_logged_nodes": len(records),
                "flagged_risk_anomalies": critical_flags_count,
                "regulatory_scope": [
                    "EU_AI_ACT_ART_10",
                    "ISO_42001_AI_GOVERNANCE",
                ],
            },
            "immutable_ledger_trail": records,
        }

        target_filepath = os.path.join(self.output_dir, filename)
        with open(target_filepath, "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=4)

        logging.info(
            f"💼 Formal regulatory audit pack generated safely at: {target_filepath}"
        )
        return target_filepath


if __name__ == "__main__":
    generator = ComplianceReportGenerator()
    generator.generate_json_compliance_package()
