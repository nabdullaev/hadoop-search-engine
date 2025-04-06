#!/usr/bin/env python3
import sys
from collections import defaultdict

current_word = None
current_doc = None
count = 0

for line in sys.stdin:
    word, doc_id, freq = line.strip().split('\t')
    freq = int(freq)

    key = (word, doc_id)

    if (current_word, current_doc) == (word, doc_id):
        count += freq
    else:
        if current_word:
            print(f"{current_word}\t{current_doc}\t{count}")
        current_word, current_doc, count = word, doc_id, freq

if current_word:
    print(f"{current_word}\t{current_doc}\t{count}")