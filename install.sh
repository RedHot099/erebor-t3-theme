#!/bin/sh
# Install the Erebor theme into T3 Code on this computer (Linux, macOS).
# T3 Code reads themes from $T3CODE_HOME/userdata/themes, and T3CODE_HOME defaults to ~/.t3.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
themes="${T3CODE_HOME:-$HOME/.t3}/userdata/themes"

mkdir -p "$themes"
cp "$here/dist/erebor.json" "$here/dist/erebor.png" "$themes/"
echo "Installed erebor.json and erebor.png to $themes"
echo "In T3 Code, open Settings and select Erebor under Theme."
