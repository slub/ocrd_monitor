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
	- MANAGER_DATA		host directory to mount into `/data` (shared with Manager)
	  currently: "$(MANAGER_DATA)"
	- MANAGER_WORKFLOWS	host directory to mount into `/workflows` (shared with Manager)
	  currently: "$(MANAGER_WORKFLOWS)"
	- NETWORK		Docker network to use (manage via "docker network")
	  currently: $(NETWORK)
EOF
endef
export HELP
help: ; @eval "$$HELP"

MANAGER_DATA ?= $(CURDIR)
MANAGER_WORKFLOWS ?= $(CURDIR)
MONITOR_PORT_WEB ?= 5000
NETWORK ?= bridge
run: $(DATA)
	docker run -d --rm \
	-h ocrd_monitor \
	--name ocrd_monitor \
	--network=$(NETWORK) \
	-p $(MONITOR_PORT_WEB):5000 \
	-v $(MANAGER_DATA):/data \
	-v $(MANAGER_WORKFLOWS):/workflows \
	-v shared:/run/lock/ocrd.jobs \
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
