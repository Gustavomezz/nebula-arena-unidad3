#!/usr/bin/env bash
set -euo pipefail
mkdir -p stream/video/live/nebula
ffmpeg -hide_banner -y -f lavfi -i testsrc2=size=640x360:rate=30 -t 300 \
  -c:v libx264 -preset veryfast -b:v 800k -maxrate 800k -bufsize 1600k \
  -g 60 -sc_threshold 0 -hls_time 2 -hls_playlist_type vod \
  -hls_segment_filename 'stream/video/live/nebula/360p_%03d.ts' \
  stream/video/live/nebula/360p.m3u8
