import uvicorn
from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from tests.testdoubles._browserspy import html_template
from ._backgroundprocess import BackgroundProcess


FAKE_HOST_IP = "127.0.0.1"
FAKE_HOST_PORT = 8000
FAKE_HOST_ADDRESS = f"{FAKE_HOST_IP}:{FAKE_HOST_PORT}"


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
    uvicorn.run(app, host=FAKE_HOST_IP, port=FAKE_HOST_PORT)


def broadway_fake(workspace: str) -> BackgroundProcess:
    process = BackgroundProcess(_run_app, workspace)

    return process
