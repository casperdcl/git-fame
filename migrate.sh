#!/usr/bin/env bash
python ci-env-migrate/gh.py $TRAVIS_REPO_SLUG \
  "DOCKER_PWD=$DOCKER_PWD" \
  "DOCKER_USR=$DOCKER_USR" \
  "GITHUB_TOKEN=$GITHUB_TOKEN" \
  "GITHUB_USR=$GITHUB_USR" \
  "SNAP_TOKEN=$SNAP_TOKEN" \
  "TWINE_PASSWORD=$TWINE_PASSWORD" \
  "TWINE_USERNAME=$TWINE_USERNAME" \
  "GPG_KEY=$(gpg --export-secret-key --armour casper.dcl@physics.org)"
