import cv2
import numpy as np
import os
import json
from collections import OrderedDict


def train_face_model(dataset_path, output_model="face_recognizer_model.xml"):
    label_dict = OrderedDict()
    folders = sorted([f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))])
    for idx, folder_name in enumerate(folders):
        label_dict[folder_name] = idx

    faces = []
    labels = []

    # 检测器：正脸强检测 + 侧脸
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
    profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

    for folder in folders:
        folder_path = os.path.join(dataset_path, folder)
        valid_count = 0
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                img_path = os.path.join(folder_path, file)
                try:
                    img = cv2.imread(img_path)
                    if img is None:
                        continue
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    # 第一级：严格检测
                    faces_detected = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.02,
                        minNeighbors=3,
                        minSize=(40, 40)
                    )

                    # 第二级：宽松检测
                    if len(faces_detected) == 0:
                        faces_detected = face_cascade.detectMultiScale(
                            gray,
                            scaleFactor=1.05,
                            minNeighbors=2,
                            minSize=(30, 30)
                        )

                    # 第三级：侧脸检测
                    if len(faces_detected) == 0:
                        faces_detected = profile_cascade.detectMultiScale(
                            gray,
                            scaleFactor=1.03,
                            minNeighbors=2,
                            minSize=(30, 30)
                        )

                    if len(faces_detected) >= 1:
                        x, y, w, h = faces_detected[0]

                        # ROI扩展
                        y1 = max(0, y - int(0.15 * h))
                        y2 = min(gray.shape[0], y + h + int(0.15 * h))
                        x1 = max(0, x - int(0.15 * w))
                        x2 = min(gray.shape[1], x + w + int(0.15 * w))
                        face_roi = gray[y1:y2, x1:x2]
                        face_roi = cv2.resize(face_roi, (92, 112))

                        # 预处理：降噪 + 对比度增强
                        face_roi = cv2.GaussianBlur(face_roi, (3, 3), 0)
                        face_roi = cv2.equalizeHist(face_roi)
                        face_roi = cv2.convertScaleAbs(face_roi, alpha=1.3, beta=10)

                        faces.append(face_roi)
                        labels.append(label_dict[folder])
                        valid_count += 1
                except:
                    pass
        print(f"✅ {folder} 有效图：{valid_count}")

    # LBPH参数
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8,
        threshold=160
    )
    recognizer.train(faces, np.array(labels))

    # 保存模型
    os.makedirs(os.path.dirname(output_model), exist_ok=True)
    recognizer.save(output_model)

    # 保存标签映射
    label_path = os.path.join(os.path.dirname(output_model), "label_mapping.json")
    with open(label_path, "w") as f:
        json.dump({
            "name_to_id": label_dict,
            "id_to_name": {v: k for k, v in label_dict.items()}
        }, f, indent=4)

    print(f"✅ 模型训练完成！保存至：{output_model}")
    print(f"✅ 标签映射保存至：{label_path}")


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(current_dir, "TestData", "Faces_train")
    output_model = os.path.join(current_dir, "Algorithm", "face_recognizer_model.xml")

    if not os.path.exists(dataset_path):
        print(f"❌ 数据集路径不存在：{dataset_path}")
    else:
        train_face_model(dataset_path, output_model)