from typing import Dict, Callable, Tuple
from config import TRANSPORT_CONTROLS, MODE_BUTTONS, NAVIGATION, MIDI


class MIDIEventHandler:
    def __init__(self, controller):
        self.controller = controller
        self.global_handlers: Dict[Tuple, Callable] = {}
        self.mode_handlers: Dict[Tuple, Callable] = {}
        self._setup_global_handlers()

    def _setup_global_handlers(self):
        """Setup handlers that work across all modes"""
        for midi_key, action_name in TRANSPORT_CONTROLS.items():
            self.global_handlers[midi_key] = getattr(self.controller.transport, action_name)

        for midi_key, mode in MODE_BUTTONS.items():
            self.global_handlers[midi_key] = lambda m=mode: self.controller.switch_mode(m)

        for midi_key, action_name in NAVIGATION.items():
            handler_name = f"handle_{action_name}"
            if hasattr(self.controller, handler_name):
                self.global_handlers[midi_key] = getattr(self.controller, handler_name)
        
        self.global_handlers[(MIDI.CC, 0x38, 0x7F)] = self.controller.handle_nav_left_press
        self.global_handlers[(MIDI.CC, 0x38, 0x00)] = self.controller.handle_nav_left_release
        self.global_handlers[(MIDI.CC, 0x39, 0x7F)] = self.controller.handle_nav_right_press
        self.global_handlers[(MIDI.CC, 0x39, 0x00)] = self.controller.handle_nav_right_release

    def process_event(self, event_data) -> bool:
        """
        Process incoming MIDI event
        Returns True if event was handled
        """
        event_key = (event_data.status, event_data.data1)
        event_key_full = (event_data.status, event_data.data1, event_data.data2)

        if self._try_global_navigation_handler(event_key_full, event_data):
            return True

        current_mode = self.controller.current_mode_handler
        if current_mode and current_mode.handle_event(event_data):
            return True

        if event_data.status == 0x91 and event_data.data2 == 0:
            note_off_key = (0x81, event_data.data1)
            if self._try_global_handler(note_off_key, event_data):
                return True

        if self._try_global_handler(event_key_full, event_data):
            return True
        if self._try_global_handler(event_key, event_data):
            return True

        return False

    def _try_global_navigation_handler(self, event_key: Tuple, event_data) -> bool:
        """Try to handle navigation events specifically for dual press detection"""
        if event_data.status == MIDI.CC and event_data.data1 in [0x38, 0x39]:
            handler = self.global_handlers.get(event_key)
            if handler:
                try:
                    result = handler()
                    if result is True:
                        event_data.handled = True
                        return True
                except Exception as e:
                    print(f"Navigation handler error for {event_key}: {e}")
        return False

    def _try_global_handler(self, event_key: Tuple, event_data) -> bool:
        """Try to handle event with global handlers"""
        handler = self.global_handlers.get(event_key)
        if handler:
            try:
                result = handler()
                if result is not False:
                    event_data.handled = True
                    return True
            except Exception as e:
                print(f"Handler error for {event_key}: {e}")
        return False

    def register_mode_handler(self, event_key: Tuple, handler: Callable):
        """Register a mode-specific handler"""
        self.mode_handlers[event_key] = handler

    def clear_mode_handlers(self):
        """Clear all mode-specific handlers"""
        self.mode_handlers.clear()