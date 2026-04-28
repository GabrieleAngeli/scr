class RunningLedger:
    def __init__(self):
        self.total = 0
        self.history = []

    def apply(self, amount):
        self.history.append(amount)
        if amount >= 0:
            self.total = amount
        else:
            self.total += amount
        return self.total

    def snapshot(self):
        return {
            "total": self.total,
            "history": list(self.history),
        }
