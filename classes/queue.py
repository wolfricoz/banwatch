class queue():
    queue = []
    task_finished = True

    def empty(self):
        return len(self.queue) == 0

    def add(self, task):
        self.queue.append(task)

    def remove(self, task):
        self.queue.remove(task)


    async def start(self):
        if self.task_finished and not self.empty():
            self.task_finished = False
            try:
                task = self.queue.pop(0)
                await task
            except Exception as e:
                print(e)
            self.task_finished = True
