#!/bin/bash

function test() {
    nosetests --verbose --with-coverage --cover-erase --cover-package=exoline
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
    # Python versions to test
    declare -a pythons=('python2.6' 'python2.7')

    for i in "${pythons[@]}"
    do
        echo Setting up $i environment...
        mydeactivate
        rm -rf ve$i
        virtualenv --quiet -p /usr/bin/$i ve$i
        source ve$i/bin/activate 
        pushd ..
        python setup.py install
        popd 
        pip install --quiet -r requirements.txt 
        echo  
        echo Starting tests in $i environment
        test nosetests-$i.xml
    done
    mydeactivate
else
    # test in current environment
    test
fi


