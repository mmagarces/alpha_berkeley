# BOLT Setup Guide

## SSH Port Forwarding Setup

Open 3 terminal windows and run the following commands:

```bash
# Terminal 1 - Tiled port forwarding
ssh -N -L 8000:localhost:8000 user@128.3.117.8
# Password: xray$1300

# Terminal 2 - Queue server port forwarding  
ssh -N -L 8003:localhost:60610 user@128.3.117.8
# Password: xray$1300
```

## Project Setup

```bash
# Create project directory and clone repository
mkdir bolt && cd bolt
git clone https://github.com/mmagarces/alpha_berkeley.git
cd alpha_berkeley

# Create environment file

touch .env && cp env.example .env
#In the .env file, grab a cborg API key here:
# https://cborg.lbl.gov/api_request/

#When running alpha using the webUI, you will need to set this up in a separate terminal:
cd alpha_berkeley
pip install config
uvicorn server:app --host 127.0.0.1 --port 8004 --reload
#server in this case is what I named my file (server.py in my case), so this can be modified to your liking
```

## Configuration File

In the `config.yml` file, make sure you modify the project root to be where your alpha_berkeley is located, or as a result from pwd

In src/framework/config.yml, these following lines have been modiifed to use cborg instead of ollama:

models:
    orchestrator:
      provider: cborg
      model_id: anthropic/claude-sonnet
    response:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 5000
    classifier:
      provider: cborg
      model_id: google/gemini-flash
    approval:
      provider: cborg
      model_id: google/gemini-flash
    task_extraction:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 1024
    memory:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 256
    python_code_generator:
      provider: cborg
      model_id: anthropic/claude-haiku # claude-sonnet
      max_tokens: 4096
    time_parsing:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 512

whereas the original was:

models:
    orchestrator:
      provider: cborg
      model_id: anthropic/claude-sonnet
    response:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 5000
    classifier:
      provider: ollama
      model_id: mistral:7b
    approval:
      provider: ollama
      model_id: mistral:7b
    task_extraction:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 1024
    memory:
      provider: cborg
      model_id: google/gemini-flash
      max_tokens: 256
    python_code_generator:
      provider: cborg
      model_id: anthropic/claude-haiku # claude-sonnet
      max_tokens: 4096
    time_parsing:
      provider: ollama
      model_id: mistral:7b
      max_tokens: 512



```

### Important Configuration Switch

In `src/applications/bolt/bolt_api.py` at lines 68-70, you'll find FASTAPI_URL settings for both `host.docker.internal` and `localhost`:

- **For CLI usage**: Use `localhost` and comment out `host.docker.internal`
- **For WebUI usage**: Use `host.docker.internal` and comment out `localhost`

# If you kepe getting -1.0 degree results

Run podman desktop and run the services (compose)

In a terminal, run the following:

podman exec -it pipelines pip install tiled entrypoints stamina

