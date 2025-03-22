import re
import config
import pandas as pd

# 正则：句子结束符（带括号表示捕获，用于后续拼接）
SENTENCE_ENDINGS = re.compile(r'([。？！])')

def split_text(text):
    sentences = []
    buffer = ""
    i = 0

    while i < len(text):
        char = text[i]

        # 遇到前引号，进入对话模式
        if char == "“":
            if buffer.strip():
                # 对引号前的普通文本进行分句（保留标点）
                parts = SENTENCE_ENDINGS.split(buffer)
                for j in range(0, len(parts) - 1, 2):
                    sentence = parts[j].strip() + parts[j + 1]
                    if sentence:
                        sentences.append(sentence)
                # 如果有结尾剩余的非完整句子（没有标点），也加进去
                if len(parts) % 2 == 1 and parts[-1].strip():
                    sentences.append(parts[-1].strip())
                buffer = ""

            # 开始收集对话内容
            dialogue = "“"
            i += 1
            while i < len(text):
                dialogue += text[i]
                if text[i] == "”":
                    break
                i += 1
            sentences.append(dialogue.strip())
            buffer = ""
        else:
            buffer += char
        i += 1

    # 处理剩余文本
    if buffer.strip():
        parts = SENTENCE_ENDINGS.split(buffer)
        for j in range(0, len(parts) - 1, 2):
            sentence = parts[j].strip() + parts[j + 1]
            if sentence:
                sentences.append(sentence)
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())

    return sentences

# 读取文本
text = config.read_original_text()

# 处理文本
lines = split_text(text)

# 构建 DataFrame
df = config.create_empty_processed_df(len(lines))
df["内容"] = lines

# 写入处理结果
config.write_processed_csv(df)

print(f"处理完成，结果已保存至 {config.PROCESSED_FILE_PATH}")
