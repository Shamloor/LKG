import csv
import json
import config  # 需要提供 config.py，包含 API 配置

# DeepSeek API 调用
def llm_for_ner(prompt):
    """
    调用 DeepSeek API 进行 NER 任务
    """
    response = config.CLIENT.chat.completions.create(
        model="deepseek-v3",
        messages=[
            #{"role": "user", "content": f"请从以下文本中识别命名实体及其类别，并以 JSON 格式返回：\n{text}"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content  # 获取 API 返回的内容


# 读取 CSV 文件
ner_results = []

with open(config.SENTENCE_SPLIT_FILE_PATH, "r", encoding=config.CSV_ENCODING) as file:
    reader = csv.DictReader(file, delimiter=config.CSV_DELIMITER)
    rows = list(reader)  # 读取所有行

# 处理 NER
for row in rows:
    index = row["句子"]  # 句子索引（编号）
    text = row["内容"]  # 需要处理的文本

    # 调用 API 进行 NER
    print(f"Processing NER for index {index}...")
    prompt = ("从以下文本中识别命名实体及其类别，并以 JSON 格式返回：\n" + text + ""
              "请按JSON格式返回，不要添加格式以外信息")
    ner_response = llm_for_ner(prompt)

    # 假设 API 返回 JSON 格式：{"entities": [{"text": "年轻人", "type": "Person"}]}
    try:
        ner_data = json.loads(ner_response)
        entities = ner_data.get("entities", [])

        # 记录NER结果
        for entity in entities:
            ner_results.append([index, entity["text"], entity["type"]])

    except json.JSONDecodeError:
        print(ner_response)
        print(f"Error parsing NER response for index {index}")
        continue

# 写入 NER 结果到 CSV
with open(config.NER_FILE_PATH, "w", encoding=config.CSV_ENCODING, newline="") as file:
    writer = csv.writer(file, delimiter=config.CSV_DELIMITER)
    writer.writerow(["句子", "实体", "类别"])  # CSV 头部
    writer.writerows(ner_results)

print(f"NER results saved to {config.NER_FILE_PATH}")
