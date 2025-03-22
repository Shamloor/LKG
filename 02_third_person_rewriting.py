import config

# 读取原始文本，每行一个句子
with open(config.PROCESSED_FILE_PATH, "r", encoding="utf-8-sig") as f:
    lines = [line.strip() for line in f.readlines()]

new_lines = []

for line in lines:
    if line.startswith("“"):
        prompt = f'''为了方便后续的命名实体识别和关系抽取任务，请将人物的主观表达（如第一人称内心独白或对话）转换为客观的第三人称叙述。
        \n请将内容进行合理断句，每个句子换一行。
        \n请只返回转换后的文本，不要返回Markdown格式内容，不要添加解释或说明。
        内容如下："{line}"'''
        result = config.llm_api(prompt)
        # 多行文本按行插入
        new_lines.extend([l.strip() for l in result.strip().split('\n') if l.strip()])
    else:
        new_lines.append(line)

# 覆盖写入回原文件
with open(config.PROCESSED_FILE_PATH, "w", encoding="utf-8-sig") as f:
    for line in new_lines:
        f.write(line + "\n")

print(f"转换完成，结果已保存至 {config.PROCESSED_FILE_PATH}")
