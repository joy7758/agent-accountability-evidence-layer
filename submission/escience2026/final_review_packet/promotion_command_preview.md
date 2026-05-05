# Promotion Command Preview

Do not run this command automatically.

Replace `<HUMAN_AUTHOR_NAME>` before use.

Run only after the human author has checked the PDF, deadline, repository policy, license, sensitive scan, AI disclosure, and final PDF.

This command will create final gate files in `submission/escience2026/`:

```bash
PYTHONPATH=src python scripts/promote_recommended_gates.py \
  --human-confirm-final-gates \
  --approved-by "<HUMAN_AUTHOR_NAME>" \
  --confirm-deadline \
  --confirm-repository-policy \
  --confirm-license \
  --confirm-sensitive-scan \
  --confirm-layout \
  --confirm-ai-disclosure \
  --confirm-final-pdf
```
