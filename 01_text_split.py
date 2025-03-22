import csv
import re
import config

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
with open(config.ORIGINAL_FILE_PATH, "r", encoding="utf-8") as file:
    text = file.read()

# 处理文本
sentences = split_text(text)

# 保存到 CSV
with open(config.PROCESSED_FILE_PATH, "w", encoding="utf-8-sig", newline="") as file:
    writer = csv.writer(file, delimiter=config.CSV_DELIMITER)
    for sentence in sentences:
        writer.writerow([sentence])

print(f"处理完成，结果已保存至 {config.PROCESSED_FILE_PATH}")