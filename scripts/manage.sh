#!/usr/bin/env bash

# Some variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=${PYTHONPATH:+"$PYTHONPATH:"}"$SCRIPT_DIR/../backend"

do_help () {
    cat <<USAGE
USAGE:

    $0 command args
    $0 command -h

Valid commands are:

    import          Import data into the database
    add_picture     Add a picture into the database

Use
    $0 command -h
to get help on a specific command.
USAGE
}

cmd=$1
shift

case $cmd in
    help|-h|--help)
        do_help
        exit
        ;;
    import)
        "$SCRIPT_DIR/importer/importer.py" "$@"
        ;;
    picture)
        "$SCRIPT_DIR/add_picture_to_db.py" "$@"
        ;;
    *)
        printf 'Error: Invalid command "%s"\n' "$cmd" >&2
        do_help >&2
        exit 1
esac
