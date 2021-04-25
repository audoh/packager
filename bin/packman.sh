#!/bin/bash -e

log() {
  if [ -z "$PACKMANDEBUG" ]; then
    return 0
  fi
  echo $@ >&2
}

SCRIPT_DIR="$(dirname "${BASH_SOURCE}")"
ROOT_DIR="$SCRIPT_DIR/.."

# Activate venv
log Activating venv
pushd "$ROOT_DIR" > /dev/null
VENV_DIR=`poetry env info -p`
source "$VENV_DIR/bin/activate"
popd > /dev/null

# Run script
log Running script
export PYTHONPATH="$ROOT_DIR/packman_cli"
python -m packman_cli.cli "$@"
