.PHONY: setup new report doctor test lint

setup:
	python -m venv .venv
	.venv/bin/python -m pip install -e ".[dev,pdf]"

new:
	@test -n "$(MEETING)" || (echo "Use: make new MEETING=YYYY-MM-DD"; exit 2)
	.venv/bin/treasurer-flash-report init $(MEETING)

report:
	@if test -n "$(MEETING)"; then \
		.venv/bin/treasurer-flash-report report meetings/$(MEETING); \
	else \
		.venv/bin/treasurer-flash-report; \
	fi

doctor:
	@if test -n "$(MEETING)"; then \
		.venv/bin/treasurer-flash-report doctor meetings/$(MEETING); \
	else \
		.venv/bin/treasurer-flash-report doctor; \
	fi

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/python -m ruff check .
