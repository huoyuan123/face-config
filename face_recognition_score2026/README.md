# 人脸识别项目使用说明

本项目基于 OpenCV LBPH 人脸识别实现，目录结构以 `split.py`、`train_LBPH.py`、`test_face.py` 为主要入口。

## 1. 环境准备

建议新建 Python 虚拟环境后安装依赖：

```bash
pip install -r requirements.txt
```

依赖主要包括：
- `numpy`
- `opencv_contrib_python`
- `Pillow`

## 2. 数据集目录说明

当前默认数据集目录为：
- `TestData/Faces`：原始人脸图像数据，每个人一个子文件夹，文件夹名为学号或编号
- `TestData/Faces_train`：`split.py` 生成的训练集
- `TestData/Faces_test`：`split.py` 生成的测试集

## 3. 使用 `split.py` 划分数据集

`split.py` 会把 `TestData/Faces` 下每个用户的照片，按默认 80% 训练、20% 测试比例划分到：
- `TestData/Faces_train`
- `TestData/Faces_test`

运行方式：

```bash
python split.py
```

如果你想修改划分比例，可编辑 `split.py` 中 `split_dataset` 的 `train_ratio` 参数。

## 4. 训练模型：`train_LBPH.py`

`train_LBPH.py` 用 `TestData/Faces_train` 训练 LBPH 人脸识别模型，并保存模型文件为：
- `Algorithm/face_recognizer_model.xml`

运行方式：

```bash
python train_LBPH.py
```

## 5. 测试模型：`test_face.py`

`test_face.py` 会加载测试集 `TestData/Faces_test`，并通过项目中已有的算法管理框架执行测试，最后输出得分：

```bash
python test_face.py
```

## 6. 提高人脸识别准确度的方法


1. 优化人脸检测和预处理
   - `train_LBPH.py` 中使用了 Haar 级联进行人脸检测
   - 可以尝试更强的人脸检测器，如 `cv2.dnn`、MTCNN、RetinaFace
   - 对检测到的人脸进行裁剪并统一尺寸、灰度化、直方图均衡化

2. 调整 LBPH 参数
   - `train_LBPH.py` 中已给出参数注释，常用参数包括：
     - `radius`：LBPH 半径
     - `neighbors`：邻域点数
     - `grid_x`、`grid_y`：分格数
   - 在 `recognizer = cv2.face.LBPHFaceRecognizer_create(...)` 中调整这些参数，试不同组合

3. 统一人脸姿态和表情
   - 尽量让训练和测试图像中的人脸朝向一致
   - 使用人脸对齐（关键点检测后旋转、缩放）可显著提升精度


## 8. 运行示例

1. 划分数据集：
   ```bash
   python split.py
   ```
2. 训练模型：
   ```bash
   python train_LBPH.py
   ```
3. 测试模型：
   ```bash
   python test_face.py
   ```
