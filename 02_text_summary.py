import pandas as pd
import json
import config

# 先清空 JSON 文件，防止旧数据影响
with open(config.JSON_FILE_PATH, "w", encoding="utf-8") as f:
    json.dump([], f, ensure_ascii=False, indent=4)

# 读取 CSV，指定 `|` 作为分隔符
df = pd.read_csv(config.CSV_FILE_PATH, sep="|")

# 确保 "段" 和 "内容" 列存在
if "段" not in df.columns or "内容" not in df.columns:
    raise ValueError("CSV 文件中缺少 '段' 或 '内容' 列，请检查文件格式！")

# 拼接所有段落，并带上段落编号，格式："1. 段落内容"
text = "\n".join([f"{row['段']}. {row['内容']}" for _, row in df.iterrows()])

# 构造 API 请求，要求返回 JSON 格式的事件总结
prompt = f"""
请阅读以下小说文本，并按顺序对文章内容进行总结。

**要求**：
1. 以简短的句子描述每个事件，确保逻辑顺序清晰。
2. 当总结完所有事件后，按顺序检查所总结的事件：
    1) 如果事件之间存在因果关系，则将相连的事件合并为一个完整事件。
    2) 如果相连的事件内容相似，则归并为同一事件。
3. 为每个事件标注它在小说文本中的 **起始段落索引**，索引来源于原始文本中的段落编号。
4. 结果必须是 JSON 格式的数组，示例为：
   [
       {{"事件": "主人公走在大街上，心情沉重。", "起始段落": 3}},
       {{"事件": "主人公进入大厦，试图找人谈话。", "起始段落": 5}},
       {{"事件": "他遇到一个神秘人物，并交谈许久。", "起始段落": 7}}
   ]

小说文本：
{text}

请仅返回 JSON 格式的数组，不要附加额外的文本。
"""

# ️ 调用 API
response = config.CLIENT.chat.completions.create(
    model="deepseek-v3",
    messages=[
        {"role": "user", "content": prompt},
    ],
    stream=False
)

# 解析 API 响应
try:
    summary_events = json.loads(response.choices[0].message.content)
    print("总结结果:", summary_events)
except json.JSONDecodeError:
    print("错误：API 返回的内容无法解析为 JSON！")
    summary_events = []

# 保存总结结果为 JSON 文件
with open(config.JSON_FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(summary_events, f, ensure_ascii=False, indent=4)

print(f"总结已保存到 {config.JSON_FILE_PATH}")