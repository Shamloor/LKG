import re
import json
from openai import OpenAI

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "12345678"

API_KEY = "sk-969b6309421740869719b25527b46e41"
API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CLIENT = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

#TXT_FILE_PATH = "DATA/original/罪与罚 第一部 第一章(original).txt"
TXT_FILE_PATH = "DATA/original/tmp.txt"
#SENTENCE_SPLIT_FILE_PATH = "DATA/split/罪与罚 第一部 第一章(split).csv"
SENTENCE_SPLIT_FILE_PATH = "DATA/split/tmp.csv"
#NER_FILE_PATH = "DATA/ner/罪与罚 第一部 第一章(ner).csv"
NER_FILE_PATH = "DATA/ner/tmp.csv"
RE_FILE_PATH = "DATA/re/罪与罚 第一部 第一章(re).csv"
TMP_FILE_PATH = "DATA/tmp/暂时文件.json"

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

def clean_api_response(api_response):
    match = re.search(r'{"命名实体":\s*\[.*?\]}', api_response, re.DOTALL)

    if match:
        clean_json = match.group(0)
        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            print("JSON 解析失败，可能仍有格式问题")
            return None
    else:
        print("未找到有效 JSON 结构")
        return None