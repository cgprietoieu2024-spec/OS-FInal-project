# Operating Systems Project

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
import threading
import queue
import random
import time

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
            "jetski": 0,  # <---- EDIT EVENTS
            "catapult": 0,   # <---- EDIT EVENTS
            "tunnel": 0,    # <---- EDIT EVENTS
            "fence_jump": 0     # <---- EDIT EVENTS
        }

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

            # Count special event( if happende)
            if attempt.special_event is not None:
                self.special_events_triggered += 1
                if attempt.special_event in self.special_event_counts:
                    self.special_event_counts[attempt.special_event] += 1

            # Count final result category
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

# CONCRETE HANDLERS

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

        # If documents are okay (or if illegal entry), continue
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


class SpecialCaseHandler(AbstractHandler):
    def handle(self, request: CrossingAttempt) -> Optional[str]:
        # This handler is used for special rare events
        if request.special_event is not None:


            # 70% chance of being caught
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

        # If no special event happened, continue to final stage
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

#SIMULATION CLASS

class BorderSimulation:
    def __init__(self, num_attempts: int = 40, num_threads: int = 4):
        # Number of crossing attempts to simulate
        self.num_attempts = num_attempts

        # Number of worker threads
        self.num_threads = num_threads

        # Shared queue of attempts
        # Threads will take one attempt at a time from here
        self.attempt_queue = queue.Queue()

        self.stats = Stats()

        # Build the chain of responsibility:

        # Arrival -> Documents -> Security -> SpecialCase -> Final
        self.chain = ArrivalHandler()
        self.chain.set_next(DocumentCheckHandler()) \
                  .set_next(SecurityCheckHandler()) \
                  .set_next(SpecialCaseHandler()) \
                  .set_next(FinalHandler())


    # Create one random crossing attempt
    def generate_attempt(self, attempt_id: int) -> CrossingAttempt:

        # Most attempts are legal
        entry_type = random.choices(
            ["legal", "illegal"],
            weights=[75, 25],
            k=1
        )[0]

        # Special events only happen on illegal attempts
        special_event = None
        if entry_type == "illegal":
            # Probability intentionally increased for demo/testing
            has_special = random.random() < 0.55
            if has_special:
                special_event = random.choice(
                    ["jetski", "catapult", "tunnel", "fence_jump"] #<---- CHANGE EVENTS
                )

        # Legal attempts may or may not have documents
        if entry_type == "legal":
            has_documents = random.random() < 0.90
        else:
            # Illegal attempts do not use normal legal documents here
            has_documents = False

        suspicious = random.random() < 0.20


        return CrossingAttempt(
            attempt_id=attempt_id,
            entry_type=entry_type,
            has_documents=has_documents,
            suspicious=suspicious,
            special_event=special_event
        )


    def prepare_attempts(self):
        for i in range(1, self.num_attempts + 1):
            attempt = self.generate_attempt(i)
            self.attempt_queue.put(attempt)

# Worker method
    def worker(self, worker_id: int):
        while True:
            try:
                # get one attempt from  queue
                attempt = self.attempt_queue.get_nowait()
            except queue.Empty:
                break

            time.sleep(random.uniform(0.1, 0.4))

            result_message = self.chain.handle(attempt)

            self.stats.update_result(attempt)

            # Keep a log
            log_message = f"[Worker {worker_id}] {result_message}"

            self.stats.add_log(log_message)

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
            thread = threading.Thread(target=self.worker, args=(i + 1,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.stats.print_summary()

        print("\nSAMPLE LOG ENTRIES:")
        for line in self.stats.log[:10]:
            print(line)



if __name__ == "__main__":
    # Create the simulation with:
    # - 50 total attempts
    # - 4 worker threads
    simulation = BorderSimulation(num_attempts=50, num_threads=4)

    # Start the simulation
    simulation.run()