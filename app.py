import asyncio
import time
import typing
import strawberry
from typing import Annotated, List, Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path
from pydantic import BaseModel

from fastapi import FastAPI, Form, File, UploadFile
from strawberry.fastapi import GraphQLRouter

class Item(BaseModel):
    name: str

class ProjectSummary(BaseModel):
    name: Union[str, None] = "project_name"
    layer_num: int = 0
    layer_height: float = 1.0
    printing_speed: float = 2.0
    non_printing_speed: float = 10.0
    extrusion_speed: float = 0.8

class Project(BaseModel):
    id: Union[str, None] = None
    name: Union[str, None] = None
    image: Union[str, None] = None
    summary: ProjectSummary = ProjectSummary()
    simulation_file: str = "/home/fangyi/Desktop/api_ws/sim_data.json"

def get_books():
    return [
        Book(
            title="The Great Gatsby",
            author="F. Scott Fitzgerald",
        ),
    ]

@strawberry.type
class Book:
    title: str
    author: str

"""
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello World"
"""
@strawberry.type
class Query:
    books: typing.List[Book] = strawberry.field(resolver=get_books)


schema = strawberry.Schema(Query)
graphql = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql, prefix="/graphql")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

img = "http://192.168.1.11:8000/project-card/1234"
projects = [Project(id="1234", name="SamplePrject1", image=img), Project(id="4567", name="SamplePrject2", image=img)]
project_repo = {"1234": projects[0], "4567": projects[1]}

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Accpeted connection:", websocket.url)
    count = 0
    try:
        while True:
            # await websocket.receive_text()
            data = f"Current count: {count}"
            print("Sending: ", data, " state: ", websocket.client_state)
            await websocket.send_text(f"Message text was: {data}")
            count = count + 1
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Disconnected")
    except Exception as e:
        print(">>>> [Exception]: ", e)
    print("=== Done ===")

@app.get("/projects")
async def list_projects(
) -> List[Project]:
    time.sleep(3)
    return projects

@app.get("/project-card/{project_id}")
async def project_card(project_id: str):
    img = "/home/fangyi/Desktop/api_ws/sample_model.webp"
    return FileResponse(img)

@app.get("/project-summary/{project_id}")
async def project_summary(project_id: str) -> ProjectSummary:
    summary = project_repo.get(project_id).summary
    return project_repo.get(project_id).summary

@app.get("/project-simulation/{project_id}")
async def project_sim_file(
    project_id: str
):
    proj = project_repo.get(project_id)

    def iterfile():
        with open(proj.simulation_file, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    headers = {"Content-Disposition": 'attachment; filename="sim_data.json"'}
    return StreamingResponse(iterfile(), headers=headers, media_type="application/json")

@app.post("/project")
async def create_project(
    project_name: Annotated[str, Form()],
    nozzle_width: Annotated[float, Form()],
    layer_height: Annotated[float, Form()],
    printing_speed: Annotated[float, Form()],
    non_printing_speed: Annotated[float, Form()],
    extrusion_speed: Annotated[float, Form()],
    image: Annotated[UploadFile, File()],
) -> dict:
    print("Project name: ", project_name)
    print("Image: ", image.filename)
    print("Type", image.content_type)
    PROJ_ROOT_DIR = Path("/home/fangyi/Desktop/api_ws")
    file_path = PROJ_ROOT_DIR / image.filename
    file_path.write_bytes(await image.read())
    return {"success": True}

@app.post("/uploadfile")
async def add_design_file(
    file: UploadFile,
) -> StreamingResponse:
    def iterfile():
        model_file_path = "/home/fangyi/Desktop/api_ws/fastapi_exp/sample3.json"
        with open(model_file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    headers = {"Content-Disposition": 'attachment; filename="model_data.json"'}
    return StreamingResponse(iterfile(), headers=headers, media_type="application/json")

@app.post("/joint", tags=["joint"])
async def send_joint_command(
    name: str,
    command: str,
) -> dict:
    print("Joint: ", name, " ", command)
    return {"success": True}

@app.get("/joint/{joint_name}", tags=["joint"])
async def get_joint_status(
    joint_name: str,
) -> dict:
    return {"status": 100}
