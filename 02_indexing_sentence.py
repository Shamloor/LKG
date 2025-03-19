import csv
import config


def modify_csv():
    # 读取原始 CSV 文件内容
    with open(config.CSV_FILE_PATH, "r", encoding="utf-8-sig") as file:
        rows = file.readlines()

    # 重新写入 CSV 文件，插入表头并修改数据
    with open(config.CSV_FILE_PATH, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=config.CSV_DELIMITER)

        # 写入表头
        writer.writerow(["句子", "内容", "标签"])

        # 写入修改后的行（索引从1开始）
        for index, sentence in enumerate(rows, start=1):
            writer.writerow([index, sentence.strip(), ""])

    print(f"修改完成，结果已保存至 {config.CSV_FILE_PATH}")


# 运行修改函数
modify_csv()
