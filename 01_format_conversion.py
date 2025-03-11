import os
import csv

# 输入 TXT 文件路径
txt_file_path = "./DATA/original/罪与罚 第一部 第二章(original).txt"
# 输出 CSV 文件路径
csv_file_path = "./DATA/processed/罪与罚 第一部 第二章(processed).csv"

# 确保输出目录存在
os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

# 解析文件名，提取"哪一部"和"哪一章"
file_name = os.path.basename(txt_file_path).replace("(original).txt", "")
parts = file_name.split()
if len(parts) >= 3:
    part_name = parts[1]  # "第一部"
    chapter_name = parts[2]  # "第一章"
else:
    part_name = "未知"
    chapter_name = "未知"

# 读取 TXT 文件并转换为 CSV
with open(txt_file_path, "r", encoding="utf-8") as txt_file, \
        open(csv_file_path, "w", encoding="utf-8", newline="") as csv_file:
    csv_writer = csv.writer(csv_file, delimiter="|")
    csv_writer.writerow(["部", "章", "段", "内容", "特殊"])  # 写入表头

    paragraph_id = 1  # 初始化段落编号

    for line in txt_file:
        line = line.strip()  # 去除前后空白字符
        if line:  # 忽略空行
            csv_writer.writerow([part_name, chapter_name, paragraph_id, line, ""])  # “特殊”列留空
            paragraph_id += 1  # 每写入一行，段编号+1

print(f"CSV 文件已生成: {csv_file_path}")
