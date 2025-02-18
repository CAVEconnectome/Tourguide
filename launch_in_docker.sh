#!/bin/zsh
docker run \
    --env-file .env.docker \
    -p 8080:8080 \
    gbv2-testing