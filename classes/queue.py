import inspect
import logging


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class queue(metaclass=Singleton):
    high_priority_queue = []
    normal_priority_queue = []
    low_priority_queue = []
    task_finished = True

    def status(self):
        return f"Remaining queue: High: {len(self.high_priority_queue)} Normal: {len(self.normal_priority_queue)} Low: {len(self.low_priority_queue)}"

    def empty(self):
        return len(self.high_priority_queue) == 0 and len(self.normal_priority_queue) == 0 and len(self.low_priority_queue) == 0

    def add(self, task, priority: int = 1) -> float:
        """Adds a task to the queue with a priority of high(2), normal(1), or low(0)"""
        match priority:
            case 2:
                self.high_priority_queue.append(task)
            case 1:
                self.normal_priority_queue.append(task)
            case 0:
                self.low_priority_queue.append(task)
            case _:
                self.normal_priority_queue.append(task)
        return round(self.get_queue_time() / 60, 2)

    def remove(self, task):
        if task in self.high_priority_queue:
            self.high_priority_queue.remove(task)
        if task in self.normal_priority_queue:
            self.normal_priority_queue.remove(task)
        if task in self.low_priority_queue:
            self.low_priority_queue.remove(task)

    def process(self):
        if len(self.high_priority_queue) > 0:
            return self.high_priority_queue.pop(0)
        if len(self.normal_priority_queue) > 0:
            return self.normal_priority_queue.pop(0)
        if len(self.low_priority_queue) > 0:
            return self.low_priority_queue.pop(0)

    async def start(self):
        if self.task_finished and not self.empty():
            self.task_finished = False
            try:
                task = self.process()

                if not task:
                    self.low_priority_queue = [i for i in self.low_priority_queue if i is not None]
                    self.normal_priority_queue = [i for i in self.normal_priority_queue if i is not None]
                    self.high_priority_queue = [i for i in self.high_priority_queue if i is not None]
                    print(self.status())
                    self.task_finished = True
                    return
                if not inspect.iscoroutine(task):
                    task()
                    self.task_finished = True
                    logging.info(f"Processing task: {task.__name__}")

                    print(self.status())
                    return
                logging.info(f"Processing task: {task.__name__}")
                await task

            except Exception as e:
                logging.error(f"Error in queue: {e}")
            self.task_finished = True
            print(f"Remaining queue: High: {len(self.high_priority_queue)} Normal: {len(self.normal_priority_queue)} Low: {len(self.low_priority_queue)}")

    def get_queue_time(self) -> float:
        return len(self.high_priority_queue) + len(self.normal_priority_queue) * 0.3
