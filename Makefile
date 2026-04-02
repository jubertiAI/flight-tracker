TRACKER_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON := $(TRACKER_DIR).venv/bin/python3

.PHONY: check schedule unschedule history install

## Run a single price check now
check:
	$(PYTHON) $(TRACKER_DIR)tracker.py

## Install Python dependencies
install:
	$(TRACKER_DIR).venv/bin/pip install -r $(TRACKER_DIR)requirements.txt

## Show price history
history:
	@if [ -f $(TRACKER_DIR)price_history.csv ]; then \
		column -t -s, $(TRACKER_DIR)price_history.csv; \
	else \
		echo "No price history yet. Run 'make check' first."; \
	fi

## Install cron job — 6 runs/day at Buenos Aires times (UTC-3):
## 8am, 11am, 1pm, 4pm, 7pm, 10pm → UTC: 11:00, 14:00, 16:00, 19:00, 22:00, 01:00
schedule:
	@(crontab -l 2>/dev/null | grep -v "flight-tracker/tracker.py"; \
	  echo "0 11,14,16,19,22,1 * * * . $$HOME/.zshrc && cd $(TRACKER_DIR) && $(PYTHON) $(TRACKER_DIR)tracker.py >> $(TRACKER_DIR)cron.log 2>&1") | crontab -
	@echo "Cron job installed. Verify with: crontab -l"

## Remove the flight tracker cron job
unschedule:
	@(crontab -l 2>/dev/null | grep -v "flight-tracker/tracker.py") | crontab -
	@echo "Cron job removed."
