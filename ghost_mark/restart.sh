#!/bin/bash
sudo pkill -f gunicorn
nohup gunicorn --bind 127.0.0.1:8000 ghost_mark.wsgi:application &
echo "Application restarted"
