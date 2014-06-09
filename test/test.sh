#!/bin/bash

function test() {
    PYTHONPATH=../exoline/:$PYTHONPATH
    nosetests --verbose --with-coverage --cover-erase --cover-package=exoline --cover-package=exoline.plugins
    #nosetests --with-xunit --xunit-file=$1 --verbose --with-coverage --cover-erase --cover-package=exoline
    #python -m coverage xml
    #cp coverage.xml coverage$1.xml
    #pushd ../exoline
    # python -m doctest -v exo.py
    #popd
}

function fn_exists() {
    # appended double quote is an ugly trick to make sure we do get a string -- if $1 is not a known command, type does not output anything
    [ `type -t $1`"" == 'function' ]
}

function mydeactivate() {
    if fn_exists deactivate; then
        deactivate
    fi
}

if [ "$1" == "full" ];
then
    #set -e
    # Python versions to test
    declare -a pythons=('python2.6' 'python2.7' 'python3.2' 'python3.3' 'python3.4')
    #declare -a pythons=('python2.6')

    for i in "${pythons[@]}"
    do
        echo Setting up $i environment...
        unset PYTHONPATH
        mydeactivate
        rm -rf ve$i
        PYTHON=/usr/bin/$i
        if [ ! -f "$PYTHON" ]; then
            PYTHON=/usr/local/bin/$i
        fi

        if [ ! -f "$PYTHON" ]; then
            echo $PYTHON not found, skipping it...
            continue
        fi
        virtualenv --quiet -p $PYTHON ve$i || exit 1
        source ve$i/bin/activate 
        pushd ..
        if [ "$2" == "--quiet" ];
        then
            python setup.py --quiet install 2>&1 >/dev/null | grep error | grep -v Py | grep -v __pyx_
        else
            python setup.py install
        fi
        popd 
        pip install --upgrade --quiet -r requirements.txt 
        echo  
        echo Starting tests in $i environment
        test nosetests-$i.xml
    done
    mydeactivate
else
    # test in current environment
    test
fi


