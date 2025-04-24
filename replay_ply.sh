#!/bin/bash

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <source_folder> <destination_folder> <delay_in_seconds>"
  exit 1
fi

SOURCE_FOLDER="$1"
DEST_FOLDER="$2"
DELAY="$3"

mkdir -p "$DEST_FOLDER"

# Get sorted list of PLY files by filename
FILES=$(ls "$SOURCE_FOLDER"/pointcloud1_*.ply | sort)

for file in $FILES; do
  base_file=$(basename "$file")
  cp "$file" "$DEST_FOLDER/$base_file"
  echo "Copied: $base_file"
  sleep "$DELAY"
done

