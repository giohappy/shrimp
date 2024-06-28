from .configuration import read_configuration
from .clock import Clock 
from .midi import MIDIOut, MIDIIn
import code

CONFIGURATION = read_configuration()
clock = Clock(CONFIGURATION["tempo"])
now = clock.beat
midi = MIDIOut(CONFIGURATION["midi_out_port"], clock)
midi_in = MIDIIn(CONFIGURATION["midi_in_port"], clock)
# The monitoring loop is blocking exit...
# clock.add(now, midi_in._monitoring_loop)
clock.start()

def exit():
    """Exit the interactive shell"""
    clock.stop()
    raise SystemExit

def dada():
    """Print the current clock state"""
    print(f"Bar: {clock.bar}, Beat: {clock.beat}, Phase: {clock.phase}, Tempo: {clock.tempo}")
    clock.add(clock.beat + 1, dada)

def bip():
    """Play a note"""
    from random import randint, choice
    midi.note(72, 100, 1, 1)
    clock.add(int(clock.beat) + 1, bip)

if __name__ == "__main__":
    code.interact(
        local=locals(),
        banner="Welcome to the Baston interactive shell!", 
        exitmsg="Goodbye!"
    )
    exit()