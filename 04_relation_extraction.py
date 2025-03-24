import json
import re
import config

# 加载数据
df = config.read_processed_csv()
df["关系事实"] = None

for i, row in df.iterrows():
    content = row["内容"]
    try:
        parsed = json.loads(row["命名实体"])
        raw_entities = parsed["命名实体"]
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
    \n{content}
    \n这是文本中的命名实体（已加临时索引）：
    \n{json.dumps(indexed_entities, ensure_ascii=False, indent=2)}
    \n请根据上述文本和实体，抽取所有存在的关系，返回一个 JSON 数组，数组中的每一项表示一条关系，其格式如下：
    \n{{"head": "实体索引（如E1）","relation": "关系动词","direction": "方向符号","tail": "实体索引（如E2）"}}
    \n请注意，"relation" 字段中的关系动词必须使用简体中文表达。
    \n另外，其中方向符号有三种符号，'>' 表示 head -> tail，'<' 表示 head <- tail"，'-'表示没有方向或判断不出方向。
    \n例如：[{{"head": "E1", "relation": "走进", "direction": ">", "tail": "E2"}}]
    \n如果命名实体间不存在任何关系，请返回空数组：[]
    \n请按JSON格式返回纯文本，不要返回Markdown格式内容，不要添加格式以外信息。"""

    valid_indexes = {ent["index"] for ent in indexed_entities}
    index2entity = {ent["index"]: ent for ent in indexed_entities}

    for attempt in range(3):
        response = config.llm_api(prompt)

        try:
            parsed = json.loads(response)
            print(parsed)
            if not isinstance(parsed, list):
                raise ValueError("返回结果不是JSON数组")
        except Exception as e:
            print(f"第{i}行第{attempt + 1}次返回非JSON数组格式，重试中... 错误信息: {e}")
            continue

        error = False
        relations = []
        for rel in parsed:
            if not all(k in rel for k in ["head", "relation", "direction", "tail"]):
                error = True
                break
            head = rel["head"]
            tail = rel["tail"]
            if head not in valid_indexes or tail not in valid_indexes:
                error = True
                break
            relations.append(rel)

        if error:
            print(f"第{i}行第{attempt + 1}次返回包含非法索引或字段缺失，重试中...")
            continue

        # 构造“关系事实”字段（不保留临时索引）
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
config.write_processed_csv(df)
print("关系抽取完成，结果已保存")


