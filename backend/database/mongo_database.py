"""
PULSE Database Module (MongoDB Atlas)
Persistent storage for the same records the SQLite prototype keeps locally:
patients, simulated vitals, handover notes, extractions, clinician reviews,
pending tasks, analysis history and the report index.

The class exposes exactly the same public methods as ``backend.database.database.Database``
so the FastAPI routes do not need to know which backend is active. It is selected
automatically when ``MONGODB_URI`` is present in the environment (see database.py).

Document primary keys are integers (``_id``) allocated from a counters collection,
mirroring SQLite AUTOINCREMENT so the frontend keeps working with numeric ids.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, MongoClient, ReturnDocument

try:  # imported as part of the backend package
    from backend.database.demo_patients import DEMO_PATIENT_SPECS
except ImportError:  # pragma: no cover - direct module import fallback
    from demo_patients import DEMO_PATIENT_SPECS

DEFAULT_DB_NAME = "pulse"


class MongoDatabase:
    """MongoDB Atlas implementation of the PULSE storage interface."""

    def __init__(self, uri: str = "", db_name: str = DEFAULT_DB_NAME, client: Optional[MongoClient] = None):
        if not uri and client is None:
            raise ValueError("A MongoDB connection string (MONGODB_URI) is required.")

        self.db_name = db_name or DEFAULT_DB_NAME
        self._client = client or MongoClient(
            uri,
            appname="PULSE-Clinical-Handover-Prototype",
            serverSelectionTimeoutMS=8000,
        )
        self._db = self._client[self.db_name]

        if client is None:
            # Fail fast with a clear error when the cluster is unreachable or the
            # credentials are wrong, instead of failing on the first request.
            try:
                self._client.admin.command("ping")
            except NotImplementedError:  # mongomock
                pass

        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _coll(self, name: str):
        return self._db[name]

    def _next_id(self, sequence: str) -> int:
        doc = self._coll("counters").find_one_and_update(
            {"_id": sequence},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc["seq"])

    @staticmethod
    def _clean(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return a plain dict with the public ``id`` field and no ObjectId."""
        if not doc:
            return doc
        result = dict(doc)
        internal_id = result.pop("_id", None)
        if "id" not in result and internal_id is not None and not isinstance(internal_id, dict):
            result["id"] = internal_id
        return result

    @staticmethod
    def _clean_many(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [MongoDatabase._clean(doc) for doc in docs]

    def _init_db(self):
        self._coll("patients").create_index([("display_id", ASCENDING)], unique=True, name="ux_patients_display_id")
        self._coll("patients").create_index([("name", ASCENDING)], name="ix_patients_name")
        self._coll("patient_notes").create_index([("patient_id", ASCENDING)], name="ix_notes_patient_id")
        self._coll("note_extractions").create_index([("note_id", ASCENDING)], name="ix_extractions_note_id")
        self._coll("note_reviews").create_index([("note_id", ASCENDING)], name="ix_reviews_note_id")
        self._coll("simulated_vitals").create_index([("patient_id", ASCENDING)], name="ix_vitals_patient_id")
        self._coll("patient_tasks").create_index([("patient_id", ASCENDING)], name="ix_tasks_patient_id")
        self._coll("patient_tasks").create_index(
            [("patient_id", ASCENDING), ("status", ASCENDING)], name="ix_tasks_patient_status"
        )
        self.seed_demo_patients()

    # ------------------------------------------------------------------
    # Patients
    # ------------------------------------------------------------------

    def seed_demo_patients(self) -> int:
        """Idempotently seeds the ten synthetic demonstration patient profiles."""
        inserted_count = 0
        now = datetime.now().isoformat()

        for spec in DEMO_PATIENT_SPECS:
            if self._coll("patients").find_one({"display_id": spec["display_id"]}, {"_id": 1}):
                continue

            patient_id = self._next_id("patients")
            self._coll("patients").insert_one({
                "_id": patient_id,
                "display_id": spec["display_id"],
                "name": spec["name"],
                "age": spec.get("age"),
                "gender": spec.get("gender"),
                "ward": spec.get("ward"),
                "bed_number": spec.get("bed_number"),
                "consultant": spec.get("consultant"),
                "admitting_diagnosis": spec.get("admitting_diagnosis"),
                "created_at": now,
                "updated_at": now,
            })
            inserted_count += 1

            vitals = spec.get("vitals")
            if vitals:
                self._coll("simulated_vitals").insert_one({
                    "_id": self._next_id("simulated_vitals"),
                    "patient_id": patient_id,
                    "hr": vitals.get("hr"),
                    "spo2": vitals.get("spo2"),
                    "bp_sys": vitals.get("bp_sys"),
                    "bp_dia": vitals.get("bp_dia"),
                    "rr": vitals.get("rr"),
                    "temperature": vitals.get("temperature"),
                    "recorded_at": now,
                    "data_source": "Simulated Clinical Demonstration Data (Synthetic Engine)",
                })

        return inserted_count

    def list_patients(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if search and search.strip():
            term = re.escape(search.strip())
            query = {"$or": [
                {"display_id": {"$regex": term, "$options": "i"}},
                {"name": {"$regex": term, "$options": "i"}},
                {"ward": {"$regex": term, "$options": "i"}},
                {"consultant": {"$regex": term, "$options": "i"}},
            ]}
        docs = list(self._coll("patients").find(query).sort("_id", ASCENDING))
        return self._clean_many(docs)

    def get_patient(self, patient_identifier: Any) -> Optional[Dict[str, Any]]:
        doc = None
        identifier = str(patient_identifier).strip() if patient_identifier is not None else ""
        if identifier.isdigit():
            doc = self._coll("patients").find_one({"_id": int(identifier)})
        if doc is None and identifier:
            doc = self._coll("patients").find_one({"display_id": identifier})
        if doc is None:
            return None

        patient = self._clean(doc)
        vital = self._coll("simulated_vitals").find_one(
            {"patient_id": patient["id"]}, sort=[("_id", -1)]
        )
        patient["vitals"] = self._clean(vital)
        return patient

    def generate_next_display_id(self) -> str:
        max_num = 0
        for doc in self._coll("patients").find({}, {"display_id": 1}):
            display_id = doc.get("display_id") or ""
            if display_id.startswith("PULSE-DEMO-"):
                suffix = display_id.replace("PULSE-DEMO-", "")
                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))

        next_num = max(max_num + 1, 11)
        candidate = f"PULSE-DEMO-{next_num:03d}"
        while self._coll("patients").find_one({"display_id": candidate}, {"_id": 1}):
            next_num += 1
            candidate = f"PULSE-DEMO-{next_num:03d}"
        return candidate

    def create_patient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Patient 'name' is required and cannot be empty or whitespace only.")

        display_id = (data.get("display_id") or "").strip()
        if not display_id:
            display_id = self.generate_next_display_id()

        if self._coll("patients").find_one({"display_id": display_id}, {"_id": 1}):
            raise ValueError(f"Patient with display_id '{display_id}' already exists.")

        now = datetime.now().isoformat()
        patient_id = self._next_id("patients")
        self._coll("patients").insert_one({
            "_id": patient_id,
            "display_id": display_id,
            "name": name,
            "age": data.get("age"),
            "gender": data.get("gender"),
            "ward": data.get("ward"),
            "bed_number": data.get("bed_number"),
            "consultant": data.get("consultant"),
            "admitting_diagnosis": data.get("admitting_diagnosis"),
            "created_at": now,
            "updated_at": now,
        })

        self._coll("simulated_vitals").insert_one({
            "_id": self._next_id("simulated_vitals"),
            "patient_id": patient_id,
            "hr": data.get("hr", 76),
            "spo2": data.get("spo2", 98),
            "bp_sys": data.get("bp_sys", 122),
            "bp_dia": data.get("bp_dia", 78),
            "rr": data.get("rr", 16),
            "temperature": data.get("temperature", 36.8),
            "recorded_at": now,
            "data_source": "Simulated Clinical Demonstration Data (Synthetic Engine)",
        })

        return self.get_patient(patient_id)

    # ------------------------------------------------------------------
    # Analysis history & report index
    # ------------------------------------------------------------------

    def save_analysis(
        self,
        report_id: Optional[str],
        raw_text: str,
        preprocessed_text: str,
        structured_data: Dict[str, Any],
    ) -> int:
        import json

        now = datetime.now().isoformat()
        analysis_id = self._next_id("analysis_history")
        self._coll("analysis_history").insert_one({
            "_id": analysis_id,
            "report_id": report_id or "Custom",
            "timestamp": now,
            "raw_text": raw_text,
            "preprocessed_text": preprocessed_text,
            "structured_output": json.dumps(structured_data),
            "word_count": len(raw_text.split()),
            "status": "Completed",
        })
        return analysis_id

    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        import json

        results = []
        docs = self._coll("analysis_history").find({}).sort("_id", -1).limit(limit)
        for doc in docs:
            item = {
                "id": doc.get("_id"),
                "report_id": doc.get("report_id"),
                "timestamp": doc.get("timestamp"),
                "word_count": doc.get("word_count"),
                "status": doc.get("status"),
                "snippet": (doc.get("raw_text") or "")[:120],
                "structured_output": doc.get("structured_output"),
            }
            try:
                item["structured_output"] = json.loads(item["structured_output"])
            except Exception:
                pass
            results.append(item)
        return results

    def sync_reports_cache(self, reports: List[Dict[str, Any]]):
        now = datetime.now().isoformat()
        for report in reports:
            report_id = str(report["report_id"])
            self._coll("reports_cache").replace_one(
                {"_id": report_id},
                {
                    "_id": report_id,
                    "report_id": report_id,
                    "filename": report["filename"],
                    "word_count": report["word_count"],
                    "char_count": report["char_count"],
                    "last_synced": now,
                },
                upsert=True,
            )

    # ------------------------------------------------------------------
    # Clinical notes
    # ------------------------------------------------------------------

    def create_patient_note(
        self, patient_id: int, raw_text: str, author_identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        if not raw_text or not raw_text.strip():
            raise ValueError("Clinical note text cannot be empty or whitespace only.")
        if not self._coll("patients").find_one({"_id": int(patient_id)}, {"_id": 1}):
            raise KeyError(f"Patient with ID {patient_id} not found.")

        now = datetime.now().isoformat()
        note_id = self._next_id("patient_notes")
        self._coll("patient_notes").insert_one({
            "_id": note_id,
            "patient_id": int(patient_id),
            "raw_text": raw_text,
            "status": "Draft",
            "author_identifier": author_identifier or "Staff Clinician (Demo)",
            "created_at": now,
            "updated_at": now,
        })
        return self.get_patient_note(patient_id, note_id)

    def _note_document(self, note_doc: Dict[str, Any]) -> Dict[str, Any]:
        note_id = note_doc["_id"]

        reviews_list = []
        for review in self._coll("note_reviews").find({"note_id": note_id}).sort("_id", -1):
            reviews_list.append({
                "id": review.get("_id"),
                "reviewer_identifier": review.get("reviewer_identifier"),
                "reviewed_data": review.get("reviewed_data"),
                "review_notes": review.get("review_notes"),
                "reviewed_at": review.get("reviewed_at"),
            })

        latest_review = reviews_list[0] if reviews_list else None
        note = {
            "id": note_id,
            "patient_id": note_doc.get("patient_id"),
            "raw_text": note_doc.get("raw_text"),
            "status": note_doc.get("status"),
            "author_identifier": note_doc.get("author_identifier"),
            "created_at": note_doc.get("created_at"),
            "updated_at": note_doc.get("updated_at"),
            "extraction": None,
            "review": latest_review,
            "review_history": reviews_list,
            "reviewer_identifier": latest_review["reviewer_identifier"] if latest_review else None,
            "reviewed_at": latest_review["reviewed_at"] if latest_review else None,
        }

        extraction = self._coll("note_extractions").find_one(
            {"note_id": note_id}, sort=[("_id", -1)]
        )
        if extraction:
            note["extraction"] = {
                "id": extraction.get("_id"),
                "engine_used": extraction.get("engine_used"),
                "extracted_at": extraction.get("created_at"),
                "data": extraction.get("extracted_data"),
            }
        return note

    def get_patient_notes(self, patient_id: int) -> List[Dict[str, Any]]:
        patient_id = int(patient_id)
        if not self._coll("patients").find_one({"_id": patient_id}, {"_id": 1}):
            raise KeyError(f"Patient with ID {patient_id} not found.")

        docs = self._coll("patient_notes").find({"patient_id": patient_id}).sort("_id", -1)
        return [self._note_document(doc) for doc in docs]

    def get_patient_note(self, patient_id: int, note_id: int) -> Optional[Dict[str, Any]]:
        doc = self._coll("patient_notes").find_one(
            {"_id": int(note_id), "patient_id": int(patient_id)}
        )
        return self._note_document(doc) if doc else None

    def process_patient_note(
        self,
        patient_id: int,
        note_id: int,
        extraction_data: Dict[str, Any],
        engine_used: str = "Bio_ClinicalBERT",
    ) -> Dict[str, Any]:
        note = self._coll("patient_notes").find_one(
            {"_id": int(note_id), "patient_id": int(patient_id)}, {"_id": 1}
        )
        if not note:
            raise KeyError(f"Note {note_id} not found for patient {patient_id}.")

        now = datetime.now().isoformat()
        self._coll("note_extractions").insert_one({
            "_id": self._next_id("note_extractions"),
            "note_id": int(note_id),
            "engine_used": engine_used,
            "extracted_data": extraction_data,
            "created_at": now,
        })
        self._coll("patient_notes").update_one(
            {"_id": int(note_id), "patient_id": int(patient_id)},
            {"$set": {"status": "Processed", "updated_at": now}},
        )
        return self.get_patient_note(patient_id, note_id)

    def review_patient_note(
        self,
        patient_id: int,
        note_id: int,
        reviewed_data: Dict[str, Any],
        reviewer_identifier: Optional[str] = None,
        review_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(reviewed_data, dict) or not reviewed_data:
            raise ValueError("reviewed_data must be a valid non-empty structured dictionary.")

        note = self._coll("patient_notes").find_one(
            {"_id": int(note_id), "patient_id": int(patient_id)}, {"status": 1}
        )
        if not note:
            raise KeyError(f"Note {note_id} not found for patient {patient_id}.")
        if note.get("status") == "Draft":
            raise ValueError(
                f"Cannot review note #{note_id} because it has not been processed. "
                "Process the note with AI first."
            )

        now = datetime.now().isoformat()
        reviewer = reviewer_identifier or "Staff Clinician (Demo)"
        review_id = self._next_id("note_reviews")
        self._coll("note_reviews").insert_one({
            "_id": review_id,
            "note_id": int(note_id),
            "reviewer_identifier": reviewer,
            "reviewed_data": reviewed_data,
            "review_notes": review_notes,
            "reviewed_at": now,
        })
        self._coll("patient_notes").update_one(
            {"_id": int(note_id), "patient_id": int(patient_id)},
            {"$set": {"status": "Reviewed", "updated_at": now}},
        )

        return {
            "review_id": review_id,
            "note_id": int(note_id),
            "patient_id": int(patient_id),
            "status": "Reviewed",
            "reviewer_identifier": reviewer,
            "reviewed_data": reviewed_data,
            "review_notes": review_notes,
            "reviewed_at": now,
            "note": self.get_patient_note(patient_id, note_id),
        }

    # ------------------------------------------------------------------
    # Pending clinical tasks
    # ------------------------------------------------------------------

    def list_patient_tasks(self, patient_id: int) -> List[Dict[str, Any]]:
        docs = self._coll("patient_tasks").find({"patient_id": int(patient_id)}).sort("_id", -1)
        return self._clean_many(docs)

    def create_patient_task(self, patient_id: int, task_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        task_name = (task_data.get("task") or "").strip()
        priority = task_data.get("priority") or "Unassigned / Awaiting Clinician Triage"

        if task_name:
            existing = self._coll("patient_tasks").find_one(
                {
                    "patient_id": int(patient_id),
                    "status": "Pending",
                    "task": {"$regex": f"^\\s*{re.escape(task_name)}\\s*$", "$options": "i"},
                },
                sort=[("_id", -1)],
            )
            if existing:
                return self._clean(existing)

        source_sentence = task_data.get("source_sentence", "")
        evidence = task_data.get("evidence")
        if evidence is None and source_sentence:
            evidence = f'Sourced from: "{source_sentence}"'

        task_doc = {
            "_id": self._next_id("patient_tasks"),
            "patient_id": int(patient_id),
            "task": task_name,
            "type": task_data.get("type", "Clinical Pending Action"),
            "priority": priority,
            "source_note_id": task_data.get("source_note_id"),
            "source_sentence": source_sentence,
            "recorded_time": task_data.get("recorded_time", now),
            "due_time": task_data.get("due_time"),
            "status": task_data.get("status", "Pending"),
            "evidence": evidence,
            "created_at": now,
            "updated_at": now,
        }
        self._coll("patient_tasks").insert_one(task_doc)
        return self._clean(task_doc)

    def update_patient_task(
        self, patient_id: int, task_id: int, status: str, evidence: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        update: Dict[str, Any] = {"status": status, "updated_at": now}
        if evidence:
            update["evidence"] = evidence

        result = self._coll("patient_tasks").find_one_and_update(
            {"_id": int(task_id), "patient_id": int(patient_id)},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            raise KeyError(f"Task {task_id} not found for patient {patient_id}.")
        return self._clean(result)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        self._client.close()


__all__ = ["MongoDatabase", "DEFAULT_DB_NAME"]
