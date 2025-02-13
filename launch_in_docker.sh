#!/bin/zsh
docker run \
    --env-file .env.debug \
    -p 8080:8080 \
    gbv2-testing