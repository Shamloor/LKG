import json
import os
from neo4j import GraphDatabase
from openai import OpenAI
import re
import config

driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))

# **读取 Neo4j 里的所有事件（返回 `id` 和 `name`）**
def get_all_events(tx):
    query = "MATCH (e:Event) RETURN id(e) AS id, e.name AS name"
    result = tx.run(query)
    return [{"id": record["id"], "name": record["name"]} for record in result]

# **发送事件列表到 LLM，让它分类**
def classify_events(events):
    # **构造 ID-事件映射，确保 LLM 只看到 ID**
    id_to_event = {event["id"]: event["name"] for event in events}

    prompt = f"""
    请对以下事件进行分类，每个事件只能属于以下两类之一：
    1. 交互性事件（Interaction Event）：涉及两个或更多人物的对话、争执、互动
    2. 非交互性事件（Non-Interaction Event）：仅描述单个人物的独立行动，没有涉及其他人物

    事件列表（仅提供 ID 以确保匹配）：
    {json.dumps(list(id_to_event.keys()), indent=4)}

    请按照以下 JSON 格式返回，不要添加额外的文本：
    {{
        "交互性事件": [1, 3, 5],
        "非交互性事件": [2, 4, 6]
    }}
    """

    response = config.CLIENT.chat.completions.create(
        model="deepseek-v3",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )

    print("LLM 原始返回内容:", response)

    # 数据清洗
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        json_data = json_match.group(1)  # 提取 JSON 内部内容
        try:
            classification = json.loads(json_data)
            return classification
        except json.JSONDecodeError as e:
            print("JSON 解析失败，错误信息:", e)
            return None
    else:
        print("LLM 输出不包含 JSON 数据")
        return None

# **保存 API 返回的分类结果到 JSON 文件**
def save_classification_results(classification):
    output_file = "./DATA/tmp/事件分类结果.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(classification, f, ensure_ascii=False, indent=4)
    print(f"分类结果已保存到 {output_file}")

# **使用 `id` 更新事件分类**
def update_event_category(tx, event_id, category):
    query = """
    MATCH (e:Event) WHERE elementId(e) = $event_id
    SET e.category = $category
    RETURN e
    """
    tx.run(query, event_id=event_id, category=category)

# **执行流程**
with driver.session() as session:
    print("读取 Neo4j 事件数据...")
    events = session.execute_read(get_all_events)

    if not events:
        print("没有找到任何事件，检查 Neo4j 数据库")
    else:
        print(f"找到 {len(events)} 个事件，正在发送到 LLM 进行分类...")
        classified_events = classify_events(events)

        if classified_events:
            # **保存分类结果到本地文件**
            save_classification_results(classified_events)

            print("事件分类成功，正在更新 Neo4j...")
            with driver.session() as session:
                for event_id in classified_events.get("交互性事件", []):
                    session.execute_write(update_event_category, event_id, "交互性事件")

                for event_id in classified_events.get("非交互性事件", []):
                    session.execute_write(update_event_category, event_id, "非交互性事件")

            print("所有事件分类已写入 Neo4j")

# **关闭 Neo4j 连接**
driver.close()
