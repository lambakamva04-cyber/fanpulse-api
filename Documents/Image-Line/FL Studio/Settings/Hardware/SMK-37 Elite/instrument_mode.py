"""
Handles instrument note mapping and FPC detection
"""
import channels
import device
from config import Colors, GRID_PADS, PAD_TO_LIGHT, MIDI


class InstrumentModeHandler:
    def __init__(self, device_comm):
        self.device = device_comm
        self.is_fpc_instrument = False
        self.current_channel_name = ""
        self.light_states = {}
        self.pad_handlers = {}
        self._setup_handlers()

    NOTE_REMAP = {
        0x28: None,
        0x26: 0x3D,
        0x2e: 0x3F,
        0x2c: None,
        0x31: 0x42,
        0x37: 0x44,
        0x33: 0x46,
        0x35: None,
        0x25: 0x3C,
        0x24: 0x3E,
        0x2a: 0x40,
        0x36: 0x41,
        0x30: 0x43,
        0x2f: 0x45,
        0x2d: 0x47,
        0x2b: 0x48
    }

    NOTE_NAMES = {
        0x3C: "C",   0x3D: "C#",  0x3E: "D",   0x3F: "D#",
        0x40: "E",   0x41: "F",   0x42: "F#",  0x43: "G",
        0x44: "G#",  0x45: "A",   0x46: "A#",  0x47: "B",
        0x48: "C5"
    }

    def _setup_handlers(self):
        """Setup instrument mode handlers"""
        for pad in GRID_PADS:
            self.pad_handlers[(MIDI.NOTE_ON_CH2, pad)] = lambda p=pad: self._note_on(p)
            self.pad_handlers[(MIDI.NOTE_OFF_CH2, pad)] = lambda p=pad: self._note_off(p)

    def handle_event(self, event_data) -> bool:
        """Handle MIDI events for instrument mode"""
        if event_data.data1 not in GRID_PADS:
            return False

        self._update_channel_detection()

        if self.is_fpc_instrument:
            return self._handle_fpc_event(event_data)
        else:
            return self._handle_normal_instrument_event(event_data)

    def _handle_fpc_event(self, event_data) -> bool:
        """Handle events for FPC instruments"""
        if event_data.status == MIDI.NOTE_ON_CH2:
            light_index = PAD_TO_LIGHT.get(event_data.data1)
            if light_index is not None:
                self.device.set_light_solid(light_index + 16, Colors.WHITE)

        elif event_data.status == MIDI.NOTE_OFF_CH2 or (
                event_data.status == MIDI.NOTE_ON_CH2 and event_data.data2 == 0):
            light_index = PAD_TO_LIGHT.get(event_data.data1)
            if light_index is not None:
                self.device.set_light_solid(light_index + 16, Colors.INSTRUMENT_FPC)

        return False

    def _handle_normal_instrument_event(self, event_data) -> bool:
        """Handle events for normal instruments"""
        if event_data.status in [MIDI.NOTE_ON_CH1, MIDI.NOTE_OFF_CH1]:
            return False

        if event_data.status in [MIDI.NOTE_ON_CH2, MIDI.NOTE_OFF_CH2]:
            remapped_note = self.NOTE_REMAP.get(event_data.data1)

            if remapped_note is not None:
                self._send_remapped_note(event_data.status, remapped_note, event_data.data2)

                handler_key = (event_data.status, event_data.data1)
                if handler_key in self.pad_handlers:
                    self.pad_handlers[handler_key]()

                event_data.handled = True
                return True
            else:
                handler_key = (event_data.status, event_data.data1)
                if handler_key in self.pad_handlers:
                    self.pad_handlers[handler_key]()

                event_data.handled = True
                return True

        if event_data.status == MIDI.NOTE_ON_CH2 and event_data.data2 == 0:
            remapped_note = self.NOTE_REMAP.get(event_data.data1)
            if remapped_note is not None:
                self._send_remapped_note(MIDI.NOTE_OFF_CH2, remapped_note, 0)

                note_off_key = (MIDI.NOTE_OFF_CH2, event_data.data1)
                if note_off_key in self.pad_handlers:
                    self.pad_handlers[note_off_key]()

                event_data.handled = True
                return True

        return False

    def _send_remapped_note(self, status: int, note: int, velocity: int):
        """Send the remapped MIDI note to FL Studio"""

        selected_channel = channels.selectedChannel()

        if status == MIDI.NOTE_ON_CH2:
            channels.midiNoteOn(selected_channel, note, velocity)
        elif status == MIDI.NOTE_OFF_CH2 or velocity == 0:
            channels.midiNoteOn(selected_channel, note, 0)

    def on_enter_mode(self):
        """Initialize instrument mode"""
        self.device.clear_mode_strings()
        self._update_channel_detection()
        self._update_all_lights()

    def on_exit_mode(self):
        """Clean up when leaving instrument mode"""
        for i in range(16, 32):
          self.device.turn_off_light(i)

    def update_lights(self):
        """Update instrument mode lights"""
        channel_name = self._get_channel_name()
        if channel_name != self.current_channel_name:
            self.current_channel_name = channel_name
            self._update_channel_detection()
            self._update_all_lights()

    def _note_on(self, pad_value: int):
        """Handle note on for any instrument"""
        light_index = PAD_TO_LIGHT.get(pad_value)
        if light_index is not None:
            self.device.set_light_solid(light_index + 16, Colors.WHITE)

    def _note_off(self, pad_value: int):
        """Handle note off for any instrument"""
        light_index = PAD_TO_LIGHT.get(pad_value)
        if light_index is not None:
            if self.is_fpc_instrument:
                default_color = Colors.INSTRUMENT_FPC
            else:
                default_color = Colors.INSTRUMENT_MODE if self.NOTE_REMAP.get(pad_value) else Colors.OFF

            self.device.set_light_solid(light_index + 16, default_color)

    def _update_channel_detection(self):
        """Update FPC detection based on current channel"""
        channel_name = self._get_channel_name()
        self.is_fpc_instrument = channel_name and channel_name.startswith("FPC")
        self.current_channel_name = channel_name

    def _update_all_lights(self):
        """Update all instrument mode lights and pad strings"""
        if self.is_fpc_instrument:
            for i in range(16):
                self.device.set_light_solid(i + 16, Colors.INSTRUMENT_FPC)
                self.device.send_pad_string(i + 16, "FPC")
        else:
            for i, pad in enumerate(GRID_PADS):
                if self.NOTE_REMAP.get(pad) is not None:
                    self.device.set_light_solid(i + 16, Colors.INSTRUMENT_MODE)
                    note_num = self.NOTE_REMAP[pad]
                    note_name = self.NOTE_NAMES.get(note_num, f"N{note_num}")
                    self.device.send_pad_string(i + 16, note_name)
                else:
                    self.device.turn_off_light(i + 16)
                    self.device.send_pad_string(i + 16, " ")

    def _get_channel_name(self) -> str:
        """Get current channel name"""
        try:
            current_channel = channels.selectedChannel()
            if current_channel is not None:
                return channels.getChannelName(current_channel)
        except:
            pass
        return ""