"""
Controls channel selection with 16 pads, volume control with 8 knobs
"""
import channels
import ui
import math
import time
from config import Colors, GRID_PADS, PAD_TO_LIGHT, KNOB_CCS, MIDI, DEVICE_SETTINGS, NAVIGATION_BUTTONS


class ChannelModeHandler:
    def __init__(self, device_comm):
        self.device = device_comm
        self.track_offset = 0
        self.currently_selected = 0
        self.last_channel_count = 0
        self.breathing_timers = {}
        self.mute_states = {}
        self.pad_handlers = {}
        self.knob_handlers = {}
        self.channel_names_cache = {}
        self.displayed_names_cache = {}
        
        self.last_sent_knob_names = {}
        self.last_sent_volumes = {}
        self.last_volume_send_time = {}
        self.volume_throttle_delay = 0.02
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup all channel mode handlers"""
        self._setup_channel_select_pads()
        self._setup_knob_controls()
        self._setup_cc_navigation()

    def _setup_channel_select_pads(self):
        """Setup channel selection pads (all 16 pads)"""
        for i, pad in enumerate(GRID_PADS):
            self.pad_handlers[(MIDI.NOTE_ON_CH2, pad)] = lambda idx=i: self._select_channel(idx)

    def _setup_knob_controls(self):
        """Setup knob controls - all 8 knobs control channel volumes based on selected range"""
        for i, knob_cc in enumerate(KNOB_CCS):
            self.knob_handlers[(MIDI.CC, knob_cc, MIDI.LEFT_TURN)] = lambda idx=i: self._knob_volume_down(idx)
            self.knob_handlers[(MIDI.CC, knob_cc, MIDI.RIGHT_TURN)] = lambda idx=i: self._knob_volume_up(idx)

    def _setup_cc_navigation(self):
        """Setup CC-based navigation for channel mode"""
        self.knob_handlers[NAVIGATION_BUTTONS['UP']] = self._navigate_up
        self.knob_handlers[NAVIGATION_BUTTONS['DOWN']] = self._navigate_down

    def handle_event(self, event_data) -> bool:
        """Handle MIDI events for channel mode"""
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

        return False

    def on_enter_mode(self):
        """Initialize channel mode"""
        self.device.clear_mode_strings()
        
        self.last_sent_knob_names.clear()
        self.last_sent_volumes.clear()
        self.last_volume_send_time.clear()
        
        self.displayed_names_cache.clear()
        
        self.last_channel_count = channels.channelCount()
        self._update_track_offset()
        self._update_all_lights()
        self._update_all_channel_names()
        self._update_all_knob_displays()

    def on_exit_mode(self):
        """Clean up when leaving channel mode"""
        for i in range(16, 32):
            self.device.turn_off_light(i)

    def update_lights(self):
        """Update channel mode lights"""
        selected_channel = channels.selectedChannel()
        current_channel_count = channels.channelCount()

        if current_channel_count != self.last_channel_count:
            self.last_channel_count = current_channel_count
            
            self._invalidate_channel_names_cache()
            
            self.last_sent_knob_names.clear()
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()

            old_offset = self.track_offset
            self._update_track_offset()

            if old_offset != self.track_offset or True:
                self._update_all_lights()
                self._update_all_channel_names()
                self._update_all_knob_displays()
                self.currently_selected = selected_channel
                return

        self._update_mute_states()

        self._update_breathing_effects()

        if selected_channel != self.currently_selected:
            self._update_channel_selection_lights(selected_channel)
            self.currently_selected = selected_channel

    def _select_channel(self, pad_index: int):
        """Select channel based on pad (0-15)"""
        channel_index = pad_index + self.track_offset

        if channel_index >= channels.channelCount():
            return

        old_knob_range = self._get_knob_control_range()
        
        channels.selectOneChannel(channel_index)
        self._play_channel_note(channel_index)
        
        display_pad_index = pad_index + 16
        self._update_channel_name_display(display_pad_index, channel_index)
        
        new_knob_range = self._get_knob_control_range()
        if old_knob_range != new_knob_range:
            self.last_sent_knob_names.clear()
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()
            self._update_all_knob_displays()
        
        self._update_display()

    def _get_knob_control_range(self):
        """Get the 8-channel range that knobs should control based on selected channel"""
        selected = channels.selectedChannel()
        knob_range_start = (selected // 8) * 8
        return knob_range_start

    def _knob_volume_down(self, knob_index: int):
        """Decrease volume for specific knob's assigned channel"""
        knob_range_start = self._get_knob_control_range()
        target_channel = knob_range_start + knob_index
        
        if target_channel >= channels.channelCount():
            return
            
        current_volume = channels.getChannelVolume(target_channel)
        new_volume = max(current_volume - DEVICE_SETTINGS['VOLUME_STEP'], 0)
        channels.setChannelVolume(target_channel, new_volume)
        self._trigger_breathing_effect(target_channel)
        self._update_knob_display(knob_index, target_channel)

    def _knob_volume_up(self, knob_index: int):
        """Increase volume for specific knob's assigned channel"""
        knob_range_start = self._get_knob_control_range()
        target_channel = knob_range_start + knob_index
        
        if target_channel >= channels.channelCount():
            return
            
        current_volume = channels.getChannelVolume(target_channel)
        new_volume = min(current_volume + DEVICE_SETTINGS['VOLUME_STEP'], 1)
        channels.setChannelVolume(target_channel, new_volume)
        self._trigger_breathing_effect(target_channel)
        self._update_knob_display(knob_index, target_channel)

    def _update_knob_display(self, knob_index: int, channel_index: int):
        """Update knob display with channel info and throttling (like mixer mode)"""
        if not (0 <= knob_index <= 7):
            return
            
        if channel_index >= channels.channelCount():
            self.device.send_knob_name_string(knob_index + 8, "")
            self.device.send_knob_volume_string(knob_index + 8, "")
            self.last_sent_knob_names[knob_index] = ""
            return
            
        channel_name = self._get_channel_name(channel_index)
        
        knob_display_name = channel_name[:12]
        if self.last_sent_knob_names.get(knob_index) != knob_display_name:
            self.device.send_knob_name_string(knob_index + 8, knob_display_name)
            self.last_sent_knob_names[knob_index] = knob_display_name
        
        volume_float = channels.getChannelVolume(channel_index)
        try:
            volume_db = channels.getChannelVolume(channel_index, 1)
        except:
            if volume_float <= 0:
                volume_db = -100
            else:
                volume_db = 20 * math.log10(volume_float)
        
        volume_0_100 = round(volume_float * 100)
        
        if volume_db <= -100:
            volume_db_str = "-INF db"
        else:
            volume_db_str = f"{volume_db:.1f}db"
        
        volume_key = f"{volume_0_100}:{volume_db_str}"
        current_time = time.time()
        
        should_send = False
        last_send_time = self.last_volume_send_time.get(knob_index, 0)
        
        if self.last_sent_volumes.get(knob_index) != volume_key:
            if current_time - last_send_time >= self.volume_throttle_delay:
                should_send = True
        
        if should_send:
            self.device.send_knob_volume_with_value(knob_index + 8, volume_0_100, volume_db_str)
            self.last_sent_volumes[knob_index] = volume_key
            self.last_volume_send_time[knob_index] = current_time
            
            ui.crDisplayRect(0, channel_index, 1, 1, 500, 32)

    def _update_all_knob_displays(self):
        """Update all knob displays based on current knob control range"""
        knob_range_start = self._get_knob_control_range()
        
        for knob_index in range(8):
            target_channel = knob_range_start + knob_index
            self._update_knob_display(knob_index, target_channel)

    def _navigate_up(self):
        """Navigate to next channel (CC-based)"""
        old_knob_range = self._get_knob_control_range()
        
        current = channels.selectedChannel()
        next_channel = (current + 1) % channels.channelCount()
        channels.selectOneChannel(next_channel)
        self._update_track_offset()
        self._update_all_lights()
        self._update_all_channel_names()
        
        new_knob_range = self._get_knob_control_range()
        if old_knob_range != new_knob_range:
            self.last_sent_knob_names.clear()
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()
            self._update_all_knob_displays()

        self._update_display()

    def _navigate_down(self):
        """Navigate to previous channel (CC-based)"""
        old_knob_range = self._get_knob_control_range()
        
        current = channels.selectedChannel()
        prev_channel = (current - 1) % channels.channelCount()
        channels.selectOneChannel(prev_channel)
        self._update_track_offset()
        self._update_all_lights()
        self._update_all_channel_names()
        
        new_knob_range = self._get_knob_control_range()
        if old_knob_range != new_knob_range:
            self.last_sent_knob_names.clear()
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()
            self._update_all_knob_displays()
			
        self._update_display()

    def _update_track_offset(self):
        """Update track offset based on selected channel"""
        selected = channels.selectedChannel()
        self.track_offset = (selected // 16) * 16

    def _get_channel_name(self, channel_index: int) -> str:
        """Get channel name with caching"""
        if channel_index not in self.channel_names_cache:
            try:
                has_content = False
                try:
                    name = channels.getChannelName(channel_index)
                    if name and name.strip() != "":
                        has_content = True
                    
                    try:
                        plugin_name = channels.getChannelPluginName(channel_index)
                        if plugin_name and plugin_name.strip() != "":
                            has_content = True
                    except:
                        pass
                        
                except:
                    name = ""
                
                if has_content and name and name.strip() != "":
                    self.channel_names_cache[channel_index] = name[:12]
                else:
                    self.channel_names_cache[channel_index] = f"Channel {channel_index + 1}"
                    
            except:
                self.channel_names_cache[channel_index] = f"Channel {channel_index + 1}"
        
        return self.channel_names_cache[channel_index]

    def _update_channel_name_display(self, pad_index: int, channel_index: int):
        """Display channel name on specific pad"""
        if not (16 <= pad_index <= 31):
            return
            
        if channel_index >= channels.channelCount():
            default_channel_name = f"Channel {channel_index + 1}"
            if self.displayed_names_cache.get(pad_index) != default_channel_name:
                self.device.send_pad_string(pad_index, default_channel_name)
                self.displayed_names_cache[pad_index] = default_channel_name
            return
            
        channel_name = self._get_channel_name(channel_index)
        
        if self.displayed_names_cache.get(pad_index) != channel_name:
            self.device.send_pad_string(pad_index, channel_name)
            self.displayed_names_cache[pad_index] = channel_name

    def _update_all_channel_names(self):
        """Update channel names for all visible channels (pads 16-31)"""
        channel_count = channels.channelCount()
        
        for i in range(16):
            pad_index = i + 16
            channel_index = i + self.track_offset
            
            if channel_index < channel_count:
                self._update_channel_name_display(pad_index, channel_index)
            else:
                default_channel_name = f"Channel {channel_index + 1}"
                if self.displayed_names_cache.get(pad_index) != default_channel_name:
                    self.device.send_pad_string(pad_index, default_channel_name)
                    self.displayed_names_cache[pad_index] = default_channel_name

    def _clear_channel_name_display(self, pad_index: int):
        """Clear channel name display for a specific pad"""
        if 16 <= pad_index <= 31:
            self.device.send_pad_string(pad_index, "")
            self.displayed_names_cache.pop(pad_index, None)

    def _invalidate_channel_names_cache(self):
        """Clear channel names cache to force refresh"""
        self.channel_names_cache.clear()

    def _update_all_lights(self):
        """Update all channel mode lights"""
        selected_channel = channels.selectedChannel()
        channel_count = channels.channelCount()

        self.breathing_timers.clear()

        for i in range(16):
            channel_index = i + self.track_offset
            pad_index = i + 16

            if channel_index < channel_count:
                is_muted = channels.isChannelMuted(channel_index)
                is_selected = (channel_index == selected_channel)

                if is_selected:
                    if is_muted:
                        self.device.set_light_solid(pad_index, Colors.CHANNEL_MUTE_SELECTED)
                    else:
                        self.device.set_light_solid(pad_index, Colors.WHITE)
                else:
                    if is_muted:
                        self.device.set_light_solid(pad_index, Colors.CHANNEL_MUTE)
                    else:
                        self.device.set_light_solid(pad_index, Colors.CHANNEL_MODE)

                self.mute_states[channel_index] = is_muted
            else:
                self.device.turn_off_light(pad_index)
                default_channel_name = f"Channel {channel_index + 1}"
                if self.displayed_names_cache.get(pad_index) != default_channel_name:
                    self.device.send_pad_string(pad_index, default_channel_name)
                    self.displayed_names_cache[pad_index] = default_channel_name

    def _update_channel_selection_lights(self, selected_channel: int):
        """Update channel selection pad lights"""
        if selected_channel < self.track_offset or selected_channel >= self.track_offset + 16:
            self._update_track_offset()
            self._update_all_lights()
            self._update_all_channel_names()
            return

        channel_count = channels.channelCount()

        old_pad_index = (self.currently_selected - self.track_offset)
        new_pad_index = (selected_channel - self.track_offset)

        if (0 <= old_pad_index < 16 and
            self.currently_selected < channel_count and
            self.currently_selected >= self.track_offset and
            self.currently_selected not in self.breathing_timers):

            old_is_muted = channels.isChannelMuted(self.currently_selected)
            old_color = Colors.CHANNEL_MUTE if old_is_muted else Colors.CHANNEL_MODE
            self.device.set_light_solid(old_pad_index + 16, old_color)
            self.mute_states[self.currently_selected] = old_is_muted

        if (0 <= new_pad_index < 16 and
            selected_channel < channel_count and
            selected_channel >= self.track_offset):

            new_is_muted = channels.isChannelMuted(selected_channel)
            new_color = Colors.CHANNEL_MUTE_SELECTED if new_is_muted else Colors.WHITE
            self.device.set_light_solid(new_pad_index + 16, new_color)

            self.mute_states[selected_channel] = new_is_muted

    def _play_channel_note(self, channel_index: int):
        """Play a note on the selected channel"""
        channels.midiNoteOn(channel_index, 60, 127)
        channels.midiNoteOn(channel_index, 60, 0)

    def _update_display(self):
        """Update FL Studio display"""
        ui.crDisplayRect(0, self.track_offset, 16, 16, 500, 32)
        knob_range_start = self._get_knob_control_range()
        ui.crDisplayRect(0, knob_range_start, 16, 8, 500, 8)

    def _trigger_breathing_effect(self, channel_index: int):
        """Trigger breathing effect for a channel pad"""
        if self.track_offset <= channel_index < self.track_offset + 16:
            pad_index = channel_index - self.track_offset

            is_muted = channels.isChannelMuted(channel_index)
            is_selected = (channel_index == channels.selectedChannel())

            if is_selected:
                breath_color = Colors.CHANNEL_MUTE_SELECTED if is_muted else Colors.WHITE
            else:
                breath_color = Colors.CHANNEL_MUTE if is_muted else Colors.CHANNEL_MODE

            self.device.set_light_breathing(pad_index + 16, breath_color)

            import time
            self.breathing_timers[channel_index] = time.time() + 2.0

    def _update_breathing_effects(self):
        """Update breathing effects and restore normal lights when expired"""
        import time
        current_time = time.time()
        expired_channels = []

        for channel_index, expire_time in self.breathing_timers.items():
            if current_time >= expire_time:
                expired_channels.append(channel_index)

        for channel_index in expired_channels:
            if self.track_offset <= channel_index < self.track_offset + 16:
                pad_index = channel_index - self.track_offset

                is_muted = channels.isChannelMuted(channel_index)
                is_selected = (channel_index == channels.selectedChannel())

                if is_selected:
                    normal_color = Colors.CHANNEL_MUTE_SELECTED if is_muted else Colors.WHITE
                else:
                    normal_color = Colors.CHANNEL_MUTE if is_muted else Colors.CHANNEL_MODE

                self.device.set_light_solid(pad_index + 16, normal_color)

            del self.breathing_timers[channel_index]

    def _update_mute_states(self):
        """Update mute state display for all visible channels"""
        channel_count = channels.channelCount()

        for i in range(16):
            channel_index = i + self.track_offset

            if channel_index < channel_count:
                current_mute = channels.isChannelMuted(channel_index)
                cached_mute = self.mute_states.get(channel_index, False)

                if (current_mute != cached_mute and
                    channel_index not in self.breathing_timers):

                    is_selected = (channel_index == channels.selectedChannel())

                    if is_selected:
                        new_color = Colors.CHANNEL_MUTE_SELECTED if current_mute else Colors.WHITE
                    else:
                        new_color = Colors.CHANNEL_MUTE if current_mute else Colors.CHANNEL_MODE

                    self.device.set_light_solid(i + 16, new_color)
                    self.mute_states[channel_index] = current_mute