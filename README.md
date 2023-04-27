# Serge - MikeD
![License](https://img.shields.io/github/license/nsarrazin/serge)
[![Discord](https://img.shields.io/discord/1088427963801948201?label=Discord)](https://discord.gg/62Hc6FEYQH)

A chat interface based on [llama.cpp](https://github.com/ggerganov/llama.cpp) for running Alpaca models. Entirely self-hosted, no API keys needed. Fits on 4GB of RAM and runs on the CPU.

- **SvelteKit** frontend
- **Redis** for storing chat history & parameters
- **FastAPI + langchain** for the API, wrapping calls to [llama.cpp](https://github.com/ggerganov/llama.cpp) using the [python bindings](https://github.com/abetlen/llama-cpp-python)

IMPLEMENTATION OF THE RESOURCE MANAGER
AUTOLOCK (MULTIPLE POSTS FROM SAME WINDOW WHEN THE MODEL STILL WRITING)


TUTORIAL ADD WAITING FOR RESOURCES & QUEUE LINE TO SERGE

1. 1st we need to edit Dockerfile from /serge/Dockerfile
At the end of the file you need to put:
```
RUN pip install psutil
```

2. We need to edit the file /serge/api/src/serge/main.py as following
On top add:
from pydantic import BaseModel
from typing import Dict
import psutil
import uvicorn
from fastapi import APIRouter

3. After
api_app.include_router(model_router)
app.mount("/api", api_app)

ADD:
<code>
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
</code>

4. At the end of the file you need to add CORS

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

Now we have routes to seek in the processor usage and also the queue line
USAGE: XXX.XXX.XXX.XXX:8008/cpu_usage
LINE: XXX.XXX.XXX.XXX:8008/tasks



5. Go to /serge/web/src/routes/chat/[id] and edit with nano +page.svelte

After  
 $: prompt = "";
let container;
Remove the function askQuestion() and add the following:
////////////////HERE THE MODIFIED FUNCTION
async function askQuestion() {
  try {
    const response = await fetch('/cpu_usage');
    const content = await response.json();

    if (content.idle_cores >= data.chat.params.n_threads && prompt) {
      const data = new URLSearchParams();
      data.append("prompt", prompt);

      const eventSource = new EventSource(
        "/api/chat/" + $page.params.id + "/question?" + data.toString()
      );

      history = [
        ...history,
        {
          type: "human",
          data: {
            content: prompt,
          },
        },
        {
          type: "ai",
          data: {
            content: "",
          },
        },
      ];

      prompt = "";
      eventSource.addEventListener("message", (event) => {
        history[history.length - 1].data.content += event.data;
      });

      eventSource.addEventListener("close", async () => {
        eventSource.close();
        await invalidate("/api/chat/" + $page.params.id);
      });

      eventSource.onerror = async (error) => {
        eventSource.close();
        history[history.length - 1].data.content = "A server error occurred.";
        await invalidate("/api/chat/" + $page.params.id);
      };
    } else {
      console.log("Function cannot run... No idle cores available. Retrying in 1 second.");
      setTimeout(() => {
        askQuestion();
      }, 1000);
    }
  } catch (error) {
    console.error("Error fetching cpu_usage:", error);
  }
}

/////END OF MODIFIED FUNCTION

6. Now remove your old docker files and image: 
DOCKER_BUILDKIT=1 docker compose down && docker image rm serge_serge:latest
7. Rebuild Docker
DOCKER_BUILDKIT=1 docker compose up -d --build

8. And test it

