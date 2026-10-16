BASE ?= HEAD
COMPOSE := docker compose

.PHONY: build up test catalog-tiers catalog-tiers-base review tool-test demo

build:
	$(COMPOSE) build

up:  ## serve the helpdesk on :$${HELPDESK_PORT:-8000}
	$(COMPOSE) up helpdesk

test:  ## run the example codebase suite
	$(COMPOSE) run --rm catalog-tiers pytest -q

catalog-tiers:  ## catalog line -> tests and test -> tier for the working tree
	CATALOG=head $(COMPOSE) run --rm catalog-tiers

catalog-tiers-base:  ## the same, for a snapshot of $(BASE)
	rm -rf .tier-review/base && mkdir -p .tier-review/base
	git archive $(BASE) example-codebase | tar -x -C .tier-review/base
	CATALOG=base CATALOG_SRC=./.tier-review/base/example-codebase $(COMPOSE) run --rm catalog-tiers

review: catalog-tiers catalog-tiers-base  ## classify the working-tree diff (vs $(BASE))
	BASE=$(BASE) $(COMPOSE) run --rm tier-review

tool-test:  ## unit tests of tier-review itself (see tier-review/Makefile)
	$(MAKE) -C tier-review test

demo:  ## apply each demo scenario, classify it, revert it
	./scripts/demo.sh
