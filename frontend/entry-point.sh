#!/bin/sh
set -e

if [ "$APP_ENV" = "development" ]; then
    echo "FRONT EM DESENVOLVIMENTO"
    exec npm run dev -- --host
fi

npm run build
exec npm run preview -- --host