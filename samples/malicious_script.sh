#!/bin/sh
# Consume CPU and memory aggressively
dd if=/dev/urandom | bzip2 -9 >> /dev/null