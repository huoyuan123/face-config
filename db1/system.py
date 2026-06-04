import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import warnings

matplotlib.rcParams['font.family'] = ['Microsoft YaHei']  # 设置中文字体显示
warnings.filterwarnings("ignore")  # 忽略所有 UserWarning 警告

# ================= 数据库连接 =================
def get_conn():
    return sqlite3.connect("attendance.db")


# ================= 主界面 ====================
def main_window(role):
    current_date = datetime.date.today()

    # ================ 补全当天记录 ================
    def auto_fill_today_records(date):
        date_str = date.strftime("%Y-%m-%d")
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM face_recognition_record WHERE record_date=?", (date_str,))
        existing_ids = set([row[0] for row in cur.fetchall()])
        cur.execute("SELECT id FROM student")
        for (sid,) in cur.fetchall():
            if sid not in existing_ids:
                cur.execute("""
                    INSERT INTO face_recognition_record (student_id, record_date, recognition_time, is_signed)
                    VALUES (?, ?, ?, 0)
                """, (sid, date_str, None))
        conn.commit()
        conn.close()

    # ================ 修改学生信息 ================
    def edit_student():
        selected = student_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请选择一名学生")
            return
        sid, name, cls = student_tree.item(selected[0], 'values')

        edit_win = tk.Toplevel()
        edit_win.title("修改学生信息")
        tk.Label(edit_win, text="学号:").grid(row=0, column=0)
        id_entry = tk.Entry(edit_win)
        id_entry.insert(0, sid)
        id_entry.grid(row=0, column=1)

        tk.Label(edit_win, text="姓名:").grid(row=1, column=0)
        name_entry = tk.Entry(edit_win)
        name_entry.insert(0, name)
        name_entry.grid(row=1, column=1)

        tk.Label(edit_win, text="班级:").grid(row=2, column=0)
        class_entry = tk.Entry(edit_win)
        class_entry.insert(0, cls)
        class_entry.grid(row=2, column=1)

        def save_student():
            new_id = id_entry.get()
            new_name = name_entry.get()
            new_class = class_entry.get()
            if not new_id or not new_name or not new_class:
                messagebox.showerror("错误", "信息不能为空")
                return
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE student SET id=?, name=?, class=? WHERE id=?", (new_id, new_name, new_class, sid))
            conn.commit()
            conn.close()
            load_students()
            load_records(current_date)
            edit_win.destroy()
            messagebox.showinfo("成功", "学生信息已更新")

        tk.Button(edit_win, text="保存修改", command=save_student).grid(row=3, columnspan=2, pady=10)

    # ================ 修改签到记录 ================
    def edit_record():
        selected = record_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请选择一条签到记录")
            return
        sid, name, status, time = record_tree.item(selected[0], 'values')

        def save_record():
            new_status = var_status.get()
            new_time = time_entry.get().strip()
            is_signed = 1 if new_status == "已签到" else 0

            if is_signed and not new_time:
                messagebox.showerror("错误", "已签到必须填写签到时间！")
                return
            if not is_signed:
                new_time = None

            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE face_recognition_record
                SET is_signed=?, recognition_time=?
                WHERE student_id=? AND record_date=?
            """, (is_signed, new_time, sid, current_date.strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
            load_records(current_date)
            edit_win.destroy()
            messagebox.showinfo("成功", "签到记录已更新")

        edit_win = tk.Toplevel()
        edit_win.title("修改签到记录")
        tk.Label(edit_win, text=f"学生: {sid} - {name}").pack(pady=5)

        tk.Label(edit_win, text="签到状态:").pack()
        var_status = tk.StringVar()
        var_status.set(status)
        status_menu = ttk.Combobox(edit_win, textvariable=var_status, values=["未签到", "已签到"])
        status_menu.pack()

        tk.Label(edit_win, text="签到时间 (HH:MM:SS):").pack()
        time_entry = tk.Entry(edit_win)
        time_entry.insert(0, time)
        time_entry.pack()

        tk.Button(edit_win, text="保存修改", command=save_record).pack(pady=10)

    def load_students(selected_class=None):
        student_tree.delete(*student_tree.get_children())
        conn = get_conn()
        cur = conn.cursor()
        if selected_class and selected_class != "全部":
            cur.execute("SELECT id, name, class FROM student WHERE class=?", (selected_class,))
        else:
            cur.execute("SELECT id, name, class FROM student")
        all_students = cur.fetchall()
        for row in all_students:
            student_tree.insert("", tk.END, values=row)
        update_student_page_label()
        conn.close()

    def load_records(date, selected_class=None):
        nonlocal current_date
        date_str = date.strftime("%Y-%m-%d")
        date_label.config(text=f"当前日期: {date_str}")
        auto_fill_today_records(date)
        record_tree.delete(*record_tree.get_children())
        conn = get_conn()
        cur = conn.cursor()
        if selected_class and selected_class != "全部":
            cur.execute("""
                SELECT s.id, s.name, r.is_signed, r.recognition_time
                FROM face_recognition_record r
                JOIN student s ON r.student_id = s.id
                WHERE r.record_date = ? AND s.class = ?
                ORDER BY r.is_signed ASC, s.id ASC
            """, (date_str, selected_class))
        else:
            cur.execute("""
                SELECT s.id, s.name, r.is_signed, r.recognition_time
                FROM face_recognition_record r
                JOIN student s ON r.student_id = s.id
                WHERE r.record_date = ?
                ORDER BY r.is_signed ASC, s.id ASC
            """, (date_str,))
        all_records = cur.fetchall()
        signed = sum(1 for r in all_records if r[2] == 1)
        total = len(all_records)
        for sid, name, signed_flag, time in all_records:
            status = "已签到" if signed_flag else "未签到"
            record_tree.insert("", tk.END, values=(sid, name, status, time if time else ""))
        conn.close()
        current_date = date
        update_pie_chart(signed, total)
        update_line_chart(selected_class)

    def prev_day():
        load_records(current_date - datetime.timedelta(days=1), class_var.get())

    def next_day():
        load_records(current_date + datetime.timedelta(days=1), class_var.get())

    def update_student_page_label():
        total = len(student_tree.get_children())
        student_page_label.config(text=f"共 {total} 人")

    def update_pie_chart(signed, total):
        pie_ax.clear()
        pie_ax.pie([signed, total - signed], labels=["已签到", "未签到"], autopct='%1.1f%%')
        pie_ax.set_title("今日签到情况")
        pie_canvas.draw()

    def update_line_chart(selected_class=None):
        line_ax.clear()
        conn = get_conn()
        cur = conn.cursor()
        dates = []
        rates = []
        for i in range(6, -1, -1):
            d = (current_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            if selected_class and selected_class != "全部":
                cur.execute("""
                    SELECT COUNT(*), SUM(is_signed)
                    FROM face_recognition_record r
                    JOIN student s ON r.student_id = s.id
                    WHERE r.record_date=? AND s.class=?
                """, (d, selected_class))
            else:
                cur.execute("""
                    SELECT COUNT(*), SUM(is_signed)
                    FROM face_recognition_record
                    WHERE record_date=?
                """, (d,))
            total, signed = cur.fetchone()
            if total and total > 0:
                rate = signed / total * 100
            else:
                rate = 0
            dates.append(d[5:])  # 只要月日
            rates.append(rate)
        conn.close()
        line_ax.plot(dates, rates, marker='o')
        line_ax.set_title("最近7天签到率变化")
        line_ax.set_ylabel("%")
        line_ax.set_ylim(0, 100)
        line_canvas.draw()

    win = tk.Tk()
    win.title("人脸识别系统")
    win.geometry("1300x900")

    left_frame = tk.Frame(win)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

    student_frame = tk.LabelFrame(left_frame, text="学生信息", font=('微软雅黑', 12))
    student_frame.pack(fill=tk.BOTH, expand=True)

    # 选择班级下拉框
    class_frame = tk.Frame(student_frame)
    class_frame.pack(fill=tk.X, pady=5)

    tk.Label(class_frame, text="选择班级:").pack(side=tk.LEFT, padx=5)

    class_var = tk.StringVar()
    class_combobox = ttk.Combobox(class_frame, textvariable=class_var, state="readonly")
    class_combobox.pack(side=tk.LEFT)

    def on_class_selected(event):
        selected_class = class_var.get()
        load_students(selected_class)
        load_records(current_date, selected_class)

    class_combobox.bind("<<ComboboxSelected>>", on_class_selected)


    student_tree_scroll = tk.Scrollbar(student_frame)
    student_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    student_tree = ttk.Treeview(student_frame, columns=("id", "name", "class"), show="headings", yscrollcommand=student_tree_scroll.set, height=20)
    for col in ("id", "name", "class"):
        student_tree.heading(col, text=col)
        student_tree.column(col, width=100, anchor=tk.CENTER)
    student_tree.pack(fill=tk.BOTH, expand=True)
    student_tree_scroll.config(command=student_tree.yview)

    student_page_label = tk.Label(student_frame, text="")
    student_page_label.pack(anchor=tk.SE, padx=5, pady=2)

    right_frame = tk.Frame(win)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    record_frame = tk.LabelFrame(right_frame, text="签到记录", font=('微软雅黑', 12))
    record_frame.pack(fill=tk.X, padx=10, pady=10)

    date_label = tk.Label(record_frame, font=('微软雅黑', 12))
    date_label.pack()

    record_tree = ttk.Treeview(record_frame, columns=("id", "name", "status", "time"), show="headings", height=18)
    record_scrollbar = tk.Scrollbar(record_frame, orient="vertical", command=record_tree.yview)
    record_tree.configure(yscrollcommand=record_scrollbar.set)
    record_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    for col, name in zip(("id", "name", "status", "time"), ("学号", "姓名", "是否签到", "时间")):
        record_tree.heading(col, text=name)
        record_tree.column(col, width=130, anchor=tk.CENTER)
    record_tree.pack(fill=tk.X, padx=10)



    nav_frame = tk.Frame(record_frame)
    nav_frame.pack(fill=tk.X)
    tk.Button(nav_frame, text="← 前一天", command=prev_day).pack(side=tk.LEFT, padx=10, pady=5)
    tk.Button(nav_frame, text="后一天 →", command=next_day).pack(side=tk.RIGHT, padx=10, pady=5)

    if role == "teacher":
        button_frame = tk.Frame(record_frame)
        button_frame.pack(pady=5)
        tk.Button(button_frame, text="✏️ 修改学生", command=edit_student).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="✏️ 修改签到", command=edit_record).pack(side=tk.LEFT, padx=10)

    chart_frame = tk.Frame(right_frame)
    chart_frame.pack(fill=tk.BOTH, expand=True, padx=10)

    fig, (pie_ax, line_ax) = plt.subplots(1, 2, figsize=(8, 3))
    fig.tight_layout()

    pie_canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    line_canvas = pie_canvas  # 同一张图中两个子图

    # 在main_window最开始时，查一遍所有班级
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT class FROM student")
    classes = [row[0] for row in cur.fetchall()]
    conn.close()
    classes.sort()  # 排序一下更美观
    class_combobox['values'] = ["全部"] + classes
    class_combobox.set("全部")


    load_students()
    load_records(current_date)
    win.mainloop()

# ================= 登录窗口 ====================
def login_window():
    def login_as(role):
        login.destroy()
        main_window(role)

    login = tk.Tk()
    login.title("登录系统")
    tk.Label(login, text="请选择登录身份", font=('微软雅黑', 14)).pack(pady=10)
    tk.Button(login, text="👩‍🏫 教师", width=15, command=lambda: login_as("teacher")).pack(pady=5)
    tk.Button(login, text="🧑‍🎓 学生", width=15, command=lambda: login_as("student")).pack(pady=5)
    login.mainloop()

# 启动程序
if __name__ == "__main__":
    login_window()
