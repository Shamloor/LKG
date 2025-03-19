import json
from neo4j import GraphDatabase
import config

# **Neo4j 连接**
driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD))

# **读取 JSON 文件**
with open(config.JSON_FILE_PATH, "r", encoding="utf-8") as f:
    summary_events = json.load(f)

# **确保 JSON 里有 "事件" 列表**
if not isinstance(summary_events, list) or len(summary_events) == 0:
    raise ValueError(" JSON 文件格式错误，未找到 '事件' 列表！")

# **创建事件节点 & 关系**
def create_events(tx, events):
    prev_event = None  # 记录前一个事件

    for event in events:
        event_name = event["事件"]  # 事件名称

        # **创建事件节点**
        tx.run("MERGE (e:Event {name: $name})", name=event_name)

        # **创建 :NEXT 关系**
        if prev_event:
            tx.run("""
                MATCH (e1:Event {name: $prev_name})
                MATCH (e2:Event {name: $curr_name})
                MERGE (e1)-[:NEXT]->(e2)
            """, prev_name=prev_event, curr_name=event_name)

        prev_event = event_name  # 更新上一个事件

# **运行 Neo4j 导入**
try:
    with driver.session() as session:
        session.execute_write(create_events, summary_events)
    print("事件数据成功导入到 Neo4j！")
except Exception as e:
    print(f"发生错误: {e}")

# **关闭连接**
driver.close()
