PREFIX ?= /usr/local
SHAREDIR := $(PREFIX)/share/linux-ops-toolkit
.DEFAULT_GOAL := help

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

lint: ## ShellCheck + ruff
	shellcheck -x bin/* lib/*.sh tests/integration/*.sh
	ruff check . && ruff format --check .

test: ## bats + pytest
	bats tests/bats
	pytest

integration: ## Run bootstrap-server in Ubuntu and Debian containers
	for img in ubuntu:22.04 ubuntu:24.04 debian:12; do tests/integration/run.sh $$img || exit 1; done

install: ## Install scripts to $(PREFIX)/bin (needs root)
	install -d $(SHAREDIR)/bin $(SHAREDIR)/lib $(PREFIX)/bin
	install -m 0755 bin/* $(SHAREDIR)/bin/
	install -m 0644 lib/common.sh $(SHAREDIR)/lib/
	for f in bin/*; do ln -sf $(SHAREDIR)/$$f $(PREFIX)/bin/$$(basename $$f); done

.PHONY: help lint test integration install
