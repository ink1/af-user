#!/bin/bash

yum install -y epel-release

# process monitoring
yum install -y python-psutil

# required to build s3fs-fuse 
# curl & xml2 pull xz-devel and zlib-devel
yum install -y fuse-devel libcurl-devel libxml2-devel openssl-devel

#yum install -y R-core

