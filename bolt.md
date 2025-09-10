# BOLT Setup Guide

To initialize bolt at the BOLT machine, perform the following:

Refer to startup.txt @ Bolt under /home/user/Desktop for copy and pasting these codes if this repo is not opened at bolt

## Galil motor controller:

This window is for initializing the motor controller, but also serves as a way to see all of the available process variables using the command ```dbl```. Our main motor being used is DMC01:A, for the rotation motor.

In a terminal window:
```bash
cd /opt/epics/modules/motorGalil/Galil-3-0/3-6/iocBoot/iocGalilTest/
./st.cmd
```

## Allied Vision Camera

This window is for intializing the detector, or the camera in this case. The camera is defined with multiple plug ins, but the main one is 13ARV1:cam1.

In a terminal window:
```bash
cd /opt/epics/modules/synApps_6_1_epics7/support/areaDetector-R3-7 ADAravis/iocs/aravisIOC/iocBoot/iocAravis
./st.cmd.AV_Alvium_1800
```
## Qserver:

This window should be run in the terminal after you have accessed bluesky-web, as shown below. This address is constant at Bolt, and is what contians the plans and devices avaiallbe at the beamline. If you would like to see these plans, please refer to bluesky-web/queueserver/startup_bolt.

In a visual studio window:
```bash
cd /home/user/Repos/bluesky-web
conda activate bluesky
start-re-manager --zmq-publish-console ON --startup-dir /home/user/Repos/bluesky-web/queue-server/startup_bolt --keep-re
```

## Qserver # 2:

This window is mainly to be used to run the GUI screen for the queue server. This is very useful as it describes the plans, shows you what goes into executing each plan, provides detail on plans results, etc.

It is important to note this also gives you the runID and the 'fingerprint ID'. This is how I was able to do a majority of my work, since by checking the history for the fingerprint, I was able to find the corresponding runID. This let me access information on tiled afterwards, since due to TiledWriter's nature (will explain later), this is what each run's results was saved under.

In a visual studio window:
```bash
cd home/user/Repos/BOLT/frontend
npm run dev
```
## Qserver Rest API:

This window should be run on a terminal window. It describes the Qserver's Http side of things. It shows you the nature of the queue server constnatly checking it's history and getting items from the queue. It does this natively, and infinitely while the queue server runs. Most of them are GET requests, as it's just checking if the queue is busy and if there's anything being added to the queue. In this window, you can see when POST requests are made, which are used frequently due to my use of the API calls.

Along with this window, if you go to your browser and access http://localhost:60610/docs, you can find all of the API calls available for this particular queue server (There might be other features in others, so I don't want to go ahead and say it is at every queue server.)

In a terminal window:
```bash
conda activate bluesky
QSERVER_HTTP_SERVER_SINGLE_USER_API_KEY=test QSERVER_HTTP_SERVER_ALLOW_ORIGINS=* uvicorn --host localhost --port 60610 bluesky_httpserver.server:app
```
## Tiled Setup:

At bolt, this is natively where I'm running everything. This is bound to change due to organization and such, but this call is always consistently working. Under ```/home/user/tiledData/tiled/deploy```, you will find a ```catalog.db``` file. I'm sure a SQL call would display things in an interesting way, but if you ever wish to clear Tiled, delete the ```catalog.db``` file from the system and restart the tiled service as described below.

In a visual studio window:
```bash
cd /home/user/tiledData
conda activate bluesky
tiled serve config config.yml
```

## SSH Port Forwarding Setup

Open 2 terminal windows and run the following commands:

```bash
Terminal 1 - Tiled port forwarding
ssh -N -L 8000:localhost:8000 user@128.3.117.8
# Password: xray$1300
```

```bash
Terminal 2 - Queue server port forwarding  
ssh -N -L 8003:localhost:60610 user@128.3.117.8
# Password: xray$1300
```

## Project Setup

```bash
# Create project directory and clone repository
mkdir bolt && cd bolt
git clone https://github.com/mmagarces/alpha_berkeley.git
cd alpha_berkeley
```
## Create environment file

For this, you will need a CBORG API key, which can be found here (if you don't already have one): https://cborg.lbl.gov/api_request/. Once here, click continue to CBORG API Key Manager, and proceed with your LBL google login. Once you have copied your key, paste it into CBORG_API_KEY=(YOUR KEY GOES HERE)

```bash
touch .env && cp env.example .env
```

It is important to note you may receive some errors due to the following in the .env file:

NO_PROXY=no-proxy-list
HTTP_PROXY=http-proxy

I have found 2 solutions to this:
1) Deleting these lines seems to solve the issue for some systems

2) Another solution is:

Modify the lines to NO_PROXY='localhost,127.0.0.1' and HTTP_PROXY='localhost,127.0.0.1', and run the following in the terminal:

```bash
python -c "import os; [os.environ.pop(v, None) for v in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy']]"
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


### Important Configuration Switch

In `src/applications/bolt/bolt_api.py` at lines 68-70, you'll find FASTAPI_URL settings for both `host.docker.internal` and `localhost`:

- **For CLI usage**: Use `localhost` and comment out `host.docker.internal`
- **For WebUI usage**: Use `host.docker.internal` and comment out `localhost`

