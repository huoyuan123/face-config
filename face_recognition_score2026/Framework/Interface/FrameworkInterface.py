class FrameworkInterface:

    def __init__(self):
        pass

    # 初始化函数
    def initial(self):
        pass

    # 填充任务
    def addTask(self, taskManager):
        pass

    # 填充数据
    def addData(self, images, labels):
        pass

    # 填充算法
    def addAlgorithm(self, algorithmInterface):
        pass

    # 运行算法
    def run(self):
        pass

    # 取得成绩
    def getScore(self):
        pass

    # 清空已有数据
    def clearData(self):
        pass

    # 清除当前算法所有结果，为下一个算法做准备
    def clearTask(self):
        pass

    def clearAlgorithm(self):
        pass
