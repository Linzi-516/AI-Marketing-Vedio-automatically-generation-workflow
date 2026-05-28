# Internal REST API Contract

The API layer is for the internal frontend tool. It uses asynchronous workflow
runs, polling, and state-machine checkpoints.

## Run Server

```bash
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

## Endpoints

- `POST /api/runs`
  - Creates a background workflow run and returns `{ "run_id": "...", "status": "queued" }`.

- `GET /api/runs/{run_id}`
  - Returns run status: `queued | running | waiting_user | completed | failed`.

- `GET /api/runs/{run_id}/checkpoint`
  - Returns the pending checkpoint when status is `waiting_user`.

- `POST /api/runs/{run_id}/checkpoint`
  - Submits the pending checkpoint response and resumes the background workflow.

- `GET /api/runs/{run_id}/artifacts`
  - Returns generated file lists and the current `state.json` snapshot.

- `GET /api/config`
  - Returns non-secret runtime config for the frontend.

## Checkpoint Types

- `image_confirm`
  - Submit `action: "next"` or `action: "regenerate"` with optional `new_prompt`.

- `script_confirm`
  - Submit final `full_script` and `scenes`.

- `scene_image_select`
  - Submit `scene_image_selections`, one item per scene.
