_exocompleter() 
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    length_terms=${#COMP_WORDS[@]}

    # exo _____ -> list commands
    if [[ ${length_terms} == 2 ]] ; then 
        # exo ________
        # Autocomplete commands
        # Get commands from whatever exo runs as help
        local keys=$(python -c'from exoline import exo; print(" ".join(exo.cmd_doc.keys()))')
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    # exo COMMAND ____ -> list CIKs
    elif [[ ${length_terms} == 3 ]] ; then
        # exo command ______
        # Autocomplete keys
        local keys=$(exo keys)
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    # exo COMMAND CIK -> list dataports
    elif [[ ${length_terms} == 4 ]] ; then 
        # exo command cik ____
        # Autcomplete dataports / scripts
        # Maybe pin
        local keys=$(exo aliases ${COMP_WORDS[2]})
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    # exo COMMAND CIK DATAPORT -> complete switches for command
    elif [[ ${length_terms} == 5 ]] ; then 
        # exo command cik dataport ____ 
        # Autcomplete switches for command
        local keys=$(exo switches ${COMP_WORDS[1]})
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    else
        return 0
    fi
}

complete -F _exocompleter exoline
complete -F _exocompleter exo

