.PHONY: report doctor test lint

report:
	.venv/bin/treasurer-flash-report

doctor:
	.venv/bin/treasurer-flash-report doctor

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/python -m ruff check .
