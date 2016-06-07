#!/bin/bash
SCRIPT=$(readlink -f "$0")
basedir=$(dirname "$SCRIPT")
python $basedir/app_serve_form.py >> $basedir/app_serve_form.log 2>&1 &
echo $! > $basedir/app_serve_form.pid