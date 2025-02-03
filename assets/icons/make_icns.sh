#!/usr/bin/env sh

ICONFILE="labquake_explorer.svg"
BASENAME="${ICONFILE%.*}"
ICONSET="$BASENAME.iconset"

mkdir -p "$ICONSET"

ICON_SPECS=(
    "16 icon_16x16.png"
    "32 icon_16x16@2x.png"
    "32 icon_32x32.png"
    "64 icon_32x32@2x.png"
    "128 icon_128x128.png"
    "256 icon_128x128@2x.png"
    "256 icon_256x256.png"
    "512 icon_256x256@2x.png"
    "512 icon_512x512.png"
    "1024 icon_512x512@2x.png"
)

convert_icon() {
    local size="$1"
    local output="$2"
    inkscape "$ICONFILE" \
        --export-filename="$ICONSET/$output" \
        --export-width="$size" \
        --export-height="$size" \
        --export-type="png"
}

for spec in "${ICON_SPECS[@]}"; do
    read -r size filename <<< "$spec"
    convert_icon "$size" "$filename"
done

# Convert to icns for macOS
iconutil -c icns "$ICONSET" -o "${BASENAME}.icns"

# Convert one of the PNGs to ico for Windows
convert "$ICONSET/icon_256x256.png" "${BASENAME}.ico"

# Keep a PNG version for Linux
cp "$ICONSET/icon_128x128.png" "${BASENAME}.png"

# Clean up the temporary iconset
rm -rf "$ICONSET"