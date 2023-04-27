import sys
import os

from pydantic import BaseModel
from typing import Dict
import psutil
import uvicorn
from fastapi import APIRouter
import math

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from loguru import logger

from serge.routers.chat import chat_router
from serge.routers.model import model_router
from serge.models.settings import Settings
from serge.utils.convert import convert_all


# Configure logging settings
# Define a logger for the current mo
logger.add(sys.stderr, format="{time} {level} {message}", level="DEBUG")

settings = Settings()

tags_metadata = [
    {
        "name": "misc.",
        "description": "Miscellaneous endpoints that don't fit anywhere else",
    },
    {
        "name": "chats",
        "description": "Used to manage chats",
    },
]

description = """
Serge answers your questions poorly using LLaMA/alpaca. 🚀
"""

origins = [
    "http://localhost",
    "http://api:9124",
    "http://localhost:9123",
    "http://localhost:9124",
]

app = FastAPI(
    title="Serge", version="0.0.1", description=description, tags_metadata=tags_metadata
)

api_app = FastAPI(title="Serge API")
api_app.include_router(chat_router)
api_app.include_router(model_router)
app.mount("/api", api_app)


########ADDED ROUTES#######

@app.get("/cpu_usage")
def get_cpu_usage():
    total_cores = psutil.cpu_count()
    cpu_usage = psutil.cpu_percent()  # in percentage

    # Calculate the total core usage
    total_core_usage = total_cores * (cpu_usage / 100)

    # Split the core usage into full and partially used cores
    full_cores_used = int(math.floor(total_core_usage))
    partial_core_usage = total_core_usage - full_cores_used

    # Calculate the number of idle cores
    idle_cores = total_cores - full_cores_used - (1 if partial_core_usage > 0 else 0)

    return {"idle_cores": idle_cores}

###CREATE JSON IF NOT EXISTS
def create_json_if_not_exists(file_path, default_content):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default_content, f)

    json_file_path = "static/data.json"
    default_content = {"tasks": []}
    create_json_if_not_exists(json_file_path, default_content)

@app.get("/tasks")###SEE THE QUEUE LINE
async def get_tasks():
    return FileResponse(json_file_path, media_type="application/json")
###########################


# handle serving the frontend as static files in production
if settings.NODE_ENV == "production":

    @app.middleware("http")
    async def add_custom_header(request, call_next):
        response = await call_next(request)
        if response.status_code == 404:
            return FileResponse("static/200.html")
        return response

    @app.exception_handler(404)
    def not_found(request, exc):
        return FileResponse("static/200.html")

    async def homepage(request):
        return FileResponse("static/200.html")

    app.route("/", homepage)
    app.mount("/", StaticFiles(directory="static"))

    start_app = app
else:
    start_app = api_app


@start_app.on_event("startup")
async def start_database():
    WEIGHTS = "/usr/src/app/weights/"
    files = os.listdir(WEIGHTS)
    files = list(filter(lambda x: x.endswith(".tmp"), files))

    for file in files:
        os.remove(WEIGHTS + file)

    logger.info("initializing models")
    convert_all("/usr/src/app/weights/", "/usr/src/app/weights/tokenizer.model")

# Set up CORS middleware
origins = [
    "http://localhost",
    "http://127.0.0.1",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
