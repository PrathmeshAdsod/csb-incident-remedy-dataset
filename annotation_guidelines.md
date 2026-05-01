# CSB Incident-to-Systemic-Remedy Gold Dataset — Annotation Guidelines

## Purpose
This document defines the rules for annotating, reviewing, and completing rows in the CSB Gold Dataset. Follow these guidelines to ensure gold-quality, evidence-grounded labeling.

---

## Field Definitions

### `row_id`
A unique stable identifier generated as `csb_{incident_id}_{rec_id}`. If no stable IDs exist, use `csb_{hash8}_{index}`.

### `incident_id`
CSB's internal incident identifier when available (e.g., from the URL slug or recommendation number prefix). Example: `2010-08-I-WA`.

### `incident_title`
The official title of the incident as stated on the CSB incident page or report. Do NOT paraphrase.

### `incident_date`
ISO 8601 format: `YYYY-MM-DD`. If only year/month is known, use `YYYY-MM-01` and note partial date in `notes`. Leave `null` if unknown.

### `facility_name`
Exact name of the facility as stated in the source. Do not infer.

### `facility_type`
Select from taxonomy. If ambiguous between two types, select the more specific one and note in `notes`.

### `location`
City, State format preferred. Use source text directly.

### `hazard_type`
Select from taxonomy. Multiple hazard types are possible — select the **primary** hazard that caused the incident.

### `incident_summary`
Concise factual summary of the incident, derived directly from source text. Max 300 words. Must be traceable to `source_incident_url`.

### `root_cause_text`
Exact or near-exact text from the source document describing the root cause or key finding. Do NOT paraphrase unless the source uses indirect language, in which case note it.

### `primary_root_cause_label`
Select **one** label from the `primary_root_cause_label` taxonomy. This should represent the single most critical systemic cause.

**Disambiguation rules:**
- If the finding mentions "lack of hazard review" or "PHA not performed" → `process_hazard_analysis_failure`
- If about equipment corrosion, wear, or failure → `mechanical_integrity_failure`
- If about LOTO or isolation procedure → `maintenance_isolation_failure`
- If about combustible dust not recognized → `dust_hazard_management_failure`
- If about alarm floods or alarm disabled → `alarm_management_failure`
- If about no training or inadequate training for specific task → `training_competency_failure`
- Use `other` only as last resort; add note.

### `contributing_factors_text`
Extracted text listing secondary or contributing factors from the source. May be null.

### `contributing_factor_labels`
JSON array of labels from the `contributing_factor_labels` taxonomy. Multiple allowed. Empty array `[]` if none identified.

### `recommendation_id`
CSB's official recommendation number (e.g., `2010-08-I-WA-R1`). Extract from source. Null if not explicitly stated.

### `recommendation_text`
Exact recommendation text from the CSB source. Do NOT paraphrase. If the recommendation spans multiple sentences, include all of them.

### `recommendation_target`
The named entity that the recommendation is directed to (e.g., "OSHA", "Tesoro Refining", "API").

### `recommendation_target_type`
Select from taxonomy:
- `operator` — the facility/company operating the site
- `regulator` — OSHA, EPA, state agencies, etc.
- `standards_body` — API, NFPA, ASTM, etc.
- `industry_association` — ACC, AFPM, etc.
- `emergency_response_org` — fire departments, HAZMAT teams
- `manufacturer` — equipment/chemical manufacturers
- `other` — if none of the above fit clearly

### `recommendation_theme_label`
Select **one** label from `recommendation_theme_label` taxonomy. Captures the systemic remedy type.

### `recommendation_status`
Normalized status from taxonomy. Map raw status text:
- "Closed - Acceptable Action" → `closed_acceptable_action`
- "Closed - Acceptable Alternate Action" → `closed_acceptable_alternate_action`
- "Closed - No Longer Applicable" → `closed_no_longer_applicable`
- "Closed - Unacceptable Action" → `closed_unacceptable_action`
- "Open" → `open`
- "Superseded" → `superseded`
- Unknown or missing → `unknown`

### `recommendation_status_raw`
Original status string from the source page. Preserve exactly.

### Evidence Spans
Evidence spans are short (1-4 sentence) verbatim or near-verbatim excerpts from the source document that directly support the field they accompany.

**Good evidence span:**
> "The investigation found that the facility had not conducted a process hazard analysis (PHA) for the hydrogen system despite operating it for over 10 years."

**Bad evidence span (too vague):**
> "There were safety problems at the plant."

**Bad evidence span (fabricated/paraphrased without label):**
> "The company ignored safety rules." ← this is an inference, not a direct quote

#### `incident_evidence_span`
Supporting text for the incident summary and context. From the incident page.

#### `cause_evidence_span`
Supporting text for root cause. Must directly mention the causal factor.

#### `recommendation_evidence_span`
Must contain the recommendation text itself or text immediately surrounding it on the source page.

#### `status_evidence_span`
Text from the status page confirming the recommendation status. May be null if status page is not available.

---

## Handling Multiple Recommendations Per Incident

Create **one row per recommendation**. If an incident has 5 recommendations, it produces 5 rows.
- `row_id` must differ for each row (append `_R1`, `_R2`, etc.)
- `incident_id`, `incident_title`, `incident_summary`, and incident-level fields are repeated.
- Each recommendation-level field is unique per row.
- This is correct behavior — it is not duplication.

---

## Confidence Scoring

| Score Range | Meaning |
|---|---|
| 0.90 – 1.00 | Field directly extracted from explicit, structured source text |
| 0.75 – 0.89 | Confidently inferred from strong textual evidence |
| 0.50 – 0.74 | Partial match or weak phrasing; some uncertainty |
| < 0.50 | Low confidence; must set `needs_manual_review = true` |

Assign a **single score** per row reflecting the weakest-confidence field in the row.

---

## Handling Ambiguous Root Causes

1. If multiple root causes are cited, select the one described as **primary** or **key** in the source.
2. If the source does not distinguish, select the cause most directly linked to the physical event sequence.
3. Add remaining causes as `contributing_factor_labels`.
4. If genuinely ambiguous, set confidence to 0.60–0.74 and `needs_manual_review = true`.

---

## Resolving Conflicting Source Text

- If the incident page and the PDF report give different root cause descriptions, **prefer the final report** as it is the authoritative source.
- Note the conflict in the `notes` field.
- Set `needs_manual_review = true`.

---

## Review Queue Criteria

A row goes to `review_queue.csv` when ANY of the following is true:
- `annotation_confidence < 0.50`
- `recommendation_status` is `unknown`
- `primary_root_cause_label` is `null`
- `recommendation_text` is null or less than 20 characters
- Evidence spans are null when labels are non-null
- Source URL is null or returns a 404
