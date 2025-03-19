from openai import OpenAI

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "12345678"

API_KEY = "sk-969b6309421740869719b25527b46e41"
API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CLIENT = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

TXT_FILE_PATH = "./DATA/original/罪与罚 第一部 第一章(original).txt"
CSV_FILE_PATH = "./DATA/processed/罪与罚 第一部 第一章(processed).csv"
JSON_FILE_PATH = "./DATA/summary/罪与罚 第一部 第一章(summary).json"
TMP_FILE_PATH = "./DATA/tmp/暂时文件.json"

CSV_DELIMITER = "|"