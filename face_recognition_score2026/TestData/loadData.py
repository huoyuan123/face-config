import os
import cv2

from Framework.Interface.Model.BlockDataTransferModel import BlockDataTransferModel
from Framework.Interface.Model.PersonDataTransferModel import PersonDataTransferModel


class ImageCollector:
    def __init__(self, dataset_path):
        self.__dataset_path = dataset_path

    def load_data(self):
        images = []
        labels = []
        for root, dirs, files in os.walk(self.__dataset_path):
            for file in files:
                if file.endswith(('.jpg','.pgm')):
                    label = os.path.basename(root)
                    image_path = os.path.join(root, file)
                    try:
                        image = cv2.imread(image_path)
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        _, buffer = cv2.imencode('.jpg', image_rgb)
                        binary_image = buffer.tobytes()
                        images.append(binary_image)
                        labels.append(label)
                    except Exception as e:
                        print(f"Error loading image {image_path}: {e}")
        return images, labels
