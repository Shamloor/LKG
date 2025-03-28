import json
import config

import json
import config

def process_relations_and_generate_graph_data():
    """
    从CSV中提取每行关系事实，构建顺序节点、实体节点、边结构
    :return: (sequence_nodes, entity_nodes, edge_list)
    """
    df = config.read_processed_csv()

    sequence_nodes = []
    entity_nodes = []
    edge_list = []
    last_sequence_id = None
    skipped_count = 0

    for idx, row in df.iterrows():
        sequence_id = f"s{idx + 1}"

        # 始终构建顺序节点
        sequence_nodes.append({
            "id": sequence_id,
            "type": "Sequence",
            "text": row["内容"] if "内容" in row and isinstance(row["内容"], str) else ""
        })

        # 默认当前节点没有处理关系事实
        processed_relations = False

        # 获取关系事实列
        raw_value = row.get("关系事实", "")

        if isinstance(raw_value, str) and raw_value.strip() != "":
            try:
                relation_json = json.loads(raw_value)
                relation_list = relation_json.get("关系事实", [])

                for relation in relation_list:
                    head_text = relation["头实体"]["文本"]
                    head_type = relation["头实体"]["类型"]
                    rel_text  = relation["关系"]["文本"]
                    tail_text = relation["尾实体"]["文本"]
                    tail_type = relation["尾实体"]["类型"]

                    # 每次都生成新的唯一实体 ID
                    head_id = config.generate_entity_id(sequence_id, head_text)
                    tail_id = config.generate_entity_id(sequence_id, tail_text)

                    entity_nodes.append({"id": head_id, "text": head_text, "type": head_type})
                    entity_nodes.append({"id": tail_id, "text": tail_text, "type": tail_type})

                    edge_list.append({"start": head_id, "rel": rel_text, "end": tail_id})
                    edge_list.append({"start": sequence_id, "rel": "include", "end": head_id})
                    edge_list.append({"start": sequence_id, "rel": "include", "end": tail_id})

                processed_relations = True

            except Exception as e:
                print(f"[!] 第{idx + 1}行解析失败：{e}")
                skipped_count += 1
        else:
            print(f"[!] 第{idx + 1}行关系为空，仅构建顺序链")

        # 无论有没有实体，都连接顺序节点
        if last_sequence_id:
            edge_list.append({
                "start": last_sequence_id,
                "rel": "next",
                "end": sequence_id
            })
        last_sequence_id = sequence_id

    print(f"处理完成，共跳过异常关系数据 {skipped_count} 条。")
    print(f"共构建顺序节点 {len(sequence_nodes)} 个。")
    return sequence_nodes, entity_nodes, edge_list




def import_graph_to_neo4j(sequence_nodes, entity_nodes, edge_list):
    driver = config.neo4j_connection()

    with driver.session() as session:
        # 创建实体节点（动态使用类型作为标签）
        for node in entity_nodes:
            label = node["type"]
            session.run(
                f"""
                MERGE (e:`{label}` {{id: $id}})
                SET e.name = $text
                """,
                id=node["id"],
                text=node["text"]
            )

        # 创建顺序节点（固定使用 Sequence 标签）
        for node in sequence_nodes:
            session.run(
                """
                MERGE (s:Sequence {id: $id})
                SET s.type = $type,
                    s.text = $text
                """,
                id=node["id"],
                type=node["type"],
                text=node.get("text", "")
            )

        # 创建边（动态关系名）
        for edge in edge_list:
            session.run(
                f"""
                MATCH (a {{id: $start}})
                MATCH (b {{id: $end}})
                MERGE (a)-[r:`{edge['rel']}`]->(b)
                """,
                start=edge["start"],
                end=edge["end"]
            )

    driver.close()
    print("所有节点和关系已成功导入 Neo4j（节点类型 = 标签）。")

if __name__ == "__main__":
    seq_nodes, ent_nodes, edges = process_relations_and_generate_graph_data()
    import_graph_to_neo4j(seq_nodes, ent_nodes, edges)