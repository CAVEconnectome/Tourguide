#!/bin/zsh
docker run \
    --env-file .env.debug \
    -p 8080:8080 \
    -v /Users/caseysm/.cloudvolume/secrets:/root/.cloudvolume/secrets \
    gbv2-testing