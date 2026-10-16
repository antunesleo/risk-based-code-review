BASE ?= HEAD
COMPOSE := docker compose

.PHONY: build up test map review tool-test demo

build:
	$(COMPOSE) build

up:  ## serve the helpdesk on :$${HELPDESK_PORT:-8000}
	$(COMPOSE) up helpdesk

test:  ## run the helpdesk suite
	$(COMPOSE) run --rm coverage-map pytest -q

map:  ## rebuild the line -> tests -> tier map from the working tree
	$(COMPOSE) run --rm coverage-map

review: map  ## which review tier does the working-tree diff (vs $(BASE)) need?
	BASE=$(BASE) $(COMPOSE) run --rm tier-review

tool-test:  ## unit tests of tier-review itself
	$(COMPOSE) run --rm tier-review-tests

demo:  ## apply each demo scenario, classify it, revert it
	./scripts/demo.sh
