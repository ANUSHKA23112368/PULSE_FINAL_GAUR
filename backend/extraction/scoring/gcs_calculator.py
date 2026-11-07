def calculate_gcs(eye: int, verbal: int, motor: int) -> dict:
    total = max(3, min(15, eye + verbal + motor))
    severity = "Severe" if total <= 8 else ("Moderate" if total <= 12 else "Mild")
    return {"total_score": total, "severity": severity, "eye": eye, "verbal": verbal, "motor": motor}
