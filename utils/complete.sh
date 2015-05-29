_exocompleter() 
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    length_terms=${#COMP_WORDS[@]}

    # Complete exo _____ -> parse 
    if [[ ${length_terms} == 2 ]] ; then 
        # exo ________
        # Autocomplete commands
        # Get commands from whatever exo runs as help
        local keys=$(python -c'from exoline import exo; print " ".join(exo.cmd_doc.keys())')
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    # Complete exo COMMAND ____ (parse ~/.exoline file for keys)
    elif [[ ${length_terms} == 3 ]] ; then
        # exo command ______
        # Autocomplete keys
        local keys=$(python ./get_keys.py)
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    elif [[ ${length_terms} == 4 ]] ; then 
        # exo command cik ____
        # Autcomplete dataports / scripts
        # Maybe pin
        local keys=$(exo info ${prev} | python -c 'import json; import sys; data = sys.stdin.read(); data = json.loads(data); aliases = data.get("aliases", {}); aliases = " ".join(v[0] for k,v in aliases.iteritems()); print aliases')
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    elif [[ ${length_terms} == 5 ]] ; then 
        # exo command cik dataport ____ 
        # Autcomplete switches for command
        local keys=$(python get_switches.py ${COMP_WORDS[1]})
        COMPREPLY=( $(compgen -W "${keys}" -- ${cur}) )
        return 0
    else
        return 0
    fi
}

complete -F _exocompleter exoline
complete -F _exocompleter exo
