.DEFAULT_GOAL := help

MANIFEST ?= target/manifest.json
AUDIT_OUT ?= gap_finder/DOCS_AUDIT.md
PORT      ?= 8080

.PHONY: help audit serve install

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Variables:"
	@echo "    MANIFEST=$(MANIFEST)"
	@echo "    AUDIT_OUT=$(AUDIT_OUT)"
	@echo "    PORT=$(PORT)"

install: ## Install Python dependencies
	pip3 install -r requirements.txt

audit: ## Run the Documentation Gap Finder and generate DOCS_AUDIT.md
	python3 gap_finder/gap_finder.py --manifest $(MANIFEST) --output $(AUDIT_OUT)
	@echo ""
	@echo "  ✅ Audit complete. Open $(AUDIT_OUT) to view results."

serve: ## Start local HTTP server for the governance dashboard
	@echo "  🌐 Dashboard: http://localhost:$(PORT)/dashboard.html"
	python3 -m http.server $(PORT)

open: ## Open the governance dashboard in the browser (macOS)
	open http://localhost:$(PORT)/dashboard.html
