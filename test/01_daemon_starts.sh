#!/usr/bin/env bash
#
# This script just tries to make sure that the tornado webserver starts and
# doesn't crash immediately.

if timeout 5 python route.py; then
    exit 1
else
    exit 0
fi
