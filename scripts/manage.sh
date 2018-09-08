#!/usr/bin/env bash

# Some variables
COMMANDS=(import add_picture)
PRINT_HELP=$#
SCRIPT_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}/../backend"

# Figure out if -h/--help goes to this script or to the command
for arg in $@
do 
    for command in ${COMMANDS[@]}; do [[ "$arg" == "$command" ]] && break 2; done
    [[ "$arg" == "-h" ]] || [[ "$arg" == "--help" ]] && PRINT_HELP="0"
done

if [[ "$PRINT_HELP" == "0" ]]
then
    cat <<-USAGE
USAGE: $0 [command] <args>

Valid commands are:

    import          Import data into the database.
    add_picture     Add a picture into the database

Use $0 [command] -h or --help to get help on a specific command.
USAGE
fi

while (( "$#" ))
do
    arg="$1"
    shift
    [[ "$arg" == "import"      ]] && ${SCRIPT_DIR}/importer/importer.py $@ && break
    [[ "$arg" == "add_picture" ]] && ${SCRIPT_DIR}/add_picture_to_db.py $@ && break
done
