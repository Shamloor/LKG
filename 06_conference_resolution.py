import json
import config
from collections import defaultdict

# 获取 Neo4j 驱动
driver = config.neo4j_connection()

# 记忆表初始化
memory_table = []

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

def get_all_entities_for_nodes(tx, node_ids):
    query = """
    MATCH (s:Sequence)-[:include]->(e)
    WHERE s.id IN $node_ids
    RETURN s.id as sequence_id, e.id as entity_id, e.name as entity_name
    """
    result = tx.run(query, node_ids=node_ids)
    entities = []
    for record in result:
        entities.append({
            "sequence_id": record["sequence_id"],
            "entity_id": record["entity_id"],
            "entity_name": record["entity_name"]
        })
    return entities

def assign_temp_ids(entities):
    temp_entities = []
    for i, entity in enumerate(entities):
        temp_id = f"e{i + 1}"
        temp_entities.append({
            "temp_id": temp_id,
            "sequence_id": entity.get("sequence_id", ""),
            "entity_id": entity.get("entity_id", ""),
            "entity_name": entity.get("entity_name", "")
        })
    return temp_entities

def restore_entities(temp_entities):
    return [
        {
            "sequence_id": e.get("sequence_id", ""),
            "entity_id": e.get("entity_id", ""),
            "entity_name": e.get("entity_name", "")
        }
        for e in temp_entities
    ]

def pronoun_detection(text, entities):
    temp_entities = assign_temp_ids(entities)
    entity_lines = [
        {"id": e["temp_id"], "name": e["entity_name"]}
        for e in temp_entities
    ]
    entity_json = json.dumps(entity_lines, ensure_ascii=False, indent=2)

    prompt = f"""
    本任务中，凡是用于替代或泛指某一对象/事件的词/短语，都视为“指代表达”，而所有“具备被指代可能性”的实体表达可称为“指代候选”。
    例如：
    - "他"、"她"、"它"（人称代词）
    - "这件事"、"那个人"、"某个人"、"年轻人"、"这里"、"那里"、“这件事”（泛指性短语）
    - 人物名字、地点名、角色身份（如“母亲”、“年轻人”、“审讯官”）
    请在以下实体中判断哪些具有“指代表达”或“指代候选”功能
    句子："{text}"
    该句子中包含的命名实体如下：
    {entity_json}
    返回“指代表达”或“指代候选”的命名实体对应的 "id"（JSON 数组）。JSON 格式如下：
    ["e1", "e5"]
    请按JSON格式返回纯文本，不要返回Markdown格式内容，不要添加格式以外信息
    如果无具有指代功能的实体，请返回空列表 []
    """

    response_text = config.llm_api(prompt)
    print("指代结点为: " + response_text)
    try:
        pronoun_ids = json.loads(response_text)
        filtered = [e for e in temp_entities if e["temp_id"] in pronoun_ids]
        return restore_entities(filtered)
    except Exception as e:
        print(f"[!] JSON解析失败: {e}")
        print("返回内容:", response_text)
        return []

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
    
    请你判断每个临时实体：
    - 是否要创建新的记忆条目？（create）
    - 是否指代某个已有记忆实体？（update）
    - 是否应该从记忆表中移除某条（因错误或冗余）？（delete）
    
    请返回 JSON 数组，格式如下：
    [
      {{
        "operation": "create",
        "content": "年轻人",
        "isname": "yes",
        "confidence": 0.92
      }},
      {{
        "operation": "update",
        "memory_id": "m2",
        "content": "他",
        "isname": "no",
        "confidence": 0.87
      }},
      {{
        "operation": "delete",
        "memory_id": "m3",
        "content": "不相关的内容",
        "isname": "no",
        "confidence": 0.4
      }}
    ]
    
    说明：
    - operation: 三种操作类型分别为"create" 、"update"和"delete"
    - content: 实体的名称；
    - isname: 是否是特指名称（如人名、定指短语）；
    - confidence: 模型判断置信度，范围为 0 到 1；
    - 如果没有任何操作，请返回空数组 []
    请只返回合法 JSON 纯文本，不要添加解释、说明或 Markdown。
"""

    # 5. 调用大模型
    response_text = config.llm_api(prompt)
    print("[模型返回] ", response_text)

    try:
        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"[!] JSON 解析失败: {e}")
        return []

if __name__ == "__main__":
    memory_table = config.load_memory_table()
    # 全图所有数据
    with driver.session() as session:
        sequence_nodes = session.read_transaction(get_ordered_sequence_nodes)
        node_ids = [n["id"] for n in sequence_nodes]
        all_entities = session.read_transaction(get_all_entities_for_nodes, node_ids)

    # 实体按顺序结点分组
    entity_map = defaultdict(list)
    for ent in all_entities:
        entity_map[ent["sequence_id"]].append(ent)

    window_size = 3
    candidates_cache = {}  # 缓存每个顺序节点的指代表达或指代候选

    # 滑动窗口
    for i in range(len(sequence_nodes) - window_size + 1):
        window_nodes = sequence_nodes[i:i + window_size]

        # 对窗口中的每一个顺序节点调用一次 pronoun_detection（只调用一次）
        for node in window_nodes:
            sid = node["id"]
            if sid not in candidates_cache:
                text = node["text"]
                entities = entity_map.get(sid, [])
                result = pronoun_detection(text, entities)
                candidates_cache[sid] = result

        # 合并当前窗口中所有候选实体
        all_candidates = []
        for node in window_nodes:
            sid = node["id"]
            all_candidates.extend(candidates_cache.get(sid, []))

        # 对这些实体分配临时ID
        temp_entities = assign_temp_ids(all_candidates)

        # 获取当前窗口所对应顺序结点的所有text
        texts = [node["text"] for node in window_nodes]

        print(texts)