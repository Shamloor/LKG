import json
import config

driver = config.neo4j_connection()

# 读取处理好的 DataFrame
df = config.read_processed_csv()


# 清空数据库（可选）
def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")


# 创建顺序节点
def create_sequence_node(tx, index):
    tx.run("MERGE (s:Step {索引: $index})", index=index)


# 创建实体节点和三元组关系
def create_triple(tx, h, r, t, step_index):
    # 创建实体
    tx.run("MERGE (h:Entity {name: $h})", h=h)
    tx.run("MERGE (t:Entity {name: $t})", t=t)

    # 创建三元组关系
    tx.run("""
        MATCH (h:Entity {name: $h}), (t:Entity {name: $t})
        MERGE (h)-[rel:RELATION {type: $r}]->(t)
    """, h=h, t=t, r=r)

    # 连接到对应顺序节点
    tx.run("""
        MATCH (e:Entity), (s:Step {索引: $index})
        WHERE e.name IN [$h, $t]
        MERGE (s)-[:include]->(e)
    """, h=h, t=t, index=step_index)


# 创建顺序连接
def connect_sequence_nodes(tx, from_index, to_index):
    tx.run("""
        MATCH (a:Step {索引: $from_index}), (b:Step {索引: $to_index})
        MERGE (a)-[:next]->(b)
    """, from_index=from_index, to_index=to_index)


# 执行图谱构建
with driver.session() as session:
    session.execute_write(clear_database)  # 如不清空，可注释掉

    prev_index = None

    for _, row in df.iterrows():
        index = row["索引"]
        step_node_id = f"Index_{index}"
        triples_json = row["三元组"]

        try:
            triple_data = json.loads(triples_json)
            triples = triple_data.get("三元组", [])
        except Exception as e:
            print(f"解析三元组失败：索引 {index}, 原始数据: {triples_json}")
            continue

        session.execute_write(create_sequence_node, index)

        for h, r, t in triples:
            session.execute_write(create_triple, h, r, t, index)

        if prev_index is not None:
            session.execute_write(connect_sequence_nodes, prev_index, index)

        prev_index = index

print("图谱构建完成")