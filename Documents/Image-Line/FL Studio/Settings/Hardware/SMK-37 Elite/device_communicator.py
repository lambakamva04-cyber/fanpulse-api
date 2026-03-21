import device
import time
from config import Colors
from text_encoding import text_to_bytes


class DeviceCommunicator:
    EFFECT_SOLID = 0x5A
    EFFECT_BREATHING = 0x5B
    EFFECT_RESTORE = 0x5C

    def __init__(self):
        self.connected = False
        self._pad_light_states = {}

    def connect(self):
        """Initialize device connection"""
        self.connected = True

    def disconnect(self):
        """Clean shutdown"""
        if self.connected:
            self._shutdown_lights()
            self._send_close_message()
            self.connected = False

    def send_midi(self, status: int, data1: int, data2: int):
        """Send standard MIDI message"""
        if not self.connected:
            return
        device.midiOutMsg(status | (data1 << 8) | (data2 << 16))

    def set_pad_light(self, pad_index: int, color: int, effect: int = None):
        """Set individual pad light with caching"""
        if effect is None:
            effect = self.EFFECT_SOLID

        cache_key = (pad_index, color, effect)
        if self._pad_light_states.get(pad_index) == cache_key:
            return

        self._send_sysex_light(pad_index, color, effect)
        self._pad_light_states[pad_index] = cache_key

    def set_light_solid(self, pad_index: int, color: int):
        """Set solid color light"""
        self.set_pad_light(pad_index, color, self.EFFECT_SOLID)

    def set_light_breathing(self, pad_index: int, color: int):
        """Set breathing effect light"""
        self.set_pad_light(pad_index, color, self.EFFECT_BREATHING)

    def set_light_flashing(self, pad_index: int, color1: int, color2: int):
        """Set flashing between two colors"""
        self.set_pad_light(pad_index, color1, color2)

    def turn_off_light(self, pad_index: int):
        """Turn off specific light"""
        self.set_pad_light(pad_index, Colors.OFF)

    def switch_bank(self, bank: int):
        """Switch device bank (0 or 1)"""
        sysex1 = [0xF0, 0x35, 0x36, 0x00, bank, 0xF7]
        sysex2 = [0xF0, 0x35, 0x36, 0x01, bank, 0xF7]
        device.midiOutSysex(bytes(sysex1))
        device.midiOutSysex(bytes(sysex2))

    def send_pad_string(self, pad_index: int, text: str):
        """Send a string to a specific pad."""
        if not (0 <= pad_index <= 31):
            return
        target_id = 0x00 + pad_index
        self._send_string_message(target_id, text)

    def send_knob_name_string(self, knob_index: int, text: str):
        """Send a string to a specific knob's name display."""
        if not (0 <= knob_index <= 15):
            return
        target_id = 0x20 + knob_index
        self._send_string_message(target_id, text)

    def send_knob_volume_string(self, knob_index: int, text: str):
        """Send a string to a specific knob's volume display."""
        if not (0 <= knob_index <= 15):
            return
        target_id = 0x30 + knob_index
        self._send_string_message(target_id, text)

    def send_knob_volume_with_value(self, knob_index: int, volume_0_125: int, volume_db_text: str):
        """Send volume with 0-125 value bytes followed by dB text."""
        if not (0 <= knob_index <= 15):
            return
        if not self.connected:
            return
            
        target_id = 0x30 + knob_index
        
        volume_byte = volume_0_125
        
        db_text_bytes = text_to_bytes(volume_db_text)
        
        combined_bytes = [volume_byte] + db_text_bytes
        length = len(combined_bytes)
        
        if length > 255:
            combined_bytes = combined_bytes[:255]
            length = 255
            
        sysex_message = [0xF0, 0x35, 0x37, target_id, length] + combined_bytes + [0xF7]
        device.midiOutSysex(bytes(sysex_message))

    def clear_all_strings(self):
        """Clear all string displays on the device"""
        if not self.connected:
            return
        clear_message = [0xF0, 0x35, 0x37, 0x7F, 0x03, 0x7F, 0x7F, 0xF7]
        device.midiOutSysex(bytes(clear_message))
    
    def clear_mode_strings(self):
        """Clear only mode-specific pad strings (pads 16-31), preserving global pads 0-15"""
        if not self.connected:
            return
        
        for i in range(16, 32):
            self.send_pad_string(i, "")

    def send_startup_message(self):
        """Send FL Studio startup message to device ID 0x40"""
        self._send_string_message(0x40, "FL Studio")

    def send_fader_name_string(self, fader_index: int, text: str):
        """Send a string to a specific fader's name display (faders 0-7)."""
        if not (0 <= fader_index <= 7):
            return
        target_id = 0x41 + fader_index
        self._send_string_message(target_id, text)

    def send_fader_value_string(self, fader_index: int, text: str):
        """Send a string to a specific fader's value display (faders 0-7)."""
        if not (0 <= fader_index <= 7):
            return
        target_id = 0x49 + fader_index
        self._send_string_message(target_id, text)

    def _send_string_message(self, target_id: int, text: str):
        """Helper to construct and send the string SysEx message."""
        if not self.connected:
            return

        text_bytes = text_to_bytes(text)
        length = len(text_bytes)

        if length > 255:
            text_bytes = text_bytes[:255]
            length = 255

        sysex_message = [0xF0, 0x35, 0x37, target_id, length] + list(text_bytes) + [0xF7]
        device.midiOutSysex(bytes(sysex_message))

    def _send_sysex_light(self, pad_index: int, color: int, effect: int):
        """Send SYSEX lighting message"""
        if not (0 <= pad_index <= 33):
            print(f"Invalid pad index: {pad_index}")
            return

        sysex_data = [0xF0, 0x35, pad_index, color, effect, 0xF7]
        device.midiOutSysex(bytes(sysex_data))

    def _shutdown_lights(self):
        """Turn off all lights on shutdown"""
        for pad_index in range(32):
            self.set_pad_light(pad_index, Colors.OFF, self.EFFECT_RESTORE)
            time.sleep(0.01)
        self._pad_light_states.clear()

    def _send_close_message(self):
        """Send device close message"""
        self.send_midi(0x9F, 0x7F, 0x7F)