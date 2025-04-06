#!/usr/bin/env python3
import sys

for line in sys.stdin:
    doc_id, length = line.strip().split('\t')
    print(f"{doc_id}\t{length}")
