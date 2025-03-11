import pandas as pd

# 读取 CSV 文件，提取“段”和“内容”
csv_file_path = "./DATA/processed/罪与罚 第一部 第一章(processed).csv"

df = pd.read_csv(csv_file_path, sep="|")

# 清空防止旧的标记影响
df["特殊"] = ""

# **必须重新保存 CSV，才能使修改生效**
df.to_csv(csv_file_path, sep="|", index=False)

print(f"CSV 文件已更新，'特殊' 列已成功清空：{csv_file_path}")