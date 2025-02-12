#!/bin/zsh
docker run \
    --env-file .env.debug \
    -p 8080:8080 \
    -v ${HOME}/.cloudvolume/secrets:/root/.cloudvolume/secrets \
    gbv2-testing