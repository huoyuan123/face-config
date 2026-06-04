
import sqlite3
import pandas as pd

# 要读取的文件列表
file_list = ["11班 中级项目课-课堂花名册2026.xls", "12班 中级项目课-课堂花名册.xls", "13班 中级项目课-课堂花名册2026.xls"]

# 连接数据库
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# 创建学生表（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS student (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    class TEXT NOT NULL
)
''')

# 创建识别记录表（如果不存在）
cursor.execute("""
CREATE TABLE IF NOT EXISTS face_recognition_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    record_date TEXT NOT NULL,
    recognition_time TEXT,
    is_signed INTEGER DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES student(id)
)
""")

# 遍历所有文件，依次读取并插入
for file in file_list:
    try:
        df = pd.read_excel(file)

        # 只保留需要的列
        df_filtered = df[["学号", "姓名", "班级"]]
        df_filtered.columns = ["id", "name", "class"]  # 重命名列为数据库列名

        # 插入数据
        for _, row in df_filtered.iterrows():
            cursor.execute('''
            INSERT OR IGNORE INTO student (id, name, class) VALUES (?, ?, ?)
            ''', (row['id'], row['name'], row['class']))

        print(f"✅ 成功导入 {file} 的学生数据！")

    except Exception as e:
        print(f"❌ 读取 {file} 失败: {e}")

# 提交并关闭连接
conn.commit()
conn.close()

print("🎉 全部学生信息已成功导入数据库！")