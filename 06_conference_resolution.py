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

def get_entities_for_nodes(tx, node_ids):
    query = """
    MATCH (s:Sentence)-[:include]->(e:Entity)
    WHERE id(s) IN $node_ids
    RETURN id(s) as sentence_id, id(e) as entity_id, e.name as entity_name
    """
    result = tx.run(query, node_ids=node_ids)
    entity_map = {}
    for record in result:
        sid = record["sentence_id"]
        entity = {
            "entity_id": record["entity_id"],
            "entity_name": record["entity_name"]
        }
        entity_map.setdefault(sid, []).append(entity)
    return entity_map

def build_prompt(texts, entity_map):
    prompt = "以下是小说中的三句话，请进行代词消解任务：\n\n"
    for i, text in enumerate(texts):
        prompt += f"{i+1}. {text}\n"
    prompt += "\n这些句子中出现的实体包括：\n"
    for sid, entities in entity_map.items():
        for entity in entities:
            prompt += f"- {entity['entity_name']}（entity_id={entity['entity_id']}，出现在句子 {sid}）\n"
    prompt += "\n请列出每个代词及其指代的实体。\n输出格式：\n代词：[文本]，位置：[顺序节点id]，指代：[实体名]（entity_id）"
    return prompt

def parse_response(response_text):
    # 简单解析：每行格式：
    # 代词：[他]，位置：[123]，指代：[拉斯科尔尼科夫]（entity_id=456）
    results = []
    for line in response_text.strip().splitlines():
        try:
            pronoun = line.split("代词：[")[1].split("]")[0]
            node_id = int(line.split("位置：[")[1].split("]")[0])
            alias = line.split("指代：[")[1].split("]")[0]
            entity_id = int(line.split("entity_id=")[1].split(")")[0])
            results.append({
                "pronoun": pronoun,
                "alias": alias,
                "node_id": node_id,
                "entity_id": entity_id
            })
        except Exception as e:
            print(f"解析失败：{line}，错误：{e}")
    return results

def process_initial_windows():
    global memory_table
    with driver.session() as session:
        nodes = session.read_transaction(get_ordered_sequence_nodes)
        node_ids = [node.id for node in nodes]
        texts = [node["text"] for node in nodes]

        for i in range(len(nodes) - 2):  # 窗口大小为 3
            window_nodes = nodes[i:i+3]
            window_ids = [n.id for n in window_nodes]
            window_texts = [n["text"] for n in window_nodes]

            entity_map = session.read_transaction(get_entities_for_nodes, window_ids)
            prompt = build_prompt(window_texts, entity_map)
            response_text = config.llm_api(prompt)

            results = parse_response(response_text)
            memory_table.extend(results)

            print(f"窗口{i}-{i+2}处理完成，记忆表大小：{len(memory_table)}")

def test_print_sequence_nodes():
    driver = config.neo4j_connection()
    with driver.session() as session:
        nodes = session.read_transaction(get_ordered_sequence_nodes)
        print("共获取到顺序节点数量：", len(nodes))
        for i, node in enumerate(nodes):
            print(f"{i+1}. {node.get('text')}")

if __name__ == "__main__":
    test_print_sequence_nodes()



