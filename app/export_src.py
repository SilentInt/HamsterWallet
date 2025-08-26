import os


def collect_source_files(output_file):
    """
    遍历当前目录及其子目录，将指定类型文件的内容汇总到输出文件中。

    Args:
        output_file (str): 输出文件的名称。
    """
    # 定义要查找的文件扩展名
    extensions_to_find = (".js", ".css", "html")

    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            # os.walk会遍历当前目录和所有子目录
            for dirpath, _, filenames in os.walk("."):
                for filename in filenames:
                    # 检查文件扩展名是否在我们的目标列表中
                    if filename.endswith(extensions_to_find):
                        # 构建完整的文件路径
                        file_path = os.path.join(dirpath, filename)

                        try:
                            with open(
                                file_path, "r", encoding="utf-8", errors="ignore"
                            ) as infile:
                                content = infile.read()

                                # 写入文件名作为标题
                                outfile.write(f"--- {file_path} ---\n")
                                # 写入被代码块包围的内容
                                outfile.write(f"```\n{content}\n```\n\n")
                        except Exception as e:
                            print(f"读取文件时出错 {file_path}: {e}")

    except IOError as e:
        print(f"写入输出文件时出错 {output_file}: {e}")


if __name__ == "__main__":
    # 设置输出文件的名称
    output_filename = "src.txt"
    collect_source_files(output_filename)
    print(f"所有源代码已成功汇总到 {output_filename}")
