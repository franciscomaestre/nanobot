#!/bin/bash
# Wrapper for launchd — runs nanobot gateway from TCC-free venv.
# Template: replace __HOME__ before installing to ~/.nanobot/bin/.
# The venv at ~/.nanobot/venv must exist (see install-launchd.sh).
export PATH="__HOME__/.nanobot/venv/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin"
export HOME="__HOME__"
export VIRTUAL_ENV="__HOME__/.nanobot/venv"
export LANG="en_US.UTF-8"
cd __HOME__/.nanobot
exec __HOME__/.nanobot/venv/bin/nanobot gateway
