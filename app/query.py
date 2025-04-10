import sys
import math
import re
from pyspark.sql import SparkSession
from pyspark.sql import Row
from cassandra.cluster import Cluster

# ----- Hyperparameters -----
k1 = 1.5
b = 0.75

# ----- Tokenizer -----
def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

# ----- Setup Spark -----
spark = SparkSession.builder \
    .appName("BM25 Ranker") \
    .getOrCreate()
    
    # .config("spark.executor.memory", "3g") \
    # .config("spark.driver.memory", "3g") \
    # .config("spark.executor.cores", "2") \


sc = spark.sparkContext

# ----- Read Query -----
query_text = " ".join(sys.argv[1:])
query_terms = tokenize(query_text)

# ----- Connect to Cassandra -----
cluster = Cluster(['cassandra-server'])
session = cluster.connect('searchengine')

# ----- Fetch Metadata from Cassandra -----
# 1. Get doc lengths
doc_len_rows = session.execute("SELECT doc_id, doc_len FROM doc_stats")
doc_lens = {row.doc_id: row.doc_len for row in doc_len_rows}
N = len(doc_lens)
avgdl = sum(doc_lens.values()) / N

# 2. Get vocabulary (df)
vocab_rows = session.execute("SELECT word, doc_freq FROM vocabulary")
df_map = {row.word: row.doc_freq for row in vocab_rows}

# 3. Get inverted index for all query terms
inverted_rows = []
for term in query_terms:
    rows = session.execute("SELECT doc_id, term_freq FROM inverted_index WHERE word=%s", [term])
    for row in rows:
        inverted_rows.append((term, row.doc_id, row.term_freq))

cluster.shutdown()

# ----- Parallelize data -----
rdd = sc.parallelize(inverted_rows)

# ----- Compute BM25 -----
def compute_bm25(row):
    term, doc_id, fqd = row
    df = df_map.get(term, 0)
    dl = doc_lens.get(doc_id, 0)
    idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

    score = idf * (fqd * (k1 + 1)) / (fqd + k1 * (1 - b + b * dl / avgdl))
    return (doc_id, score)

bm25_scores = rdd.map(compute_bm25) \
                 .reduceByKey(lambda x, y: x + y) \
                 .takeOrdered(10, key=lambda x: -x[1])

# ----- Fetch titles for top docs -----
doc_ids = [doc_id for doc_id, _ in bm25_scores]
title_rdd = sc.parallelize(doc_ids)

# Assume title is in filename: id_title.txt
def extract_title(doc_id):
    import os
    data_dir = "/app/data"
    for filename in os.listdir(data_dir):
        if filename.startswith(doc_id + "_"):
            return (doc_id, filename.replace(".txt", "").split("_", 1)[1].replace("_", " "))
    return (doc_id, "Unknown Title")

titles = dict(title_rdd.map(extract_title).collect())

# ----- Print top 10 -----
print("\nTop 10 documents:")
for doc_id, score in bm25_scores:
    print(f"{doc_id}\t{titles.get(doc_id, 'Unknown Title')}\tScore: {round(score, 4)}")
