#!/bin/bash
# based on https://github.com/jupyter/docker-stacks/blob/main/base-notebook/start.sh
set -e

_log () {
    if [[ "$*" == "ERROR:"* ]] || [[ "$*" == "WARNING:"* ]] || [[ "${LOG_QUIET}" == "" ]]; then
        echo "$@"
    fi
}

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

# Default to starting bash if no command was specified
if [ $# -eq 0 ]; then
    cmd=( "sh" )
else
    cmd=( "$@" )
fi


if [ "$(id -u)" == 0 ] ; then
    if id ${DEFAULT_USER} &> /dev/null ; then
		if ! usermod --home "/home/${CUSTOM_USER}" --login "${CUSTOM_USER}" ${DEFAULT_USER} 2>&1 | grep "no changes" > /dev/null; then
          	_log "Updated the ${DEFAULT_USER} user:"
	        _log "- username: ${DEFAULT_USER}       -> ${CUSTOM_USER}"
            _log "- home dir: /home/${DEFAULT_USER} -> /home/${CUSTOM_USER}"
        fi
    elif ! id -u "${CUSTOM_USER}" &> /dev/null; then
        _log "ERROR: Neither the ${DEFAULT_USER} user or '${CUSTOM_USER}' exists. This could be the result of stopping and starting, the container with a different CUSTOM_USER environment variable."
        exit 1
    fi
    # Ensure the desired user (NB_USER) gets its desired user id (NB_UID) and is
    # a member of the desired group (NB_GROUP, NB_GID)
    if [ "${CUSTOM_UID}" != "$(id -u "${CUSTOM_USER}")" ] || [ "${CUSTOM_GID}" != "$(id -g "${CUSTOM_USER}")" ]; then
        _log "Update ${CUSTOM_USER}'s UID:GID to ${CUSTOM_UID}:${CUSTOM_GID}"
        # Ensure the desired group's existence
        if [ "${CUSTOM_GID}" != "$(id -g "${CUSTOM_USER}")" ]; then
            groupadd --force --gid "${CUSTOM_GID}" --non-unique "${CUSTOM_GROUP:-${CUSTOM_USER}}"
        fi
        # Recreate the desired user as we want it
        userdel "${CUSTOM_USER}"
        useradd --home "/home/${CUSTOM_USER}" --uid "${CUSTOM_UID}" --gid "${CUSTOM_GID}" --groups 100 --no-log-init "${CUSTOM_USER}"
    fi

    # Move or symlink the jovyan home directory to the desired users home
    # directory if it doesn't already exist, and update the current working
    # directory to the new location if needed.
    if [[ "${CUSTOM_USER}" != "${DEFAULT_USER}" ]]; then
        if [[ ! -e "/home/${CUSTOM_USER}" ]]; then
            _log "Attempting to copy /home/${DEFAULT_USER} to /home/${CUSTOM_USER}..."
            mkdir "/home/${CUSTOM_USER}"
            if cp -av "/home/${DEFAULT_USER}/." "/home/${CUSTOM_USER}/"; then
                _log "Success!"
            else
                _log "Failed to copy data from /home/${DEFAULT_USER} to /home/${CUSTOM_USER}!"
                _log "Attempting to symlink /home/${DEFAULT_USER} to /home/${CUSTOM_USER}..."
                if ln -s "/home/${DEFAULT_USER}" "/home/${CUSTOM_USER}"; then
                    _log "Success creating symlink!"
                else
                    _log "ERROR: Failed copy data from /home/${DEFAULT_USER} to /home/${CUSTOM_USER} or to create symlink!"
                    exit 1
                fi
            fi
        fi
        # Ensure the current working directory is updated to the new path
        if [[ "${PWD}/" == "/home/${DEFAULT_USER}/"* ]]; then
            new_wd="/home/${CUSTOM_USER}/${PWD:13}"
            _log "Changing working directory to ${new_wd}"
            cd "${new_wd}"
        fi
    fi
    export XDG_CACHE_HOME="/home/${CUSTOM_USER}/.cache"
    export PWD=/home/${CUSTOM_USER}
    export DEFAULT_USER="${CUSTOM_USER}"
    export PYTHONPATH="/home/${CUSTOM_USER}"
    export BASE_PATH="/home/${CUSTOM_USER}"
    export PATH="$PATH:/opt/conda/bin"
    export HOME="/home/${CUSTOM_USER}"
    if command_exists "conda" &> /dev/null
    then
     	ln -s /opt/conda/bin/conda /usr/local/bin/conda
    fi
    exec su --preserve-environment "${CUSTOM_USER}" \
         --session-command "${cmd[@]}"
else
    exec "${cmd[@]}"
fi
