#!/usr/bin/env bash

echo env: $ARTASCOPE_ENV
echo commnd: $0 $1
echo all command: $@

set -e

if [[ "$1" = 'web' ]]; then
	# start web
	echo "start web server"
	gunicorn -w 2 -b 0.0.0.0:16666 artascope.src.wsgi:app
fi

if [[ "$1" = 'celery' ]]; then
	# start celery worker
	echo "start celery worker"
	celery -A artascope.src.celery_app worker -E --loglevel=info
fi

if [[ "$1" = 'beat' ]]; then
	# start celery beat
	echo "start celery beat"
	celery -A artascope.src.celery_app beat --loglevel=info
fi

if [[ "$1" = 'test' ]]; then
	# run test
	echo "run test"
	python -m pytest --cov-report term  --cov=artascope/src
	echo "test result" "$?"
	exit "$?"
fi

exec "$@"
