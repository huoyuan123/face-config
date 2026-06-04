# 人脸识别签到系统 — 本地部署教程

基于 **Flask + OpenCV LBPH** 的课堂人脸识别签到系统，支持学生端摄像头刷脸签到、教师端签到管理与数据可视化。

---

## 目录

- [1. 环境要求](#1-环境要求)
- [2. 克隆项目](#2-克隆项目)
- [3. 安装依赖](#3-安装依赖)
- [4. 数据库说明](#4-数据库说明)
- [5. 人脸识别模型说明](#5-人脸识别模型说明)
- [6. 启动应用](#6-启动应用)
- [7. 使用指南](#7-使用指南)
- [8. 自定义数据集（可选）](#8-自定义数据集可选)
- [9. 项目结构](#9-项目结构)
- [10. 常见问题](#10-常见问题)

---

## 1. 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | ≥ 3.9 | 推荐 3.10+ |
| Git | 任意版本 | 用于克隆仓库 |
| Git LFS | ≥ 3.0 | 人脸模型文件超过 100MB，必须通过 LFS 下载 |
| 浏览器 | Chrome / Edge / Firefox | 用于访问 Web 界面 |
| 摄像头 | USB 或内置 | 学生端签到需要 |

> **Windows 用户注意**：确保 Python 已添加到系统 PATH 环境变量。

---

## 2. 克隆项目

### 2.1 安装 Git LFS

**Windows**：
```powershell
# 下载安装包：https://git-lfs.com
# 或通过 winget 安装：
winget install Git.LFS

# 安装后初始化
git lfs install
```

**macOS**：
```bash
brew install git-lfs
git lfs install
```

**Linux (Ubuntu/Debian)**：
```bash
sudo apt install git-lfs
git lfs install
```

### 2.2 克隆仓库

```bash
git clone https://github.com/huoyuan123/face-config.git
cd face-config
```

> 克隆完成后，验证 `face_recognition_score2026/Algorithm/face_recognizer_model.xml` 文件大小约为 218MB。如果只有几百字节，说明 LFS 未正确下载，请执行 `git lfs pull`。

---

## 3. 安装依赖

### 3.1 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3.2 安装 Python 包

```bash
pip install flask opencv-contrib-python numpy pandas openpyxl xlrd matplotlib
```

> **关键说明**：必须安装 `opencv-contrib-python`（不是 `opencv-python`），后者不包含 LBPH 人脸识别模块。

如果下载速度慢，可以使用国内镜像：
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask opencv-contrib-python numpy pandas openpyxl xlrd matplotlib
```

---

## 4. 数据库说明

项目已包含预置数据库 `db1/attendance.db`，内含：

- **82 名学生**（来自 3 个班级：2024211210、2024211211、2024211212）
- **学生密码**：默认均为 `123456`
- **教师账号**：`admin` / `123456`
- **签到记录**：已有部分历史数据

### 4.1 使用自己的学生数据

如果你有自己的花名册，可以按以下步骤替换：

1. 准备 Excel 花名册，至少包含三列：`学号`、`姓名`、`班级`
2. 将文件放入 `db1/` 目录
3. 修改并运行 `db1/sqltest.py`：

```python
# 编辑 sqltest.py，修改 file_list 为你的文件名
file_list = ["你的花名册.xls"]

# 然后运行
python db1/sqltest.py
```

---

## 5. 人脸识别模型说明

项目已包含训练好的 LBPH 模型：

| 文件 | 路径 | 说明 |
|------|------|------|
| 模型文件 | `face_recognition_score2026/Algorithm/face_recognizer_model.xml` | LBPH 人脸识别模型 (218MB) |
| 标签映射 | `face_recognition_score2026/Algorithm/label_mapping.json` | 模型标签 → 学号 映射表 |

**模型覆盖的学生**：82 人，与数据库中的学生一一对应。

> 如果你替换了学生数据，需要重新训练模型（见[第 8 节](#8-自定义数据集可选)）。

---

## 6. 启动应用

```bash
python app.py
```

启动成功后会显示：

```
==================================================
  人脸识别签到系统
  访问地址: http://localhost:5000
  教师账号: admin / 123456
  学生账号: 学号 / 123456
==================================================
 * Running on http://127.0.0.1:5000
```

在浏览器打开 `http://localhost:5000` 即可访问。

> **注意**：默认端口为 5000。如果端口被占用，可编辑 `app.py` 最后一行 `app.run(host='0.0.0.0', port=5000)` 修改端口号。

---

## 7. 使用指南

### 7.1 教师端操作

1. 打开 `http://localhost:5000`，选择「教师登录」
2. 使用账号 `admin`，密码 `123456` 登录
3. 进入教师面板后：

   | 操作 | 说明 |
   |------|------|
   | **开启签到** | 点击绿色按钮，为当日所有学生创建签到记录 |
   | **结束签到** | 点击红色按钮，关闭签到通道 |
   | **筛选班级** | 下拉选择特定班级查看 |
   | **切换日期** | 日期选择器查看历史签到 |
   | **编辑记录** | 点击某行的「编辑」按钮，手动修正签到状态和时间 |
   | **查看图表** | 饼图展示当日签到占比，折线图展示近 7 天趋势 |

### 7.2 学生端操作

1. 打开 `http://localhost:5000`，选择「学生登录」
2. 输入学号（如 `2023210855`），密码 `123456` 登录
3. 浏览器会请求摄像头权限，点击「允许」
4. 确认摄像头画面正常后，点击「签到」按钮
5. 系统进行人脸识别：
   - **成功**：绿色提示，签到时间自动记录
   - **失败**：红色提示（未检测到人脸 / 人脸不匹配），可重新尝试
6. 右侧自动显示个人近 30 天签到记录

### 7.3 局域网内多人使用

如果想让同一局域网的其他设备访问（如学生的手机），启动时应用会自动监听所有网络接口：

```
Running on http://10.125.26.43:5000  ← 局域网地址
```

同一 WiFi 下的设备通过这个 IP + 端口即可访问。

---

## 8. 自定义数据集（可选）

如果你替换了学生数据，需要重新训练人脸识别模型。

### 8.1 准备人脸数据

在 `face_recognition_score2026/TestData/Faces/` 下按学号创建子文件夹，每个文件夹放入对应学生的正面照片（建议 15~30 张）：

```
TestData/Faces/
├── 2023210855/     ← 学号
│   ├── 1.jpg
│   ├── 2.jpg
│   └── ...
├── 2023212336/
│   ├── 1.jpg
│   └── ...
└── ...
```

### 8.2 划分训练集和测试集

```bash
cd face_recognition_score2026
python split.py
```

默认按 80% 训练 / 20% 测试的比例划分。

### 8.3 训练模型

```bash
python train_LBPH.py
```

训练完成后会更新 `Algorithm/face_recognizer_model.xml` 和 `Algorithm/label_mapping.json`。

### 8.4 测试模型准确率

```bash
python test_face.py
```

输出最终得分（百分制），建议达到 85% 以上再用于实际签到。

---

## 9. 项目结构

```
face-config/
├── app.py                              # Flask Web 应用主入口
├── templates/
│   ├── login.html                      # 登录页（深色科技风 UI）
│   ├── student.html                    # 学生端（摄像头签到）
│   └── teacher.html                    # 教师端（签到管理 + 图表）
├── static/
│   ├── css/style.css                   # 全局样式
│   └── js/
│       ├── student.js                  # 学生端前端逻辑
│       └── teacher.js                  # 教师端前端逻辑（含 Chart.js）
├── db1/
│   ├── attendance.db                   # SQLite 数据库
│   ├── system.py                       # [参考] 原 Tkinter 桌面版
│   ├── sqltest.py                      # [工具] 花名册导入脚本
│   └── *.xls                           # 花名册 Excel 文件
└── face_recognition_score2026/
    ├── Algorithm/
    │   ├── face_recognizer_model.xml   # LBPH 训练模型 (LFS)
    │   ├── label_mapping.json          # 标签 ↔ 学号 映射
    │   └── AlgorithmImplement.py       # 识别算法实现
    ├── Framework/                      # 算法框架层
    ├── Task/                           # 任务管理 + 评分
    └── TestData/
        ├── Faces/                      # 训练人脸数据集
        ├── Faces_train/                # 训练集（split.py 生成）
        ├── Faces_test/                 # 测试集（split.py 生成）
        └── loadData.py                 # 数据加载器
```

---

## 10. 常见问题

### Q1：启动时报错 `ModuleNotFoundError: No module named 'cv2'`

安装的是 `opencv-python`，需要换成 `opencv-contrib-python`：

```bash
pip uninstall opencv-python
pip install opencv-contrib-python
```

### Q2：人脸识别模型加载失败

检查 `face_recognition_score2026/Algorithm/face_recognizer_model.xml` 是否完整下载（应约 218MB）。如果只有几百字节：

```bash
git lfs pull
```

### Q3：学生签到提示「未检测到人脸」

- 确保摄像头已正确连接且未被其他应用占用
- 检查浏览器是否已授权摄像头权限
- 调整光线，确保面部清晰可见
- 正对摄像头，保持适当距离

### Q4：签到提示「人脸验证失败」

- 确认登录的学号与摄像头前的人是同一个人
- 调整光线和角度，避免侧脸或遮挡
- 如果持续失败，可能是该学生的人脸未在训练集中，需重新收集数据训练模型

### Q5：教师登录密码错误

默认教师账号为 `admin`，密码为 `123456`。如果在数据库中手动修改过，请检查 `admin_user` 表中的记录。

### Q6：学生登录密码错误

学生初始密码均为 `123456`。如果数据库中有自定义密码，请检查 `student` 表中的 `password` 字段。

### Q7：如何修改端口号

编辑 `app.py` 最后一行：

```python
app.run(host='0.0.0.0', port=8080, debug=True)  # 改为 8080
```

### Q8：macOS/Linux 下中文显示异常

这是终端编码问题，不影响浏览器中的 Web 页面显示。Web 页面使用 UTF-8 编码，中文正常显示。
