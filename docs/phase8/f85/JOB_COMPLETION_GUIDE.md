# Job Completion Guide

1. Contractor: `POST /workspace/jobs/{job_id}/complete` with notes, declaration, and file evidence (via files API).
2. Reviewer: `POST /completions/{id}/review` with `approved`, `rejected`, or `additional_work_required`.
3. Job reaches `verified` only after approval review — never automatic.

Before/after photos should use existing secure upload flows linked to job completion records in follow-up work.
