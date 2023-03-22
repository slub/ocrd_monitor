# OCR-D Monitor

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

The tests are intended to be run outside of a container, as some of them will set up containers themselves.
Therefore you need to have a Python version >= 3.9 installed on your system.

1. Install runtime and dev dependencies with `pip` or a project management tool like `pdm`

```bash
    pip install -e ".[dev]"
```

```bash
    pdm install -G dev
```

2. Run nox or pytest

```bash
    nox
```

```bash
    pytest tests
```

## General overview

![](docs/img/monitor-overview.png)

## Overview of workspaces endpoint functionality

When opening a workspace OCR-D Monitor will launch a new `OcrdBrowser` instance (either as a Docker container or a sub process).
From there on it will proxy requests to the `/workspaces/view/<path>` endpoint to the browser instance.

![](docs/img/workspaces-endpoint.png)
