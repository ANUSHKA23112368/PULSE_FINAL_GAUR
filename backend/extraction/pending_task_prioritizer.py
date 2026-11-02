"""
Pending Clinical Task Priority Ranking Engine.
Classifies tasks as Urgent, High, Routine, or Handover-Only based on clinical urgency markers.
"""

from typing import List, Dict, Any

URGENT_KEYWORDS = ["stat", "immediately", "critical", "deteriorating", "urgent", "unstable"]
HIGH_KEYWORDS = ["today", "repeat", "fasting", "post-op", "chase", "pending lab", "inr"]

def prioritize_tasks(tasks: List[str]) -> List[Dict[str, Any]]:
    ranked = []
    for t in tasks:
        t_low = t.lower()
        if any(w in t_low for w in URGENT_KEYWORDS):
            priority = "URGENT"
            color = "#ef4444"
        elif any(w in t_low for w in HIGH_KEYWORDS):
            priority = "HIGH"
            color = "#f59e0b"
        else:
            priority = "ROUTINE"
            color = "#10b981"
            
        ranked.append({"task": t, "priority": priority, "priority_color": color})
        
    order = {"URGENT": 0, "HIGH": 1, "ROUTINE": 2}
    ranked.sort(key=lambda x: order.get(x["priority"], 3))
    return ranked
