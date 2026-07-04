#!/bin/bash
# make_video_pin.sh — turn a static Pinterest pin image into a 9:16 video pin
# Usage: ./make_video_pin.sh <input.jpg> <hook_text> <cta_text> <output.mp4>
set -e

IN="$1"
HOOK="$2"
CTA="$3"
OUT="$4"
DUR=10   # seconds, within Pinterest/Buffer 4-15s window
FPS=30
W=1080
H=1920
FONT="/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
WORKDIR=$(mktemp -d)
FADE_OUT_ST=$((DUR - 2))
TOTAL_FRAMES=$((DUR * FPS))

# --- Pass 1: build a 1080x1920 composite frame (blurred backdrop + sharp centered pin) ---
ffmpeg -y -i "$IN" -filter_complex "
[0:v]scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},boxblur=24:2,eq=brightness=-0.12:saturation=0.9[bg];
[0:v]scale=${W}:-1[fg_full];
[bg][fg_full]overlay=(W-w)/2:(H-h)/2:shortest=1[comp]
" -map "[comp]" -frames:v 1 "$WORKDIR/frame.png" 2>"$WORKDIR/pass1.log" || { cat "$WORKDIR/pass1.log"; exit 1; }

# --- synthesize a soft, royalty-free ambient background bed (no external audio needed) ---
ffmpeg -y -f lavfi -i "sine=frequency=196:duration=${DUR}" \
  -f lavfi -i "sine=frequency=246:duration=${DUR}" \
  -f lavfi -i "sine=frequency=294:duration=${DUR}" \
  -filter_complex "
[0:a]volume=0.05[a1];
[1:a]volume=0.04[a2];
[2:a]volume=0.03[a3];
[a1][a2][a3]amix=inputs=3:duration=longest[mixed];
[mixed]afade=t=in:st=0:d=1.2,afade=t=out:st=${FADE_OUT_ST}:d=1.5,alimiter=limit=0.4[aout]
" -map "[aout]" -ar 44100 "$WORKDIR/music.wav" 2>"$WORKDIR/audio.log" || { cat "$WORKDIR/audio.log"; exit 1; }

# --- Pass 2: Ken Burns zoom on the composite + text overlays + music, encode final mp4 ---
ffmpeg -y -loop 1 -i "$WORKDIR/frame.png" -i "$WORKDIR/music.wav" -filter_complex "
[0:v]scale=$((W*2)):$((H*2)),zoompan=z='min(zoom+0.0012,1.12)':d=${TOTAL_FRAMES}:s=${W}x${H}:fps=${FPS}[zoomed];
[zoomed]drawbox=x=0:y=0:w=${W}:h=230:color=black@0.45:t=fill[b1];
[b1]drawtext=fontfile=${FONT}:text='${HOOK}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=70:line_spacing=10:box=0[b2];
[b2]drawbox=x=0:y=${H}-190:w=${W}:h=190:color=black@0.55:t=fill[b3];
[b3]drawtext=fontfile=${FONT}:text='${CTA}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=${H}-130[vout]
" -map "[vout]" -map 1:a -t ${DUR} -r ${FPS} -c:v libx264 -pix_fmt yuv420p -profile:v high -movflags +faststart -c:a aac -b:a 128k -shortest "$OUT" 2>"$WORKDIR/pass2.log" || { cat "$WORKDIR/pass2.log"; exit 1; }

echo "DONE: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name -of default=noprint_wrappers=1 "$OUT"
rm -rf "$WORKDIR"
