"""
Tabular Exporter for PULSE Handover Summaries (CSV & JSON Lines).
"""

import csv
import io
from typing import Dict, Any, List

def export_handover_to_csv(structured_handover: Dict[str, List[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Item Index", "Description"])
    
    for category, items in structured_handover.items():
        if isinstance(items, list):
            for idx, item in enumerate(items, 1):
                writer.writerow([category, idx, str(item)])
        elif isinstance(items, dict):
            for k, v in items.items():
                if v:
                    writer.writerow([category, k, str(v)])
                    
    return output.getvalue()
