.PHONY: selftest test validate-example

selftest:
	PYTHONPATH=src python scripts/selftest.py

test:
	PYTHONPATH=src pytest

validate-example:
	PYTHONPATH=src python -m asiep_validator examples/valid_chatbot_improvement.json
