#!/usr/bin/env bash

git subtree split -P rocket-solver/ -b bears_rocket_solver
git push newrepo bears_rocket_solver:master
git push bears-github bears_rocket_solver:master
