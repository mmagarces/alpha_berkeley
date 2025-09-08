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

#This will vary depending on your system, but wherever you install the bolt-api call, perform the following
pip install config
uvicorn server:app --host 127.0.0.1 --port 8004 --reload
#server in this case is what I named my file (server.py in my case), so this can be modified to your liking
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
```

## Configuration File

In the `config.yml` file, make sure you modify the project root to be where your alpha_berkeley is located, or as a result from pwd

```

### Important Configuration Switch

In `src/applications/bolt/bolt_api.py` at lines 68-70, you'll find FASTAPI_URL settings for both `host.docker.internal` and `localhost`:

- **For CLI usage**: Use `localhost` and comment out `host.docker.internal`
- **For WebUI usage**: Use `host.docker.internal` and comment out `localhost`

# If you kepe getting -1.0 degree results

Run podman desktop and run the services (compose)

In a terminal, run the following:

podman exec -it pipelines pip install tiled entrypoints stamina