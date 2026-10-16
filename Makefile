BASE ?= HEAD
COMPOSE := docker compose

.PHONY: build up test map map-base review tool-test demo

build:
	$(COMPOSE) build

up:  ## serve the helpdesk on :$${HELPDESK_PORT:-8000}
	$(COMPOSE) up helpdesk

test:  ## run the example codebase suite
	$(COMPOSE) run --rm coverage-map pytest -q

map:  ## rebuild the line -> tests -> tier map from the working tree
	MAP=head $(COMPOSE) run --rm coverage-map

map-base:  ## rebuild the same map from a snapshot of $(BASE)
	rm -rf .tier-review/base && mkdir -p .tier-review/base
	git archive $(BASE) example-codebase | tar -x -C .tier-review/base
	MAP=base MAP_SRC=./.tier-review/base/example-codebase $(COMPOSE) run --rm coverage-map

review: map map-base  ## which review tier does the working-tree diff (vs $(BASE)) need?
	BASE=$(BASE) $(COMPOSE) run --rm tier-review

tool-test:  ## unit tests of tier-review itself (see tier-review/Makefile)
	$(MAKE) -C tier-review test

demo:  ## apply each demo scenario, classify it, revert it
	./scripts/demo.sh
