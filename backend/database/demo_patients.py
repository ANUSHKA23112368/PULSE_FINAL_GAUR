"""
Synthetic demonstration patient profiles shared by the SQLite and MongoDB stores.

All records are explicit synthetic demonstration data derived from the ten reference
sample handover reports.
"""

DEMO_PATIENT_SPECS = [
    {
        "display_id": "PULSE-DEMO-001",
        "name": "Michael I Wu",
        "age": "48 years",
        "gender": "Male",
        "ward": "Neurology (Demo Ward A)",
        "bed_number": "Bed 8",
        "consultant": "Dr. Hanlen",
        "admitting_diagnosis": "Headache and vertigo (Synthetic demonstration narrative from Report 0)",
        "vitals": {"hr": 78, "spo2": 98, "bp_sys": 124, "bp_dia": 82, "rr": 16, "temperature": 36.8}
    },
    {
        "display_id": "PULSE-DEMO-002",
        "name": "Vera Abbott",
        "age": "93 years",
        "gender": "Female",
        "ward": "Cardiology (Demo Ward B)",
        "bed_number": "Bed 4",
        "consultant": "Dr. Liu",
        "admitting_diagnosis": "Chest pain evaluation (Synthetic demonstration narrative from Report 1)",
        "vitals": {"hr": 84, "spo2": 96, "bp_sys": 138, "bp_dia": 86, "rr": 18, "temperature": 37.0}
    },
    {
        "display_id": "PULSE-DEMO-003",
        "name": "Leila Sonya Da Silva",
        "age": "34 years",
        "gender": "Female",
        "ward": "Endocrinology (Demo Ward C)",
        "bed_number": "Bed 5",
        "consultant": "Dr. Liu",
        "admitting_diagnosis": "Diabetes management (Synthetic demonstration narrative from Report 12)",
        "vitals": {"hr": 76, "spo2": 99, "bp_sys": 118, "bp_dia": 76, "rr": 14, "temperature": 36.6}
    },
    {
        "display_id": "PULSE-DEMO-004",
        "name": "Pierre Cox",
        "age": "77 years",
        "gender": "Male",
        "ward": "Vascular Surgery (Demo Ward A)",
        "bed_number": "Bed 2",
        "consultant": "Dr. Gregor",
        "admitting_diagnosis": "Right leg pain and swelling query embolism (Synthetic demonstration narrative from Report 15)",
        "vitals": {"hr": 88, "spo2": 95, "bp_sys": 142, "bp_dia": 88, "rr": 20, "temperature": 37.2}
    },
    {
        "display_id": "PULSE-DEMO-005",
        "name": "Frank Morgan Montgomery",
        "age": "78 years",
        "gender": "Male",
        "ward": "Cardiothoracic (Demo Ward B)",
        "bed_number": "Bed 5",
        "consultant": "Dr. Sanchez",
        "admitting_diagnosis": "Shortness of breath and post-op tiredness (Synthetic demonstration narrative from Report 22)",
        "vitals": {"hr": 92, "spo2": 94, "bp_sys": 130, "bp_dia": 80, "rr": 22, "temperature": 36.9}
    },
    {
        "display_id": "PULSE-DEMO-006",
        "name": "Nina Maria Carey",
        "age": "67 years",
        "gender": "Female",
        "ward": "Respiratory (Demo Ward C)",
        "bed_number": "Bed 1",
        "consultant": "Dr. Jaime",
        "admitting_diagnosis": "Bronchitis, fever and cough (Synthetic demonstration narrative from Report 35)",
        "vitals": {"hr": 96, "spo2": 93, "bp_sys": 126, "bp_dia": 78, "rr": 24, "temperature": 38.4}
    },
    {
        "display_id": "PULSE-DEMO-007",
        "name": "Matt Owen",
        "age": "43 years",
        "gender": "Male",
        "ward": "Transplant Unit (Demo Ward A)",
        "bed_number": "Bed 3",
        "consultant": "Dr. Kenzie",
        "admitting_diagnosis": "Post lung transplant recovery (Synthetic demonstration narrative from Report 48)",
        "vitals": {"hr": 82, "spo2": 97, "bp_sys": 122, "bp_dia": 78, "rr": 16, "temperature": 37.1}
    },
    {
        "display_id": "PULSE-DEMO-008",
        "name": "Dave McKenzie",
        "age": "72 years",
        "gender": "Male",
        "ward": "Psychogeriatric (Demo Ward D)",
        "bed_number": "Bed 3",
        "consultant": "Dr. Jorge De Silva",
        "admitting_diagnosis": "Acute confusion and dementia monitoring (Synthetic demonstration narrative from Report 56)",
        "vitals": {"hr": 74, "spo2": 98, "bp_sys": 132, "bp_dia": 82, "rr": 15, "temperature": 36.7}
    },
    {
        "display_id": "PULSE-DEMO-009",
        "name": "Lisa Kerr",
        "age": "62 years",
        "gender": "Female",
        "ward": "Neurology (Demo Ward A)",
        "bed_number": "Bed 6",
        "consultant": "Dr. Laine",
        "admitting_diagnosis": "Cerebral haemorrhage evaluation (Synthetic demonstration narrative from Report 75)",
        "vitals": {"hr": 70, "spo2": 98, "bp_sys": 148, "bp_dia": 92, "rr": 14, "temperature": 36.9}
    },
    {
        "display_id": "PULSE-DEMO-010",
        "name": "Evan Stephenson",
        "age": "22 years",
        "gender": "Male",
        "ward": "Renal & Trauma (Demo Ward B)",
        "bed_number": "Bed 3",
        "consultant": "Dr. Medical Officer",
        "admitting_diagnosis": "Post-fall rhabdomyolysis and renal monitoring (Synthetic demonstration narrative from Report 90)",
        "vitals": {"hr": 80, "spo2": 99, "bp_sys": 116, "bp_dia": 74, "rr": 16, "temperature": 36.8}
    }
]
