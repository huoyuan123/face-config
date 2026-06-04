import cv2
import logging
from Algorithm.Interface.ProblemInterface import ProblemInterface
from Task.Interface.TaskInterface import TaskInterface
from Task.Model.CurrentProcessModel import CurrentProcessModel
from Task.Interface.Model.ScoreModel import ScoreModel
from Algorithm.Interface.Model.DataModel import DataModel
import numpy as np
import math
from random import shuffle

class TaskManager(TaskInterface, ProblemInterface):

    def __init__(self):
        # 受试者信息
        super().__init__()
        # 正确人脸记录
        self.personTable = []
        # 图像文件信息列表
        self.imageFileTable = []
        # 结果记录信息
        self.recordTable = []
        # 当前进度模型
        self.currentProcessModel = None
        # 日志配置
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("TaskManager")

    def initial(self, taskConfiguration):
        # self.taskConfiguration = taskConfiguration
        self.currentProcessModel = CurrentProcessModel()
        self.personTable = [['ID', 'NAME']]
        self.imageFileTable = [['ID', 'PERSONTABLEID', 'IMAGE_BINARY', 'LABEL']]
        self.recordTable = [['ID', 'IMAGEFILETABLEID', 'PREDICTED_LABEL']]

    def addData(self, images, labels):
        self.personNum = len(set(labels))
        for i in range(len(images)):
            image = images[i]
            label = labels[i]
            personID = self.__addPerson(label)
            self.__addImageFile(personID, image, label)

    def getScore(self):
        # 调用函数
        scoreModel = self.__calculateScore()
        return scoreModel

    def clearData(self):
        self.personTable = [['ID', 'NAME']]
        self.imageFileTable = [['ID', 'PERSONTABLEID', 'IMAGE_BINARY', 'LABEL']]
        TaskManager.clearRecord(self)

    def clearRecord(self):
        self.recordTable = [['ID', 'IMAGEFILETABLEID', 'PREDICTED_LABEL']]
        self.currentProcessModel.dataFileTableID = 1
        self.currentProcessModel.currentPosition = 0

    def initialRecord(self):
        self.shuffleList = [i + 1 for i in range(0, len(self.imageFileTable) - 1)]
        shuffle(self.shuffleList)
        self.shuffleImageFileTable = [['ID', 'PERSONTABLEID', 'IMAGE_BINARY', 'LABEL']]
        for i in self.shuffleList:
            self.shuffleImageFileTable.append(self.imageFileTable[i])

        # print(self.shuffleList)

    def getData(self):
        dataModel = DataModel()
        shuffleImageFileTable_local = self.shuffleImageFileTable
        current_id = self.currentProcessModel.dataFileTableID

        # 检查是否超出有效数据范围（索引从1开始，数据长度为 len-1）
        if current_id >= len(shuffleImageFileTable_local):
            dataModel.finishedFlag = True
            return dataModel

        # 获取当前数据
        # imageFileTableID = shuffleImageFileTable_local[current_id][0]
        personReadID = shuffleImageFileTable_local[current_id][1]
        image_binary = shuffleImageFileTable_local[current_id][2]

        # 解码图像
        try:
            nparr = np.frombuffer(image_binary, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("图像解码失败")
        except Exception as e:
            self.logger.error(f"图像加载失败: {e}")

        # 填充返回数据
        dataModel.data = image

        # 更新索引和完成标志
        self.currentProcessModel.dataFileTableID += 1
        dataModel.finishedFlag = self.currentProcessModel.dataFileTableID >= len(shuffleImageFileTable_local)

        return dataModel

    def report(self, reportModel):
        predicted_label = reportModel.result_label
        imageFileTableID = self.shuffleImageFileTable[self.currentProcessModel.dataFileTableID - 1][0]
        if len(self.recordTable) > 1:
            newRecordId = len(self.recordTable)
        else:
            newRecordId = 1
        self.recordTable.append([newRecordId, imageFileTableID, predicted_label])
        # self.logger.info(f"本次识别结果：{[newRecordId, imageFileTableID, predicted_label]}")

    def __addPerson(self, name):
        if len(self.personTable) > 1:
            personID = len(self.personTable)
        else:
            personID = 1
        self.personTable.append([personID, name])
        # newPersonID = name[1:len(name)]   #这里的personID可能计数有问题 后面根据情况再改
        newPersonID = name
        newPersonID = int(newPersonID)
        return newPersonID

    def __addImageFile(self, personID, image_binary, label):
        if len(self.imageFileTable) > 1:
            newImageFileId = len(self.imageFileTable)
        else:
            newImageFileId = 1
        self.imageFileTable.append([newImageFileId, personID, image_binary, label])

    def __calculateScore(self):
        correct_count = 0
        wrong_count = 0
        total_count = len(self.recordTable) - 1  # 减去表头行

        for recordIndex in range(1, len(self.recordTable)):
            imageFileTableID = self.recordTable[recordIndex][1]
            for imageIndex in range(1, len(self.imageFileTable)):
                if imageFileTableID == self.imageFileTable[imageIndex][0]:
                    true_label = self.imageFileTable[imageIndex][3]
                    predicted_label = self.recordTable[recordIndex][2]
                    if true_label == predicted_label:
                        correct_count += 1
                    else:
                        wrong_count += 1
                        self.logger.info(
                            f"图片ID{imageFileTableID}识别错误：真实标签={true_label}，预测标签={predicted_label}")
                    break  # 找到匹配的图像后跳出内循环，提高效率

        # 使用实际测试的图像数量作为分母
        accuracy = correct_count / total_count if total_count > 0 else 0
        self.logger.info(f"结果报告\n总人脸数：{total_count}，正确识别数：{correct_count}，错误识别数：{wrong_count}")


        scoreModel = ScoreModel()
        scoreModel.score = accuracy * 100
        return scoreModel





