import random
import asyncio
import time
import typing
import strawberry
from enum import Enum
from typing import Annotated, List, Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from pydantic import BaseModel

from fastapi import FastAPI, Form, File, UploadFile
from strawberry.fastapi import GraphQLRouter

class Item(BaseModel):
    name: str

class MaterialState(str, Enum):
    low = "low"
    ok = "ok"
    unknown = "unknown"

class MaterialStatus(BaseModel):
    state: MaterialState = MaterialState.unknown
    hi_level: int = 0
    lo_level: int = 0
    data: List[int] = [400, 400, 400, 400, 400]

class SystemStatus(BaseModel):
    material_status: MaterialStatus = MaterialStatus()
    nozzle_distance: float = 0.0

class TaskStatus(str, Enum):
    ready = "ready"
    waiting = "waiting"
    paused = "paused"
    printing = "printing"

class Task(BaseModel):
    name: str = "SampleProject0"
    from_layer: int = 1
    to_layer: int = 100
    status: TaskStatus = TaskStatus.ready
    task_progress: float = 0.0
    current_layer: int = 1
    remaining_time: str = "0 hr 0 m"
    applied_extrusion_speed: float = 1.0

class PrintingStatus(BaseModel):
    task_queue: List[Task] = []

class ExtrusionStatus(BaseModel):
    on: bool = False
    speed: float = 0.8

class ExtrusionSettings(BaseModel):
    extrude_on: bool = False
    extrusion_speed: float = 0.8
    ccw_speed: float = 1.0
    cw_speed: float = 0.55
    motion_delay: float = 0.6

class MaterialSettings(BaseModel):
    auto_refill_enabled: bool = False
    hi_level: int = 435
    lo_level: int = 400

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
    status: str = "Completed"
    progress: float = 1.0
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

img = "http://127.0.0.1:8000/project-card/1234"
projects = [Project(id="1234", name="SamplePrject1", image=img), Project(id="4567", name="SamplePrject2", image=img, status="Processing", progress=0.6)]
project_repo = {"1234": projects[0], "4567": projects[1]}

extrude_settings = ExtrusionSettings()
material_settings = MaterialSettings()

task_queue = [
    Task(name="SampleProject0",
         from_layer=0,
         to_layer=100,
         current_layer=3,
         status=TaskStatus.ready,
         task_progress=0.2,
         applied_extrusion_speed=0.8),
    Task(name="SampleProject1", from_layer=10, to_layer=100, status=TaskStatus.waiting, applied_extrusion_speed=1.1),
]

system_status = SystemStatus()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.websocket("/printing-status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Accpeted connection:", websocket.url)
    status = PrintingStatus()
    status.task_queue = task_queue
    try:
        while True:
            cur_task = status.task_queue[0]
            cur_task.task_progress += 0.05
            if cur_task.task_progress > 1.0:
                cur_task.task_progress = 0
            data = jsonable_encoder(status)
            # print("Sending:")
            # print(data)
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Status client disconnected")
    except Exception as e:
        print(">>>> [Exception]: ", e)
        print("=== Done Printing Status ===")

@app.websocket("/system-status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Accpeted connection:", websocket.url)
    try:
        while True:
            system_status.nozzle_distance = 10 + random.random()
            system_status.material_status.data.pop()
            system_status.material_status.data.append(420 + 10 * random.random())
            data = jsonable_encoder(system_status)
            print("Sending:")
            print(data)
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Status client disconnected")
    except Exception as e:
        print(">>>> [Exception]: ", e)
        print("=== Done System Status ===")

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
    proj2 = project_repo.get("4567")
    proj2.progress += 0.05
    if proj2.progress > 1.0:
        proj2.progress = 0.0
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

@app.get("/extrusion/settings", tags=["extrusion"])
async def get_extrusion_settings(
) -> ExtrusionSettings:
    print("Current extrusion settings: ")
    print(extrude_settings)
    return extrude_settings

@app.post("/extrusion/settings", tags=["extrusion"])
async def update_extrusion_settings(
    extrusion_speed: Annotated[float, Form()],
    ccw_speed: Annotated[Union[float, None], Form()] = None,
    cw_speed: Annotated[Union[float, None], Form()] = None,
    motion_delay: Annotated[Union[float, None], Form()] = None,
) -> dict:
    extrude_settings.extrusion_speed = extrusion_speed
    extrude_settings.ccw_speed = ccw_speed
    extrude_settings.cw_speed = cw_speed
    extrude_settings.motion_delay = motion_delay
    print("Updated settings:")
    print(extrude_settings)
    time.sleep(1)
    return {"success": True}

@app.post("/extrusion", tags=["extrusion"])
async def toggle_exturde() -> ExtrusionStatus:
    extrude_settings.extrude_on = not extrude_settings.extrude_on
    status = ExtrusionStatus(on=extrude_settings.extrude_on, speed="0.8")
    time.sleep(1)
    return status

@app.get("/material/settings", tags=["material"])
async def get_material_settings(
) -> MaterialSettings:
    print("Current material settings: ")
    print(material_settings)
    return material_settings

@app.post("/material/settings", tags=["material"])
async def update_material_settings(
    hi_level: Annotated[int, Form()],
    lo_level: Annotated[int, Form()],
) -> MaterialSettings:
    material_settings.hi_level = hi_level
    material_settings.lo_level = lo_level
    print("Updated material settings:")
    print(material_settings)
    time.sleep(1)
    return material_settings

@app.post("/material", tags=["material"])
async def toggle_material() -> MaterialSettings:
    material_settings.auto_refill_enabled = not material_settings.auto_refill_enabled
    time.sleep(1)
    return material_settings

@app.post("/task/pause-resume", tags=["task"])
async def toggle_pause_resume(
    dry_run: bool = False,
) -> TaskStatus:
    cur_task = task_queue[0]
    if cur_task.status is TaskStatus.ready:
        cur_task.status = TaskStatus.printing
    elif cur_task.status is TaskStatus.paused:
        cur_task.status = TaskStatus.printing
    elif cur_task.status is TaskStatus.printing:
        cur_task.status = TaskStatus.paused
    print("Dry run: ", dry_run)
    return cur_task.status

@app.post("/task/overwrite-extrusion-speed", tags=["task"])
async def overwrite_extrusion_speed(
    speed: float,
) -> dict:
    cur_task = task_queue[0]
    cur_task.applied_extrusion_speed = speed
    print("Updated speed: ", cur_task.applied_extrusion_speed)
    return {"success": True}
