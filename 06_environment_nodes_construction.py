import pandas as pd
import config  # 引入全局配置文件

# **读取 CSV 文件**
df = pd.read_csv(config.CSV_FILE_PATH, sep=config.CSV_DELIMITER)

# **确保 CSV 包含必要的列**
if "段" not in df.columns or "内容" not in df.columns or "特殊" not in df.columns:
    raise ValueError("CSV 文件中缺少 '段'、'内容' 或 '特殊' 列，请检查文件格式！")

# **存储事件信息**
events = []
current_event_id = 1
current_text = []

for _, row in df.iterrows():
    if pd.notna(row["特殊"]) and row["特殊"].strip():  # "特殊"列不为空，新事件
        if current_text:  # 存储上一个事件
            events.append({"eventId": current_event_id, "text": " ".join(current_text)})
        current_event_id += 1  # 事件 ID 递增
        current_text = []  # 清空当前文本

    current_text.append(row["内容"])  # 累积文本

# **存储最后一个事件**
if current_text:
    events.append({"eventId": current_event_id, "text": " ".join(current_text)})

# **测试输出**
for event in events:
    print(f"Event ID: {event['eventId']}\nText: {event['text']}\n{'-'*40}")