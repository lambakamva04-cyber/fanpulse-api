from enum import Enum


class Mode(Enum):
    CHANNEL = 'Channel'
    SEQUENCER = 'Sequencer'
    MIXER = 'Mixer'
    INSTRUMENTS = 'Instruments'


class MIDI:
    NOTE_ON_CH1 = 0x90
    NOTE_OFF_CH1 = 0x80
    NOTE_ON_CH2 = 0x91
    NOTE_OFF_CH2 = 0x81
    CC = 0xB0

    LEFT_TURN = 0x01
    RIGHT_TURN = 0x45


TRANSPORT_CONTROLS = {
    (0x91, 0x7b): 'play',
    (0x91, 0x7c): 'record',

    (0x91, 0x73): 'view_channel_rack',
    (0x91, 0x74): 'view_playlist',
    (0x91, 0x75): 'view_mixer',
    (0x91, 0x76): 'rewind_press',
    (0x91, 0x77): 'fast_forward_press',
    (0x91, 0x78): 'metronome',
    (0x91, 0x79): 'loop',
    (0x91, 0x7A): 'undo',

    (0x81, 0x76): 'rewind_release',
    (0x81, 0x77): 'fast_forward_release',
    (0x81, 0x78): 'metronome_release',
    (0x81, 0x79): 'loop_release',
    (0x81, 0x7A): 'undo_release',
}

MODE_BUTTONS = {
    (0x91, 0x10): Mode.CHANNEL,
    (0x91, 0x11): Mode.SEQUENCER,
    (0x91, 0x12): Mode.MIXER,
    (0x91, 0x13): Mode.INSTRUMENTS
}

NAVIGATION = {
    (0x91, 0x6f): 'globe_up',
    (0x91, 0x70): 'globe_down',
    (0x91, 0x71): 'globe_right',
    (0x91, 0x72): 'globe_left',

    (0x81, 0x6f): 'globe_up_release',
    (0x81, 0x70): 'globe_down_release',
    (0x81, 0x71): 'globe_right_release',
    (0x81, 0x72): 'globe_left_release'
}

GRID_PADS = [0x28, 0x26, 0x2e, 0x2c, 0x31, 0x37, 0x33, 0x35,
             0x25, 0x24, 0x2a, 0x36, 0x30, 0x2f, 0x2d, 0x2b]

LIGHT_INDICES = list(range(16))

KNOB_CCS = list(range(0x1E, 0x26))
FADER_CCS = [0x44, 0x45, 0x46, 0x47]

NAVIGATION_BUTTONS = {
    'UP': (MIDI.CC, 0x39, 0x00),
    'DOWN': (MIDI.CC, 0x38, 0x00),
}


class Colors:
    OFF = 0x00
    WHITE = 0x1C
    CHANNEL_MODE = 0x11
    CHANNEL_MODE_SELECTED = 0x12
    CHANNEL_SHIFT = 0x33
    SEQUENCER_MODE = 0x09
    SEQUENCER_ACTIVE = 0x0F
    CHANNEL_MUTE = 0x03
    CHANNEL_MUTE_SELECTED = 0x04
    MIXER_MUTE = 0x23
    MIXER_SOLO = 0x25
    MIXER_MASTER = 0x26
    INSTRUMENT_MODE = 0x07
    INSTRUMENT_FPC = 0x2f
    GLOBE_MODE = 0x19
    GLOBE_TRANSPORT = 0x15


PAD_TO_LIGHT = {
    0x28: 0, 0x26: 1, 0x2e: 2, 0x2c: 3,
    0x31: 4, 0x37: 5, 0x33: 6, 0x35: 7,
    0x25: 8, 0x24: 9, 0x2a: 10, 0x36: 11,
    0x30: 12, 0x2f: 13, 0x2d: 14, 0x2b: 15
}

DEVICE_SETTINGS = {
    'MAX_CHANNELS': 199,
    'MAX_TRACKS': 125,
    'GRID_SIZE': 16,
    'KNOB_COUNT': 8,
    'VOLUME_STEP': 0.02,
    'PAN_STEP': 0.02,
    'EQ_FADER_COUNT': 4,
    'EQ_DB_RANGE': 18.0,
    'EQ_BANDS': ['Low shelf', 'Peaking', 'High shelf']
}