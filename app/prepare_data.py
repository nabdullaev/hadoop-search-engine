from pathvalidate import sanitize_filename
from pyspark.sql import SparkSession
import os
from tqdm import tqdm

# Start Spark session
spark = SparkSession.builder \
    .appName('data preparation') \
    .master("local") \
    .config("spark.sql.parquet.enableVectorizedReader", "true") \
    .getOrCreate()

# Read parquet from HDFS
df = spark.read.parquet("/a.parquet")

# Sample and filter
n = 10
df = df.select(['id', 'title', 'text']) \
       .filter("text IS NOT NULL") \
       .sample(fraction=100 * n / df.count(), seed=0) \
       .limit(n)

# Save .txt files to local /app/data folder
os.makedirs("data", exist_ok=True)

def save_text(row):
    if row['text']:
        filename = f"data/{sanitize_filename(str(row['id']) + '_' + row['title']).replace(' ', '_')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(row['text'])

df = df.repartition(5)
df.foreach(save_text)

# Create RDD: <id>\t<title>\t<text>
rdd = df.rdd.map(lambda row: f"{row['id']}\t{row['title']}\t{row['text']}")

# Save to HDFS at /index/data
rdd.saveAsTextFile("/index/data")
