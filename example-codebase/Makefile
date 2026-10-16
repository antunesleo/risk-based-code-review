IMAGE ?= example-codebase
PORT ?= 8000

.PHONY: test up

test:  ## run the test suite in Docker (dev requirements install ../tier-review)
	docker build -q -f Dockerfile.test -t $(IMAGE)-tests .. > /dev/null
	docker run --rm $(IMAGE)-tests

up:  ## serve the helpdesk API on :$(PORT) (PORT=8089 make up)
	docker build -q -t $(IMAGE) . > /dev/null
	docker run --rm -p $(PORT):8000 $(IMAGE)
