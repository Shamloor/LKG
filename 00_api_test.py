import config

response = config.CLIENT.chat.completions.create(
    model="deepseek-v3",
    messages=[
        {"role": "user", "content": "请返回空字符串"},
    ],
    stream=False
)

print(response.choices[0].message.content)