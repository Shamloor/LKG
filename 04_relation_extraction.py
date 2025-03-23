import json
import re
import pandas as pd
import config

# 加载数据
df = config.read_processed_csv()
df["关系事实"] = None

for i, row in df.iterrows():
    content = row["内容"]
    try:
        raw_entities = json.loads(row["命名实体"])
    except Exception as e:
        print(f"第{i}行命名实体解析失败: {e}")
        continue

    if len(raw_entities) < 2:
        continue  # 跳过

    # 添加临时索引：E1, E2, ...
    indexed_entities = []
    for idx, ent in enumerate(raw_entities):
        ent_with_index = {
            "index": f"E{idx+1}",
            "text": ent["文本"],
            "type": ent["类型"]
        }
        indexed_entities.append(ent_with_index)

    # 构造 prompt
    prompt = f"""以下是文本内容：
{content}

这是文本中的命名实体（已加临时索引）：
{json.dumps(indexed_entities, ensure_ascii=False, indent=2)}

请根据上述文本和实体，抽取所有存在的关系，并使用"索引 - 关系(方向) - 索引"的形式输出。
如果没有关系，请返回空。
"""

    valid_indexes = {ent["index"] for ent in indexed_entities}
    index2entity = {ent["index"]: ent for ent in indexed_entities}

    for attempt in range(3):
        response = config.llm_api(prompt)
        relations = []
        error = False

        for line in response.strip().split("\n"):
            match = re.match(r"(E\d+)\s*-\s*(.+?)\((.+?)\)\s*-\s*(E\d+)", line)
            if not match:
                error = True
                break
            head, relation, direction, tail = match.groups()
            if head not in valid_indexes or tail not in valid_indexes:
                error = True
                break
            relations.append({
                "head": head,
                "relation": relation,
                "direction": direction,
                "tail": tail
            })

        if error:
            print(f"第{i}行第{attempt+1}次返回格式或索引错误，重试中...")
            continue

        # 构造不含索引的“关系事实”
        relation_facts = {
            "关系事实": [
                {
                    "头实体": {
                        "文本": index2entity[r["head"]]["text"],
                        "类型": index2entity[r["head"]]["type"]
                    },
                    "关系": {
                        "文本": r["relation"],
                        "方向": r["direction"]
                    },
                    "尾实体": {
                        "文本": index2entity[r["tail"]]["text"],
                        "类型": index2entity[r["tail"]]["type"]
                    }
                }
                for r in relations
            ]
        }

        df.at[i, "关系事实"] = json.dumps(relation_facts, ensure_ascii=False, indent=2)
        break
    else:
        print(f"第{i}行超过最大重试次数，跳过。")

# 保存结果
df.to_csv("data_with_relations.csv", index=False, encoding="utf-8-sig")
print("关系抽取完成，结果已保存到 data_with_relations.csv")


