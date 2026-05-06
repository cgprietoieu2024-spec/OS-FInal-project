# Operating Systems Project

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
import threading
import queue
import random
import time

# -----------------------------
# STRATEGY (ADDED)
# -----------------------------

class AttemptStrategy(ABC):
    @abstractmethod
    def build(self, attempt_id: int):
        pass


class WaterStrategy(AttemptStrategy):
    def build(self, attempt_id: int):
        entry_type = random.choices(["legal", "illegal"], weights=[65, 35], k=1)[0]

        if entry_type == "legal":
            method = "boat"
            has_documents = random.random() < 0.90
        else:
            method = random.choice(["swimming", "jetski"])
            has_documents = False

        suspicious = random.random() < 0.15

        return CrossingAttempt(
            attempt_id=attempt_id,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
            special_event=method if entry_type == "illegal" else None
        )


class AirStrategy(AttemptStrategy):
    def build(self, attempt_id: int):
        entry_type = random.choices(["legal", "illegal"], weights=[70, 30], k=1)[0]

        if entry_type == "legal":
            method = "plane"
            has_documents = random.random() < 0.95
        else:
            method = random.choice(["unauthorized plane", "catapult"])
            has_documents = False

        suspicious = random.random() < 0.10

        return CrossingAttempt(
            attempt_id=attempt_id,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
            special_event=method if entry_type == "illegal" else None
        )


class LandStrategy(AttemptStrategy):
    def build(self, attempt_id: int):
        entry_type = random.choices(["legal", "illegal"], weights=[55, 45], k=1)[0]

        if entry_type == "legal":
            method = "vehicle"
            has_documents = random.random() < 0.88
        else:
            method = random.choice(["hiding in vehicle", "fence_jump"])
            has_documents = False

        suspicious = random.random() < 0.20

        return CrossingAttempt(
            attempt_id=attempt_id,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
            special_event=method if entry_type == "illegal" else None
        )


class AttemptFactory:
    def __init__(self, strategy: AttemptStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: AttemptStrategy):
        self.strategy = strategy

    def create(self, attempt_id: int):
        return self.strategy.build(attempt_id)


# -----------------------------
# DATA MODEL (UNCHANGED)
# -----------------------------

@dataclass
class CrossingAttempt:
    attempt_id: int

    # Type of crossing:
    # "legal" or "illegal"
    entry_type: str

    # Whether this attempt has valid documents
    has_documents: bool

    # Security check
    suspicious: bool

    # Special event
    # jetski, catapult, etc
    special_event: Optional[str] = None

    # "Accepted", "Rejected", "Caught", "Not Caught"
    result: str = "Pending"

    # Why?
    reason: str = ""

    # True/False if relevant for caught/not caught situations
    caught: Optional[bool] = None


# -----------------------------
# PROXY (ADDED)
# -----------------------------

class BorderService(ABC):
    @abstractmethod
    def process(self, request: CrossingAttempt) -> Optional[str]:
        pass


class RealBorderService(BorderService):
    def __init__(self, chain, stats):
        self.chain = chain
        self.stats = stats

    def process(self, request: CrossingAttempt):
        result = self.chain.handle(request)
        self.stats.update_result(request)
        return result


class BorderProxy(BorderService):
    def __init__(self, real_service):
        self.real_service = real_service

    def process(self, request: CrossingAttempt):
        print(f"Border surveillance: observing attempt {request.attempt_id}")

        # Small chance to catch illegal attempts early
        if request.entry_type == "illegal" and random.random() < 0.30:
            request.result = "Caught"
            request.reason = "Caught before checkpoint"
            request.caught = True
            self.real_service.stats.update_result(request)
            return f"Attempt {request.attempt_id}: Caught before checkpoint"

        return self.real_service.process(request)


# SHARED STATISTICS ( protected with a lock)

class Stats:
    def __init__(self):
        self.total_attempts = 0

        # Counts of final outcomes
        self.accepted = 0
        self.rejected = 0
        self.caught = 0
        self.not_caught = 0

        # Counts of entry types
        self.legal_attempts = 0
        self.illegal_attempts = 0

        # Total special event
        self.special_events_triggered = 0

        # Count each special event separately  <---- EDIT EVENTS
        self.special_event_counts = {
            "jetski": 0,
            "catapult": 0,
            "tunnel": 0,
            "fence_jump": 0
        }

        # Save text  of what happened during the simulation
        self.log = []

        self.lock = threading.Lock()

    def add_log(self, message: str):
        with self.lock:
            self.log.append(message)

    def update_result(self, attempt: CrossingAttempt):
        with self.lock:
            self.total_attempts += 1

            if attempt.entry_type == "legal":
                self.legal_attempts += 1
            else:
                self.illegal_attempts += 1

            if attempt.special_event is not None:
                self.special_events_triggered += 1
                if attempt.special_event in self.special_event_counts:
                    self.special_event_counts[attempt.special_event] += 1

            if attempt.result == "Accepted":
                self.accepted += 1
            elif attempt.result == "Rejected":
                self.rejected += 1
            elif attempt.result == "Caught":
                self.caught += 1
            elif attempt.result == "Not Caught":
                self.not_caught += 1

    def print_summary(self):
        print("\n" + "=" * 60)
        print("FINAL SIMULATION SUMMARY")
        print("=" * 60)
        print(f"Total attempts processed: {self.total_attempts}")
        print(f"Legal attempts:          {self.legal_attempts}")
        print(f"Illegal attempts:        {self.illegal_attempts}")
        print(f"Accepted:                {self.accepted}")
        print(f"Rejected:                {self.rejected}")
        print(f"Caught:                  {self.caught}")
        print(f"Not Caught:              {self.not_caught}")
        print(f"Special events total:    {self.special_events_triggered}")

        print("\nSpecial event breakdown:")
        for event_name, count in self.special_event_counts.items():
            print(f"  {event_name}: {count}")

        print("=" * 60)


#CHAIN OF RESPONSIBILITY BASE CLASSES

class Handler(ABC):
    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        pass

    @abstractmethod
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        pass


class AbstractHandler(Handler):
    _next_handler: Handler = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler

    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if self._next_handler:
            return self._next_handler.handle(request)
        return None


# CONCRETE HANDLERS

class ArrivalHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if request.entry_type in ["legal", "illegal"]:
            return super().handle(request)
        else:
            request.result = "Rejected"
            request.reason = "Invalid entry type"
            return f"Attempt {request.attempt_id}: Rejected - invalid entry type"


class DocumentCheckHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if request.entry_type == "legal":
            if not request.has_documents:
                request.result = "Rejected"
                request.reason = "Missing or invalid documents"
                return f"Attempt {request.attempt_id}: Rejected - missing documents"
        return super().handle(request)


class SecurityCheckHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if request.entry_type == "legal" and request.suspicious:
            if random.random() < 0.30:
                request.result = "Rejected"
                request.reason = "Failed security check"
                return f"Attempt {request.attempt_id}: Rejected - security issue"
        return super().handle(request)


class SpecialCaseHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if request.special_event is not None:
            if random.random() < 0.70:
                request.result = "Caught"
                request.reason = f"Caught during special event ({request.special_event})"
                request.caught = True
                return f"Attempt {request.attempt_id}: Caught during {request.special_event}"
            else:
                request.result = "Not Caught"
                request.reason = f"Not caught during special event ({request.special_event})"
                request.caught = False
                return f"Attempt {request.attempt_id}: Not caught during {request.special_event}"
        return super().handle(request)


class FinalHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if request.entry_type == "legal":
            request.result = "Accepted"
            request.reason = "Legal entry approved"
            return f"Attempt {request.attempt_id}: Accepted - legal entry approved"
        elif request.entry_type == "illegal":
            if random.random() < 0.80:
                request.result = "Caught"
                request.reason = "Caught during normal illegal crossing"
                request.caught = True
                return f"Attempt {request.attempt_id}: Caught during illegal crossing"
            else:
                request.result = "Not Caught"
                request.reason = "Managed to cross illegally without being caught"
                request.caught = False
                return f"Attempt {request.attempt_id}: Not caught during illegal crossing"


#SIMULATION CLASS

class BorderSimulation:
    def __init__(self, num_attempts: int = 40, num_threads: int = 4):
        self.num_attempts = num_attempts
        self.num_threads = num_threads
        self.attempt_queue = queue.Queue()
        self.stats = Stats()

        self.chain = ArrivalHandler()
        self.chain.set_next(DocumentCheckHandler()) \
                  .set_next(SecurityCheckHandler()) \
                  .set_next(SpecialCaseHandler()) \
                  .set_next(FinalHandler())

        self.factory = AttemptFactory(WaterStrategy())
        self.proxy = BorderProxy(RealBorderService(self.chain, self.stats))

    def generate_attempt(self, attempt_id: int) -> CrossingAttempt:
        strategy = random.choice([WaterStrategy(), AirStrategy(), LandStrategy()])
        self.factory.set_strategy(strategy)
        return self.factory.create(attempt_id)

    def prepare_attempts(self):
        for i in range(1, self.num_attempts + 1):
            attempt = self.generate_attempt(i)
            self.attempt_queue.put(attempt)

    def worker(self, worker_id: int):
        while True:
            try:
                attempt = self.attempt_queue.get_nowait()
            except queue.Empty:
                break

            time.sleep(random.uniform(0.1, 0.4))

            result_message = self.proxy.process(attempt)

            self.stats.add_log(f"[Official {worker_id}] {result_message}")
            print(f"[Official {worker_id}] {result_message}")

            self.attempt_queue.task_done()

    def run(self):
        self.prepare_attempts()

        threads = []

        print("=" * 60)
        print("STARTING BORDER CROSSING SIMULATION")
        print("=" * 60)

        for i in range(self.num_threads):
            thread = threading.Thread(target=self.worker, args=(i + 1,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.stats.print_summary()

if __name__ == "__main__":
    simulation = BorderSimulation(num_attempts=50, num_threads=4)
    simulation.run()