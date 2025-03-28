import json

from neo4j import GraphDatabase
import config

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

    prompt = f"""本任务中，凡是用于替代或泛指某一对象/事件的词/短语，都视为“指代表达”。
    例如：
    - "他"、"她"、"它"（人称代词）
    - "这件事"、"那个人"、"某个人"、"年轻人"、"这里"、"那里"（泛指性短语）
    请在以下实体中判断哪些具有这种“指代表达”功能
    句子："{text}"
    该句子中包含的命名实体如下：
    {entity_json}
    返回指代表达的命名实体对应的 "id"（JSON 数组）。JSON 格式如下：
    ["e1", "e5"]
    请按JSON格式返回纯文本，不要返回Markdown格式内容，不要添加格式以外信息
    如果无具有指代功能的实体，请返回空列表 []
    """

    response_text = config.llm_api(prompt)
    print("答案为" + response_text)
    try:
        pronoun_ids = json.loads(response_text)
        filtered = [e for e in temp_entities if e["temp_id"] in pronoun_ids]
        return restore_entities(filtered)
    except Exception as e:
        print(f"[!] JSON解析失败: {e}")
        print("返回内容:", response_text)
        return []

def test_pronoun_detection_from_graph():
    driver = config.neo4j_connection()
    test_node_ids = ["s1"]

    with driver.session() as session:
        entities = session.read_transaction(get_all_entities_for_nodes, test_node_ids)

    text = "7月初，在天气非常炎热的季节，将近傍晚，有个年轻人走出他在某巷二房东那儿租到的小屋，来到街上，慢腾腾往К桥走去，仿佛犹疑不决似的。"
    result = pronoun_detection(text, entities)

    print("代词识别结果：")
    if result:
        for r in result:
            print(r)
    else:
        print("无代词。")

if __name__ == "__main__":
    test_pronoun_detection_from_graph()