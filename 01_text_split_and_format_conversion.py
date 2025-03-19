import csv
import re
import config

# 句子结束符，包括 "……"
SENTENCE_ENDINGS = re.compile(r'([。？！”……])')

def split_text(text):
    sentences = []
    buffer = ""
    in_dialogue = False  # 是否在双引号中的标记
    i = 0  # 逐字符遍历索引

    while i < len(text):
        char = text[i]
        buffer += char  # 逐个字符拼接 buffer

        # 特殊处理 "……"
        if char == "…" and i + 1 < len(text) and text[i + 1] == "…":
            buffer += "…"  # 再拼接第二个 "…"
            i += 1  # 跳过下一个字符，避免重复处理

            # 在对话中，处理 "……"
            if in_dialogue:
                if i + 1 < len(text) and text[i + 1] == "”":
                    buffer += "”"  # 替换为 "……”"
                    sentences.append(buffer.strip())
                    buffer = ""
                    in_dialogue = False  # 退出对话模式
                else:
                    buffer += "”"  # 手动补上后双引号
                    sentences.append(buffer.strip())
                    buffer = "“"  # 开始新对话
            else:
                sentences.append(buffer.strip())
                buffer = ""

        # 处理前双引号 "“"
        elif char == "“":
            in_dialogue = True

        # 在对话中，处理句子结束符
        elif in_dialogue and char in "。？！":
            if i + 1 < len(text) and text[i + 1] == "”":
                buffer += "”"
                sentences.append(buffer.strip())
                buffer = ""
                in_dialogue = False  # 退出对话模式
            else:
                buffer += "”"
                sentences.append(buffer.strip())
                buffer = "“"

        # 退出对话模式
        elif char == "”":
            in_dialogue = False
            buffer = ""

        # 处理普通句子
        elif char in "。？！":
            sentences.append(buffer.strip())
            buffer = ""

        i += 1  # 继续下一个字符

    # 处理剩余的 buffer（如果有）
    if buffer.strip():
        sentences.append(buffer.strip())

    return sentences


# 读取文本
with open(config.TXT_FILE_PATH, "r", encoding="utf-8") as file:
    text = file.read()

# 处理文本
sentences = split_text(text)

# 保存到 CSV
with open(config.SENTENCE_SPLIT_FILE_PATH, "w", encoding="utf-8-sig", newline="") as file:
    writer = csv.writer(file, delimiter=config.CSV_DELIMITER)
    for sentence in sentences:
        writer.writerow([sentence])

print(f"处理完成，结果已保存至 {config.SENTENCE_SPLIT_FILE_PATH}")
