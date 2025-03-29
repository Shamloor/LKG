import json
import config
from collections import defaultdict

# Neo4j 驱动
driver = config.neo4j_connection()

# 记忆表初始化
memory_table = []

def graph_update(memory_table, temp_entities, updated_set, texts):
    context = "\n".join([f"{i + 1}. {t}" for i, t in enumerate(texts)])
    # 构造 prompt 输入
    memory_lines = [
        {"memory_id": m["memory_id"], "name": m["name"], "alias": m.get("alias", []),
         "description": m["description"]}
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

    [候选实体]：是当前窗口中出现的实体，包含实体编号 entity_id 和名称 name
    {entity_json}
    
    文本内容如下：
    {context}

    请你根据文本内容判断：记忆表中的哪个 name 可以用于替换哪个候选实体的名称，匹配关系为一对一或一对多。
    输出格式为 JSON 数组，每个元素形如：
    {{"memory_id": "m1", "entity_id": "e4"}}

    如果没有可替换项或判断条件不足，请返回空数组 []
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
        temp_entities = config.assign_temp_ids(center_entities)

        # 执行图谱更新（只针对中心节点）
        graph_update(memory_table, temp_entities, updated_set, texts)
