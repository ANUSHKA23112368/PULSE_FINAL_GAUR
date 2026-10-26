"""
PULSE — Benchmark Annotation & Manifest Validation Engine
Validates independent benchmark annotations, relational endpoints, source-text offsets,
assertion/temporality enums, conditional instructions, and dataset partition disjointness.
Includes scientific safeguards against cross-medication contamination, unverified approvals,
and missing patient identifier leakage.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Set, Tuple


APPROVED_MACRO_CATEGORIES: Set[str] = {
    "Demographics_Bed",
    "Demographics_Name",
    "Demographics_Age",
    "Demographics_Gender",
    "Demographics_Doctor",
    "Clinical_Condition",
    "Clinical_Observation",
    "Medication",
    "Investigation_Procedure",
    "Care_Activity",
    "Plan_Goal",
    "Unclassified",
}

APPROVED_ASSERTIONS: Set[str] = {"Positive", "Negated", "Possible"}
APPROVED_TEMPORALITIES: Set[str] = {"Current", "Historical", "Planned"}
APPROVED_INVESTIGATION_STATUSES: Set[str] = {
    "Ordered",
    "Sent",
    "Awaiting Results",
    "Completed",
    "Not Ordered",
    "Unspecified",
}
APPROVED_SPLITS: Set[str] = {"development", "validation", "held_out_test"}
APPROVED_RELATION_TYPES: Set[str] = {
    "has_dosage",
    "has_route",
    "has_frequency",
    "has_prn_indication",
    "indicates_condition",
    "has_attribute",
    "linked_action",
    "modifies",
}

PROTOCOL_TARGET_SPLITS: Dict[str, int] = {
    "development": 100,
    "validation": 50,
    "held_out_test": 100,
}

PROTOCOL_TARGET_SPECIALTIES: Dict[str, int] = {
    "General Medicine": 50,
    "Surgery & Orthopedics": 45,
    "Pediatrics & NICU": 40,
    "Obstetrics & Gynecology": 35,
    "Emergency Medicine": 40,
    "Critical Care (ICU)": 40,
}

MIN_DOCUMENT_CHAR_LENGTH: int = 80
MAX_DOCUMENT_CHAR_LENGTH: int = 3500


class ValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {
            "documents_checked": 0,
            "entities_checked": 0,
            "relationships_checked": 0,
            "conditional_directives_checked": 0,
            "splits_checked": {},
            "specialties_checked": {},
            "docs_missing_patient_id": 0,
            "patient_independence_guaranteed": False,
        }

    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }


class BenchmarkAnnotationValidator:
    """
    Validates clinical benchmark documents and manifests according to the
    PULSE Independent Benchmark Annotation Protocol.
    """

    def __init__(self):
        pass

    def validate_document(self, doc: Dict[str, Any], doc_index: int = 0) -> ValidationResult:
        result = ValidationResult()
        result.stats["documents_checked"] = 1

        doc_id = doc.get("document_id")
        if not doc_id or not isinstance(doc_id, str):
            result.add_error(f"Doc[{doc_index}]: missing or non-string 'document_id'")
            doc_id = f"doc_{doc_index}"

        # 1. Raw Text & Char Count
        raw_text = doc.get("raw_text")
        if raw_text is None or not isinstance(raw_text, str):
            result.add_error(f"{doc_id}: 'raw_text' must be a valid string")
            return result

        doc_len = len(raw_text)
        char_count = doc.get("char_count")
        if char_count is not None and char_count != doc_len:
            result.add_error(f"{doc_id}: 'char_count' ({char_count}) != len(raw_text) ({doc_len})")

        # Bounds check per Section 2.2 of protocol
        if doc_len < MIN_DOCUMENT_CHAR_LENGTH:
            result.add_warning(
                f"{doc_id}: document length ({doc_len} chars) is below protocol minimum ({MIN_DOCUMENT_CHAR_LENGTH} chars)"
            )
        elif doc_len > MAX_DOCUMENT_CHAR_LENGTH:
            result.add_warning(
                f"{doc_id}: document length ({doc_len} chars) exceeds protocol maximum ({MAX_DOCUMENT_CHAR_LENGTH} chars)"
            )

        # 2. Dataset Split
        split = doc.get("dataset_split")
        if split and split not in APPROVED_SPLITS:
            result.add_error(f"{doc_id}: invalid dataset_split '{split}'. Allowed: {APPROVED_SPLITS}")

        # 3. Patient ID Check
        patient_id = doc.get("patient_id")
        if patient_id is None or (isinstance(patient_id, str) and not patient_id.strip()):
            result.stats["docs_missing_patient_id"] = 1
            result.add_warning(
                f"{doc_id}: missing or blank 'patient_id'. Patient-level independence cannot be verified across splits."
            )

        # 4. Entities
        entities = doc.get("entities")
        if entities is None or not isinstance(entities, list):
            result.add_error(f"{doc_id}: 'entities' must be a list")
            return result

        entity_ids: Set[str] = set()
        seen_spans: Set[Tuple[str, int, int]] = set()
        seen_spans_list: List[Tuple[str, int, int]] = []
        entity_map: Dict[str, Dict[str, Any]] = {}

        for ent_idx, ent in enumerate(entities):
            result.stats["entities_checked"] += 1
            if not isinstance(ent, dict):
                result.add_error(f"{doc_id} Entity[{ent_idx}]: entity must be a dictionary")
                continue

            ent_id = ent.get("entity_id")
            if not ent_id or not isinstance(ent_id, str):
                result.add_error(f"{doc_id} Entity[{ent_idx}]: missing or invalid 'entity_id'")
                continue

            if ent_id in entity_ids:
                result.add_error(f"{doc_id}: duplicate entity_id '{ent_id}'")
            entity_ids.add(ent_id)
            entity_map[ent_id] = ent

            # Category
            cat = ent.get("macro_category")
            if not cat or cat not in APPROVED_MACRO_CATEGORIES:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: invalid macro_category '{cat}'. Allowed: {APPROVED_MACRO_CATEGORIES}"
                )

            # Character Offsets
            start = ent.get("start_char")
            end = ent.get("end_char")
            source_text = ent.get("source_text")

            if start is None or not isinstance(start, int) or start < 0:
                result.add_error(f"{doc_id} Entity[{ent_id}]: start_char must be an integer >= 0")
                continue
            if end is None or not isinstance(end, int) or end <= start or end > doc_len:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: end_char ({end}) out of bounds (start={start}, doc_len={doc_len})"
                )
                continue

            # Exact Verbatim Slice Check
            actual_slice = raw_text[start:end]
            if source_text != actual_slice:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: source_text '{source_text}' != raw_text[{start}:{end}] '{actual_slice}'"
                )

            # Whitespace Discipline
            if source_text and (source_text != source_text.strip()):
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: source_text has untrimmed leading/trailing whitespace: '{source_text}'"
                )

            # Duplicate Span Detection (Identical start, end, category)
            span_key = (cat or "", start, end)
            if span_key in seen_spans:
                result.add_error(f"{doc_id}: duplicate entity span detected with category '{cat}' at [{start}:{end}]")
            seen_spans.add(span_key)

            # Partial Overlapping Entities within the Same Category
            for prev_cat, prev_s, prev_e in seen_spans_list:
                if prev_cat == cat and cat != "Unclassified":
                    if max(start, prev_s) < min(end, prev_e) and (start, end) != (prev_s, prev_e):
                        result.add_error(
                            f"{doc_id}: partial overlapping entity spans within category '{cat}': [{prev_s}:{prev_e}] and [{start}:{end}]"
                        )
            seen_spans_list.append((cat or "", start, end))

            # Assertion Enum
            assertion = ent.get("assertion")
            if assertion is not None and assertion not in APPROVED_ASSERTIONS:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: invalid assertion '{assertion}'. Allowed: {APPROVED_ASSERTIONS}"
                )

            # Temporality Enum
            temporality = ent.get("temporality")
            if temporality is not None and temporality not in APPROVED_TEMPORALITIES:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: invalid temporality '{temporality}'. Allowed: {APPROVED_TEMPORALITIES}"
                )

            # Investigation Status Enum
            inv_status = ent.get("investigation_status")
            if inv_status is not None and inv_status not in APPROVED_INVESTIGATION_STATUSES:
                result.add_error(
                    f"{doc_id} Entity[{ent_id}]: invalid investigation_status '{inv_status}'. Allowed: {APPROVED_INVESTIGATION_STATUSES}"
                )
            if cat == "Investigation_Procedure" and inv_status is None:
                result.add_warning(
                    f"{doc_id} Entity[{ent_id}]: Investigation_Procedure has null investigation_status (expected workflow status)"
                )

            # Medication Attributes Object (if nested representation is used)
            med_attrs = ent.get("medication_attributes")
            if med_attrs is not None:
                if not isinstance(med_attrs, dict):
                    result.add_error(f"{doc_id} Entity[{ent_id}]: 'medication_attributes' must be a dict or null")
                elif cat != "Medication":
                    result.add_warning(
                        f"{doc_id} Entity[{ent_id}]: medication_attributes present on non-Medication category '{cat}'"
                    )

        # 5. Explicit Relational Edges
        relationships = doc.get("relationships", [])
        if not isinstance(relationships, list):
            result.add_error(f"{doc_id}: 'relationships' must be a list if present")
        else:
            seen_rels: Set[Tuple[str, str, str]] = set()
            med_attr_target_to_med: Dict[str, str] = {}

            for rel_idx, rel in enumerate(relationships):
                result.stats["relationships_checked"] += 1
                if not isinstance(rel, dict):
                    result.add_error(f"{doc_id} Rel[{rel_idx}]: relationship must be a dict")
                    continue

                rel_id = rel.get("rel_id")
                rel_type = rel.get("rel_type")
                source_id = rel.get("source_entity_id")
                target_id = rel.get("target_entity_id")

                if not rel_type or rel_type not in APPROVED_RELATION_TYPES:
                    result.add_error(
                        f"{doc_id} Rel[{rel_id or rel_idx}]: invalid rel_type '{rel_type}'. Allowed: {APPROVED_RELATION_TYPES}"
                    )

                # Endpoint referential integrity
                if not source_id or source_id not in entity_map:
                    result.add_error(
                        f"{doc_id} Rel[{rel_id or rel_idx}]: source_entity_id '{source_id}' does not exist in entities"
                    )
                if not target_id or target_id not in entity_map:
                    result.add_error(
                        f"{doc_id} Rel[{rel_id or rel_idx}]: target_entity_id '{target_id}' does not exist in entities"
                    )

                # Medication-specific relationship rules
                if rel_type in {"has_dosage", "has_route", "has_frequency", "has_prn_indication"}:
                    if source_id in entity_map:
                        source_ent = entity_map[source_id]
                        if source_ent.get("macro_category") != "Medication":
                            result.add_error(
                                f"{doc_id} Rel[{rel_id or rel_idx}]: medication attribute edge '{rel_type}' source '{source_id}' is '{source_ent.get('macro_category')}', expected 'Medication'"
                            )
                    if target_id in entity_map:
                        target_ent = entity_map[target_id]
                        if target_ent.get("macro_category") == "Medication":
                            result.add_error(
                                f"{doc_id} Rel[{rel_id or rel_idx}]: medication attribute edge '{rel_type}' target '{target_id}' cannot be 'Medication'"
                            )

                    # Cross-medication contamination check
                    is_shared = rel.get("is_shared_attribute", False)
                    if target_id in med_attr_target_to_med and not is_shared:
                        existing_med = med_attr_target_to_med[target_id]
                        if existing_med != source_id:
                            result.add_error(
                                f"{doc_id}: cross-medication attribute contamination: attribute span '{target_id}' bound to distinct medications '{existing_med}' and '{source_id}' without 'is_shared_attribute: true'"
                            )
                    med_attr_target_to_med[target_id] = source_id

                # Duplicate relationship check
                rel_tuple = (rel_type or "", source_id or "", target_id or "")
                if rel_tuple in seen_rels:
                    result.add_error(
                        f"{doc_id}: duplicate relationship detected of type '{rel_type}' between '{source_id}' and '{target_id}'"
                    )
                seen_rels.add(rel_tuple)

        # 6. Conditional Directives Structure
        conditionals = doc.get("conditional_directives", [])
        if not isinstance(conditionals, list):
            result.add_error(f"{doc_id}: 'conditional_directives' must be a list if present")
        else:
            for c_idx, c_dir in enumerate(conditionals):
                result.stats["conditional_directives_checked"] += 1
                if not isinstance(c_dir, dict):
                    result.add_error(f"{doc_id} Conditional[{c_idx}]: conditional directive must be a dict")
                    continue
                trigger = c_dir.get("trigger_condition")
                action = c_dir.get("resulting_action")
                if not trigger or not isinstance(trigger, str):
                    result.add_error(f"{doc_id} Conditional[{c_idx}]: missing or non-string 'trigger_condition'")
                if not action or not isinstance(action, str):
                    result.add_error(f"{doc_id} Conditional[{c_idx}]: missing or non-string 'resulting_action'")

                source_span = c_dir.get("source_span")
                if source_span is not None:
                    if (
                        not isinstance(source_span, list)
                        or len(source_span) != 2
                        or not isinstance(source_span[0], int)
                        or not isinstance(source_span[1], int)
                    ):
                        result.add_error(
                            f"{doc_id} Conditional[{c_idx}]: source_span must be [start_char, end_char]"
                        )
                    else:
                        cs, ce = source_span
                        if cs < 0 or ce > doc_len or cs >= ce:
                            result.add_error(
                                f"{doc_id} Conditional[{c_idx}]: source_span [{cs}, {ce}] out of bounds for doc len {doc_len}"
                            )

        return result

    def validate_corpus(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validates an entire corpus document collection, including partition disjointness,
        patient-episode leakage, and specialty distribution tracking.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("Top-level dataset structure must be a JSON object (dict)")
            return result

        metadata = data.get("metadata", {})
        if not metadata or not isinstance(metadata, dict):
            result.add_warning("Corpus missing top-level 'metadata' dictionary")

        documents = data.get("documents")
        if documents is None or not isinstance(documents, list):
            result.add_error("Corpus missing 'documents' list")
            return result

        doc_ids: Set[str] = set()
        splits_docs: Dict[str, Set[str]] = {s: set() for s in APPROVED_SPLITS}
        splits_patients: Dict[str, Set[str]] = {s: set() for s in APPROVED_SPLITS}
        specialty_counts: Dict[str, int] = {}
        missing_patient_count = 0

        for idx, doc in enumerate(documents):
            doc_res = self.validate_document(doc, doc_index=idx)
            result.stats["documents_checked"] += 1
            result.stats["entities_checked"] += doc_res.stats["entities_checked"]
            result.stats["relationships_checked"] += doc_res.stats["relationships_checked"]
            result.stats["conditional_directives_checked"] += doc_res.stats["conditional_directives_checked"]

            if not doc_res.is_valid:
                result.is_valid = False
                result.errors.extend(doc_res.errors)
            result.warnings.extend(doc_res.warnings)

            # Track specialty distribution
            spec = doc.get("specialty")
            if spec:
                specialty_counts[spec] = specialty_counts.get(spec, 0) + 1

            # Track for corpus-level uniqueness and partition disjointness
            doc_id = doc.get("document_id")
            if doc_id:
                if doc_id in doc_ids:
                    result.add_error(f"Corpus level: duplicate document_id '{doc_id}' across documents")
                doc_ids.add(doc_id)

                split = doc.get("dataset_split")
                if split in APPROVED_SPLITS:
                    splits_docs[split].add(doc_id)

                patient_id = doc.get("patient_id")
                if patient_id and isinstance(patient_id, str) and patient_id.strip():
                    if split in APPROVED_SPLITS:
                        splits_patients[split].add(patient_id.strip())
                else:
                    missing_patient_count += 1

        result.stats["docs_missing_patient_id"] = missing_patient_count
        result.stats["specialties_checked"] = specialty_counts

        # Patient Independence Assessment
        total_docs = len(documents)
        if missing_patient_count > 0:
            result.stats["patient_independence_guaranteed"] = False
            result.add_warning(
                f"Patient independence cannot be verified across splits: {missing_patient_count}/{total_docs} notes lack a valid 'patient_id'"
            )
        else:
            result.stats["patient_independence_guaranteed"] = (total_docs > 0)

        # Split Disjointness Verification
        # 1. Document Disjointness
        split_names = list(APPROVED_SPLITS)
        for i in range(len(split_names)):
            for j in range(i + 1, len(split_names)):
                s1, s2 = split_names[i], split_names[j]
                overlap = splits_docs[s1].intersection(splits_docs[s2])
                if overlap:
                    result.add_error(
                        f"Partition Disjointness Violation: Documents {overlap} present in both '{s1}' and '{s2}'"
                    )

        # 2. Patient-Episode Disjointness (where patient IDs are recorded)
        for i in range(len(split_names)):
            for j in range(i + 1, len(split_names)):
                s1, s2 = split_names[i], split_names[j]
                pat_overlap = splits_patients[s1].intersection(splits_patients[s2])
                if pat_overlap:
                    result.add_error(
                        f"Patient Leakage Violation: Patient IDs {pat_overlap} present in both '{s1}' and '{s2}'"
                    )

        for s in APPROVED_SPLITS:
            result.stats["splits_checked"][s] = len(splits_docs[s])

        # Quota Validation for Complete Benchmarks
        if total_docs >= 250:
            for s, target_count in PROTOCOL_TARGET_SPLITS.items():
                actual_count = len(splits_docs[s])
                if actual_count != target_count:
                    result.add_error(
                        f"Split Allocation Mismatch: '{s}' has {actual_count} documents, target is {target_count}"
                    )
            for spec, target_count in PROTOCOL_TARGET_SPECIALTIES.items():
                actual_count = specialty_counts.get(spec, 0)
                if actual_count != target_count:
                    result.add_error(
                        f"Specialty Quota Mismatch: '{spec}' has {actual_count} documents, target is {target_count}"
                    )

        return result


class BenchmarkLifecycleEvaluator:
    """
    Evaluates the operational lifecycle state of an independent benchmark manifest.
    Distinguishes:
    - Stage 1: Protocol Created
    - Stage 2: Data Collected
    - Stage 3: Annotations Completed
    - Stage 4: Annotations Adjudicated
    - Stage 5: Benchmark Ready for Evaluation

    Enforces scientific evidence verification:
    - Refuses to mark approvals complete without supporting identifiers / institutions / dates.
    - Requires distinct double-blind annotator IDs.
    - Requires non-empty clinical adjudicator credentials.
    - Enforces protocol length bounds (>= 80 characters per note).
    """

    @staticmethod
    def evaluate_manifest_readiness(manifest: Dict[str, Any], base_dir: str = ".") -> Dict[str, Any]:
        report = {
            "protocol_created": False,
            "data_collected": False,
            "annotations_completed": False,
            "annotations_adjudicated": False,
            "benchmark_ready_for_evaluation": False,
            "governance_status": "UNRESOLVED",
            "blocking_reasons": [],
            "evidence": {},
        }

        # Check Protocol
        protocol_path = os.path.join(
            base_dir, "docs", "benchmark", "independent_benchmark_annotation_protocol.md"
        )
        if os.path.exists(protocol_path):
            report["protocol_created"] = True
            report["evidence"]["protocol_path"] = protocol_path
        else:
            report["blocking_reasons"].append(
                "Protocol document missing: docs/benchmark/independent_benchmark_annotation_protocol.md"
            )

        # Check Governance & Approvals with Evidence Verification
        gov = manifest.get("governance", {})
        iec_approved = gov.get("iec_irb_approved", False)
        data_auth = gov.get("data_owner_authorized", False)
        dua_signed = gov.get("dua_signed", False)

        iec_num = gov.get("iec_approval_number")
        iec_inst = gov.get("iec_institution")
        data_entity = gov.get("data_owner_entity")
        dua_date = gov.get("dua_execution_date")

        # Safeguard: Boolean flag alone cannot grant approval without recorded institutional evidence
        gov_errors = []
        if iec_approved:
            if not iec_num or not isinstance(iec_num, str) or not iec_num.strip():
                gov_errors.append("IEC/IRB approved flagged as True, but 'iec_approval_number' is missing or empty")
                iec_approved = False
            if not iec_inst or not isinstance(iec_inst, str) or not iec_inst.strip():
                gov_errors.append("IEC/IRB approved flagged as True, but 'iec_institution' is missing or empty")
                iec_approved = False
        else:
            gov_errors.append("IEC/IRB ethics approval pending")

        if data_auth:
            if not data_entity or not isinstance(data_entity, str) or not data_entity.strip():
                gov_errors.append("Data-owner authorization flagged as True, but 'data_owner_entity' is missing or empty")
                data_auth = False
        else:
            gov_errors.append("Institutional data-owner authorization pending")

        if dua_signed:
            if not dua_date or not isinstance(dua_date, str) or not dua_date.strip():
                gov_errors.append("DUA signed flagged as True, but 'dua_execution_date' is missing or empty")
                dua_signed = False
        else:
            gov_errors.append("Data Transfer Agreement / DUA unsigned")

        if iec_approved and data_auth and dua_signed:
            report["governance_status"] = "APPROVED"
            report["evidence"]["iec_approval_number"] = iec_num
            report["evidence"]["iec_institution"] = iec_inst
            report["evidence"]["data_owner_entity"] = data_entity
            report["evidence"]["dua_execution_date"] = dua_date
        else:
            report["governance_status"] = "UNRESOLVED"
            report["blocking_reasons"].extend(gov_errors)

        # Check Data Collection
        docs = manifest.get("documents", [])
        total_docs = len(docs)
        is_synthetic = manifest.get("metadata", {}).get("is_synthetic", False)

        valid_length_docs = sum(1 for d in docs if len(d.get("raw_text", "")) >= MIN_DOCUMENT_CHAR_LENGTH)
        de_id_docs = sum(1 for d in docs if d.get("de_identification_verified") is True)

        if total_docs >= 250 and not is_synthetic and de_id_docs == total_docs and valid_length_docs == total_docs:
            report["data_collected"] = True
            report["evidence"]["total_real_documents"] = total_docs
        else:
            if total_docs == 0:
                report["blocking_reasons"].append("Zero independent benchmark documents present in manifest")
            elif total_docs < 250:
                report["blocking_reasons"].append(f"Incomplete benchmark size ({total_docs}/250 target notes collected)")
            if is_synthetic:
                report["blocking_reasons"].append("Manifest declared as synthetic; not real clinical records")
            if total_docs > 0 and de_id_docs < total_docs:
                report["blocking_reasons"].append(
                    f"De-identification incomplete: {de_id_docs}/{total_docs} notes verified"
                )
            if total_docs > 0 and valid_length_docs < total_docs:
                report["blocking_reasons"].append(
                    f"Notes below protocol length minimum: {valid_length_docs}/{total_docs} meet {MIN_DOCUMENT_CHAR_LENGTH} char threshold"
                )

        # Check Annotations (Requires distinct double-blind annotator IDs)
        annotated_docs = sum(1 for d in docs if len(d.get("entities", [])) > 0)
        double_blind_docs = sum(
            1 for d in docs if len(set(d.get("annotation_metadata", {}).get("annotator_ids", []))) >= 2
        )
        if report["data_collected"] and annotated_docs == total_docs and double_blind_docs == total_docs:
            report["annotations_completed"] = True
            report["evidence"]["annotated_documents"] = annotated_docs
        else:
            if report["data_collected"]:
                report["blocking_reasons"].append(
                    f"Incomplete annotations: {annotated_docs}/{total_docs} annotated, {double_blind_docs}/{total_docs} distinct double-blinded"
                )

        # Check Adjudication (Requires confirmed adjudicator ID)
        adjudicated_docs = sum(
            1
            for d in docs
            if d.get("annotation_metadata", {}).get("adjudication_status") == "clinically_adjudicated"
            and bool(d.get("annotation_metadata", {}).get("adjudicator_id"))
        )
        if report["annotations_completed"] and adjudicated_docs == total_docs:
            report["annotations_adjudicated"] = True
            report["evidence"]["adjudicated_documents"] = adjudicated_docs
        else:
            if report["annotations_completed"]:
                report["blocking_reasons"].append(
                    f"Incomplete adjudication: {adjudicated_docs}/{total_docs} adjudicated with senior clinician ID"
                )

        # Check Ready for Evaluation Gate
        if (
            report["protocol_created"]
            and report["data_collected"]
            and report["annotations_completed"]
            and report["annotations_adjudicated"]
            and report["governance_status"] == "APPROVED"
        ):
            report["benchmark_ready_for_evaluation"] = True
        else:
            report["benchmark_ready_for_evaluation"] = False

        return report
