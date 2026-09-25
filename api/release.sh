#!/bin/sh
# Release step: bring the database schema up to date, then import every committed Stack
# version. Safe to run on every deploy: already-imported versions are left unchanged.
set -e
alembic upgrade head
content-import "${CONTENT_DIR:-/app/content}"
