from cassandra.cluster import Cluster
import sys

def create_schema(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS searchengine
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
    """)
    session.set_keyspace("searchengine")
    session.execute("""
        CREATE TABLE IF NOT EXISTS inverted_index (
            word text,
            doc_id text,
            term_freq int,
            PRIMARY KEY (word, doc_id)
        );
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS vocabulary (
            word text PRIMARY KEY,
            doc_freq int
        );
    """)
    session.execute("""
        CREATE TABLE IF NOT EXISTS doc_stats (
            doc_id text PRIMARY KEY,
            doc_len int
        );
    """)

def store_index():
    cluster = Cluster(['cassandra-server'])
    session = cluster.connect()
    create_schema(session)

    word_doc_freq = {}

    for line in sys.stdin:
        word, doc_id, freq = line.strip().split('\t')
        freq = int(freq)

        session.execute("""
            INSERT INTO inverted_index (word, doc_id, term_freq)
            VALUES (%s, %s, %s)
        """, (word, doc_id, freq))

        word_doc_freq[word] = word_doc_freq.get(word, set())
        word_doc_freq[word].add(doc_id)

    # Store document frequency
    for word, docs in word_doc_freq.items():
        session.execute("""
            INSERT INTO vocabulary (word, doc_freq)
            VALUES (%s, %s)
        """, (word, len(docs)))

    cluster.shutdown()
    
    
def store_doclen():
    cluster = Cluster(['cassandra-server'])
    session = cluster.connect()
    session.set_keyspace("searchengine")

    for line in sys.stdin:
        try:
            doc_id, doc_len = line.strip().split('\t')
            doc_len = int(doc_len)
            session.execute("""
                INSERT INTO doc_stats (doc_id, doc_len)
                VALUES (%s, %s)
            """, (doc_id, doc_len))
        except:
            continue

    cluster.shutdown()
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "store_index":
            store_index()
        elif sys.argv[1] == "store_doclen":
            store_doclen()
