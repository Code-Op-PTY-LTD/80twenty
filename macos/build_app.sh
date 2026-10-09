#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
app="$repo_dir/.local/dist/KIN Companion.app"
binary="$app/Contents/MacOS/KIN Companion"
cache="$repo_dir/.local/build/module-cache"
consumer="$repo_dir/.local/bin/kin-capability-consumer"

mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" "$cache" "$(dirname "$consumer")"
cp "$script_dir/Info.plist" "$app/Contents/Info.plist"
CLANG_MODULE_CACHE_PATH="$cache" SWIFT_MODULE_CACHE_PATH="$cache" \
    swiftc -O -framework AppKit -framework Security -o "$binary" "$script_dir/KINCompanion.swift"
CLANG_MODULE_CACHE_PATH="$cache" SWIFT_MODULE_CACHE_PATH="$cache" \
    swiftc -O -o "$consumer" "$script_dir/KINCapabilityConsumer.swift"
xattr -cr "$app"
codesign --force --sign - --entitlements "$script_dir/KINCompanion.entitlements" "$app"
xattr -cr "$app"
codesign --verify --deep --strict "$app"
printf '%s\n' "$app"
printf '%s\n' "$consumer"
