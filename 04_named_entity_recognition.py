import csv
import config

ner_results = []

with open(config.PROCESSED_FILE_PATH, "r", encoding=config.CSV_ENCODING) as file:
    reader = csv.DictReader(file, delimiter=config.CSV_DELIMITER)
    rows = list(reader)
    fieldnames = reader.fieldnames


for row in rows:
    index = row["句子"]
    text = row["内容"]

    print(f"Processing NER for index {index}...")
    prompt = ("从以下文本中识别命名实体及其类型，并以 JSON 格式返回：\n" + text + '''
              \n返回的内容需要为中文
              \n命名实体类型分为人物、时间、天气、地点、行动、事物、描述
              \n人物实体包括：明确指代的人物名称（如姓名、称谓）、可能指代人物的普通名词（如‘年轻人’、‘老人’）、以及指代人物的人称代词（如‘他’、‘她’）。
              \n时间实体包括：年份（如‘1866年’）、月份（如‘六月’）、具体日期（如‘6月18日’）、一天中的具体时间（如‘上午十点’）、相对时间（如‘昨天’、‘三天后’）、时间段（如‘20世纪’、‘一个小时’）等。
              \n天气实体包括：描述天气的形容词（如‘晴朗’、‘阴沉’、‘湿冷’）、天气现象名词（如‘雨’、‘雪’、‘雷暴’）、以及涉及天气的短语表达（如‘狂风大作’、‘细雨绵绵’）。
              \n地点实体包括：地名（如‘圣彼得堡’）、建筑（如‘公寓’）、自然环境（如‘森林’）、抽象空间（如‘街角’）等。
              \n行动实体包括：人物执行的物理动作（如‘走’、‘奔跑’、‘坐下’）、交互行为（如‘交谈’、‘握手’、‘争吵’）、以及影响物品或环境的动作（如‘拾起’、‘推开’、‘敲门’）。
              \n事物实体包括：小说中指代某些不属于具体人物、地点、时间的概念性名词，如‘事’（泛指某种事件或事务）、‘话’（言语内容）、‘想法’（抽象概念）、‘信’（信件）、‘计划’（方案）、‘问题’（困境）等。
              \n描述实体包括：对人物、事物、场景、环境和行动的修饰性表达，涵盖人物的外貌（如‘瘦弱’）、性格（如‘固执’）、心理状态（如‘焦虑’）、物品的状态（如‘破旧’）、场景氛围（如‘沉闷’）、自然环境（如‘荒凉’），以及对不及物动词（vi）的状态性表达（如‘易怒的’ 对应‘发脾气’，‘疑心重的’ 对应‘患疑心病’，‘紧张的’ 对应‘心情紧张’）。
              \n请按JSON格式返回纯文本，不要返回Markdown格式内容，不要添加格式以外信息
              \n返回示例：{"命名实体": [{"文本": "年轻人", "类型": "人物"}, {"文本": "小屋", "类型": "地点"}]}''')
    response = config.llm_api(prompt)
    print(text + "\n" + response)
    row["命名实体"] = response

with open(config.PROCESSED_FILE_PATH, "w", encoding=config.CSV_ENCODING, newline='') as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=config.CSV_DELIMITER)
    writer.writeheader()
    writer.writerows(rows)

