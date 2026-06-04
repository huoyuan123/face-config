import os
import shutil
import re
import random
from PIL import Image

# 固定随机种子，保证每次运行结果一样（可删掉）
random.seed(42)

def split_dataset(source_dir, train_dir, test_dir, train_ratio=0.8):
    """
    每个文件夹内部 随机 8:2 划分数据集
    :param source_dir: 原始数据路径
    :param train_dir: 训练集路径
    :param test_dir: 测试集路径
    :param train_ratio: 训练集比例，默认 0.8 = 80%
    """
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)

    # 遍历所有人物文件夹
    for person_dir in sorted(os.listdir(source_dir)):
        if not re.match(r'^\d{6,12}$', person_dir):
            continue

        print(f"正在处理：{person_dir}")

        # 创建输出子文件夹
        train_p = os.path.join(train_dir, person_dir)
        test_p = os.path.join(test_dir, person_dir)
        os.makedirs(train_p, exist_ok=True)
        os.makedirs(test_p, exist_ok=True)

        # 获取当前文件夹所有图片
        img_dir = os.path.join(source_dir, person_dir)
        img_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('jpg', 'jpeg', 'png', 'bmp'))]

        if len(img_files) == 0:
            continue

        # 随机打乱
        random.shuffle(img_files)

        # 计算分割点
        split_idx = int(len(img_files) * train_ratio)
        train_files = img_files[:split_idx]
        test_files = img_files[split_idx:]

        # 复制训练集
        for f in train_files:
            src = os.path.join(img_dir, f)
            dst = os.path.join(train_p, f)
            shutil.copy2(src, dst)

        # 复制测试集
        for f in test_files:
            src = os.path.join(img_dir, f)
            dst = os.path.join(test_p, f)
            shutil.copy2(src, dst)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    source_directory = os.path.join(current_dir, 'TestData', 'Faces')
    train_directory = os.path.join(current_dir, 'TestData', 'Faces_train')
    test_directory = os.path.join(current_dir, 'TestData', 'Faces_test')

    split_dataset(source_directory, train_directory, test_directory)
    print("[OK] 数据集随机 8:2 分割完成!")