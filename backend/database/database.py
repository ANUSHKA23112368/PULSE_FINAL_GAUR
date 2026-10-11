"""
PULSE Database Module (SQLite)
Maintains local prototype storage for:
- Analysis execution history
- Report caching and indexing
The original dataset in data/ remains strictly read-only.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pulse_prototype.db"))

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Existing Analysis history table (preserved exactly)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT,
                    timestamp TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    preprocessed_text TEXT NOT NULL,
                    structured_output TEXT NOT NULL,
                    word_count INTEGER,
                    status TEXT DEFAULT 'Completed'
                )
            """)

            # 2. Existing Reports cache table (preserved exactly)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports_cache (
                    report_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    last_synced TEXT NOT NULL
                )
            """)

            # 3. Patient database table (synthetic demonstration foundation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    age TEXT,
                    gender TEXT,
                    ward TEXT,
                    bed_number TEXT,
                    consultant TEXT,
                    admitting_diagnosis TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_display_id ON patients(display_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name)")

            # 4. Patient notes table (preserves verbatim clinical notes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patient_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    raw_text TEXT NOT NULL,
                    status TEXT DEFAULT 'Draft',
                    author_identifier TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_patient_id ON patient_notes(patient_id)")

            # 5. Note extractions table (links NLP pipeline output to notes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL,
                    engine_used TEXT NOT NULL,
                    extracted_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (note_id) REFERENCES patient_notes(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_extractions_note_id ON note_extractions(note_id)")

            # 6. Note reviews table (links verified human modifications to notes)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL,
                    reviewer_identifier TEXT,
                    reviewed_data TEXT NOT NULL,
                    review_notes TEXT,
                    reviewed_at TEXT NOT NULL,
                    FOREIGN KEY (note_id) REFERENCES patient_notes(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_note_id ON note_reviews(note_id)")

            # 7. Simulated vitals table (clearly labelled synthetic demonstration observations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulated_vitals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    hr INTEGER,
                    spo2 INTEGER,
                    bp_sys INTEGER,
                    bp_dia INTEGER,
                    rr INTEGER,
                    temperature REAL,
                    recorded_at TEXT NOT NULL,
                    data_source TEXT DEFAULT 'Simulated Demonstration Data',
                    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vitals_patient_id ON simulated_vitals(patient_id)")

            # 8. Patient tasks table (persistent pending actions tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patient_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    task TEXT NOT NULL,
                    type TEXT DEFAULT 'Clinical Pending Action',
                    priority TEXT DEFAULT 'Medium',
                    source_note_id INTEGER,
                    source_sentence TEXT,
                    recorded_time TEXT,
                    due_time TEXT,
                    status TEXT DEFAULT 'Pending',
                    evidence TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_patient_id ON patient_tasks(patient_id)")
            conn.commit()

        # Seed synthetic demo patients idempotently
        self.seed_demo_patients()

    def seed_demo_patients(self) -> int:
        """
        Idempotently seeds 10 synthetic demo patient profiles derived from the 10 reference sample reports
        (Report IDs: 0, 1, 12, 15, 22, 35, 48, 56, 75, 90).
        All records are explicitly labelled as synthetic demonstration data.
        Returns the number of newly inserted patient records (0 if already seeded).
        """
        demo_patients_spec = [
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

        inserted_count = 0
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for spec in demo_patients_spec:
                # Check idempotency by unique display_id
                cursor.execute("SELECT id FROM patients WHERE display_id = ?", (spec["display_id"],))
                existing = cursor.fetchone()
                if not existing:
                    cursor.execute("""
                        INSERT INTO patients (display_id, name, age, gender, ward, bed_number, consultant, admitting_diagnosis, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        spec["display_id"],
                        spec["name"],
                        spec["age"],
                        spec["gender"],
                        spec["ward"],
                        spec["bed_number"],
                        spec["consultant"],
                        spec["admitting_diagnosis"],
                        now,
                        now
                    ))
                    patient_id = cursor.lastrowid
                    inserted_count += 1

                    # Seed matching simulated vitals
                    v = spec.get("vitals")
                    if v:
                        cursor.execute("""
                            INSERT INTO simulated_vitals (patient_id, hr, spo2, bp_sys, bp_dia, rr, temperature, recorded_at, data_source)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient_id,
                            v["hr"],
                            v["spo2"],
                            v["bp_sys"],
                            v["bp_dia"],
                            v["rr"],
                            v["temperature"],
                            now,
                            "Simulated Clinical Demonstration Data (Synthetic Engine)"
                        ))
            conn.commit()
        return inserted_count

    def list_patients(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists patients, with optional parameterized search across name, display_id, ward, or consultant.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search and search.strip():
                term = f"%{search.strip()}%"
                cursor.execute("""
                    SELECT id, display_id, name, age, gender, ward, bed_number, consultant, admitting_diagnosis, created_at, updated_at
                    FROM patients
                    WHERE display_id LIKE ? OR name LIKE ? OR ward LIKE ? OR consultant LIKE ?
                    ORDER BY id ASC
                """, (term, term, term, term))
            else:
                cursor.execute("""
                    SELECT id, display_id, name, age, gender, ward, bed_number, consultant, admitting_diagnosis, created_at, updated_at
                    FROM patients
                    ORDER BY id ASC
                """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_patient(self, patient_identifier: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single patient profile by primary key id or display_id.
        Includes latest simulated vitals if available.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = None
            if isinstance(patient_identifier, int) or (isinstance(patient_identifier, str) and patient_identifier.isdigit()):
                cursor.execute("SELECT * FROM patients WHERE id = ?", (int(patient_identifier),))
                row = cursor.fetchone()
            if not row and isinstance(patient_identifier, str):
                cursor.execute("SELECT * FROM patients WHERE display_id = ?", (patient_identifier,))
                row = cursor.fetchone()

            if not row:
                return None

            patient_dict = dict(row)
            cursor.execute("""
                SELECT id, hr, spo2, bp_sys, bp_dia, rr, temperature, recorded_at, data_source
                FROM simulated_vitals
                WHERE patient_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (patient_dict["id"],))
            vital_row = cursor.fetchone()
            patient_dict["vitals"] = dict(vital_row) if vital_row else None
            return patient_dict

    def generate_next_display_id(self) -> str:
        """
        Generates the next sequential unique demonstration patient display ID (e.g. PULSE-DEMO-011).
        Collision-safe and thread-safe within SQLite transactions.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT display_id FROM patients")
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                d_id = r["display_id"]
                if d_id and d_id.startswith("PULSE-DEMO-"):
                    suffix = d_id.replace("PULSE-DEMO-", "")
                    if suffix.isdigit():
                        max_num = max(max_num, int(suffix))
            next_num = max(max_num + 1, 11)
            candidate = f"PULSE-DEMO-{next_num:03d}"
            while True:
                cursor.execute("SELECT id FROM patients WHERE display_id = ?", (candidate,))
                if not cursor.fetchone():
                    return candidate
                next_num += 1
                candidate = f"PULSE-DEMO-{next_num:03d}"

    def create_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registers a new synthetic/demo patient record.
        Prevents duplicate display_id creation.
        Auto-generates display_id if omitted or empty.
        Seeds default baseline simulated vitals.
        """
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Patient 'name' is required and cannot be empty or whitespace only.")

        display_id = (data.get("display_id") or "").strip()
        if not display_id:
            display_id = self.generate_next_display_id()

        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM patients WHERE display_id = ?", (display_id,))
            if cursor.fetchone():
                raise ValueError(f"Patient with display_id '{display_id}' already exists.")

            cursor.execute("""
                INSERT INTO patients (display_id, name, age, gender, ward, bed_number, consultant, admitting_diagnosis, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                display_id,
                name,
                data.get("age"),
                data.get("gender"),
                data.get("ward"),
                data.get("bed_number"),
                data.get("consultant"),
                data.get("admitting_diagnosis"),
                now,
                now
            ))
            new_id = cursor.lastrowid

            # Seed default baseline simulated vitals for the new synthetic demonstration patient
            cursor.execute("""
                INSERT INTO simulated_vitals (patient_id, hr, spo2, bp_sys, bp_dia, rr, temperature, recorded_at, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_id,
                data.get("hr", 76),
                data.get("spo2", 98),
                data.get("bp_sys", 122),
                data.get("bp_dia", 78),
                data.get("rr", 16),
                data.get("temperature", 36.8),
                now,
                "Simulated Clinical Demonstration Data (Synthetic Engine)"
            ))

            conn.commit()

        return self.get_patient(new_id)


    def save_analysis(self, report_id: Optional[str], raw_text: str, preprocessed_text: str, structured_data: Dict[str, Any]) -> int:
        timestamp = datetime.now().isoformat()
        word_count = len(raw_text.split())
        structured_json = json.dumps(structured_data)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_history (report_id, timestamp, raw_text, preprocessed_text, structured_output, word_count, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Completed')
            """, (report_id or "Custom", timestamp, raw_text, preprocessed_text, structured_json, word_count))
            conn.commit()
            return cursor.lastrowid

    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, report_id, timestamp, word_count, status, 
                       substr(raw_text, 1, 120) as snippet,
                       structured_output
                FROM analysis_history
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["structured_output"] = json.loads(item["structured_output"])
                except Exception:
                    pass
                results.append(item)
            return results

    def create_patient_note(self, patient_id: int, raw_text: str, author_identifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new clinical note for a specific patient.
        Preserves original raw_text exactly without modification.
        Initial status is 'Draft'.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Clinical note text cannot be empty or whitespace only.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Verify patient exists
            cursor.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
            if not cursor.fetchone():
                raise KeyError(f"Patient with ID {patient_id} not found.")

            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO patient_notes (patient_id, raw_text, status, author_identifier, created_at, updated_at)
                VALUES (?, ?, 'Draft', ?, ?, ?)
            """, (patient_id, raw_text, author_identifier or "Staff Clinician (Demo)", now, now))
            note_id = cursor.lastrowid
            conn.commit()

        return self.get_patient_note(patient_id, note_id)

    def get_patient_notes(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all chronological clinical notes belonging to a specific patient.
        Never exposes notes from other patients.
        Attaches original extraction results and latest human review if present.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Verify patient exists
            cursor.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
            if not cursor.fetchone():
                raise KeyError(f"Patient with ID {patient_id} not found.")

            cursor.execute("""
                SELECT n.id, n.patient_id, n.raw_text, n.status, n.author_identifier, n.created_at, n.updated_at,
                       e.id AS extraction_id, e.engine_used, e.extracted_data, e.created_at AS extracted_at
                FROM patient_notes n
                LEFT JOIN note_extractions e ON n.id = e.note_id
                WHERE n.patient_id = ?
                ORDER BY n.id DESC
            """, (patient_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                note_id = r["id"]
                # Fetch reviews for this note
                cursor.execute("""
                    SELECT id, reviewer_identifier, reviewed_data, review_notes, reviewed_at
                    FROM note_reviews
                    WHERE note_id = ?
                    ORDER BY id DESC
                """, (note_id,))
                rev_rows = cursor.fetchall()
                reviews_list = []
                for rev_r in rev_rows:
                    try:
                        r_data = json.loads(rev_r["reviewed_data"])
                    except Exception:
                        r_data = rev_r["reviewed_data"]
                    reviews_list.append({
                        "id": rev_r["id"],
                        "reviewer_identifier": rev_r["reviewer_identifier"],
                        "reviewed_data": r_data,
                        "review_notes": rev_r["review_notes"],
                        "reviewed_at": rev_r["reviewed_at"]
                    })

                latest_rev = reviews_list[0] if reviews_list else None
                note_dict = {
                    "id": note_id,
                    "patient_id": r["patient_id"],
                    "raw_text": r["raw_text"],
                    "status": r["status"],
                    "author_identifier": r["author_identifier"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "extraction": None,
                    "review": latest_rev,
                    "review_history": reviews_list,
                    "reviewer_identifier": latest_rev["reviewer_identifier"] if latest_rev else None,
                    "reviewed_at": latest_rev["reviewed_at"] if latest_rev else None
                }
                if r["extraction_id"]:
                    try:
                        ext_data = json.loads(r["extracted_data"])
                    except Exception:
                        ext_data = r["extracted_data"]
                    note_dict["extraction"] = {
                        "id": r["extraction_id"],
                        "engine_used": r["engine_used"],
                        "extracted_at": r["extracted_at"],
                        "data": ext_data
                    }
                results.append(note_dict)
            return results

    def get_patient_note(self, patient_id: int, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single clinical note by patient_id and note_id.
        Ensures cross-patient note isolation.
        Attaches original AI extraction and latest clinician review.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, n.patient_id, n.raw_text, n.status, n.author_identifier, n.created_at, n.updated_at,
                       e.id AS extraction_id, e.engine_used, e.extracted_data, e.created_at AS extracted_at
                FROM patient_notes n
                LEFT JOIN note_extractions e ON n.id = e.note_id
                WHERE n.id = ? AND n.patient_id = ?
            """, (note_id, patient_id))
            r = cursor.fetchone()
            if not r:
                return None

            # Fetch reviews for this note
            cursor.execute("""
                SELECT id, reviewer_identifier, reviewed_data, review_notes, reviewed_at
                FROM note_reviews
                WHERE note_id = ?
                ORDER BY id DESC
            """, (note_id,))
            rev_rows = cursor.fetchall()
            reviews_list = []
            for rev_r in rev_rows:
                try:
                    r_data = json.loads(rev_r["reviewed_data"])
                except Exception:
                    r_data = rev_r["reviewed_data"]
                reviews_list.append({
                    "id": rev_r["id"],
                    "reviewer_identifier": rev_r["reviewer_identifier"],
                    "reviewed_data": r_data,
                    "review_notes": rev_r["review_notes"],
                    "reviewed_at": rev_r["reviewed_at"]
                })

            latest_rev = reviews_list[0] if reviews_list else None
            note_dict = {
                "id": r["id"],
                "patient_id": r["patient_id"],
                "raw_text": r["raw_text"],
                "status": r["status"],
                "author_identifier": r["author_identifier"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "extraction": None,
                "review": latest_rev,
                "review_history": reviews_list,
                "reviewer_identifier": latest_rev["reviewer_identifier"] if latest_rev else None,
                "reviewed_at": latest_rev["reviewed_at"] if latest_rev else None
            }
            if r["extraction_id"]:
                try:
                    ext_data = json.loads(r["extracted_data"])
                except Exception:
                    ext_data = r["extracted_data"]
                note_dict["extraction"] = {
                    "id": r["extraction_id"],
                    "engine_used": r["engine_used"],
                    "extracted_at": r["extracted_at"],
                    "data": ext_data
                }
            return note_dict

    def process_patient_note(self, patient_id: int, note_id: int, extraction_data: Dict[str, Any], engine_used: str = "Bio_ClinicalBERT") -> Dict[str, Any]:
        """
        Saves structured NLP extraction output to note_extractions and updates note status to 'Processed'.
        Original raw_text remains strictly unmodified.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM patient_notes WHERE id = ? AND patient_id = ?", (note_id, patient_id))
            if not cursor.fetchone():
                raise KeyError(f"Note {note_id} not found for patient {patient_id}.")

            now = datetime.now().isoformat()
            serialized = json.dumps(extraction_data)

            # Insert extraction record
            cursor.execute("""
                INSERT INTO note_extractions (note_id, engine_used, extracted_data, created_at)
                VALUES (?, ?, ?, ?)
            """, (note_id, engine_used, serialized, now))

            # Update note status to 'Processed'
            cursor.execute("""
                UPDATE patient_notes
                SET status = 'Processed', updated_at = ?
                WHERE id = ? AND patient_id = ?
            """, (now, note_id, patient_id))
            conn.commit()

        return self.get_patient_note(patient_id, note_id)

    def review_patient_note(
        self,
        patient_id: int,
        note_id: int,
        reviewed_data: Dict[str, Any],
        reviewer_identifier: Optional[str] = None,
        review_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persists a human clinician review in the note_reviews table and updates note status to 'Reviewed'.
        Original raw_text and original AI extraction in note_extractions remain strictly unmodified.
        Uses an atomic database transaction ensuring rollback if any failure occurs.
        """
        if not isinstance(reviewed_data, dict) or not reviewed_data:
            raise ValueError("reviewed_data must be a valid non-empty structured dictionary.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Verify patient and note match
            cursor.execute("SELECT id, status FROM patient_notes WHERE id = ? AND patient_id = ?", (note_id, patient_id))
            note_row = cursor.fetchone()
            if not note_row:
                raise KeyError(f"Note {note_id} not found for patient {patient_id}.")

            current_status = note_row["status"]
            if current_status == "Draft":
                raise ValueError(f"Cannot review note #{note_id} because it has not been processed. Process the note with AI first.")

            now = datetime.now().isoformat()
            serialized_review = json.dumps(reviewed_data)

            try:
                # 1. Insert review record
                cursor.execute("""
                    INSERT INTO note_reviews (note_id, reviewer_identifier, reviewed_data, review_notes, reviewed_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (note_id, reviewer_identifier or "Staff Clinician (Demo)", serialized_review, review_notes, now))
                review_id = cursor.lastrowid

                # 2. Update note status to 'Reviewed'
                cursor.execute("""
                    UPDATE patient_notes
                    SET status = 'Reviewed', updated_at = ?
                    WHERE id = ? AND patient_id = ?
                """, (now, note_id, patient_id))

                conn.commit()
            except Exception:
                conn.rollback()
                raise

        updated_note = self.get_patient_note(patient_id, note_id)
        return {
            "review_id": review_id,
            "note_id": note_id,
            "patient_id": patient_id,
            "status": "Reviewed",
            "reviewer_identifier": reviewer_identifier or "Staff Clinician (Demo)",
            "reviewed_data": reviewed_data,
            "review_notes": review_notes,
            "reviewed_at": now,
            "note": updated_note
        }

    def list_patient_tasks(self, patient_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, patient_id, task, type, priority, source_note_id, source_sentence,
                       recorded_time, due_time, status, evidence, created_at, updated_at
                FROM patient_tasks
                WHERE patient_id = ?
                ORDER BY id DESC
            """, (patient_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def create_patient_task(self, patient_id: int, task_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO patient_tasks (
                    patient_id, task, type, priority, source_note_id, source_sentence,
                    recorded_time, due_time, status, evidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                task_data["task"],
                task_data.get("type", "Clinical Pending Action"),
                task_data.get("priority", "Medium"),
                task_data.get("source_note_id"),
                task_data.get("source_sentence", ""),
                task_data.get("recorded_time", now),
                task_data.get("due_time"),
                task_data.get("status", "Pending"),
                task_data.get("evidence", f"Sourced from: \"{task_data.get('source_sentence', '')}\"" if task_data.get("source_sentence") else None),
                now,
                now
            ))
            conn.commit()
            task_id = cursor.lastrowid
            cursor.execute("SELECT * FROM patient_tasks WHERE id = ?", (task_id,))
            return dict(cursor.fetchone())

    def update_patient_task(self, patient_id: int, task_id: int, status: str, evidence: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if evidence:
                cursor.execute("""
                    UPDATE patient_tasks
                    SET status = ?, evidence = ?, updated_at = ?
                    WHERE id = ? AND patient_id = ?
                """, (status, evidence, now, task_id, patient_id))
            else:
                cursor.execute("""
                    UPDATE patient_tasks
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND patient_id = ?
                """, (status, now, task_id, patient_id))
            conn.commit()
            cursor.execute("SELECT * FROM patient_tasks WHERE id = ? AND patient_id = ?", (task_id, patient_id))
            row = cursor.fetchone()
            if not row:
                raise KeyError(f"Task {task_id} not found for patient {patient_id}.")
            return dict(row)

    def sync_reports_cache(self, reports: List[Dict[str, Any]]):
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for r in reports:
                cursor.execute("""
                    INSERT OR REPLACE INTO reports_cache (report_id, filename, word_count, char_count, last_synced)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(r["report_id"]), r["filename"], r["word_count"], r["char_count"], now))
            conn.commit()

# Global database instance
db = Database()

