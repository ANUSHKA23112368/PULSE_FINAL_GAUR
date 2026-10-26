"""
PULSE Clinical Context & Assertion Extractor
Implements the clinical ConText / NegEx algorithm for clinical handovers:
1. Assertion Analysis:
   - Affirmative (Confirmed positive finding)
   - Negated (Explicitly denied, absent, or ruled out)
   - Possible (Hypothetical, hedged, suspected, or uncertain)
2. Temporality Analysis:
   - Current (Active present state)
   - Historical (Past episode, prior history, resolved)
   - Planned (Future event, scheduled task, prospective)
3. Sentence splitting with medical abbreviation protection.
"""

import re
from typing import Dict, Any, List, Tuple

class ClinicalContextExtractor:
    def __init__(self):
        # 1. Pre-negation triggers (negates following entity in clause)
        self.pre_negation_triggers = [
            r"\b(?:denies|denied|denying)\b",
            r"\b(?:no|not|non)\b",
            r"\b(?:without|nil|none|never)\b",
            r"\b(?:rules?\s*out|ruled\s*out|r/o)\b",
            r"\b(?:negative\s*(?:for)?)\b",
            r"\b(?:absent|free\s*of)\b",
            r"\b(?:no\s+evidence\s+of|no\s+sign\s+of|no\s+history\s+of)\b",
            r"\b(?:unremarkable\s*(?:for)?)\b",
            r"\b(?:nah?i|nahin|koi\s+nah?i|bina)\b"
        ]

        # 2. Post-negation triggers (negates preceding entity in clause)
        self.post_negation_triggers = [
            r"\b(?:unlikely)\b",
            r"\b(?:free)\b",  # e.g., pain-free, symptom-free
            r"-free\b",
            r"\b(?:resolved|ceased)\b",
            r"\b(?:negative)\b",
            r"\b(?:was\s+ruled\s+out|ruled\s+out)\b",
            r"\b(?:nah?i|nahin)\s*(?:hai|tha|thi|the|hona|aa\s*rah[aei]|ho\s*rah[aei]|hua|hui)?\b"
        ]

        # 3. Pseudo-negation phrases (phrases containing negation words that do NOT negate the finding)
        self.pseudo_negation_phrases = [
            r"\bno\s+further\b",
            r"\bno\s+increase\b",
            r"\bnot\s+only\b",
            r"\bnot\s+cause\b",
            r"\bnot\s+surprising\b",
            r"\bwithout\s+difficulty\b",
            r"\bwithout\s+delay\b"
        ]

        # 4. Uncertainty / Hedging triggers
        self.uncertainty_triggers = [
            r"\b(?:may|might|could|possible|possibly)\b",
            r"\b(?:query|\?|suspected|suspicion\s+of)\b",
            r"\b(?:evaluating\s+for|assessing\s+for|consider)\b",
            r"\b(?:cannot\s+exclude|not\s+excluded)\b",
            r"\b(?:potential|probable|likely)\b",
            r"\b(?:suggestive\s+of|suggests?)\b",
            r"\b(?:may\s+have|may\s+be|may\s+die)\b",
            r"\b(?:shayad|lagta\s+hai|ho\s+sakta\s+hai|shak\s+hai|sandeh)\b"
        ]

        # 5. Historical / Past temporality triggers
        self.historical_triggers = [
            r"\b(?:history\s+of|hx\s+of|background\s+of)\b",
            r"\b(?:k\s*[\/\.]?\s*c\s*[\/\.]?\s*o|kco|known\s+case\s+of)\b",
            r"\b(?:past|previous|previously|prior\s+to)\b",
            r"\b(?:yesterday|earlier|former)\b",
            r"\b(?:\d+\s+(?:days?|weeks?|months?|years?)\s+ago)\b",
            r"\b(?:for\s+the\s+last\s+\d+\s+years)\b",
            r"\b(?:since\s+childhood)\b",
            r"\b(?:pehle\s+se|pehle|puran[ai]|pichh?le)\b",
            r"\b(?:kal)\s*(?:se|ko|raat|subah|shaam)?\b",
            r"\b(?:hui\s+thi|hua\s+tha|aayi\s+thi|aaya\s+tha|hota\s+tha|hoti\s+thi|hote\s+the|hue\s+the|tha|thi)\b"
        ]

        # 6. Planned / Future temporality triggers
        self.planned_triggers = [
            r"\b(?:planned\s+for|is\s+planned\s+for)\b",
            r"\b(?:scheduled\s+for|booked\s+for)\b",
            r"\b(?:to\s+be\s+arranged|needs\s+another)\b",
            r"\b(?:tomorrow|next\s+shift|later|soon)\b",
            r"\b(?:is\s+for|awaiting|pending)\b",
            r"\b(?:supposed\s+to\s+have)\b",
            r"\b(?:test\s+for|for\s+test|testing|ordered?|requested?)\b",
            r"\b(?:have\s+to\s+come|meet(?:\s+me)?\s+after|come\s+after|follow[- ]?up\s+after)\b"
        ]

        # 7. Conjunctions / Scope termination markers
        self.scope_termination_pattern = re.compile(
            r"\b(?:but|however|although|yet|except|aside\s+from|secondary\s+to|caused\s+by|due\s+to|lekin|magar|kintu)\b|[,;.!]",
            re.IGNORECASE
        )

        # Protected abbreviations for robust sentence splitting
        self.abbr_pattern = re.compile(
            r"\b(Dr|Mr|Mrs|Ms|vs|eg|ie|St|approx|temp|hr|min|yr|yrs|obs|bgl|gcs)\.",
            re.IGNORECASE
        )

    def split_sentences_protected(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Splits text into sentences while strictly protecting clinical abbreviations
        and decimal numbers from accidental splitting. Returns (sentence_text, start_char, end_char).
        """
        if not text:
            return []

        # Replace protected abbreviation periods and decimal points with length-preserving 1-char tokens
        abbr_token = "\uE000"
        dec_token = "\uE001"
        safe = self.abbr_pattern.sub(lambda m: m.group(1) + abbr_token, text)
        
        # Also protect decimal numbers (e.g. 12.5) with exact 1-to-1 character length
        safe = re.sub(r'(\d+)\.(\d+)', r'\g<1>' + dec_token + r'\g<2>', safe)

        pattern = re.compile(r'([^.!?]+(?:[.!?]+|$))', re.MULTILINE)
        sentence_spans = []

        for match in pattern.finditer(safe):
            orig_match = match.group()
            # Restore protected characters
            restored_raw = orig_match.replace(abbr_token, ".").replace(dec_token, ".")
            lead = len(restored_raw) - len(restored_raw.lstrip())
            trail = len(restored_raw) - len(restored_raw.rstrip())
            restored = restored_raw.strip()
            if restored:
                s_start = match.start() + lead
                s_end = match.end() - trail
                sentence_spans.append((restored, s_start, s_end))

        if not sentence_spans and text:
            sentence_spans.append((text, 0, len(text)))

        return sentence_spans

    def analyze_assertion(self, entity_text: str, start_char: int, end_char: int, full_text: str) -> Dict[str, Any]:
        """
        Analyzes the clinical assertion and temporality of an entity span in its clause context.
        """
        # Find sentence containing span
        sentences = self.split_sentences_protected(full_text)
        sent_text = full_text
        sent_start = 0

        for s_text, s_start, s_end in sentences:
            if s_start <= start_char <= s_end:
                sent_text = s_text
                sent_start = s_start
                break

        # Clause relative offsets
        rel_start = max(0, start_char - sent_start)
        rel_end = max(rel_start, end_char - sent_start)

        # Pre-entity and post-entity windows in the sentence (up to 60 characters)
        pre_text = sent_text[:rel_start]
        post_text = sent_text[rel_end:]

        # Check for immediate compound suffix negation like "pain-free"
        if re.search(r'^-free\b', post_text, re.IGNORECASE) or entity_text.lower().endswith('-free'):
            return {
                "assertion": "Negated",
                "temporality": "Current",
                "cue": "-free",
                "is_negated": True,
                "is_uncertain": False,
                "is_historical": False,
                "is_planned": False
            }

        # Check pseudo-negation phrases in pre-text
        for pnp in self.pseudo_negation_phrases:
            pre_text = re.sub(pnp, " ", pre_text, flags=re.IGNORECASE)

        # Split pre-text by scope termination triggers (take the closest clause)
        clause_splits = list(self.scope_termination_pattern.finditer(pre_text))
        if clause_splits:
            closest_termination = clause_splits[-1].end()
            active_pre_window = pre_text[closest_termination:]
        else:
            active_pre_window = pre_text

        # Active post window (up to first scope terminator)
        post_split = self.scope_termination_pattern.search(post_text)
        active_post_window = post_text[:post_split.start()] if post_split else post_text

        # 1. Determine Assertion
        assertion = "Affirmative"
        cue = None

        # Check Pre-negation in active clause
        for neg_pat in self.pre_negation_triggers:
            m = re.search(neg_pat, active_pre_window, re.IGNORECASE)
            if m:
                assertion = "Negated"
                cue = m.group(0)
                break

        # Check Post-negation if not already negated
        if assertion == "Affirmative":
            for neg_pat in self.post_negation_triggers:
                m = re.search(neg_pat, active_post_window, re.IGNORECASE)
                if m:
                    assertion = "Negated"
                    cue = m.group(0)
                    break

        # Check Uncertainty / Hedging if not negated
        if assertion == "Affirmative":
            for unc_pat in self.uncertainty_triggers:
                m = re.search(unc_pat, active_pre_window, re.IGNORECASE) or re.search(unc_pat, active_post_window, re.IGNORECASE)
                if m:
                    assertion = "Possible"
                    cue = m.group(0)
                    break

        # 2. Determine Temporality
        temporality = "Current"
        temp_cue = None

        # Check Planned / Future
        for plan_pat in self.planned_triggers:
            m = re.search(plan_pat, active_pre_window, re.IGNORECASE) or re.search(plan_pat, active_post_window, re.IGNORECASE)
            if m:
                temporality = "Planned"
                temp_cue = m.group(0)
                break

        # Check Historical if not planned
        if temporality == "Current":
            for hist_pat in self.historical_triggers:
                m = re.search(hist_pat, active_pre_window, re.IGNORECASE) or re.search(hist_pat, active_post_window, re.IGNORECASE)
                if m:
                    temporality = "Historical"
                    temp_cue = m.group(0)
                    break

        return {
            "assertion": assertion,
            "temporality": temporality,
            "cue": cue or temp_cue or "Direct statement",
            "is_negated": (assertion == "Negated"),
            "is_uncertain": (assertion == "Possible"),
            "is_historical": (temporality == "Historical"),
            "is_planned": (temporality == "Planned")
        }

# Global singleton instance
clinical_context_extractor = ClinicalContextExtractor()
