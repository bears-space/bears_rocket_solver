#!/usr/bin/env bash

SUBMOD_NAME="bears_rocket_solver"

git subtree split -P rocket-solver/ -b ${SUBMOD_NAME}
git push newrepo ${SUBMOD_NAME}:master
