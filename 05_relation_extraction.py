import pandas as pd
import json
import config  # 你的配置文件，包含路径、编码、模型API等

def safe_load_json(entity_str):
    """
    处理命名实体列中的字符串格式，尝试去掉头尾多余引号并解析为 JSON。
    """
    if isinstance(entity_str, str):
        entity_str = entity_str.strip('"').replace('""', '"')
        try:
            return json.loads(entity_str)
        except json.JSONDecodeError:
            print("JSON 解析失败，原始字符串：", entity_str)
            return {}
    return {}

def construct_prompt(entities_json, content):
    """
    将实体信息和内容拼接成 prompt。
    """
    return f"""请根据以下内容和命名实体，抽取人物或地点之间的三元组关系（subject, predicate, object）并用 JSON 格式返回。

命名实体：
{json.dumps(entities_json, ensure_ascii=False, indent=2)}

内容：
{content}

输出格式：
{{
  "triples": [
    ["实体1", "关系", "实体2"],
    ...
  ]
}}"""

def main():
    # 读取数据
    df = pd.read_csv(
        config.PROCESSED_FILE_PATH,
        encoding=config.CSV_ENCODING,
        delimiter=config.CSV_DELIMITER
    )

    responses = []

    for idx, row in df.iterrows():
        # 解析命名实体列
        raw_entity = row.get("命名实体", "")
        entity_json = safe_load_json(raw_entity)
        entity_list = entity_json.get("命名实体", [])

        # 获取内容列
        content = row.get("内容", "")

        # 构造 prompt
        prompt = construct_prompt(entity_list, content)

        # 调用大模型 API
        response = config.llm_api(prompt)

        # 打印 response
        print(f"[第{idx+1}行] 模型返回：", response)

        # 保存 response 到列表
        responses.append(response)

    # 将 response 写入到“三元组”列
    df["三元组"] = responses

    df.to_csv(
        config.PROCESSED_FILE_PATH,
        index=False,
        encoding=config.CSV_ENCODING,
        sep=config.CSV_DELIMITER
    )

if __name__ == "__main__":
    main()