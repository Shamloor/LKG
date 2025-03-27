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
    """
    基于 sequence_id + 实体文本 生成稳定唯一的哈希 ID
    用于上下文敏感实体识别（即使 text 一样，不同行也不同）
    """
    raw = f"{sequence_id}::{text.strip()}"
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()

