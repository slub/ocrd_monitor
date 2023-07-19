TAGNAME ?= ghcr.io/slub/ocrd_monitor
SHELL = /bin/bash

build:
	docker build --tag $(TAGNAME) \
	--build-arg VCS_REF=`git rev-parse --short HEAD` \
	--build-arg BUILD_DATE=`date -u +"%Y-%m-%dT%H:%M:%SZ"` \
	.

pull:
	docker pull $(TAGNAME)


build-browse-ocrd-docker:
	docker build -t ocrd-browser:latest -f docker-browse-ocrd/Dockerfile docker-browse-ocrd


define HELP
cat <<"EOF"
Targets:
	- build	(re)compile Docker image from sources
	- pull  (re)pull Docker image from repository
	- run	start up Docker container
	- test	run some local regression tests

Variables:
	- TAGNAME		name of Docker image to build/run
	  currently: "$(TAGNAME)"
	- MONITOR_PORT_WEB	TCP port for the (host-side) web server
	  currently: $(MONITOR_PORT_WEB)
	- MANAGER_KEY		SSH key file to mount (for the Controller client)
	  currently: "$(MANAGER_KEY)"
	- MANAGER_DATA		host directory to mount into `/data` (shared with Manager)
	  currently: "$(MANAGER_DATA)"
	- MANAGER_WORKFLOWS	host directory to mount into `/workflows` (shared with Manager)
	  currently: "$(MANAGER_WORKFLOWS)"
	- NETWORK		Docker network to use (manage via "docker network")
	  currently: $(NETWORK)
	- CONTROLLER_HOST	network address for the Controller client
				(must be reachable from the container network)
	  currently: $(CONTROLLER_HOST)
	- CONTROLLER_PORT_SSH	network port for the Controller client
				(must be reachable from the container network)
	  currently: $(CONTROLLER_PORT_SSH)
EOF
endef
export HELP
help: ; @eval "$$HELP"

MANAGER_KEY ?= $(firstword $(filter-out %.pub,$(wildcard $(HOME)/.ssh/id_*)))
MANAGER_DATA ?= $(CURDIR)
MANAGER_WORKFLOWS ?= $(CURDIR)
MONITOR_PORT_WEB ?= 5000
NETWORK ?= bridge
CONTROLLER_HOST ?= $(shell dig +short $$HOSTNAME)
CONTROLLER_PORT_SSH ?= 8022
run: $(DATA)
	docker run -d --rm \
	-h ocrd_monitor \
	--name ocrd_monitor \
	--network=$(NETWORK) \
	-p $(MONITOR_PORT_WEB):5000 \
	-v ${MANAGER_KEY}:/id_rsa \
	--mount type=bind,source=$(MANAGER_KEY),target=/id_rsa \
	-v $(MANAGER_DATA):/data \
	-v $(MANAGER_WORKFLOWS):/workflows \
	-v shared:/run/lock/ocrd.jobs \
	-e CONTROLLER=$(CONTROLLER_HOST):$(CONTROLLER_PORT_SSH) \
	-e MONITOR_PORT_LOG=${MONITOR_PORT_LOG} \
	$(TAGNAME)

test:
	{ echo set -e; \
	echo cd /usr/local/ocrd-monitor/; \
	echo pip install nox; \
	echo "nox"; } | \
	docker run --rm -i \
	$(TAGNAME) bash

.PHONY: build pull run help test
