"""
PULSE Structured Handover Generator
Synthesizes extracted clinical entities, events, and temporal expressions into:
1. Standard 9-Category Clinical Handover Output
2. ISBAR Clinical Handover Framework (Identify, Situation, Background, Assessment, Recommendation)
3. Executive Clinical Shift Summary (Charge-nurse narrative handover brief)
4. Outstanding Prioritized Shift Continuity Tasks
5. Long-term Follow-Up Plan
Adheres strictly to source evidence with authentic clinical documentation formatting.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

class StructuredHandoverGenerator:
    def __init__(self):
        # Patterns for Pending Tasks (urgent or shift-level actions)
        self.pending_task_patterns = [
            (r"\b(?:told\s+patient\s+to\s+(?:take\s+)?test\s+(?:of|for)\s+[^.,;\n]+|take\s+test\s+(?:of|for)\s+[^.,;\n]+|order\s+test\s+(?:of|for)\s+[^.,;\n]+)\b", "Diagnostic Lab Investigation Ordered"),
            (r"\b(?:doctor\s+advised\s+to\s+take\s+rest|advised\s+to\s+take\s+rest|take\s+rest|bed\s*rest|adequate\s+rest)\b", "Rest & Clinical Recovery Directive"),
            (r"\b(?:(?:do\s+)?walk\s+and\s+exercise(?:\s+in\s+(?:the\s+)?morning)?|morning\s+walk(?:\s+and\s+exercise)?|exercise\s+in\s+(?:the\s+)?morning)\b", "Physical Activity & Morning Exercise Directive"),
            (r"\b(?:advised\s+to\s+take\s+fresh\s*(?:air|hair)|take\s+fresh\s*(?:air|hair)|fresh\s*(?:air|hair))\b", "Fresh Air & Ambulation Advice"),
            (r"\b(?:doctor\s+advised\s+to\s+[^.,;\n]+|advised\s+to\s+[^.,;\n]+|told\s+(?:him|her|patient)\s+to\s+[^.,;\n]+)\b", "Clinician Care Advice / Directive"),
            (r"\b([a-zA-Z\s]+?)\s+(?:is\s+)?planned\s+for\s+([a-zA-Z0-9\s]+)", "Scheduled Clinical Action / Procedure"),
            (r"\b([a-zA-Z\s]+?(?:ct|mri|scan|x-?ray|ultrasound|doppler|blood\s*test|pathology|biopsy|culture[s]?|report))\s+(?:is\s+)?pending\b", "Pending Diagnostic Investigation"),
            (r"\b(?:awaiting|waiting\s+for)\s+([a-zA-Z\s]+?(?:results?|report|findings?))\b", "Pending Diagnostic Investigation"),
            (r"\b(?:needs\s+another|rescheduled|needs|waiting\s+for|awaiting)\s+([^.,;]+)", "Diagnostic Scheduling Pending"),
            (r"\b(?:still\s+for\s+referral\s+to|referral\s+to)\s+([^.,;]+)", "Allied Health / Specialist Referral"),
            (r"\b(?:still\s+need\s+(?:the\s+)?team\s+to\s+review|still\s+for\s+review|needs?\s+review)\s*([^.,;]*)", "Medical Team Review Pending"),
            (r"\b(?:just\s+ask\s+the\s+doctor\s+for\s+the\s+next\s+dose|ask\s+doctor)\b", "Medication Dosing Clarification Required"),
            (r"\b(?:needs?\s+assistance|needs?\s+help)\b", "Patient Care Assistance Required"),
            (r"\b(?:still\s+under\s+monitoring|continuous\s+monitoring)\b", "Ongoing Active Monitoring Required"),
            (r"\b(?:is\s+for\s+([a-zA-Z\s]+?)(?:,|\.|\sbut|\she))", "Scheduled Investigation / Procedure"),
            (r"\b(?:(?:test\s+for|for\s+test|testing)\s+([^.,;\n]+?)(?=\s+and\b|\s+after\b|\s+for\b|[.,;\n]|$))", "Diagnostic Investigation Pending")
        ]

        # Patterns for Follow-Up (future evaluations, repeat tests, discharge planning)
        self.follow_up_patterns = [
            (r"\b(?:review\s+(?:patient\s+)?tomorrow|review\s+next\s+shift|review\s+later)\b", "Scheduled Clinical Review"),
            (r"\b(?:repeat\s+(?:blood\s*test|ecg|x-?ray|scan|labs?))\b", "Repeat Diagnostic Evaluation"),
            (r"\b(?:follow-?up\s+(?:appointment|with|by)|outpatient\s+clinic)\b", "Outpatient Follow-Up"),
            (r"\b(?:monitor\s+(?:bgl|bp|blood\s*pressure|vital\s*signs|sats))\b", "Targeted Parameter Monitoring"),
            (r"\b(?:referral\s+to\s+([a-zA-Z\s]+))\b", "Specialist Consultation Follow-Up"),
            (r"\b(?:needs\s+another\s+carotid\s+doppler\s+appointment)\b", "Ultrasound Unit Rescheduling"),
            (r"\b(?:(?:patient\s+)?(?:have\s+to\s+|has\s+to\s+|should\s+|to\s+)?(?:come|return|meet(?:\s+me)?|follow[- ]?up|attend|review)(?:\s+(?:back|again))?\s+(?:after|in)\s+(\d+\s*(?:days?|weeks?|months?))(?:\s+after\s+[^.,;\n]+)?)\b", "Scheduled Clinical Review / Follow-Up"),
            (r"\b(?:meet(?:\s+me)?\s+(?:after|in)\s+(\d+\s*(?:days?|weeks?|months?)))\b", "Scheduled Clinical Review / Follow-Up"),
            (r"\b(?:after\s+(\d+\s*(?:days?|weeks?|months?))(?:\s+after\s+testing[^.,;\n]*)?)\b", "Scheduled Diagnostic Follow-Up")
        ]

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        from backend.extraction.context_extractor import clinical_context_extractor
        return clinical_context_extractor.split_sentences_protected(text)

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> str:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text
        return sentence_spans[0][0] if sentence_spans else ""

    def extract_pending_tasks(self, text: str, events: List[Dict[str, Any]], entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        sentence_spans = self._split_into_sentences(text)
        pending_tasks = []
        seen = set()

        from backend.extraction.context_extractor import clinical_context_extractor

        for pattern, task_type in self.pending_task_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                matched_item = m.group(0).strip()
                source_sentence = self._find_source_sentence(m.start(), sentence_spans)

                # Filter out negated items
                ctx = clinical_context_extractor.analyze_assertion(matched_item, m.start(), m.end(), text)
                if ctx["is_negated"]:
                    continue

                groups = m.groups()
                timing = None
                task_status = "Pending"
                if len(groups) == 2 and "planned" in pattern:
                    action_part = groups[0].strip()
                    timing_part = groups[1].strip()
                    task_title = f"{action_part.capitalize()} (Planned for {timing_part})"
                    timing = timing_part
                    task_status = "Planned"
                    if "review" in action_part.lower():
                        task_type = "Scheduled Clinical Review / Consultation"
                elif "pending" in pattern or "is pending" in matched_item.lower():
                    task_title = matched_item.capitalize()
                    task_status = "Pending"
                else:
                    task_title = matched_item.capitalize()

                key = (task_type, source_sentence.lower())
                if key not in seen:
                    seen.add(key)
                    is_urgent = any(w in matched_item.lower() or w in source_sentence.lower() for w in ["urgent", "urgently", "stat", "emergency", "critical", "immediate", "code blue"])
                    priority = "High" if is_urgent else "Unassigned / Awaiting Clinician Triage"
                    pending_tasks.append({
                        "task": task_title,
                        "type": task_type,
                        "priority": priority,
                        "status": task_status,
                        "timing": timing,
                        "source_sentence": source_sentence,
                        "start_char": m.start(),
                        "end_char": m.end()
                    })

        # Also inspect entities for pending or awaiting investigations
        if entities:
            for inv in entities.get("investigations", []):
                if inv.get("is_negated"):
                    continue
                if inv.get("status") in ["Pending", "Awaiting Results"]:
                    key = ("Pending Diagnostic Investigation", inv.get("source_sentence", "").lower())
                    if key not in seen and not any(inv.get("text", "").lower() in t["task"].lower() for t in pending_tasks):
                        seen.add(key)
                        is_urgent = any(w in inv.get("source_sentence", "").lower() for w in ["urgent", "urgently", "stat", "emergency", "critical", "immediate", "code blue"])
                        priority = "High" if is_urgent else "Unassigned / Awaiting Clinician Triage"
                        pending_tasks.append({
                            "task": f"{inv.get('text', '').capitalize()} is pending",
                            "type": "Pending Diagnostic Investigation",
                            "priority": priority,
                            "status": "Pending",
                            "timing": None,
                            "source_sentence": inv.get("source_sentence", ""),
                            "start_char": inv.get("start_char", 0),
                            "end_char": inv.get("end_char", 0)
                        })

        # Also inspect events for pending or rescheduled status
        for ev in events:
            if any(k in ev.get("type", "").lower() for k in ["pending", "review", "rescheduled", "scheduled"]):
                key = ("Event Pending", ev.get("source_sentence", "").lower())
                if key not in seen:
                    seen.add(key)
                    is_urgent = any(w in ev.get("event", "").lower() or w in ev.get("source_sentence", "").lower() for w in ["urgent", "urgently", "stat", "emergency", "critical", "immediate", "code blue"])
                    priority = "High" if is_urgent else "Unassigned / Awaiting Clinician Triage"
                    pending_tasks.append({
                        "task": ev.get("event"),
                        "type": ev.get("type"),
                        "priority": priority,
                        "status": "Pending",
                        "timing": ev.get("time") if ev.get("time") != "Not specified" else None,
                        "source_sentence": ev.get("source_sentence"),
                        "start_char": ev.get("start_char", 0),
                        "end_char": ev.get("end_char", 0)
                    })

        # Deduplicate tasks
        deduped = []
        for pt in pending_tasks:
            t_low = pt["task"].lower()
            if not any(t_low == existing["task"].lower() for existing in deduped):
                deduped.append(pt)

        return deduped

    def extract_follow_up(self, text: str, pending_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not text:
            return []

        sentence_spans = self._split_into_sentences(text)
        follow_up = []
        seen = set()

        for pattern, fu_type in self.follow_up_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                matched = m.group(0).strip()
                source_sentence = self._find_source_sentence(m.start(), sentence_spans)
                key = matched.lower()
                if key not in seen:
                    seen.add(key)
                    follow_up.append({
                        "action": matched.capitalize(),
                        "type": fu_type,
                        "source_sentence": source_sentence,
                        "start_char": m.start(),
                        "end_char": m.end()
                    })

        for pt in pending_tasks:
            if any(term in pt.get("task", "").lower() for term in ["referral", "review", "appointment", "educator"]):
                key = pt.get("task", "").lower()
                if key not in seen:
                    seen.add(key)
                    follow_up.append({
                        "action": pt.get("task"),
                        "type": "Specialist / Multi-disciplinary Follow-Up",
                        "priority": pt.get("priority", "Unassigned / Awaiting Clinician Triage"),
                        "status": pt.get("status", "Pending"),
                        "timing": pt.get("timing"),
                        "source_sentence": pt.get("source_sentence"),
                        "start_char": pt.get("start_char", 0),
                        "end_char": pt.get("end_char", 0)
                    })

        # Deduplicate overlapping or substring follow-up items
        deduped = []
        for fu in follow_up:
            act_lower = fu["action"].lower()
            is_sub = False
            for idx, existing in enumerate(deduped):
                ex_lower = existing["action"].lower()
                if act_lower in ex_lower:
                    is_sub = True
                    break
                elif ex_lower in act_lower:
                    deduped[idx] = fu
                    is_sub = True
                    break
            if not is_sub:
                deduped.append(fu)

        return deduped

    def generate_executive_summary(
        self,
        patient_dict: Dict[str, str],
        conditions: List[Any],
        symptoms: List[Any],
        pending_tasks: List[Any],
        measurements: List[Any],
        raw_text: str = ""
    ) -> str:
        """
        Synthesizes a realistic, highly coherent 2-3 sentence executive clinical shift handover brief.
        Guarantees that negated, historical, or uncertain findings are never fabricated into active diagnoses,
        and severe deterioration warnings are never obscured by false stability claims.
        """
        name = patient_dict.get("Patient Name", "Patient")
        bed = patient_dict.get("Bed / Room", "Ward")
        age = patient_dict.get("Age", "")
        doc = patient_dict.get("Attending Consultant", "Medical Team")

        # Partition findings by assertion and temporality
        active_conditions = [c for c in conditions if not c.get("is_negated") and not c.get("is_historical") and not c.get("is_uncertain")]
        active_symptoms = [s for s in symptoms if not s.get("is_negated") and not s.get("is_historical") and not s.get("is_uncertain")]
        uncertain_findings = [x for x in (conditions + symptoms) if x.get("is_uncertain")]
        negated_findings = [x for x in (symptoms + conditions) if x.get("is_negated")]
        historical_findings = [x for x in (symptoms + conditions) if x.get("is_historical")]

        # Determine primary condition/reason
        if active_conditions:
            prim_cond = active_conditions[0]["normalized"]
        elif active_symptoms:
            prim_cond = active_symptoms[0]["normalized"]
        elif uncertain_findings:
            prim_cond = f"suspected {uncertain_findings[0]['normalized']}"
        elif negated_findings:
            prim_cond = f"clinical observation and symptom exclusion (denies {negated_findings[0]['text']})"
        elif historical_findings:
            prim_cond = f"ward observation following prior {historical_findings[0]['normalized']} (now resolved)"
        else:
            prim_cond = "clinical observation"

        # Check for concerning acuity cues in source text without inferring confirmed diagnoses
        text_lower = raw_text.lower()
        critical_cues = ["may die", "critical", "arrest", "deteriorat", "unstable", "emergency", "code blue", "in extremis", "life-threatening"]
        matched_cues = [cue for cue in critical_cues if cue in text_lower]
        has_critical_cue = len(matched_cues) > 0

        # Vital status synthesis
        meas_summary = None
        for m in measurements:
            if "gcs" in m.get("type", "").lower() or "15" in m.get("text", ""):
                meas_summary = f"GCS recorded as {m.get('text')}"
                break
            elif "bp" in m.get("type", "").lower():
                meas_summary = f"BP recorded as {m.get('text')}"
                break

        if not meas_summary:
            if has_critical_cue:
                cues_disp = ", ".join(repr(c) for c in matched_cues)
                meas_summary = f"Acuity unverified from note alone ({cues_disp})"
            else:
                meas_summary = "Routine ward vital sign monitoring ongoing"

        # Pending action / acuity directive
        if has_critical_cue:
            cues_disp = ", ".join(repr(c) for c in matched_cues)
            action_phrase = f"CRITICAL ALERT: Note records concerning statement ({cues_disp}) requiring clinician review and verification; objective clinical deterioration not established."
        elif pending_tasks:
            top_task = pending_tasks[0].get("task")
            action_phrase = f"Key handover priority is to follow up on {top_task.lower()}."
        else:
            action_phrase = "Patient remains under routine nursing surveillance with no acute deterioration noted."

        intro = f"{name} ({bed}, {age}{', under ' + doc if doc != 'Medical Team' else ''}) admitted for management of {prim_cond}."
        second = f"{meas_summary}; currently under active ward observation." if not has_critical_cue else f"{meas_summary}."
        return f"{intro} {second} {action_phrase}"

    def generate_isbar(
        self,
        patient_dict: Dict[str, str],
        entities: Dict[str, Any],
        events: List[Dict[str, Any]],
        pending_tasks: List[Dict[str, Any]],
        follow_up: List[Dict[str, Any]],
        text: str = ""
    ) -> Dict[str, Any]:
        """
        Synthesizes ISBAR (Identify, Situation, Background, Assessment, Recommendation),
        the gold-standard clinical communication protocol used in modern hospitals.
        """
        # I - Identify
        identify_items = [
            f"Patient: {patient_dict.get('Patient Name', 'Name not explicitly stated')}",
            f"Location: {patient_dict.get('Bed / Room', 'Bed not recorded')}",
            f"Demographics: {patient_dict.get('Age', 'Age not stated')} | {patient_dict.get('Gender / Sex', 'Gender not stated')}",
            f"Consultant: {patient_dict.get('Attending Consultant', 'Medical Team')}"
        ]

        text_lower = text.lower()
        critical_cues = ["may die", "critical", "arrest", "deteriorat", "unstable", "emergency", "code blue", "in extremis", "life-threatening"]
        matched_cues = [cue for cue in critical_cues if cue in text_lower]
        has_critical_cue = len(matched_cues) > 0

        # Categorize entity findings
        all_symptoms = entities.get("symptoms", [])
        all_conditions = entities.get("conditions", [])

        active_symptoms = [s for s in all_symptoms if not s.get("is_negated") and not s.get("is_historical") and not s.get("is_uncertain")]
        active_conditions = [c for c in all_conditions if not c.get("is_negated") and not c.get("is_historical") and not c.get("is_uncertain")]
        uncertain_findings = [x for x in (all_symptoms + all_conditions) if x.get("is_uncertain")]
        negated_findings = [x for x in (all_symptoms + all_conditions) if x.get("is_negated")]
        historical_findings = [x for x in (all_symptoms + all_conditions) if x.get("is_historical")]

        # S - Situation
        situation_items = []
        if active_symptoms:
            symptom_names = ", ".join([s["normalized"] for s in active_symptoms[:3]])
            has_explicit_acute = any("acute" in s.get("text", "").lower() for s in active_symptoms[:3])
            prefix = "Acute " if has_explicit_acute else ""
            situation_items.append(f"Current Clinical Presentation: {prefix}{symptom_names}")
        elif uncertain_findings:
            unc_names = ", ".join([x["normalized"] for x in uncertain_findings[:2]])
            situation_items.append(f"Current Clinical Presentation: Suspected / Query {unc_names}")
        elif active_conditions:
            situation_items.append(f"Current Admission Reason: Management of {active_conditions[0]['normalized']}")
        elif historical_findings:
            situation_items.append(f"Current Ward Presentation: Observation following resolved {historical_findings[0]['normalized']} ('{historical_findings[0]['text']}')")
        else:
            situation_items.append("Admitted to ward for clinical observation and symptomatic management.")

        if negated_findings:
            neg_names = ", ".join([n["text"] for n in negated_findings[:3]])
            situation_items.append(f"Pertinent Negatives (Explicitly Denied / Absent): {neg_names}")

        if has_critical_cue:
            cues_str = ", ".join([repr(c) for c in matched_cues])
            situation_items.append(f"CRITICAL NOTE ALERT: Concerning phrase recorded in source note: {cues_str} (Requires clinician review and verification; not an objective clinical deterioration finding)")

        for ev in events:
            if "admission" in ev.get("type", "").lower() or "presentation" in ev.get("type", "").lower():
                situation_items.append(f"Presentation Context: {ev.get('event')}")
                break

        # B - Background
        background_items = []
        for c in active_conditions:
            background_items.append(f"Documented Condition: {c['normalized']}")
        for c in [c for c in all_conditions if c.get("is_uncertain")]:
            background_items.append(f"Suspected Condition: {c['normalized']} (Under evaluation)")
        for h in historical_findings:
            background_items.append(f"Past Shift Episode (Resolved): {h['normalized']} ('{h['text']}')")

        if not background_items:
            background_items.append("No prior chronic medical conditions recorded in shift handover.")

        # A - Assessment
        assessment_items = []
        for m in entities.get("measurements", []):
            m_label = m.get("type") or m.get("normalized") or "Measurement"
            assessment_items.append(f"{m_label}: {m['text']}")
        for med in entities.get("medications", []):
            dose_str = f" ({med.get('dosage')})" if med.get('dosage') else ""
            assessment_items.append(f"Administered / Prescribed: {med['normalized']}{dose_str}")
        for trt in entities.get("treatments", []):
            assessment_items.append(f"Clinical Care / Mobility: {trt['normalized']} ({trt['text']})")
        for inv in entities.get("investigations", []):
            status = " [Planned]" if inv.get("is_planned") else ""
            assessment_items.append(f"Diagnostic Finding: {inv['normalized']}{status}")

        for unc in entities.get("unclassified_candidates", []):
            s_text = unc.get("source_text") or unc.get("text")
            assessment_items.append(f"Unclassified Note Statement (For Review): \"{s_text}\"")

        if has_critical_cue:
            cues_str = ", ".join([repr(c) for c in matched_cues])
            assessment_items.append(f"Unverified Acuity Cue: Clinician noted {cues_str} — unconfirmed by objective vitals; requires bedside clinical evaluation.")
        elif not assessment_items:
            # Safe non-fabricated assessment default
            assessment_items.append("Routine vital sign monitoring ongoing; acute assessment findings not explicitly documented.")

        # R - Recommendation
        recommendation_items = []
        if has_critical_cue:
            cues_str = ", ".join([repr(c) for c in matched_cues])
            recommendation_items.append(f"[Priority] Bedside clinician review to evaluate concerning statement in note: {cues_str}.")

        if pending_tasks:
            for pt in pending_tasks:
                p_label = pt.get('priority', 'Unassigned / Awaiting Clinician Triage')
                priority_str = f"[{p_label} Priority]" if p_label in ["High", "Medium", "Low"] else f"[{p_label}]"
                recommendation_items.append(f"{priority_str} {pt['task']}")
        if follow_up:
            for fu in follow_up:
                if fu['action'] not in [pt['task'] for pt in pending_tasks]:
                    recommendation_items.append(f"Follow-Up: {fu['action']}")
        if not recommendation_items:
            recommendation_items.append("Continue routine vital observations and supportive nursing care.")

        return {
            "identify": identify_items,
            "situation": situation_items,
            "background": background_items,
            "assessment": assessment_items,
            "recommendation": recommendation_items
        }

    def generate_structured_handover(
        self,
        text: str,
        entities: Dict[str, Any],
        events: List[Dict[str, Any]],
        temporal_info: List[Dict[str, Any]],
        pending_tasks: List[Dict[str, Any]],
        follow_up: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Constructs the comprehensive structured handover output:
        1. 9-category structured handover
        2. ISBAR structured protocol
        3. Executive clinical brief
        """
        patient_dict = {p.get("field"): p.get("value") for p in entities.get("patient_information", [])}

        # 1. Patient Information
        patient_info_list = []
        for p in entities.get("patient_information", []):
            patient_info_list.append(f"{p.get('field')}: {p.get('value')}")
        if not patient_info_list:
            patient_info_list.append("Demographics: Not explicitly recorded in free-text note.")

        # 2. Current Condition
        current_condition_list = []
        for s in entities.get("symptoms", []):
            occ = f" (reported {s.get('occurrences', 1)}x)" if s.get('occurrences', 1) > 1 else ""
            if s.get("is_negated"):
                current_condition_list.append(f"Pertinent Negative (Explicitly Denied / Absent): {s.get('normalized')} ('{s.get('text')}')")
            elif s.get("is_historical"):
                current_condition_list.append(f"Past Shift Episode (Resolved): {s.get('normalized')} ('{s.get('text')}')")
            elif s.get("is_uncertain"):
                current_condition_list.append(f"Suspected / Query Symptom: {s.get('normalized')}{occ}")
            else:
                has_explicit_acute = "acute" in s.get("text", "").lower()
                prefix = "Acute Symptom: " if has_explicit_acute else "Active Symptom: "
                current_condition_list.append(f"{prefix}{s.get('normalized')}{occ}")

        for m in entities.get("measurements", []):
            current_condition_list.append(f"Vital Assessment: {m.get('type')} — {m.get('text')}")

        if not current_condition_list:
            current_condition_list.append("Current condition stable; no acute distressing symptoms documented.")

        # 3. Medical History
        history_list = []
        for c in entities.get("conditions", []):
            if c.get("is_negated"):
                history_list.append(f"Ruled Out / Denied: {c.get('normalized')} ('{c.get('text')}')")
            elif c.get("is_uncertain"):
                history_list.append(f"Suspected / Differential: {c.get('normalized')}")
            else:
                history_list.append(f"Documented History / Active: {c.get('normalized')}")
        if not history_list:
            history_list.append("No significant past medical history documented in report.")

        # 4. Medications / Treatment
        med_treatment_list = []
        for med in entities.get("medications", []):
            if med.get("is_negated"):
                med_treatment_list.append(f"{med.get('normalized')} — Not administered / Ceased")
            else:
                dose_info = f"Dose: {med.get('dosage')}" if med.get('dosage') not in ["Standard ward dose", "Unspecified dose in text"] else "Dose: As charted"
                med_treatment_list.append(f"{med.get('normalized')} — {dose_info}, Route: {med.get('route')}, Frequency: {med.get('frequency')}")
        for trt in entities.get("treatments", []):
            med_treatment_list.append(f"Care Level: {trt.get('normalized')} ({trt.get('text')})")
        if not med_treatment_list:
            med_treatment_list.append("No active medications or invasive therapies recorded in handover.")

        # 5. Investigations
        investigations_list = []
        for inv in entities.get("investigations", []):
            inv_st = inv.get("status")
            if inv.get("is_negated"):
                status = " (Not Ordered / Denied)"
            elif inv_st and inv_st != "Unspecified":
                status = f" ({inv_st})"
            elif inv.get("is_planned"):
                status = " (Planned / Scheduled)"
            else:
                status = ""
            name_part = f"{inv.get('normalized')} ('{inv.get('text')}')" if inv.get('text') and inv.get('text').lower() != inv.get('normalized', '').lower() else inv.get('normalized')
            investigations_list.append(f"Investigation{status}: {name_part}")
        if not investigations_list:
            investigations_list.append("No diagnostic investigations recorded in current report.")

        # 6. Clinical Events
        clinical_events_list = []
        for ev in events:
            time_part = f" [{ev.get('time')}]" if ev.get("time") != "Not specified" else ""
            clinical_events_list.append(f"{ev.get('event')} ({ev.get('type')}){time_part}")
        if not clinical_events_list:
            clinical_events_list.append("No discrete inter-shift clinical events identified.")

        # 7. Temporal Information
        temporal_list = []
        for t in temporal_info:
            assoc = f" → Associated with: {t.get('associated_event')}" if t.get('associated_event') else ""
            temporal_list.append(f"Time: '{t.get('expression')}' ({t.get('type')}){assoc}")
        if not temporal_list:
            temporal_list.append("No explicit temporal expressions identified.")

        # 8. Pending Tasks
        pending_list = []
        for pt in pending_tasks:
            p_label = pt.get('priority', 'Unassigned / Awaiting Clinician Triage')
            priority_str = f"[{p_label} Priority]" if p_label in ["High", "Medium", "Low"] else f"[{p_label}]"
            pending_list.append(f"{priority_str} {pt.get('task')} ({pt.get('type')})")
        if not pending_list:
            pending_list.append("No outstanding pending tasks recorded for upcoming shift.")

        # 9. Follow-up
        follow_up_list = []
        for fu in follow_up:
            follow_up_list.append(f"{fu.get('action')} ({fu.get('type')})")
        if not follow_up_list:
            follow_up_list.append("No specific long-term follow-up actions recorded.")

        # Executive Summary
        exec_summary = self.generate_executive_summary(
            patient_dict=patient_dict,
            conditions=entities.get("conditions", []),
            symptoms=entities.get("symptoms", []),
            pending_tasks=pending_tasks,
            measurements=entities.get("measurements", []),
            raw_text=text
        )

        # ISBAR Protocol
        isbar = self.generate_isbar(
            patient_dict=patient_dict,
            entities=entities,
            events=events,
            pending_tasks=pending_tasks,
            follow_up=follow_up,
            text=text
        )

        unclassified_obs = []
        for unc in entities.get("unclassified_candidates", []):
            s_text = unc.get("source_text") or unc.get("text")
            m_method = unc.get("extraction_method", "open_vocabulary")
            r_stat = unc.get("review_status", "flagged_for_review")
            unclassified_obs.append(f"\"{s_text}\" (Method: {m_method}, Review Status: {r_stat})")

        return {
            "patient_information": patient_info_list,
            "current_condition": current_condition_list,
            "medical_history": history_list,
            "medications_treatment": med_treatment_list,
            "investigations": investigations_list,
            "clinical_events": clinical_events_list,
            "temporal_information": temporal_list,
            "pending_tasks": pending_list,
            "follow_up": follow_up_list,
            "executive_summary": exec_summary,
            "isbar": isbar,
            "unclassified_observations": unclassified_obs
        }

# Global singleton instance
structured_handover_generator = StructuredHandoverGenerator()
