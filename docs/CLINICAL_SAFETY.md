# PULSE Clinical Safety, Risk Mitigation & AI Governance

## 1. Regulatory Status & Research Boundary
PULSE is an AI-assisted clinical information-organization prototype. It does **not**:
- Make primary medical diagnoses.
- Prescribe or titrate pharmaceutical regimens.
- Authorize patient discharge or surgical clearance.
- Replace professional clinical judgment of licensed registered nurses or physicians.

## 2. Negation & Uncertainty Handling
To mitigate harmful hallucinations or inverted clinical assertions:
1. Every extracted entity is evaluated against preceding negation markers (`no`, `denies`, `negative for`).
2. Confirmed negative findings (e.g. "denies SOB") are suppressed from positive diagnosis categories.
3. Speculative diagnoses (e.g. "?PE", "suspected appendicitis") are explicitly tagged as uncertain.

## 3. Human-in-the-Loop Verification
All generated 9-category clinical handover summaries require nursing staff sign-off prior to electronic health record (EHR) transmission.
