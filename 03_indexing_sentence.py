import csv
import config

def modify_csv():
    # 读取原始 CSV 文件内容
    with open(config.PROCESSED_FILE_PATH, "r", encoding=config.CSV_ENCODING) as file:
        rows = file.readlines()

    # 重新写入 CSV 文件，插入表头并重构每一行格式
    with open(config.PROCESSED_FILE_PATH, "w", encoding=config.CSV_ENCODING, newline="") as file:
        writer = csv.writer(file, delimiter=config.CSV_DELIMITER)

        # 写入新表头
        writer.writerow(["句子", "内容", "命名实体", "标签"])

        # 写入每行内容
        for index, sentence in enumerate(rows, start=1):
            writer.writerow([index, sentence.strip(), "", "", ""])

    print(f"修改完成，结果已保存至 {config.PROCESSED_FILE_PATH}")


# 执行函数
modify_csv()

