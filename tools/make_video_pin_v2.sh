#!/bin/bash
# make_video_pin_v2.sh — multi-shot "editor cut" video from ONE static pin image.
# Instead of one slow continuous zoom, treats the single image as 3 different
# shots (headline / middle content / price+CTA) with quick mini zooms and
# crossfade cuts between them -- feels like an edited video, not a slideshow.
# Usage: ./make_video_pin_v2.sh <input.jpg> <hook_text> <cta_text> <output.mp4>
set -e

IN="$1"
HOOK="$2"
CTA="$3"
OUT="$4"
W=1080
H=1920
FPS=30
SHOT_DUR=3.2        # seconds per shot before crossfade overlap
XFADE=0.35           # crossfade duration between shots
FONT="/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
WORKDIR=$(mktemp -d)

SHOT_FRAMES=$(python3 -c "print(int(${SHOT_DUR}*${FPS}))")

# --- build the 1080x1920 composite (blurred backdrop + centered sharp pin), same as v1 ---
ffmpeg -y -i "$IN" -filter_complex "
[0:v]scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},boxblur=24:2,eq=brightness=-0.12:saturation=0.9[bg];
[0:v]scale=${W}:-1[fg_full];
[bg][fg_full]overlay=(W-w)/2:(H-h)/2:shortest=1[comp]
" -map "[comp]" -frames:v 1 "$WORKDIR/frame.png" 2>"$WORKDIR/pass1.log" || { cat "$WORKDIR/pass1.log"; exit 1; }

# --- 3 shots: crop into a region of the composite, then a quick small zoom-in on that crop ---
# regions given as: crop_h(fraction of H) crop_y(fraction of H, top of region)
make_shot () {
  local idx=$1 crop_h_frac=$2 crop_y_frac=$3 zoom_dir=$4
  local ch=$(python3 -c "print(int(${H}*${crop_h_frac}))")
  local cy=$(python3 -c "print(int(${H}*${crop_y_frac}))")
  local zexpr
  if [ "$zoom_dir" = "in" ]; then
    zexpr="if(lte(on,1),1.0,min(1.0+0.09*on/${SHOT_FRAMES},1.09))"
  else
    zexpr="if(lte(on,1),1.09,max(1.09-0.09*on/${SHOT_FRAMES},1.0))"
  fi
  ffmpeg -y -loop 1 -i "$WORKDIR/frame.png" -t ${SHOT_DUR} -filter_complex "
  [0:v]crop=${W}:${ch}:0:${cy},scale=${W}*2:-1,zoompan=z='${zexpr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${W}x${H}:fps=${FPS}[v]
  " -map "[v]" -r ${FPS} -pix_fmt yuv420p "$WORKDIR/shot${idx}.mp4" 2>"$WORKDIR/shot${idx}.log" || { cat "$WORKDIR/shot${idx}.log"; exit 1; }
}

# Footer/price shots are thin bands -- zooming them to fill the full 1080x1920
# frame (like make_shot does) stretches/distorts the text badly. Instead:
# crop at NATURAL resolution (no forced fill-stretch) and pad top/bottom with
# a solid color sampled from the band itself, so text stays legible and
# undistorted while still filling the frame.
make_shot_pad () {
  local idx=$1 crop_h_frac=$2 crop_y_frac=$3 pad_color=$4
  local ch=$(python3 -c "print(int(${H}*${crop_h_frac}))")
  local cy=$(python3 -c "print(int(${H}*${crop_y_frac}))")
  # mild, non-distorting zoom (1.0 -> 1.15) applied uniformly (both axes) via
  # scale, then padded -- keeps text proportions correct, just gently larger.
  ffmpeg -y -loop 1 -i "$WORKDIR/frame.png" -t ${SHOT_DUR} -filter_complex "
  [0:v]crop=${W}:${ch}:0:${cy},scale=$((W*13/10)):-1[cropped];
  color=c=${pad_color}:s=${W}x${H}:d=${SHOT_DUR}[bg];
  [bg][cropped]overlay=(W-w)/2:(H-h)/2:shortest=1[v]
  " -map "[v]" -r ${FPS} -pix_fmt yuv420p "$WORKDIR/shot${idx}.mp4" 2>"$WORKDIR/shot${idx}.log" || { cat "$WORKDIR/shot${idx}.log"; exit 1; }
}

# shot windows are content-aware (auto-picked by pick_shots.py to dodge blank
# whitespace bands) rather than fixed fractions -- falls back to hardcoded
# defaults if the analyzer isn't available for some reason.
read Y1 Y2 Y3 SHOT_H FOOTER_H FOOTER_COLOR <<< "$(python3 "$(dirname "$0")/pick_shots.py" "$IN" 2>/dev/null || echo "0.08 0.35 0.80 0.36 0.20 0x0f193c")"

# shot 1: headline zone, zoom in
make_shot 1 ${SHOT_H} ${Y1} in
# shot 2: middle feature/benefit zone, zoom out (variety)
make_shot 2 ${SHOT_H} ${Y2} out
# shot 3: price/CTA footer zone -- padded (not stretched) so text stays legible
make_shot_pad 3 ${FOOTER_H} ${Y3} "${FOOTER_COLOR}"

# --- crossfade the 3 shots together ---
OFFSET1=$(python3 -c "print(${SHOT_DUR}-${XFADE})")
OFFSET2=$(python3 -c "print((${SHOT_DUR}-${XFADE})*2)")
ffmpeg -y -i "$WORKDIR/shot1.mp4" -i "$WORKDIR/shot2.mp4" -i "$WORKDIR/shot3.mp4" -filter_complex "
[0:v][1:v]xfade=transition=fade:duration=${XFADE}:offset=${OFFSET1}[x1];
[x1][2:v]xfade=transition=fade:duration=${XFADE}:offset=${OFFSET2}[vout]
" -map "[vout]" -pix_fmt yuv420p "$WORKDIR/cut.mp4" 2>"$WORKDIR/xfade.log" || { cat "$WORKDIR/xfade.log"; exit 1; }

DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$WORKDIR/cut.mp4")
FADE_OUT_ST=$(python3 -c "print(max(${DUR}-1.5,0.1))")

# --- synthesized royalty-free ambient audio bed, same technique as v1 ---
ffmpeg -y -f lavfi -i "sine=frequency=196:duration=${DUR}" \
  -f lavfi -i "sine=frequency=246:duration=${DUR}" \
  -f lavfi -i "sine=frequency=294:duration=${DUR}" \
  -filter_complex "
[0:a]volume=0.05[a1];
[1:a]volume=0.04[a2];
[2:a]volume=0.03[a3];
[a1][a2][a3]amix=inputs=3:duration=longest[mixed];
[mixed]afade=t=in:st=0:d=1.0,afade=t=out:st=${FADE_OUT_ST}:d=1.5,alimiter=limit=0.4[aout]
" -map "[aout]" -ar 44100 "$WORKDIR/music.wav" 2>"$WORKDIR/audio.log" || { cat "$WORKDIR/audio.log"; exit 1; }

# --- final pass: fixed text overlays (hook top / CTA bottom) stay put across all cuts + mux audio ---
ffmpeg -y -i "$WORKDIR/cut.mp4" -i "$WORKDIR/music.wav" -filter_complex "
[0:v]drawbox=x=0:y=0:w=${W}:h=230:color=black@0.45:t=fill[b1];
[b1]drawtext=fontfile=${FONT}:text='${HOOK}':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=70:line_spacing=10:box=0[b2];
[b2]drawbox=x=0:y=${H}-190:w=${W}:h=190:color=black@0.55:t=fill[b3];
[b3]drawtext=fontfile=${FONT}:text='${CTA}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=${H}-130[vout]
" -map "[vout]" -map 1:a -c:v libx264 -pix_fmt yuv420p -profile:v high -movflags +faststart -c:a aac -b:a 128k -shortest "$OUT" 2>"$WORKDIR/pass2.log" || { cat "$WORKDIR/pass2.log"; exit 1; }

echo "DONE: $OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name -of default=noprint_wrappers=1 "$OUT"
rm -rf "$WORKDIR" 2>/dev/null || true
