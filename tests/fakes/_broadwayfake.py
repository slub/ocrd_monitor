import uvicorn
from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

from ._backgroundprocess import BackgroundProcess


BROWSERFAKE_HEADER = "OCRD BROWSER"


html_template = """
<!DOCTYPE html>
<html lang="en">
<body>
    <h1>OCRD BROWSER</h1>
    <p>{workspace}</p>
</body>
</html>
"""


def _create_app(workspace: str) -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def index() -> Response:
        return HTMLResponse(content=html_template.format(workspace=workspace))

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
    uvicorn.run(app, host="localhost", port=7000)


def broadway_fake(workspace: str) -> BackgroundProcess:
    process = BackgroundProcess(_run_app, workspace)

    return process
