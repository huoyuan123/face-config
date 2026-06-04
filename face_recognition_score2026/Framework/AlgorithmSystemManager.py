from Framework.Interface.FrameworkInterface import FrameworkInterface
from Task.TaskConfiguration import TaskConfiguration


class AlgorithmSystemManager(FrameworkInterface):
    # 实例属性
    def __init__(self):
        super().__init__()
        self.taskInterface = None
        self.algorithmInterface = None

    # 初始化
    def initial(self):
        pass

    # 填充任务
    def addTask(self, taskManager):
        self.taskInterface = taskManager
        taskConfiguration = TaskConfiguration()
        self.taskInterface.initial(taskConfiguration)

    # 填充数据
    def addData(self, images, labels):
        self.taskInterface.addData(images, labels)

    # 填充算法
    def addAlgorithm(self, algorithmImplement):
        self.algorithmInterface = algorithmImplement
        self.algorithmInterface.setProblemInterface(self.taskInterface)
        self.taskInterface.initialRecord()

    # 运行算法
    def run(self):
        self.algorithmInterface.run()

    # 取得成绩
    def getScore(self):
        scoreModel = self.taskInterface.getScore()
        return scoreModel

    # 清除赛题
    def clearTask(self):
        self.taskInterface = None

    # 清空已有数据
    def clearData(self):
        self.taskInterface.clearData()

    # 清除当前算法所有结果，为下一个算法做准备
    def clearAlgorithm(self):
        self.algorithmInterface = None
        self.taskInterface.clearRecord()
