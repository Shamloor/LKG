import config

# 读取原始文本，每行一个句子
df = config.read_processed_csv()

new_lines = []

for line in df['内容']:
    if line.startswith("“"):
        prompt = f'''为了方便后续的命名实体识别和关系抽取任务，
        请将人物的主观表达（如第一人称内心独白或对话）进行小幅度的总结，转换为客观的第三人称叙述。
        \n请将内容进行合理断句，每个句子另起一行。
        \n请只返回转换后的文本，不要返回Markdown格式内容，不要添加解释或说明。
        内容如下："{line}"'''
        result = config.llm_api(prompt)
        # 多行文本按行插入
        new_lines.extend([l.strip() for l in result.strip().split('\n') if l.strip()])
    else:
        new_lines.append(line)

for new_line in new_lines:
    print(new_line)

# 更新 DataFrame 并保存
converted_df = config.create_empty_processed_df(len(new_lines))
converted_df["内容"] = new_lines
converted_df["索引"] = list(range(1, len(new_lines) + 1))

config.write_processed_csv(converted_df)

print(f"转换完成，结果已保存至 {config.PROCESSED_FILE_PATH}")
