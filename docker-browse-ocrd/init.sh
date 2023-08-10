#!/usr/bin/env bash

set -x
nohup broadwayd :5 &
browse-ocrd /data/mets.xml