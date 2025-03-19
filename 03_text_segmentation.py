import pandas as pd
import json

import config

# 读取 CSV 文件
df = pd.read_csv(config.CSV_FILE_PATH, sep=config.CSV_DELIMITER)

# 确保 "段" 和 "特殊" 列存在
if "段" not in df.columns or "特殊" not in df.columns:
    raise ValueError("CSV 文件中缺少 '段' 或 '特殊' 列，请检查文件格式！")

# 读取 JSON 文件
with open(config.JSON_FILE_PATH, "r", encoding="utf-8") as f:
    summary_events = json.load(f)

# **清空 CSV 的 "特殊" 列**
df["特殊"] = ""

# **遍历 JSON 文件，根据起始段落填入事件**
for event in summary_events:
    event_text = event["事件"]
    start_paragraph = event["起始段落"]

    # **找到 CSV 中对应的段落**
    if start_paragraph in df["段"].values:
        # **如果 "特殊" 列已存在内容，则用 ";" 连接多个事件**
        existing_value = df.loc[df["段"] == start_paragraph, "特殊"].values[0]
        if existing_value:
            df.loc[df["段"] == start_paragraph, "特殊"] = existing_value + ";" + event_text
        else:
            df.loc[df["段"] == start_paragraph, "特殊"] = event_text

# **保存更新后的 CSV**
df.to_csv(config.CSV_FILE_PATH, sep=config.CSV_DELIMITER, index=False)

print(f"CSV 文件已更新，'特殊' 列已填充事件: {config.CSV_FILE_PATH}")
