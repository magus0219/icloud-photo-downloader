#!/usr/bin/env bash

echo env: $ARTASCOPE_ENV
echo commnd: $0 $1
echo all command: $@

set -e

if [[ "$1" = 'web' ]]; then
	# start web
	echo "start web server"
	gunicorn -w 2 -b 0.0.0.0:16666 artascope.src.wsgi:app --access-logfile - --error-logfile -
fi

if [[ "$1" = 'celery_worker_main' ]]; then
	# start celery worker_main
	echo "start celery worker_main"
	celery -A artascope.src.celery_app worker -n worker_main -E --loglevel=info --pidfile=/var/run/%n.pid --max-tasks-per-child=100
fi

if [[ "$1" = 'celery_worker_msg' ]]; then
	# start celery worker_msg
	echo "start celery worker_msg"
	celery -A artascope.src.celery_app worker -c1 -Q msg -n worker_msg -E --loglevel=info --pidfile=/var/run/%n.pid --max-tasks-per-child=100
fi

if [[ "$1" = 'celery_worker_upload' ]]; then
	# start celery worker_upload
	echo "start celery worker_upload"
	celery -A artascope.src.celery_app worker -c1 -Q upload -n worker_upload -E --loglevel=info --pidfile=/var/run/%n.pid --max-tasks-per-child=100
fi

if [[ "$1" = 'celery_flower' ]]; then
	# start celery worker_upload
	echo "start celery worker_upload"
	celery -A artascope.src.celery_app flower --port=5555
fi

if [[ "$1" = 'scheduler' ]]; then
	# start celery beat
	echo "start scheduler"
	python artascope/src/script/scheduler.py
fi

if [[ "$1" = 'test' ]]; then
	# run test
	echo "run test"
	python -m pytest --cov-report term  --cov=artascope/src
	echo "test result" "$?"
	exit "$?"
fi

exec "$@"
