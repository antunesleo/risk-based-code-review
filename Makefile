BASE ?= HEAD
FORMAT ?= text
CATALOGS := .tier-review
COMPOSE := docker compose --progress quiet
TIER_REVIEW := HOST_UID=$(shell id -u) HOST_GID=$(shell id -g) $(COMPOSE) run --rm tier-review

# `make tier-review -- <args>` passes <args> to the tier-review CLI in Docker. The `--`
# stops make from reading them as its own options; the rule below turns them into no-op
# goals so make does not try to build them.
ifeq (tier-review,$(firstword $(MAKECMDGOALS)))
  ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  .PHONY: $(ARGS)
  $(eval $(ARGS):;@:)
endif

.PHONY: build tier-review review demo

build:
	@$(COMPOSE) build

tier-review: build  ## run the CLI: make tier-review -- catalog --out .tier-review/head
	$(TIER_REVIEW) $(or $(ARGS),--help)

review: build  ## catalog working tree and $(BASE), classify the diff between them
	$(TIER_REVIEW) catalog --out $(CATALOGS)/head
	$(TIER_REVIEW) catalog --out $(CATALOGS)/base --ref $(BASE)
	$(TIER_REVIEW) classify --base $(BASE) --format $(FORMAT) \
		--catalog $(CATALOGS)/head --base-catalog $(CATALOGS)/base

demo: build  ## apply each demo scenario, classify it, revert it
	./scripts/demo.sh
