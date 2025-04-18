#!/usr/bin/env python3
import sys
import re

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

for line in sys.stdin:
    try:
        parts = line.strip().split('\t')
        if len(parts) < 3:
            continue
        doc_id, title, text = parts[0], parts[1], parts[2]
        words = tokenize(text)
        for word in words:
            print(f"{word}\t{doc_id}\t1")
    except Exception as e:
        continue
