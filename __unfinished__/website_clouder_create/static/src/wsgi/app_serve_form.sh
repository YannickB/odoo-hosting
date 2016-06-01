#!/bin/bash
python ./app_serve_form.py  >> ./app_serve_form.log 2>&1 &
echo $! > ./app_serve_form.pid