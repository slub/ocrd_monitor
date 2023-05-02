# OCR-D Monitor

> Web frontend for ocrd_manager

[![CI Test](https://github.com/slub/ocrd_monitor/actions/workflows/test-ci.yml/badge.svg)](https://github.com/slub/ocrd_monitor/actions/workflows/test-ci.yml)
[![CD Github Package](https://github.com/slub/ocrd_monitor/actions/workflows/publish.yml/badge.svg)](https://github.com/slub/ocrd_monitor/actions/workflows/publish.yml)

The OCR-D Monitor web application allows monitoring the progress and results of OCR-D jobs.
It is intended to be used together with the setup found in the [ocrd_kitodo repository](https://github.com/slub/ocrd_kitodo).
You can find detailed instructions on how to deploy the Kitodo/OCR-D stack (entirely or partially) [there](https://slub.github.io/ocrd_kitodo).

The Monitor web server features
- (intermediate) results for all current document workspaces (via [OCR-D Browser](https://github.com/hnesk/browse-ocrd))
- a live log viewer
- a live job viewer
- :construction: workflow editor

## Running

In order to work properly, the following **environment variables** must be set:

| Variable            | Description                                                                      |
| ------------------- | -------------------------------------------------------------------------------- |
| CONTROLLER_HOST     | Hostname of the OCR-D Controller                                                 |
| CONTROLLER_PORT_SSH | Port on the OCR-D Controller host that allows a SSH connection                   |
| MANAGER_DATA        | Path to the OCR-D workspaces on the host                                         |
| MANAGER_WORKFLOWS   | Path to the OCR-D workflows on the host                                          |
| MANAGER_KEY         | Path to a private key that can be used to authenticate with the OCR-D Controller |
| MONITOR_PORT_WEB    | The port at which the OCR-D Monitor will be available on the host                |
| MONITOR_PORT_LOG    | The port at which the Dozzle logs will be available on the host                  |

### Docker Compose

Ideally, you use the services defined in `docker-compose.yml` by just doing:

    docker compose up -d
    docker compose down

### Makefile

Alternatively, there is a Makefile with stand-alone Docker calls.

Build or pull the Docker image:

    make build # or docker build
    make pull # or docker pull ghcr.io/slub/ocrd_monitor

Then run the container – providing the same variables as above:

    make run # or docker run...

You can then open `http://localhost:5000` in your browser (or the server host name and your custom `$MONITOR_PORT_WEB`).


## Testing

The tests are intended to be run outside of a container,
because some of them will set up containers themselves.
You need to have a Python version >= 3.11 installed on your system.

### via nox

The easiest way to run the tests is via [nox](https://nox.readthedocs.io/):

1. [Install nox](https://nox.readthedocs.io/) – either via `pipx` or `pip` (system-wide, user-wide, or in a venv).
2. Run

        nox

This will install dependencies and virtualenv for tests,
and subsequently run them.

### via mypy and pytest

1. Install package along with runtime and dev dependencies
   via `pip` or a project management tool like `pdm`

        pip install -e ".[dev]"
        # ... or ...
        pdm install -G dev

2. Run

        mypy --strict ocrdbrowser ocrdmonitor tests
        pytest -vv tests

### via make

Besides targets for [stand-alone Docker calls at runtime](#Makefile),
the Makefile also allows testing the Docker image. It deactivates
those tests which cannot be run from within a container.

Run

    make test


## General overview

![](docs/img/monitor-overview.png)

## Overview of workspaces endpoint functionality

When opening a workspace OCR-D Monitor will launch a new `OcrdBrowser` instance (either as a Docker container or a sub process).
From there on it will proxy requests to the `/workspaces/view/<path>` endpoint to the browser instance.

![](docs/img/workspaces-endpoint.png)
