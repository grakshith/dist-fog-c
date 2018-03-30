#! /bin/bash

celery -A app.celery beat --loglevel=debug

