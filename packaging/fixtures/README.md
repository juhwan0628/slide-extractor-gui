# Native half fixture

`native-half.mp4` is a synthetic FFmpeg testsrc2 pattern, generated for installed smoke testing; no lecture content. H.264 AVCC, closed GOP 1 second, six keyframes. Bundled LGPL FFmpeg only needs to decode it, not include an external H.264 encoder.

Reproduce using a development FFmpeg with libx264:

    ffmpeg -v error -y -f lavfi -i testsrc2=size=160x90:rate=4:duration=6 -c:v libx264 -preset ultrafast -g 4 -bf 0 -x264-params scenecut=0 native-half.mp4
