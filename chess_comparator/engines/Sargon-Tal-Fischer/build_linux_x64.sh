#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
c++ -std=c++17 -O3 -DNDEBUG -m64 -pthread -Isrc src/main.cpp src/thc.cpp -o Sargon-Tal-Fischer-x64
