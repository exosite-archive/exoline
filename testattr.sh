# run all tests with a given attribute
# 
ATTR=$1
shift
tox $@ -- --with-coverage --cover-erase --cover-package exoline --cover-package exoline.plugins -A "'"$ATTR"'"
