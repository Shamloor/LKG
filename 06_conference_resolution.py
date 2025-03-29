import json
import config
from collections import defaultdict

# Neo4j 驱动
driver = config.neo4j_connection()

# 记忆表初始化
memory_table = []

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
                "frequency": 1
            }
            memory_table.append(new_memory)
            memory_id_counter += 1

        elif op_type == "update":
            memory_id = op.get("memory_id")
            mem = next((m for m in memory_table if m["memory_id"] == memory_id), None)
            if not mem or value not in temp_map:
                continue

            ent = temp_map[value]
            if key == "name":
                mem["name"] = value
            elif key == "alias":
                if value not in mem["alias"]:
                    mem["alias"].append(value)

            # 添加实体与位置信息（如果没有）
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

    context = "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts)])

    # 拼接指代的命名实体
    entity_lines = [
        {"id": e["temp_id"], "name": e["entity_name"]}
        for e in temp_entities
    ]
    entity_json = json.dumps(entity_lines, ensure_ascii=False, indent=2)

    # 拼接记忆表
    memory_lines = [
        {"memory_id": m["memory_id"], "name": m["name"], "alias": m["alias"]}
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
    - 是否替换记忆表中"name"和"alias"中的一个元素？(replace)
    
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
    - operation: 两种操作类型分别为"create" 、"update"、"delete"、"replace"。
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

def graph_update(memory_table, temp_entities, updated_set, texts):
    context = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(texts)])
    # 构造 prompt 输入
    memory_lines = [
        {"memory_id": m["memory_id"], "name": m["name"], "alias": m.get("alias", [])}
        for m in memory_table if m.get("name")
    ]
    memory_json = json.dumps(memory_lines, ensure_ascii=False, indent=2)

    entity_lines = [
        {"entity_id": e["temp_id"], "name": e["entity_name"]}
        for e in temp_entities if e["entity_id"] not in updated_set
    ]
    entity_json = json.dumps(entity_lines, ensure_ascii=False, indent=2)

    if not entity_lines:
        return  # 本轮窗口内所有实体都已处理，跳过

    prompt = f"""
    以下是两个列表：

    [记忆表]：每条是已确认的记忆实体，包含 memory_id、name 和别名 alias
    {memory_json}

    [候选实体]：是当前窗口中出现的实体，包含临时编号 temp_id 和原始名称 name
    {entity_json}
    
    文本内容如下：
    {context}

    请你判断：记忆表中的哪个 name 可以用于替换哪个候选实体的名称，匹配关系为一对一或一对多。
    输出格式为 JSON 数组，每个元素形如：
    {{"memory_id": "m1", "entity_id": "e4"}}

    如果没有可替换项或者无法判断，请返回空数组 []
    返回格式必须是合法 JSON，禁止包含解释说明，禁止Markdown格式输出。
    """

    response_text = config.llm_api(prompt)
    print("[图谱替换建议]", response_text)

    try:
        replace_pairs = json.loads(response_text)
    except Exception as e:
        print(f"[!] JSON 解析失败: {e}")
        return

    # 构建 temp_id -> 实体信息 映射
    temp_map = {e["temp_id"]: e for e in temp_entities}

    with driver.session() as session:
        for pair in replace_pairs:
            memory_id = pair.get("memory_id")
            temp_id = pair.get("entity_id")
            memory_entry = next((m for m in memory_table if m["memory_id"] == memory_id), None)
            entity_info = temp_map.get(temp_id)

            if not memory_entry or not entity_info:
                continue

            new_name = memory_entry["name"]
            entity_id = entity_info["entity_id"]
            sequence_id = entity_info["sequence_id"]

            if entity_id in updated_set:
                continue  # 已处理过的跳过

            session.run(
                """
                MATCH (s:Sequence {id: $sequence_id})-[:include]->(e)
                WHERE e.id = $entity_id
                SET e.name = $new_name
                """,
                sequence_id=sequence_id,
                entity_id=entity_id,
                new_name=new_name
            )

            updated_set.add(entity_id)

    print(f"[图谱更新] 本轮替换 {len(replace_pairs)} 个实体。")



if __name__ == "__main__":
    memory_table = config.load_memory_table()

    # 全图所有数据
    with driver.session() as session:
        sequence_nodes = session.execute_read(get_ordered_sequence_nodes)
        node_ids = [n["id"] for n in sequence_nodes]
        all_entities = session.execute_read(get_all_entities_for_nodes, node_ids)
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
        temp_entities = assign_temp_ids(center_entities)

        # 执行记忆更新（更新 memory_table）
        memory_update(texts, temp_entities, memory_table)

    # === 第二轮：滑动窗口，生成最终记忆表 ===
    updated_set = set()

    for i in range(len(sequence_nodes)):
        center_node = sequence_nodes[i]
        center_sid = center_node["id"]

        # 提取上下文窗口（带边界控制）
        start = max(0, i - half_window)
        end = min(len(sequence_nodes), i + half_window + 1)
        window_nodes = sequence_nodes[start:end]
        texts = [node["text"] for node in window_nodes]

        # 提取中心节点的实体
        center_entities = character_entity_map.get(center_sid, [])
        temp_entities = assign_temp_ids(center_entities)

        # 执行图谱更新（只针对中心节点）
        graph_update(memory_table, temp_entities, updated_set, texts)
