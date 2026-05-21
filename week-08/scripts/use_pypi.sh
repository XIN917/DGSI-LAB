#!/usr/bin/env bash
# Source this from project commands to override the user's global pip index only
# for the current shell/process tree.
export PIP_INDEX_URL="https://pypi.org/simple"
unset PIP_EXTRA_INDEX_URL
