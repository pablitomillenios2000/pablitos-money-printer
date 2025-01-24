#!/bin/bash

cd ../view/output

rm *.br

for file in *; do
    if [ -f "$file" ]; then
        brotli --quality=6 "$file" -o "$file.br"
    fi
done

echo "compression finished"