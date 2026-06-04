import os

from Algorithm.AlgorithmImplement import AlgorithmImplement
from Framework.AlgorithmSystemManager import AlgorithmSystemManager
from Task.TaskManager import TaskManager
from TestData.loadData import ImageCollector

if __name__ == '__main__':
    algorithmSystemManager = AlgorithmSystemManager()

    # 生成TaskManager的实例
    taskManager = TaskManager()
    # 注入框架
    algorithmSystemManager.addTask(taskManager)

    # 加载图像数据
    dataPath = os.path.join(os.getcwd(), 'TestData')
    ImagedataPath = os.path.join(dataPath, 'Faces_test')

    ImageCollector = ImageCollector(ImagedataPath)
    images, labels = ImageCollector.load_data()

    # 注入图像数据
    algorithmSystemManager.addData(images, labels)
    # 生成算法实例
    algorithmImplement = AlgorithmImplement()
    # 注入算法
    algorithmSystemManager.addAlgorithm(algorithmImplement)
    # 执行算法
    algorithmSystemManager.run()
    # 获取评分
    scoreModel = algorithmSystemManager.getScore()
    # 输出结果
    print(f"最终得分：{scoreModel.score}")
    # 清除算法
    algorithmSystemManager.clearAlgorithm()
    # 清除数据
    algorithmSystemManager.clearData()
    # 清除赛题
    algorithmSystemManager.clearTask()