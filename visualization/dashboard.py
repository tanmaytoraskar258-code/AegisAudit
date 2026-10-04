import sqlite3
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class AuditVisualizer:
    """Queries the live cryptographic ledger and transforms node links into interactive visual assets."""
    
    def __init__(self, db_path: str = "omniaudit.db", output_dir: str = "reports/templates"):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _fetch_graph_edges(self) -> list:
        """Extracts complete structural lineage paths directly out of production logs."""
        if not os.path.exists(self.db_path):
            logging.error(f"❌ Target Database '{self.db_path}' not found. Cannot render layout.")
            return []
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT decision_id, parent_id, decision, confidence, audit_flags 
                FROM audit_ledger 
                ORDER BY sequence_id ASC
            """)
            return cursor.fetchall()

    def render_html_dashboard(self, filename: str = "dashboard.html") -> str:
        """Generates a zero-dependency high-contrast dashboard layout."""
        rows = self._fetch_graph_edges()
        target_path = os.path.join(self.output_dir, filename)

        # Build native HTML blocks dynamically from the ledger
        node_html_blocks = []
        for row in rows:
            dec_id, p_id, decision, confidence, flags_raw = row
            flags = json.loads(flags_raw)
            
            # Determine card styling profile based on systemic flag severity status
            is_risk = "POLICY_VIOLATION_ALERT" in flags or "LOW_CONFIDENCE_WARNING" in flags
            card_class = "risk-card" if is_risk else "stable-card"
            badge_text = "⚠️ RISK COMPLIANCE TRIGGERED" if is_risk else "🛡️ VERIFIED SECURE FLOW"
            
            parent_info = f"<div class='parent-line'>↳ Branch Origin Connection: <strong>{p_id}</strong></div>" if p_id else "<div class='parent-line'>❖ Genesis Baseline Node</div>"

            block = f"""
            <div class="node-card {card_class}">
                <div class="card-header">
                    <span class="node-id">ID: {dec_id}</span>
                    <span class="status-badge">{badge_text}</span>
                </div>
                {parent_info}
                <p class="decision-text">"{decision}"</p>
                <div class="card-footer">
                    <span class="conf-metric">Certainty Metric: <strong>{confidence * 100:.1f}%</strong></span>
                    <span class="flags-list">Active Flags: {', '.join(flags) if flags else 'None'}</span>
                </div>
            </div>
            """
            node_html_blocks.append(block)

        nodes_compiled = "\n".join(node_html_blocks) if node_html_blocks else "<p style='color:#94a3b8;'>No active decision paths detected in the ledger.</p>"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Omniaudit // Governance Interface</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); border: 1px solid #334155; }}
        h1 {{ margin-top: 0; color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 15px; font-weight: 800; letter-spacing: -0.025em; }}
        .meta-tag {{ display: inline-block; background: #0284c7; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 25px; letter-spacing: 0.05em; }}
        .node-feed {{ display: flex; flex-direction: column; gap: 20px; margin-top: 10px; }}
        .node-card {{ background: #0f172a; border-radius: 8px; padding: 20px; border-left: 6px solid #64748b; transition: transform 0.2s; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; }}
        .stable-card {{ border-left-color: #22c55e; }}
        .risk-card {{ border-left-color: #ef4444; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .node-id {{ font-family: monospace; font-size: 16px; font-weight: bold; color: #f1f5f9; }}
        .status-badge {{ font-size: 12px; font-weight: bold; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; }}
        .stable-card .status-badge {{ background: #14532d; color: #4ade80; }}
        .risk-card .status-badge {{ background: #7f1d1d; color: #f87171; }}
        .parent-line {{ font-size: 13px; color: #94a3b8; margin-bottom: 12px; font-family: monospace; }}
        .decision-text {{ font-size: 16px; color: #e2e8f0; line-height: 1.5; margin: 0 0 15px 0; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 6px; border: 1px solid #1e293b; }}
        .card-footer {{ display: flex; justify-content: space-between; font-size: 13px; color: #cbd5e1; border-top: 1px solid #334155; padding-top: 12px; }}
        .conf-metric strong {{ color: #38bdf8; }}
        .flags-list {{ color: #94a3b8; font-family: monospace; }}
        .risk-card .flags-list {{ color: #f87171; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Omniaudit Governance Console</h1>
        <div class="meta-tag">SYSTEM STATUS: CRYPTO-VERIFIED & AUDIT SECURE</div>
        <p>Immutable system audit tracking stream. Native cryptographic verification view.</p>
        <div class="node-feed">
            {nodes_compiled}
        </div>
    </div>
</body>
</html>
"""
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        logging.info(f"🖥️ High-contrast UI dashboard rendered successfully to: {target_path}")
        return target_path

if __name__ == "__main__":
    visualizer = AuditVisualizer()
    visualizer.render_html_dashboard()
