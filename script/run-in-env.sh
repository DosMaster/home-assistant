#!/usr/bin/env sh -eu

# Activate pyenv and virtualenv if present, then run the specified command

# pyenv, pyenv-virtualenv
if [ -s .python-version ]; then
    PYENV_VERSION=$(head -n 1 .python-version)
    echo "PYENV_VERSION"
    export PYENV_VERSION
fi

# other common virtualenvs
for venv in venv .venv .; do
    if [ -f $venv/bin/activate ]; then
        echo "$venv/bin/activate"
        . $venv/bin/activate
    fi
done

echo "WORKON_HOME=$WORKON_HOME"

if [ -f $WORKON_HOME/homeassistant32/scripts/activate ]; then
    echo "aource /mnt/c/dev/envs/homeassistant32/scripts/activate"
    source $WORKON_HOME/homeassistant32/scripts/activate
fi
echo "venv=$venv"

echo "exec: $@"
#exec "$@"
