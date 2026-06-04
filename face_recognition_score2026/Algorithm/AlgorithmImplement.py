import json
import logging
import cv2
import numpy as np
import os
from Algorithm.Interface.AlgorithmInterface import AlgorithmInterface
from Algorithm.Interface.Model.ReportModel import ReportModel

class AlgorithmImplement(AlgorithmInterface):
    def __init__(self):
        super().__init__()
        logging.basicConfig(level=logging.ERROR)
        self.logger = logging.getLogger("AlgorithmLog")

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 加载LBPH模型
            self.model = cv2.face.LBPHFaceRecognizer_create()
            self.model.read(os.path.join(current_dir, "face_recognizer_model.xml"))

            # 加载标签映射
            with open(os.path.join(current_dir, "label_mapping.json"), encoding="utf-8") as f:
                self.label_mapping = json.load(f)["id_to_name"]

            # 双检测器
            self.face_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
            )
            self.profile_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_profileface.xml"
            )

        except Exception as e:
            print(f"初始化失败：{str(e)}")

    # 曝光修复（CLAHE，适配平台环境）
    def _fix_exposure(self, gray):
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    # 离焦修复（轻微锐化，不破坏特征）
    def _fix_defocus(self, gray):
        kernel = np.array([[0, -0.5, 0],
                           [-0.5, 3, -0.5],
                           [0, -0.5, 0]], dtype=np.float32)
        return cv2.filter2D(gray, -1, kernel)

    def run(self):
        end_flag = False
        while not end_flag:
            data_model = self._problemInterface.getData()
            if data_model is None:
                continue
            result = self._process_image(data_model.data)
            if result:
                report = ReportModel()
                report.result_label = result
                self._problemInterface.report(report)
            end_flag = data_model.finishedFlag

    def _process_image(self, image):
        # 1. 转灰度
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # 2. 曝光修复
        gray = self._fix_exposure(gray)

        # 3. 轻微离焦修复
        gray = self._fix_defocus(gray)

        # 4. 降噪
        gray = cv2.medianBlur(gray, 3)

        # 5. 均衡化
        gray = cv2.equalizeHist(gray)

        # 人脸检测（和你90分版本参数一致）
        faces = self.face_detector.detectMultiScale(
            gray, scaleFactor=1.03, minNeighbors=5, minSize=(40, 40)
        )
        if len(faces) == 0:
            faces = self.profile_detector.detectMultiScale(
                gray, scaleFactor=1.03, minNeighbors=5, minSize=(40, 40)
            )

        if len(faces) == 0:
            return "unknown"

        # 扩大ROI
        x, y, w, h = faces[0]
        y1 = max(0, y - int(0.15 * h))
        y2 = min(gray.shape[0], y + h + int(0.15 * h))
        x1 = max(0, x - int(0.15 * w))
        x2 = min(gray.shape[1], x + w + int(0.15 * w))
        face_roi = gray[y1:y2, x1:x2]
        face_roi = cv2.resize(face_roi, (92, 112))

        # 预测
        label, confidence = self.model.predict(face_roi)
        if confidence < 125:
            return self.label_mapping[str(label)]
        else:
            return "unknown"

    def __clearCach(self):
        self.results = []