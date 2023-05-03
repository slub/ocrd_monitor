from pathlib import Path
import uvicorn
from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from tests.testdoubles._browserspy import html_template
from ._backgroundprocess import BackgroundProcess


def _create_app(workspace: str) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def index() -> Response:
        return HTMLResponse(content=html_template)

    @app.websocket("/socket")
    async def socket(websocket: WebSocket) -> None:
        await websocket.accept("broadway")
        try:
            while True:
                echo = await websocket.receive_bytes()
                await websocket.send_bytes(echo)
        except WebSocketDisconnect:
            pass

    return app


def _run_app(workspace: str) -> None:
    app = _create_app(workspace)

    host = "localhost"
    if Path("/.dockerenv").exists():
        host = "127.0.0.1"

    uvicorn.run(app, host=host, port=7000)


def broadway_fake(workspace: str) -> BackgroundProcess:
    process = BackgroundProcess(_run_app, workspace)

    return process
