import channels
import mixer
import transport
import ui
import time
from config import Colors, GRID_PADS, MIDI, KNOB_CCS, DEVICE_SETTINGS, NAVIGATION_BUTTONS


class SequencerModeHandler:
    def __init__(self, device_comm):
        self.device = device_comm
        self.grid_offset = 0
        self.step_states = [False] * 16
        self.current_step = 0
        self.last_active_step = None
        self.navigation_counter = 0
        self.pad_handlers = {}
        self.knob_handlers = {}
        
        self.last_sent_knob_names = {}
        self.last_sent_volumes = {}
        self.last_volume_send_time = {}
        self.volume_throttle_delay = 0.02
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup sequencer mode handlers"""
        for i, pad in enumerate(GRID_PADS):
            self.pad_handlers[(MIDI.NOTE_ON_CH2, pad)] = lambda idx=i: self._toggle_step(idx)
        self._setup_knob_handlers()
        self._setup_navigation()
        
    def _setup_knob_handlers(self):
        """Setup knob handlers for volume/pan control (first 2 knobs only)"""
        knob0_cc = KNOB_CCS[0]
        self.knob_handlers[(MIDI.CC, knob0_cc, MIDI.LEFT_TURN)] = self._volume_down
        self.knob_handlers[(MIDI.CC, knob0_cc, MIDI.RIGHT_TURN)] = self._volume_up
        
        knob1_cc = KNOB_CCS[1]
        self.knob_handlers[(MIDI.CC, knob1_cc, MIDI.LEFT_TURN)] = self._pan_left
        self.knob_handlers[(MIDI.CC, knob1_cc, MIDI.RIGHT_TURN)] = self._pan_right

    def _setup_navigation(self):
        """Setup navigation for sequencer mode - navigate through channels"""
        self.knob_handlers[NAVIGATION_BUTTONS['UP']] = self._move_channel_up
        self.knob_handlers[NAVIGATION_BUTTONS['DOWN']] = self._move_channel_down

    def handle_event(self, event_data) -> bool:
        """Handle MIDI events for sequencer mode"""
        pad_key = (event_data.status, event_data.data1)
        if pad_key in self.pad_handlers:
            self.pad_handlers[pad_key]()
            event_data.handled = True
            return True

        knob_key = (event_data.status, event_data.data1, event_data.data2)
        if knob_key in self.knob_handlers:
            self.knob_handlers[knob_key]()
            event_data.handled = True
            return True

        if self._handle_navigation(event_data):
            return True

        return False

    def _handle_navigation(self, event_data) -> bool:
        """Handle navigation events with counter for sensitivity"""
        nav_events = {
            (0xB0, 0x24, 0x45): self._move_channel_up,
            (0xB0, 0x24, 0x01): self._move_channel_down,
            (0xB0, 0x25, 0x01): self._move_grid_left,
            (0xB0, 0x25, 0x45): self._move_grid_right
        }

        nav_key = (event_data.status, event_data.data1, event_data.data2)

        if nav_key in nav_events:
            self.navigation_counter += 1

            if self.navigation_counter >= 15:
                nav_events[nav_key]()
                self.navigation_counter = 0

            event_data.handled = True
            return True

        return False

    def on_enter_mode(self):
        """Initialize sequencer mode"""
        self.device.clear_mode_strings()
        
        self.last_sent_knob_names.clear()
        self.last_sent_volumes.clear()
        self.last_volume_send_time.clear()
        
        self._update_all_step_lights()
        self._update_volume_pan_displays()
        self._update_pad_strings()
        self._set_default_navigation_labels()

    def on_exit_mode(self):
        """Clean up when leaving sequencer mode"""
        self.last_active_step = None
        self._clear_navigation_feedback()
        
        for i in range(16, 32):
            self.device.turn_off_light(i)

    def update_lights(self):
        """Update sequencer mode lights"""
        self._update_step_states()
        self._update_playback_position()

    def _toggle_step(self, step_index: int):
        """Toggle step on/off"""
        selected_channel = channels.selectedChannel()
        actual_step = step_index + self.grid_offset

        current_state = channels.getGridBit(selected_channel, actual_step)
        new_state = not current_state

        channels.setGridBit(selected_channel, actual_step, new_state)

        color = Colors.SEQUENCER_ACTIVE if new_state else Colors.SEQUENCER_MODE
        self.device.set_light_solid(step_index + 16, color)

        self.step_states[step_index] = new_state

    def _volume_down(self):
        """Decrease volume for selected channel"""
        selected = channels.selectedChannel()
        current_volume = channels.getChannelVolume(selected)
        new_volume = max(current_volume - DEVICE_SETTINGS['VOLUME_STEP'], 0)
        channels.setChannelVolume(selected, new_volume)
        self._update_knob_display(0, selected)
        self._update_display()

    def _volume_up(self):
        """Increase volume for selected channel"""
        selected = channels.selectedChannel()
        current_volume = channels.getChannelVolume(selected)
        new_volume = min(current_volume + DEVICE_SETTINGS['VOLUME_STEP'], 1)
        channels.setChannelVolume(selected, new_volume)
        self._update_knob_display(0, selected)
        self._update_display()

    def _pan_left(self):
        """Pan left for selected channel"""
        selected = channels.selectedChannel()
        current_pan = channels.getChannelPan(selected)
        new_pan = max(current_pan - DEVICE_SETTINGS['PAN_STEP'], -1)
        channels.setChannelPan(selected, new_pan)
        self._update_knob_display(1, selected)
        self._update_display()

    def _pan_right(self):
        """Pan right for selected channel"""
        selected = channels.selectedChannel()
        current_pan = channels.getChannelPan(selected)
        new_pan = min(current_pan + DEVICE_SETTINGS['PAN_STEP'], 1)
        channels.setChannelPan(selected, new_pan)
        self._update_knob_display(1, selected)
        self._update_display()

    def _update_step_states(self):
        """Update step state lights if they changed"""
        selected_channel = channels.selectedChannel()

        for step in range(16):
            actual_step = step + self.grid_offset
            current_state = channels.getGridBit(selected_channel, actual_step)

            if current_state != self.step_states[step]:
                color = Colors.SEQUENCER_ACTIVE if current_state else Colors.SEQUENCER_MODE
                self.device.set_light_solid(step + 16, color)
                self.step_states[step] = current_state

    def _update_playback_position(self):
        """Update playback position indicator"""
        if not transport.isPlaying():
            if self.last_active_step is not None:
                self._restore_step_light(self.last_active_step)
                self.last_active_step = None
            return

        song_position = mixer.getSongStepPos() % 64
        current_step = song_position - self.grid_offset

        if 0 <= current_step < 16:
            if self.last_active_step is not None and self.last_active_step != current_step:
                self._restore_step_light(self.last_active_step)

            self.device.set_light_solid(current_step + 16, Colors.WHITE)
            self.last_active_step = current_step
        else:
            if self.last_active_step is not None:
                self._restore_step_light(self.last_active_step)
                self.last_active_step = None

    def _restore_step_light(self, step_index: int):
        """Restore step light to its normal state"""
        if 0 <= step_index < 16:
            color = Colors.SEQUENCER_ACTIVE if self.step_states[step_index] else Colors.SEQUENCER_MODE
            self.device.set_light_solid(step_index + 16, color)

    def _update_all_step_lights(self):
        """Update all step lights"""
        selected_channel = channels.selectedChannel()

        for step in range(16):
            actual_step = step + self.grid_offset
            current_state = channels.getGridBit(selected_channel, actual_step)
            color = Colors.SEQUENCER_ACTIVE if current_state else Colors.SEQUENCER_MODE
            self.device.set_light_solid(step + 16, color)
            self.step_states[step] = current_state

    def _move_channel_up(self):
        """Move to next channel"""
        self._show_navigation_feedback("up")
        current = channels.selectedChannel()
        next_channel = (current + 1) % channels.channelCount()
        channels.selectOneChannel(next_channel)
        self._update_all_step_lights()
        self._update_volume_pan_displays()
        self._update_pad_strings()
        self._update_display()
        self._update_navigation_knob_display()

    def _move_channel_down(self):
        """Move to previous channel"""
        self._show_navigation_feedback("down")
        current = channels.selectedChannel()
        prev_channel = (current - 1) % channels.channelCount()
        channels.selectOneChannel(prev_channel)
        self._update_all_step_lights()
        self._update_volume_pan_displays()
        self._update_pad_strings()
        self._update_display()
        self._update_navigation_knob_display()

    def _move_grid_left(self):
        """Move grid view left"""
        self._show_navigation_feedback("left")
        self.grid_offset = max(0, self.grid_offset - 16)
        self._update_all_step_lights()
        self._update_pad_strings()
        self._update_display()

    def _move_grid_right(self):
        """Move grid view right"""
        self._show_navigation_feedback("right")
        self.grid_offset = min(48, self.grid_offset + 16)
        self._update_all_step_lights()
        self._update_pad_strings()
        self._update_display()

    def _update_display(self):
        """Update FL Studio display"""
        selected_channel = channels.selectedChannel()
        ui.crDisplayRect(self.grid_offset, selected_channel, 16, 1, 500)

    def _update_knob_display(self, knob_index: int, channel_index: int):
        """Update knob display with channel info and throttling (like other modes)"""
        if knob_index not in [0, 1]:
            return
            
        if channel_index >= channels.channelCount():
            self.device.send_knob_name_string(knob_index + 8, "")
            self.device.send_knob_volume_string(knob_index + 8, "")
            self.last_sent_knob_names[knob_index] = ""
            return
            
        try:
            channel_name = channels.getChannelName(channel_index)
            if not channel_name or channel_name.strip() == "":
                channel_name = f"Ch {channel_index + 1}"
        except:
            channel_name = f"Ch {channel_index + 1}"
        
        knob_display_name = channel_name[:12]
        
        if self.last_sent_knob_names.get(knob_index) != knob_display_name:
            self.device.send_knob_name_string(knob_index + 8, knob_display_name)
            self.last_sent_knob_names[knob_index] = knob_display_name
        
        current_time = time.time()
        
        if knob_index == 0:
            volume_float = channels.getChannelVolume(channel_index)
            try:
                volume_db = channels.getChannelVolume(channel_index, 1)
            except:
                if volume_float <= 0:
                    volume_db = -100
                else:
                    import math
                    volume_db = 20 * math.log10(volume_float)
            
            volume_0_125 = round(volume_float * 125)

            if volume_db <= -100:
                volume_db_str = "-INF db"
            else:
                volume_db_str = f"{volume_db:.1f}db"

            volume_key = f"vol:{volume_0_125}:{volume_db_str}"
            
        else:
            pan = channels.getChannelPan(channel_index)

            if pan < -0.02:
                pan_value = abs(int(pan * 100))
                pan_str = f"Left {pan_value}"
                pan_byte = pan_value
            elif pan > 0.02:
                pan_value = int(pan * 100)
                pan_str = f"Right {pan_value}"
                pan_byte = pan_value
            else:
                pan_str = "Centered"
                pan_byte = 0

            volume_key = f"pan:{pan_byte}:{pan_str}"
            pan_str = pan_str

        should_send = False
        last_send_time = self.last_volume_send_time.get(knob_index, 0)

        if self.last_sent_volumes.get(knob_index) != volume_key:
            if current_time - last_send_time >= self.volume_throttle_delay:
                should_send = True
        
        if should_send:
            if knob_index == 0:
                self.device.send_knob_volume_with_value(knob_index + 8, volume_0_125, volume_db_str)
            else:
                self.device.send_knob_volume_with_value(knob_index + 8, pan_byte, pan_str)
                
            self.last_sent_volumes[knob_index] = volume_key
            self.last_volume_send_time[knob_index] = current_time

            ui.crDisplayRect(0, channel_index, 1, 1, 500, 32)

    def _update_volume_pan_displays(self):
        """Update knob displays for volume and pan (knobs 0 and 1)"""
        selected = channels.selectedChannel()
        self._update_knob_display(0, selected)
        self._update_knob_display(1, selected)

    def _get_channel_name(self, channel_index: int) -> str:
        """Get channel name with proper fallbacks"""
        try:
            if channel_index >= channels.channelCount():
                return f"Ch {channel_index + 1}"
            channel_name = channels.getChannelName(channel_index)
            if not channel_name or channel_name.strip() == "":
                return f"Ch {channel_index + 1}"
            return channel_name[:12]
        except:
            return f"Ch {channel_index + 1}"

    def _update_pad_strings(self):
        """Update pad strings with grid position info (CH1 GRID16 format)"""
        selected_channel = channels.selectedChannel()
        
        for pad_index in range(16):
            actual_step = pad_index + self.grid_offset + 1
            pad_string = f"CH{selected_channel + 1} GRID{actual_step}"
            self.device.send_pad_string(pad_index + 16, pad_string)

    def _show_navigation_feedback(self, direction: str):
        """Show navigation feedback on knobs 6 & 7 with volume bytes"""
        if direction in ["up", "down"]:
            current_channel = channels.selectedChannel()
            channel_name = self._get_channel_name(current_channel)

            if direction == "up":
                next_channel = (current_channel + 1) % channels.channelCount()
                next_channel_name = self._get_channel_name(next_channel)
                name_text = next_channel_name
                volume_text = "Up"
                volume_byte = 0
            else:
                prev_channel = (current_channel - 1) % channels.channelCount()
                prev_channel_name = self._get_channel_name(prev_channel)
                name_text = prev_channel_name
                volume_text = "Down" 
                volume_byte = 127
            
            self.device.send_knob_name_string(14, name_text)
            self.device.send_knob_volume_with_value(14, volume_byte, volume_text)
            
        elif direction in ["left", "right"]:
            if direction == "left":
                name_text = "CH Right"
                volume_text = "Right"
                volume_byte = 127
            else:
                name_text = "CH Left"
                volume_text = "Left" 
                volume_byte = 0
                
            self.device.send_knob_name_string(15, name_text)
            self.device.send_knob_volume_with_value(15, volume_byte, volume_text)

    def _update_navigation_knob_display(self):
        """Update navigation knob to show current channel name"""
        current_channel = channels.selectedChannel()
        channel_name = self._get_channel_name(current_channel)
        self.device.send_knob_name_string(14, channel_name)
        self.device.send_knob_volume_with_value(14, 127, "Down")

    def _set_default_navigation_labels(self):
        """Set default navigation knob labels"""
        current_channel = channels.selectedChannel()
        channel_name = self._get_channel_name(current_channel)
        
        self.device.send_knob_name_string(14, channel_name)
        self.device.send_knob_volume_with_value(14, 127, "Down")
        self.device.send_knob_name_string(15, "CH Right")
        self.device.send_knob_volume_with_value(15, 127, "Right")
        
    def _clear_navigation_feedback(self):
        """Clear navigation knob displays"""
        self.device.send_knob_name_string(14, "")
        self.device.send_knob_volume_string(14, "")
        self.device.send_knob_name_string(15, "")
        self.device.send_knob_volume_string(15, "")