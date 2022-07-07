#!/usr/bin/env bash
useradd -u 12001 compiler && useradd -u 12002 code && useradd -u 12003 spj && usermod -a -G code spj
mkdir /judger