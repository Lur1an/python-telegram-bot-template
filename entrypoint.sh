#!/bin/sh
alembic upgrade head
python -m src.main
