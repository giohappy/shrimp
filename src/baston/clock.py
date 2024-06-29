from dataclasses import dataclass, field
import uuid
from .utils import info_message
from queue import PriorityQueue
from .errors import BadFunctionError
from typing import Any, Callable, Dict
from time import sleep
import threading
import link
import types

Number = int | float

@dataclass(order=True)
class PriorityEvent:
    name: str
    priority: int | float
    item: Any = field(compare=False)
    once: bool = False

class Clock():

    def __init__(self, tempo: int | float):
        self._clock_thread: threading.Thread | None = None
        self._stop_event: threading.Event = threading.Event()
        self._children: Dict[str, PriorityEvent] = {}
        self._isPlaying: bool = False
        self._link = link.Link(tempo)
        self._link.enabled = True
        self._link.startStopSyncEnabled = True
        self._nominator = 4
        self._denominator = 4
        self._beat = 0
        self._bar = 0
        self._phase = 0
        self._grain = 0.001

    def sync(self, bool: bool = True):
        """Enable or disable the sync of the clock"""
        self.link.startStopSyncEnabled = bool

    @property
    def grain(self) -> Number:
        """Return the grain of the clock"""
        self._grain

    @grain.setter
    def grain(self, value: Number):
        """Set the grain of the clock"""
        self._grain = value

    @property
    def tempo(self):
        """Get the tempo of the clock"""
        return self._tempo
    
    @tempo.setter
    def tempo(self, value: Number):
        """Set the tempo of the clock"""
        if self._link:
            session = self._link.captureSessionState()
            session.setTempo(value, self._link.clock().micros())
            self._link.commitSessionState(session)

    @property
    def bar(self) -> Number:
        """Get the bar of the clock"""
        return self._bar

    @property
    def beat(self) -> Number:
        """Get the beat of the clock"""
        return self._beat

    @property
    def beat_duration(self) -> Number:
        """Get the duration of a beat"""
        return 60 / self._tempo

    @property
    def phase(self) -> Number:
        """Get the phase of the clock"""
        return self._phase

    def start(self) -> None:
        """Start the clock"""
        if not self._clock_thread:
            self._clock_thread = threading.Thread(target=self.run).start()

    def play(self) -> None:
        """Play the clock"""
        session = self._link.captureSessionState()
        session.setIsPlaying(True, self._link.clock().micros())
        self._link.commitSessionState(session)

    def pause(self) -> None:
        """Pause the clock"""
        session = self._link.captureSessionState()
        session.setIsPlaying(False, self._link.clock().micros())
        self._link.commitSessionState(session)

    def stop(self) -> None:
        """Stop the clock and wait for the thread to finish"""
        self._stop_event.set()

    def _capture_link_info(self) -> None:
        """Utility function to capture timing information from Link Session."""
        link_state = self._link.captureSessionState()
        link_time = self._link.clock().micros()
        self._beat, self._phase, self._tempo = (
            link_state.beatAtTime(link_time, self._denominator),
            link_state.phaseAtTime(link_time, self._denominator),
            link_state.tempo()
        )
        self._bar = self._beat / self._denominator
        self._isPlaying = link_state.isPlaying

    def run(self) -> None:
        """Clock Event Loop."""
        while not self._stop_event.is_set():
            self._capture_link_info()
            self._execute_due_functions()
            sleep(self._grain)

    def _execute_due_functions(self) -> None:
        """Execute all functions that are due to be executed."""
        possible_callables = sorted(self._children.values(), key=lambda event: event.priority)

        for callable in possible_callables:
            if callable.priority <= self._beat:
                try: 
                    func, args, kwargs = callable.item
                    func(*args, **kwargs)
                    if callable.once:
                        del self._children[callable.name]
                except BadFunctionError as e:
                    info_message(f"Bad Function : {e}")
                    pass

    def beats_until_next_bar(self):
        """Return the number of beats until the next bar."""
        return self._denominator - self._beat % self._denominator

    def add(self, func: Callable, time: int | float = None, once: bool = False, *args, **kwargs):
        """Add any Callable to the clock.

        Args:
            func (Callable): The function to be executed.
            time (int|float, optional): The beat at which the event 
            should be executed. Defaults to clock.beat + 1.
            once (bool, optional): If True, the function will only be executed once.
            
        Returns:
            None
        """
        if time is None:
            time = self.beat + 1

        if isinstance(func, Callable) and func.__name__ != "<lambda>":
            func_name = func.__name__
        else:
            func_name = str(uuid.uuid4())

        if func_name in self._children:
            self._children[func_name].priority = time
            self._children[func_name].item = (func, args, kwargs)
        else:
            # Extract priority from the time argument
            self._children[func_name] = PriorityEvent(
                name=func_name, 
                priority=time, 
                once=once,
                item=(func, args, kwargs)
            )

    def clear(self) -> None:
        """Clear all events from the clock."""
        self._children = {}

    def remove(self, *args) -> None:
        """Remove an event from the clock."""
        args = filter(lambda x: isinstance(x, types.FunctionType | types.LambdaType), args)
        for func in args:
            if func.__name__ in self._children:
                del self._children[func.__name__]


    def next_bar(self) -> Number:
        """Return the time position of the next bar"""
        return self.beat + self.beats_until_next_bar()
