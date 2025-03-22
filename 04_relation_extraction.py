import config
import json
import itertools

df = config.read_processed_csv()
df["关系事实"] = ""  # 初始化列

config.write_processed_csv(df)
for i, row in df.iterrows():
    index = row["索引"]
    content = row["内容"]
    entity_json = row["命名实体"]

    print(f"处理索引 {index} 的关系抽取...")

    try:
        entity_list = json.loads(entity_json).get("命名实体", [])
        if len(entity_list) < 2:
            continue  # 实体不足两个，跳过

        # 实体组合：两两组合成 [[e1, e2], [e1, e3], ...]
        entity_pairs = list(itertools.combinations(entity_list, 2))

        # 构造填空任务列表
        fill_tasks = []
        for e1, e2 in entity_pairs:
            fill_tasks.append(f'"{e1["文本"]}" ______ "{e2["文本"]}"')

        prompt = f'''请根据下列文本和命名实体信息，判断其中的实体之间的关系。文本内容：
        \n{content}
        \n命名实体列表：
        \n{json.dumps(entity_list, ensure_ascii=False)}
        \n请根据文本内容和命名实体列表补全以下填空，填入表示实体关系的动词或短语：
        \n{chr(10).join(fill_tasks)}
        \n返回格式要求如下：
        \n仅返回一个 JSON 数组，长度与填空列表一致。
        \n每项为一个字符串，格式为："关系(方向)"或"x"，
        \n如果文本内容中无法判断两个命名实体间的关系，则字符串为x。
        \n如：
        \n["走进(>)", "依赖(<)", "对话(-)", "x"]
        \n方向说明：
        \n> 表示从前者到后者，< 表示从后者到前者，- 表示无方向。
        \n不要添加任何解释或 Markdown，只返回纯 JSON 字符串数组。
'''

        response = config.llm_api(prompt)
        print(response)
        relation_list = json.loads(response)

        # 构造结构化的关系事实对象
        relation_facts = []
        for idx, relation in enumerate(relation_list):
            # 跳过无法识别的关系
            if relation.strip().lower() == "x":
                continue

            e1, e2 = entity_pairs[idx]
            direction = relation[-3:-1]  # 提取方向符号
            relation_text = relation[:-3].strip()  # 提取关系词

            # 根据方向判断 head / tail
            if direction == ">":
                head, tail = e1, e2
            elif direction == "<":
                head, tail = e2, e1
            else:  # 无方向或错误处理
                head, tail = e1, e2

            relation_facts.append({
                "头实体": {
                    "文本": head["文本"],
                    "类型": head.get("类型", "")
                },
                "关系": {
                    "文本": relation_text,
                    "方向": direction
                },
                "尾实体": {
                    "文本": tail["文本"],
                    "类型": tail.get("类型", "")
                }
            })

        # 写入到 DataFrame 当前行
        df.at[i, "关系事实"] = json.dumps({"关系事实": relation_facts}, ensure_ascii=False)

    except Exception as e:
        print(f"索引 {index} 抽取失败: {e}")
        continue

# 最后写入文件
config.write_processed_csv(df)
print("\n 关系事实提取完成，结果已保存至文件。")


