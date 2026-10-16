IMAGE ?= tier-review

.PHONY: build test install dev-test

build:  ## build the CLI image
	docker build --target runtime -t $(IMAGE) .

test:  ## run the unit tests in Docker
	docker build -q --target test -t $(IMAGE)-tests . > /dev/null
	docker run --rm $(IMAGE)-tests

install:  ## install the package and its dev extras into the current Python env
	pip install -e ".[dev]"

dev-test:  ## run the unit tests in the current Python env (after make install)
	pytest -q
