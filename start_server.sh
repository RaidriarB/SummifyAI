#!/bin/bash

cd web
SECRET_KEY=$(openssl rand -base64 32)
python3 app.py