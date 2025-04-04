import json
import os

import pandas as pd
from neo4j import GraphDatabase
from openai import OpenAI
import hashlib

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "12345678"

API_KEY = "sk-969b6309421740869719b25527b46e41"
API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CLIENT = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

ORIGINAL_FILE_PATH = "DATA/original/tmp.txt"
PROCESSED_FILE_PATH = "DATA/processed/tmp.csv"

CSV_DELIMITER = "|"
CSV_ENCODING = "utf-8-sig"

MEMORY_TABLE_PATH = "memory_table.json"

def llm_api(prompt):
    response = CLIENT.chat.completions.create(
        model="deepseek-v3",
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

def read_original_text():
    with open(ORIGINAL_FILE_PATH, "r", encoding="utf-8") as file:
        return file.read()

def create_empty_processed_df(length):
    return pd.DataFrame({
        "索引": ["" for _ in range(length)],
        "内容": ["" for _ in range(length)],
        "命名实体": ["" for _ in range(length)],
        "关系事实": ["" for _ in range(length)],
        "标签": ["" for _ in range(length)]
    })


def read_processed_csv():
    return pd.read_csv(
        PROCESSED_FILE_PATH,
        encoding=CSV_ENCODING,
        delimiter=CSV_DELIMITER
    )

def write_processed_csv(df):
    df.to_csv(
        PROCESSED_FILE_PATH,
        index=False,
        encoding=CSV_ENCODING,
        sep=CSV_DELIMITER
    )

def neo4j_connection():
    return GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

def generate_entity_id(sequence_id, text):
    raw = f"{sequence_id}::{text.strip()}"
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()

def load_memory_table():
    if os.path.exists(MEMORY_TABLE_PATH):
        with open(MEMORY_TABLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory_table(memory_table):
    with open(MEMORY_TABLE_PATH, "w", encoding="utf-8") as f:
        json.dump(memory_table, f, ensure_ascii=False, indent=2)

# 获取所有顺序结点
def get_ordered_sequence_nodes(tx):
    query = """
    MATCH (start:Sequence)
    WHERE NOT ()-[:next]->(start)
    WITH start
    MATCH path = (start)-[:next*]->(end)
    UNWIND nodes(path) AS n
    RETURN DISTINCT n
    """
    result = tx.run(query)
    return [record["n"] for record in result]

# 获取所有对应ID的实体结点
def get_all_entities_for_nodes(tx, node_ids):
    query = """
    MATCH (s:Sequence)-[:include]->(e)
    WHERE s.id IN $node_ids
    RETURN s.id as sequence_id, e.id as entity_id, e.name as entity_name, labels(e) as label
    """
    result = tx.run(query, node_ids=node_ids)
    entities = []
    for record in result:
        entities.append({
            "sequence_id": record["sequence_id"],
            "entity_id": record["entity_id"],
            "entity_name": record["entity_name"],
            "label": record["label"]
        })
    return entities

# 分配临时ID(大模型用)
def assign_temp_ids(entities):
    temp_entities = []
    for i, entity in enumerate(entities):
        temp_id = f"e{i + 1}"
        temp_entities.append({
            "temp_id": temp_id,
            "sequence_id": entity.get("sequence_id", ""),
            "entity_id": entity.get("entity_id", ""),
            "entity_name": entity.get("entity_name", ""),
            "label": entity.get("label", "")
        })
    return temp_entities

