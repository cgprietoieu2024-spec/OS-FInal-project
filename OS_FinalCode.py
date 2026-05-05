# Operating Systems Project

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
import threading
import queue
import random
import time
import sqlite3


DB_PATH = "border_simulation.db"

# Get data into SQL DB through SQLite
def db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER,medium TEXT,method TEXT,entry_type TEXT,has_documents INTEGER,
            suspicious INTEGER,result TEXT,reason TEXT,caught INTEGER,officer_id INTEGER)""")
        conn.commit()


def save_result(attempt, officer_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO results (
            attempt_id, medium, method, entry_type,
            has_documents, suspicious, result, reason,
            caught, officer_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (attempt.attempt_id,attempt.medium,attempt.method,attempt.entry_type,
            int(attempt.has_documents),int(attempt.suspicious),attempt.result,attempt.reason,
            None if attempt.caught is None else int(attempt.caught),officer_id))
        conn.commit()

# Model

@dataclass
class CrossingAttempt:
    attempt_id: int
    medium: str                 # water / air / land
    method: str                 # swimming / boat / plane / vehicle / etc.
    entry_type: str             # legal / illegal
    has_documents: bool
    suspicious: bool
    result: str = "Pending"
    reason: str = ""
    caught: Optional[bool] = None


# Design Pattern 1) --> Strategy

class AttemptStrategy(ABC):
    @abstractmethod
    def build(self, attempt_id: int) -> CrossingAttempt:
        pass


class WaterStrategy(AttemptStrategy):
    def build(self, attempt_id: int) -> CrossingAttempt:
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
            medium="water",
            method=method,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
        )


class AirStrategy(AttemptStrategy):
    def build(self, attempt_id: int) -> CrossingAttempt:
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
            medium="air",
            method=method,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
        )


class LandStrategy(AttemptStrategy):
    def build(self, attempt_id: int) -> CrossingAttempt:
        entry_type = random.choices(["legal", "illegal"], weights=[55, 45], k=1)[0]

        if entry_type == "legal":
            method = "vehicle"
            has_documents = random.random() < 0.88
        else:
            method = random.choice(["hiding in vehicle", "jumping border"])
            has_documents = False

        suspicious = random.random() < 0.20

        return CrossingAttempt(
            attempt_id=attempt_id,
            medium="land",
            method=method,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
        )


class AttemptFactory:
    def __init__(self, strategy: AttemptStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: AttemptStrategy) -> None:
        self.strategy = strategy

    def create(self, attempt_id: int) -> CrossingAttempt:
        return self.strategy.build(attempt_id)


# Design Pattern 2) --> Proxy

class BorderService(ABC):
    @abstractmethod
    def process(self, request: CrossingAttempt) -> Optional[str]:
        pass


class RealBorderService(BorderService):
    def __init__(self, chain, stats):
        self.chain = chain
        self.stats = stats

    def process(self, request: CrossingAttempt) -> Optional[str]:
        result = self.chain.handle(request)
        self.stats.update_result(request)
        return result


class BorderProxy(BorderService):
    def __init__(self, real_service: RealBorderService):
        self._real_service = real_service

    def process(self, request: CrossingAttempt) -> Optional[str]:
        print(f"Border surveillance: observing attempt {request.attempt_id} ({request.medium})")

        # Illegal crossings
        if request.entry_type == "illegal":
            request.result = "Caught"
            request.caught = True
            request.reason = f"Caught during illegal crossing via {request.method}"

            # update stats
            self._real_service.stats.update_result(request)

            return f"Attempt {request.attempt_id}: Caught via {request.method} ({request.medium})"

        # If the person is legal, then go to checkpoint
        return self._real_service.process(request)


# Design Pattern 3) --> Chain of responsability

class Handler(ABC):
    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:    #connects one handler to the next
        pass

    @abstractmethod
    def handle(self, request: CrossingAttempt) -> Optional[str]:    #processes the request
        pass


class AbstractHandler(Handler):
    # Stores a reference to the next handler in the chain #########????
    _next_handler: Handler = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler

        return handler

    @abstractmethod
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        if self._next_handler:
            return self._next_handler.handle(request)

        return None


# Concrete Handlers

class ArrivalHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        # First stage: check whether the entry_type is valid

        if request.entry_type in ["legal", "illegal"]:
            # If valid, continue
            return super().handle(request)
        else:
            # If invalid reject
            request.result = "Rejected"
            request.reason = "Invalid entry type"
            return f"Attempt {request.attempt_id}: Rejected - invalid entry type"


class DocumentCheckHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        # Only legal attempts need valid documents
        if request.entry_type == "legal":
            if not request.has_documents:
                request.result = "Rejected" # Missing documents = rejection
                request.reason = "Missing or invalid documents"
                return f"Attempt {request.attempt_id}: Rejected - missing documents"

        # If documents are ok (or if illegal entry), continue
        return super().handle(request)


class SecurityCheckHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        # Only suspicious legal attempts are checked here
        if request.entry_type == "legal" and request.suspicious:
            reject_chance = 0.30

            # 30% chance that suspicious legal attempts get rejected
            if random.random() < reject_chance:
                request.result = "Rejected"
                request.reason = "Failed security check"
                return f"Attempt {request.attempt_id}: Rejected - security issue"

        # If not rejected continue
        return super().handle(request)


class FinalHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        # Final handler gives a result only if no previous handler already stopped the chain

        # Normal legal attempt that passed all previous checks
        if request.entry_type == "legal":
            request.result = "Accepted"
            request.reason = "Legal entry approved"
            return f"Attempt {request.attempt_id}: Accepted - legal entry approved"

        # Illegal attempt without a special event outcome
        elif request.entry_type == "illegal":
            caught_chance = 0.80

            # 80% chance to be caught during normal illegal crossing
            if random.random() < caught_chance:
                request.result = "Caught"
                request.reason = "Caught during normal illegal crossing"
                request.caught = True
                return f"Attempt {request.attempt_id}: Caught during illegal crossing"
            else:
                request.result = "Not Caught"
                request.reason = "Managed to cross illegally without being caught"
                request.caught = False
                return f"Attempt {request.attempt_id}: Not caught during illegal crossing"

        return None


# Shared statistics ( protected with a lock)

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

        # Save text  of what happened during the simulation
        self.log = []

        # Lock protects all shared updates
        # Without this, multiple threads could update stats at the same time
        # and cause race conditions
        self.lock = threading.Lock()

    def add_log(self, message: str):
        # lock for log
        with self.lock:
            self.log.append(message)

    def update_result(self, attempt: CrossingAttempt):
        # counters lock
        with self.lock:
            self.total_attempts += 1

            # Count legal vs illegal attempts
            if attempt.entry_type == "legal":
                self.legal_attempts += 1
            else:
                self.illegal_attempts += 1

            # Count final result category
            if attempt.result == "Accepted":
                self.accepted += 1
            elif attempt.result == "Rejected":
                self.rejected += 1
            elif attempt.result == "Caught":
                self.caught += 1

    def print_summary(self):
        print("\n" + "=" * 60)
        print("FINAL SIMULATION SUMMARY")
        print("=" * 60)
        print(f"Total attempts processed: {self.total_attempts}")
        print(f"Legal attempts:          {self.legal_attempts}")
        print(f"Illegal attempts:        {self.illegal_attempts}")
        print(f"Accepted:                {self.accepted}")
        print(f"Rejected:                {self.rejected}")
        print("=" * 60)


# Simulation Class

class BorderSimulation:
    def __init__(self, num_attempts: int = 40, num_threads: int = 4):
        # Number of crossing attempts to simulate
        self.num_attempts = num_attempts

        # Number of officer threads
        self.num_threads = num_threads

        # Shared queue of attempts
        # Threads will take one attempt at a time from here
        self.attempt_queue = queue.Queue()

        self.stats = Stats()

        # building the chain of responsibility:

        # Arrival -> Documents -> Security -> Final
        self.chain = ArrivalHandler()
        self.chain.set_next(DocumentCheckHandler()) \
                  .set_next(SecurityCheckHandler()) \
                  .set_next(FinalHandler())

        # strategy factory
        self.factory = AttemptFactory(WaterStrategy())

        # proxy in front of the real checkpoint service
        self.real_service = RealBorderService(self.chain, self.stats)
        self.proxy = BorderProxy(self.real_service)

        # create the DB table w SQL
        db()

    # create a random crossing attempt
    def generate_attempt(self, attempt_id: int) -> CrossingAttempt:
        strategy = random.choice([WaterStrategy(), AirStrategy(), LandStrategy()])
        self.factory.set_strategy(strategy)
        return self.factory.create(attempt_id)

    def prepare_attempts(self):
        for i in range(1, self.num_attempts + 1):
            attempt = self.generate_attempt(i)
            self.attempt_queue.put(attempt)

# officer method
    def officer(self, officer_id: int):
        while True:
            try:
                # get one attempt from  queue
                attempt = self.attempt_queue.get_nowait()
            except queue.Empty:
                break

            time.sleep(random.uniform(0.1, 0.4))

            result_message = self.proxy.process(attempt)
            log_message = f"[Officer {officer_id}] {result_message}"

            self.stats.add_log(log_message)
            save_result(attempt, officer_id)
            print(log_message)

            self.attempt_queue.task_done()

  # Final run
    def run(self):
        self.prepare_attempts()

        threads = []

        print("=" * 60)
        print("STARTING BORDER CROSSING SIMULATION")
        print("=" * 60)

        for i in range(self.num_threads):
            thread = threading.Thread(target=self.officer, args=(i + 1,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.stats.print_summary()

        print("\nSAMPLE LOG ENTRIES:")
        for line in self.stats.log[:10]:
            print(line)


if __name__ == "__main__":
    # Creating the simulation with 50 attempts and 4 threads
    simulation = BorderSimulation(num_attempts=50, num_threads=4)

    # Start the simulation
    simulation.run()