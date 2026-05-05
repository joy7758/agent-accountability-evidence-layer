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
