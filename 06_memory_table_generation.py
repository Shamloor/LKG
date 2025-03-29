import json
from collections import defaultdict

import config

"""
记忆表结构
[
{
    "memory_id":
    "name":
    "alias":
    "entity_id":
    "sequence_id":
    "frequency":
    "description":
}
]
"""


def operation_parse(temp_entities, api_result, memory_table):
    # 将 temp_entities 映射成一个查找表：{entity_name: entity_info}
    temp_map = {e["entity_name"]: e for e in temp_entities}

    # 用于生成新的 memory_id
    memory_id_counter = len(memory_table) + 1

    for op in api_result:
        op_type = op.get("operation")
        key = op.get("key")
        value = op.get("value")

        if op_type == "create":
            if value not in temp_map:
                continue  # 跳过未匹配到实体的 create 请求

            ent = temp_map[value]
            new_memory = {
                "memory_id": f"m{memory_id_counter}",
                "name": value if key == "name" else None,
                "alias": [value] if key == "alias" else [],
                "entity_id": [ent["entity_id"]],
                "sequence_id": [ent["sequence_id"]],
                "frequency": 1,
                "description": ""
            }
            memory_table.append(new_memory)
            memory_id_counter += 1


        elif op_type == "update":
            memory_id = op.get("memory_id")
            if value not in temp_map:
                continue
            ent = temp_map[value]
            mem = next((m for m in memory_table if m["memory_id"] == memory_id), None)

            if not mem:
                # 模型返回了不存在的 memory_id，自动视作 create
                mem = {
                    "memory_id": memory_id,
                    "name": value if key == "name" else None,
                    "alias": [value] if key == "alias" else [],
                    "entity_id": [ent["entity_id"]],
                    "sequence_id": [ent["sequence_id"]],
                    "frequency": 1,
                    "description": ""
                }
                memory_table.append(mem)
                continue  # 创建后跳过后续 update（避免重复）

            # 否则就是正常的 update 操作
            if key == "name":
                mem["name"] = value
            elif key == "alias":
                if value not in mem["alias"]:
                    mem["alias"].append(value)
            if ent["entity_id"] not in mem["entity_id"]:
                mem["entity_id"].append(ent["entity_id"])
            if ent["sequence_id"] not in mem["sequence_id"]:
                mem["sequence_id"].append(ent["sequence_id"])
            mem["frequency"] += 1

        elif op_type == "delete":
            memory_id = op.get("memory_id")
            mem = next((m for m in memory_table if m["memory_id"] == memory_id), None)
            if not mem:
                continue

            if key == "alias" and value in mem["alias"]:
                mem["alias"].remove(value)

            if key == "name" and value in mem["name"]:
                mem["name"].remove(value)

            # 删除后如果 name 和 alias 都为空，可以选择整个 memory 条目清除
            if not mem["name"] and not mem["alias"]:
                memory_table.remove(mem)

        elif op_type == "replace":
            memory_id = op.get("memory_id")
            value1 = op.get("value1")  # 要替换的旧值
            value2 = op.get("value2")  # 替换后的新值
            mem = next((m for m in memory_table if m["memory_id"] == memory_id), None)
            if not mem:
                continue

            # 替换 name
            if mem.get("name") == value1:
                mem["name"] = value2

            # 替换 alias 中的旧值
            if value1 in mem.get("alias", []):
                mem["alias"] = [value2 if a == value1 else a for a in mem["alias"]]

    config.save_memory_table(memory_table)


# 更新记忆表
def memory_update(texts, temp_entities, memory_table):
    context = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(texts)])

    # 拼接指代的命名实体
    entity_lines = [
        {"id": e["temp_id"], "name": e["entity_name"]}
        for e in temp_entities
    ]
    entity_json = json.dumps(entity_lines, ensure_ascii=False, indent=2)

    # 拼接记忆表
    memory_lines = [
        {"memory_id": m["memory_id"], "name": m["name"], "alias": m["alias"], "description": m["description"]}
        for m in memory_table
    ]
    memory_json = json.dumps(memory_lines, ensure_ascii=False, indent=2)

    # 构造 Prompt
    prompt = f"""
    该任务为根据文本内容、实体列表和已有记忆表，判断每个实体是否需要更新到记忆表中。
    文本内容如下：
    {context}
    候选实体列表如下：
    {entity_json}  
    记忆表如下（已有记忆实体）：
    {memory_json}

    请注意，记忆表中：
    - "name"代表一个实体唯一的标记，如人物名字
    - "alias"代表一个实体的别名，可以存在多个
    - 对于泛指的表示指代的词语不能添加进记忆表中，如"他"、"她"、"人们"
    请你判断每个实体：
    - 是否要创建新的记忆条目？（create）
    - 是否指代某个已有记忆实体？（update）
    - 是否应该从记忆表中移除某条（因错误或冗余）？（delete）
    - 是否替换记忆表中"name"或"alias"中的一个元素？(replace)

    请返回 JSON 数组，格式如下：
    [
      {{
        "operation": "create",
        "key": "alias",
        "value": "别名",
      }},
      {{
        "operation": "update",
        "memory_id": "m1"
        "key": "name",
        "value": "名字"
      }},
      {{
        "operation": "delete",
        "memory_id": "m1",
        "key": "alias",
        "value": "别名"
      }},
      {{
        "operation": "replace",
        "memory_id": "m1",
        "value1": "名字",
        "value2": "别名"
      }}
    ]

    说明：
    - operation: 四种操作类型分别为"create" 、"update"、"delete"、"replace"。
    - 四种操作均只针对记忆表的"name"和"alias"。
    - 四种操作的返回格式严格参照示例。
    - 如果不用执行任何操作，请返回空数组 []
    请只返回合法 JSON 纯文本，不要添加解释、说明或 Markdown。
"""

    response_text = config.llm_api(prompt)
    print("[模型返回] ", response_text)

    try:
        api_result = json.loads(response_text)
        operation_parse(temp_entities, api_result, memory_table)
    except Exception as e:
        print(f"[!] JSON 解析失败: {e}")

if __name__ == "__main__":
    memory_table = config.load_memory_table()

    # Neo4j 驱动
    driver = config.neo4j_connection()

    # 全图所有数据
    with driver.session() as session:
        sequence_nodes = session.execute_read(config.get_ordered_sequence_nodes)
        node_ids = [n["id"] for n in sequence_nodes]
        all_entities = session.execute_read(config.get_all_entities_for_nodes, node_ids)
        # 筛选出 label 包含 "人物" 的实体
        character_entities = [e for e in all_entities if "人物" in e["label"]]

    # 实体按顺序结点分组
    character_entity_map = defaultdict(list)
    for ent in character_entities:
        character_entity_map[ent["sequence_id"]].append(ent)

    window_size = 5
    half_window = window_size // 2

    # === 第一轮：滑动窗口，生成最终记忆表 ===
    memory_table = config.load_memory_table()

    for i in range(len(sequence_nodes)):
        center_node = sequence_nodes[i]
        center_sid = center_node["id"]

        # 提取上下文窗口（带边界控制）
        start = max(0, i - half_window)
        end = min(len(sequence_nodes), i + half_window + 1)
        window_nodes = sequence_nodes[start:end]
        texts = [node["text"] for node in window_nodes]

        # 提取中心节点的实体（当前只构建记忆，不替换）
        center_entities = character_entity_map.get(center_sid, [])
        temp_entities = config.assign_temp_ids(center_entities)

        # 执行记忆更新（更新 memory_table）
        memory_update(texts, temp_entities, memory_table)