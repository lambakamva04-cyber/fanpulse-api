from config import Mode, Colors
from device_communicator import DeviceCommunicator
from event_handler import MIDIEventHandler
from transport_controller import TransportController
from channel_mode import ChannelModeHandler
from sequencer_mode import SequencerModeHandler
from mixer_mode import MixerModeHandler
from instrument_mode import InstrumentModeHandler
import ui
import time


class SMK37ProController:
    def __init__(self):
        self.device = DeviceCommunicator()
        self.transport = TransportController(self.device)
        self.event_handler = MIDIEventHandler(self)

        self.mode_handlers = {
            Mode.CHANNEL: ChannelModeHandler(self.device),
            Mode.SEQUENCER: SequencerModeHandler(self.device),
            Mode.MIXER: MixerModeHandler(self.device),
            Mode.INSTRUMENTS: InstrumentModeHandler(self.device)
        }

        self.current_mode = None
        self.previous_mode = None
        self.initialized = False
        
        self.nav_button_left_pressed = False
        self.nav_button_right_pressed = False
        self.dual_press_detected = False

    @property
    def current_mode_handler(self):
        """Get current mode handler"""
        if self.current_mode is None:
            return None
        return self.mode_handlers.get(self.current_mode)

    def initialize(self):
        """Initialize the controller"""
        if not self.initialized:
            self.device.connect()
            self.device.switch_bank(1)
            self.device.send_startup_message()
            self._setup_initial_lights()
            self._setup_initial_pad_displays()
            self.initialized = True
            self._enter_mode(Mode.CHANNEL)

    def shutdown(self):
        """Shutdown the controller"""
        if self.initialized:
            if self.current_mode_handler:
                self.current_mode_handler.on_exit_mode()
                self.device.clear_all_strings()
            self.device.disconnect()
            self.initialized = False
            

    def process_midi_event(self, event_data):
        """Process incoming MIDI event"""
        if not self.initialized:
            return

        self.event_handler.process_event(event_data)

    def switch_mode(self, new_mode: Mode):
        """Switch to a different mode"""
        if self.current_mode is None:
            self._enter_mode(new_mode)
        elif new_mode == self.current_mode:
            self.device.switch_bank(1)
        else:
            self._switch_to_mode(new_mode)

    def _enter_mode(self, mode: Mode):
        """Enter a mode for the first time"""
        self.current_mode = mode
        self._update_mode_button_lights()

        current_handler = self.current_mode_handler
        if current_handler:
            current_handler.on_enter_mode()

    def _switch_to_mode(self, new_mode: Mode):
        """Switch from one mode to another"""
        if self.current_mode_handler:
            self.current_mode_handler.on_exit_mode()

        self.previous_mode = self.current_mode
        self.current_mode = new_mode

        self._update_mode_button_lights()

        current_handler = self.current_mode_handler
        if current_handler:
            current_handler.on_enter_mode()

    def update_idle(self):
        """Update function called during idle time"""
        if not self.initialized:
            return
        self.transport.update_lights()

        if self.current_mode_handler:
            self.current_mode_handler.update_lights()

        if self.previous_mode != self.current_mode:
            self._update_mode_button_lights()
            self.previous_mode = self.current_mode

    def handle_globe_up(self):
        """Handle globe up navigation"""
        ui.up()
        self.device.set_light_solid(4, Colors.WHITE)

    def handle_globe_up_release(self):
        """Handle globe up navigation release"""
        self.device.set_light_solid(4, Colors.GLOBE_MODE)

    def handle_globe_down(self):
        """Handle globe down navigation"""
        ui.down()
        self.device.set_light_solid(5, Colors.WHITE)

    def handle_globe_down_release(self):
        """Handle globe down navigation release"""
        self.device.set_light_solid(5, Colors.GLOBE_MODE)

    def handle_globe_left(self):
        """Handle globe left navigation"""
        ui.left()
        self.device.set_light_solid(7, Colors.WHITE)

    def handle_globe_left_release(self):
        """Handle globe left navigation release"""
        self.device.set_light_solid(7, Colors.GLOBE_MODE)

    def handle_globe_right(self):
        """Handle globe right navigation"""
        ui.right()
        self.device.set_light_solid(6, Colors.WHITE)

    def handle_globe_right_release(self):
        """Handle globe right navigation release"""
        self.device.set_light_solid(6, Colors.GLOBE_MODE)

    def _setup_initial_lights(self):
        """Setup initial lights - no mode active"""
        for i in range(4):
            self.device.set_light_solid(i, Colors.GLOBE_MODE)
            time.sleep(0.01)

        for i in range(4, 8):
            self.device.set_light_solid(i, Colors.GLOBE_MODE)
            time.sleep(0.01)

        for i in range(8, 16):
            self.device.set_light_solid(i, Colors.GLOBE_TRANSPORT)
            time.sleep(0.01)

        self.device.set_light_solid(32, 0x02)

        self.device.set_light_solid(33, Colors.OFF)

        for i in range(16, 32):
            self.device.turn_off_light(i)

    def _setup_initial_pad_displays(self):
        """Send initial strings to all pads"""
        pad_texts = {
            0: "Cha Mode",
            1: "Seq Mode",
            2: "Mixer Mode",
            3: "Inst Mode",
            4: "Up",
            5: "Down",
            6: "Right",
            7: "Left",
            8: "Chan Rack",
            9: "Mixer",
            10: "Playlist",
            11: "Rewind",
            12: "Fast Fow",
            13: "Metronome",
            14: "PAT/SONG",
            15: "Undo"
        }
        for pad, text in pad_texts.items():
            self.device.send_pad_string(pad, text)

    def _update_mode_button_lights(self):
        """Update mode button lights"""
        mode_button_map = {
            Mode.CHANNEL: 0,
            Mode.SEQUENCER: 1,
            Mode.MIXER: 2,
            Mode.INSTRUMENTS: 3
        }

        if self.current_mode is None:
            for i in range(4):
                self.device.set_light_solid(i, Colors.GLOBE_MODE)
        else:
            for i in range(4):
                self.device.set_light_solid(i, Colors.GLOBE_MODE)

            current_button = mode_button_map.get(self.current_mode)
            if current_button is not None:
                self.device.set_light_solid(current_button, Colors.GLOBE_TRANSPORT)
    
    def handle_nav_left_press(self):
        """Handle left navigation button press (CC 0x38, value 0x7F)"""
        self.nav_button_left_pressed = True
        
        if self.nav_button_left_pressed and self.nav_button_right_pressed:
            self.device.switch_bank(0)
            self.dual_press_detected = True
            return True
        
        return False
    
    def handle_nav_left_release(self):
        """Handle left navigation button release (CC 0x38, value 0x00)"""
        self.nav_button_left_pressed = False
        
        if not self.nav_button_left_pressed and not self.nav_button_right_pressed and self.dual_press_detected:
            self.device.switch_bank(1)
            self.dual_press_detected = False
            return True
        
        if self.dual_press_detected:
            return True
        
        return False
    
    def handle_nav_right_press(self):
        """Handle right navigation button press (CC 0x39, value 0x7F)"""
        self.nav_button_right_pressed = True
        
        if self.nav_button_left_pressed and self.nav_button_right_pressed:
            self.device.switch_bank(0)
            self.dual_press_detected = True
            return True
        
        return False
    
    def handle_nav_right_release(self):
        """Handle right navigation button release (CC 0x39, value 0x00)"""
        self.nav_button_right_pressed = False
        
        if not self.nav_button_left_pressed and not self.nav_button_right_pressed and self.dual_press_detected:
            self.device.switch_bank(1)
            self.dual_press_detected = False
            return True
        
        if self.dual_press_detected:
            return True
        
        return False