#!/bin/bash
echo "This script includes commands to run mapreduce jobs using hadoop streaming to index documents"

INPUT_PATH="/index/data"
if [ "$1" != "" ]; then
  # check if input is HDFS or local
  if hdfs dfs -test -e "$1"; then
    INPUT_PATH="$1"
  else
    echo "Input path $1 not found in HDFS. Aborting."
    exit 1
  fi
fi


echo "Indexing input path: $INPUT_PATH"

# === FIRST PIPELINE: Inverted Index ===
echo "Running inverted index pipeline..."

# Clean intermediate output
hdfs dfs -rm -r -f /tmp/index-output

# Run Hadoop Streaming job
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming*.jar \
    -files mapreduce/mapper1.py,mapreduce/reducer1.py \
    -mapper "python3 mapper1.py" \
    -reducer "python3 reducer1.py" \
    -input "$INPUT_PATH" \
    -output /tmp/index-output


# === SECOND PIPELINE: Document Lengths ===
echo "Running document length pipeline..."

hdfs dfs -rm -r -f /tmp/doclen-output

hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming*.jar \
    -files mapreduce/mapper2.py,mapreduce/reducer2.py \
    -mapper "python3 mapper2.py" \
    -reducer "python3 reducer2.py" \
    -input "$INPUT_PATH" \
    -output /tmp/doclen-output


# === Wait for Cassandra ===

echo "Waiting for Cassandra to start..."
until python3 -c "from cassandra.cluster import Cluster; Cluster(['cassandra-server']).connect()" >/dev/null 2>&1; do
  echo "Cassandra not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "Cassandra is ready!"


# === Store outputs into Cassandra ===
echo "Storing inverted index into Cassandra..."
hdfs dfs -cat /tmp/index-output/part-* | python3 app.py store_index

echo "Storing document lengths into Cassandra..."
hdfs dfs -cat /tmp/doclen-output/part-* | python3 app.py store_doclen
