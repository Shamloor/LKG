import pandas as pd
import config  # 确保你的config.py中定义了相关路径和参数

# 读取原始 CSV 文件
df = pd.read_csv(
    config.PROCESSED_FILE_PATH,
    encoding=config.CSV_ENCODING,
    delimiter=config.CSV_DELIMITER
)

# 添加“命名实体”和“关系”两列，初始为空字符串
#df.insert(4, "三元组", "")
df.drop('关系', axis=1, inplace=True)


# 保存修改后的 DataFrame
df.to_csv(
    config.PROCESSED_FILE_PATH,
    index=False,
    encoding=config.CSV_ENCODING,
    sep=config.CSV_DELIMITER
)
