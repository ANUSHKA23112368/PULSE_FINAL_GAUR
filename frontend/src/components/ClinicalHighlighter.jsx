import React from 'react';

export function ClinicalHighlighter({ text, entities }) {
  if (!entities) return <div className="verbatim-text">{text}</div>;

  const spans = [];
  const addSpan = (ent, type, label) => {
    (ent.all_spans || [[ent.start_char, ent.end_char]]).forEach(s => {
      if (s && s[0] !== undefined) {
        spans.push({ start: s[0], end: s[1], type, label });
      }
    });
  };

  (entities.conditions || []).forEach(c => addSpan(c, 'condition', `Condition: ${c.normalized}`));
  (entities.symptoms || []).forEach(s => addSpan(s, 'symptom', `Symptom: ${s.normalized}`));
  (entities.medications || []).forEach(m => addSpan(m, 'medication', `Medication: ${m.normalized}`));
  (entities.investigations || []).forEach(i => addSpan(i, 'investigation', `Investigation: ${i.normalized}`));
  (entities.treatments || []).forEach(t => addSpan(t, 'treatment', `Treatment: ${t.normalized}`));
  (entities.measurements || []).forEach(ms => {
    if (ms.start_char !== undefined && ms.end_char !== undefined) {
      spans.push({ start: ms.start_char, end: ms.end_char, type: 'measurement', label: `Measurement: ${ms.type}` });
    }
  });

  spans.sort((a, b) => a.start - b.start);
  const nonOverlapping = [];
  let lastEnd = 0;
  for (const s of spans) {
    if (s.start >= lastEnd && s.start < s.end && s.end <= text.length) {
      nonOverlapping.push(s);
      lastEnd = s.end;
    }
  }

  const fragments = [];
  let currentIndex = 0;
  nonOverlapping.forEach((span, i) => {
    if (span.start > currentIndex) {
      fragments.push(text.substring(currentIndex, span.start));
    }
    fragments.push(
      <span key={i} className={`highlight-span ${span.type}`} title={span.label}>
        {text.substring(span.start, span.end)}
      </span>
    );
    currentIndex = span.end;
  });

  if (currentIndex < text.length) {
    fragments.push(text.substring(currentIndex));
  }

  return <div className="clinical-highlight-text">{fragments}</div>;
}
