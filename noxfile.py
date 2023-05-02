import nox


@nox.session(python=("3.11"))
def mypy(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("mypy", "--strict", "ocrdbrowser", "ocrdmonitor")


@nox.session(python=("3.11"))
def pytest(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.install("pytest-clarity")

    session.run("pytest", "-vv", "tests")
