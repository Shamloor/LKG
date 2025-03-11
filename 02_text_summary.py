import pandas as pd
import json
from openai import OpenAI

csv_file_path = "./DATA/processed/罪与罚 第一部 第一章(processed).csv"
output_json_path = "./DATA/summary/罪与罚 第一部 第一章(summary).json"

# 先清空 JSON 文件，防止旧数据影响
with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump([], f, ensure_ascii=False, indent=4)

# 读取 CSV，指定 `|` 作为分隔符
df = pd.read_csv(csv_file_path, sep="|")

# 确保 "内容" 列存在
if "内容" not in df.columns:
    raise ValueError("CSV 文件中缺少 '内容' 列，请检查文件格式！")

# 拼接所有段落，确保文本顺序不变
text = "\n".join(df["内容"].tolist())

# 设置 OpenAI API 客户端（Deepseek API）
client = OpenAI(api_key="sk-969b6309421740869719b25527b46e41",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# 构造 API 请求，要求返回 JSON 格式的事件总结
prompt = f"""
请阅读以下小说文本，并按顺序对文章内容进行总结。

**要求**：
1. 以简短的句子描述每个事件，确保逻辑顺序清晰。
2. 当总结完所有事件后，按顺序检查所总结的事件，当有下述情况时
    1) 如果事件之间存在因果关系，则把相连的事件总结到一起。
    2) 检查相连的事件，所相连的事件内容差不多，则总结为同一事件。
3. 结果必须是 JSON 格式的数组，例如：
   ["主人公走在大街上", "主人公进入了大厦", "他遇到了一个神秘人物", ...]

小说文本：
{text}

请仅返回 JSON 格式的数组，不要附加额外的文本。
"""

# ️ 调用 API
response = client.chat.completions.create(
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
with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(summary_events, f, ensure_ascii=False, indent=4)

print(f"总结已保存到 {output_json_path}")