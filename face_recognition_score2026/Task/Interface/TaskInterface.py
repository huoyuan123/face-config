class TaskInterface(object):
    def __init__(self):
        pass

    def initial(self, taskConfiguration):
        pass

    def addData(self, images, labels):
        pass

    def getScore(self):
        pass

    def clearData(self):
        pass

    def clearRecord(self):
        pass

    def initialRecord(self):
        pass