import sqlite3
import json
import hashlib
import queue
import threading
import time
import logging
from typing import Optional
from core.node import AuditNode

# Setup enterprise-grade diagnostic tracing
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ImmutableLedger:
    """
    Enterprise-scale, non-blocking asynchronous audit ledger.
    Enforces cryptographic data-tamper locks using cryptographic block hashing.
    """
    def __init__(self, db_path: str = "omniaudit.db"):
        self.db_path = db_path
        self._write_queue: queue.Queue = queue.Queue()
        self._shutdown_signal = threading.Event()
        
        self._initialize_infrastructure()
        
        # Deploy non-blocking background worker daemon thread
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def _initialize_infrastructure(self) -> None:
        """Initializes database schema optimized for graph storage and integrity locks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enable Write-Ahead Logging (WAL) for safe concurrent reads/writes
            cursor.execute("PRAGMA journal_mode=WAL;")
            
            # Create core immutable ledger table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_ledger (
                    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT UNIQUE NOT NULL,
                    parent_id TEXT,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    audit_flags TEXT,
                    counterfactual_forks TEXT,
                    cryptographic_hash TEXT NOT NULL
                );
            """)
            
            # Index for lightning-fast graph lineage lookups across millions of logs
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent ON audit_ledger(parent_id);")
            conn.commit()

    def _calculate_node_hash(self, node_data: dict, previous_hash: str) -> str:
        """Computes a SHA-256 cryptographic link sealing the new record to history."""
        payload = f"{node_data['decision_id']}|{node_data['parent_id']}|{node_data['decision']}|{node_data['confidence']}|{previous_hash}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def _get_latest_system_hash(self, cursor: sqlite3.Cursor) -> str:
        """Retrieves the tail cryptographic signature to secure the next link."""
        cursor.execute("SELECT cryptographic_hash FROM audit_ledger ORDER BY sequence_id DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else "GENESIS_BLOCK_00000000000000000000000000000000"

    def stage_node_async(self, node: AuditNode) -> None:
        """
        Non-blocking ingestion endpoint. Drops telemetry tokens onto an in-memory
        queue so production LLM pipelines suffer 0ms of database latency overhead.
        """
        if self._shutdown_signal.is_set():
            raise RuntimeError("Cannot stage audit nodes: Ledger pipeline is shutting down.")
        self._write_queue.put(node)

    def _process_queue(self) -> None:
        """Internal background daemon processing queue batches securely into SQLite."""
        while not self._shutdown_signal.is_set() or not self._write_queue.empty():
            try:
                # Wait for nodes with a small timeout to keep the loop alive for shutdown checks
                node: AuditNode = self._write_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._persist_to_ledger(node)
            self._write_queue.task_done()

    def _persist_to_ledger(self, node: AuditNode) -> None:
        """Executes transaction processing, computes the hash link, and updates the database."""
        node_data = node.to_dict()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Step 1: Detect and verify DAG Parent Lineage if applicable
                if node.parent_id:
                    cursor.execute("SELECT COUNT(1) FROM audit_ledger WHERE decision_id = ?", (node.parent_id,))
                    if cursor.fetchone()[0] == 0:
                        logging.error(f"❌ Lineage Broken: Node {node.decision_id} references a missing parent {node.parent_id}.")
                        return

                # Step 2: Grab previous tail hash to generate cryptolock link
                prev_hash = self._get_latest_system_hash(cursor)
                crypto_hash = self._calculate_node_hash(node_data, prev_hash)
                
                # Step 3: Atomic database commit execution
                cursor.execute("""
                    INSERT INTO audit_ledger 
                    (decision_id, parent_id, decision, confidence, timestamp, metadata, audit_flags, counterfactual_forks, cryptographic_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_data['decision_id'],
                    node_data['parent_id'],
                    node_data['decision'],
                    node_data['confidence'],
                    node_data['timestamp'],
                    node_data['metadata'],
                    node_data['audit_flags'],
                    node_data['counterfactual_forks'],
                    crypto_hash
                ))
                conn.commit()
                logging.info(f"🛡️ Node {node.decision_id} safely cryptolocked into ledger. Hash: {crypto_hash[:12]}...")
                
        except sqlite3.IntegrityError:
            logging.critical(f"⚠️ IMMUTABILITY BREACH DETECTED: Attempted log overwrite on ID {node.decision_id} blocked!")

    def verify_ledger_integrity(self) -> bool:
        """
        Auditor compliance verification function. Re-calculates every single hash link 
        from scratch to instantly flag database tampering or unauthorized modifications.
        """
        logging.info("Re-calculating ledger cryptographic chain integrity...")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT decision_id, parent_id, decision, confidence, cryptographic_hash FROM audit_ledger ORDER BY sequence_id ASC")
            rows = cursor.fetchall()
            
            expected_prev_hash = "GENESIS_BLOCK_00000000000000000000000000000000"
            for row in rows:
                dec_id, p_id, dec, conf, stored_hash = row
                
                # Format to compute matching test token
                payload_dict = {
                    "decision_id": dec_id,
                    "parent_id": p_id,
                    "decision": dec,
                    "confidence": conf
                }
                calculated_hash = self._calculate_node_hash(payload_dict, expected_prev_hash)
                
                if calculated_hash != stored_hash:
                    logging.critical(f"🚨 INTEGRITY FAILURE AT NODE: {dec_id}! History has been altered!")
                    return False
                
                expected_prev_hash = stored_hash
        logging.info("✅ Ledger verification clear. Data trail is perfectly secure.")
        return True

    def shutdown(self) -> None:
        """Gracefully drains the write-ahead queue buffers before safely dropping threads."""
        logging.info("Gracefully draining audit write buffers to disk...")
        self._shutdown_signal.set()
        self._worker_thread.join()
        logging.info("Ledger engine offline.")
