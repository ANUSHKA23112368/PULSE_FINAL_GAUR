"""
Shared Bio_ClinicalBERT token-classification label schema.

Used by training, evaluation, and live inference so BIO tags stay aligned
with the fine-tuned checkpoint at backend/models/clinical_bert.
"""

from typing import Dict, List

MACRO_CATEGORIES: List[str] = [
    "Demographics_Bed",
    "Demographics_Name",
    "Demographics_Age",
    "Demographics_Gender",
    "Demographics_Doctor",
    "Clinical_Condition",
    "Clinical_Observation",
    "Medication",
    "Investigation_Procedure",
    "Plan_Goal",
    "Care_Activity",
]

# NICTA / Suominen nursing-handover column labels → PULSE macro categories
CATEGORY_MAP: Dict[str, str] = {
    "PatientIntroduction_CurrentBed": "Demographics_Bed",
    "PatientIntroduction_CurrentRoom": "Demographics_Bed",
    "PatientIntroduction_GivenNames/Initials": "Demographics_Name",
    "PatientIntroduction_Lastname": "Demographics_Name",
    "PatientIntroduction_Ageinyears": "Demographics_Age",
    "PatientIntroduction_Gender": "Demographics_Gender",
    "PatientIntroduction_UnderDr_Lastname": "Demographics_Doctor",
    "PatientIntroduction_UnderDr_GivenNames/Initials": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianLastname": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianGivenNames/Initials": "Demographics_Doctor",
    "PatientIntroduction_AdmissionReason/Diagnosis": "Clinical_Condition",
    "PatientIntroduction_Disease/ProblemHistory": "Clinical_Condition",
    "PatientIntroduction_ChronicCondition": "Clinical_Condition",
    "MyShift_Status": "Clinical_Observation",
    "MyShift_OtherObservation": "Clinical_Observation",
    "MyShift_Wounds/Skin": "Clinical_Observation",
    "MyShift_Output/Diuresis/BowelMovement": "Clinical_Observation",
    "MyShift_Input/Diet": "Clinical_Observation",
    "Future_Alert/Warning/AbnormalResult": "Clinical_Observation",
    "Medication_Medicine": "Medication",
    "Medication_Dosage": "Medication",
    "Medication_Status": "Medication",
    "Appointment/Procedure_Description": "Investigation_Procedure",
    "Appointment/Procedure_Status": "Investigation_Procedure",
    "Appointment/Procedure_Day": "Investigation_Procedure",
    "Appointment/Procedure_Time": "Investigation_Procedure",
    "Appointment/Procedure_City": "Investigation_Procedure",
    "Appointment/Procedure_Ward": "Investigation_Procedure",
    "Future_Goal/TaskToBeCompleted/ExpectedOutcome": "Plan_Goal",
    "Future_Discharge/TransferPlan": "Plan_Goal",
    "PatientIntroduction_CarePlan": "Plan_Goal",
    "PatientIntroduction_Allergy": "Plan_Goal",
    "MyShift_RiskManagement": "Plan_Goal",
    "MyShift_ActivitiesOfDailyLiving": "Care_Activity",
    "MyShift_Contraption": "Care_Activity",
}

LABEL_LIST: List[str] = ["O"]
for _cat in MACRO_CATEGORIES:
    LABEL_LIST.append(f"B-{_cat}")
    LABEL_LIST.append(f"I-{_cat}")

ID2LABEL: Dict[int, str] = {i: label for i, label in enumerate(LABEL_LIST)}
LABEL2ID: Dict[str, int] = {label: i for i, label in enumerate(LABEL_LIST)}


def map_raw_label(raw_label: str) -> str:
    clean = raw_label.replace("B-", "").replace("I-", "")
    return CATEGORY_MAP.get(clean, "Other")
