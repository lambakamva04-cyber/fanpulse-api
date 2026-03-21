# name=Novation Launch Control 3 MIDI
# supportedHardwareIds=00 20 29 57 01 00 00,00 20 29 58 01 00 00,00 20 29 59 01 00 00,00 20 29 5A 01 00 00,00 20 29 5B 01 00 00,00 20 29 5C 01 00 00,00 20 29 5D 01 00 00,00 20 29 5E 01 00 00
from script.fl import FL
from script.midi_bypass import MidiBypass

fl = FL()
midi_bypass = MidiBypass(fl)


def OnPitchBend(eventData):
    midi_bypass.on_pitch_bend(eventData)
