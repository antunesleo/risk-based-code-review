BASE ?= HEAD
FORMAT ?= text
COMPOSE := docker compose

.PHONY: build catalog-tiers catalog-tiers-base review demo

build:
	$(COMPOSE) build

catalog-tiers:  ## catalog line -> tests and test -> tier for the working tree
	CATALOG=head $(COMPOSE) run --rm catalog-tiers

catalog-tiers-base:  ## the same, for a snapshot of $(BASE)
	rm -rf .tier-review/base && mkdir -p .tier-review/base
	git archive $(BASE) example-codebase | tar -x -C .tier-review/base
	CATALOG=base CATALOG_SRC=./.tier-review/base/example-codebase $(COMPOSE) run --rm catalog-tiers

review: catalog-tiers catalog-tiers-base  ## classify the working-tree diff (vs $(BASE))
	BASE=$(BASE) FORMAT=$(FORMAT) $(COMPOSE) run --rm tier-review

demo:  ## apply each demo scenario, classify it, revert it
	./scripts/demo.sh
