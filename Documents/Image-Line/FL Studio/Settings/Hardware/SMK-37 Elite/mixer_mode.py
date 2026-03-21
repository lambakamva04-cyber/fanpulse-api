import mixer
import ui
import os
import time
from config import Colors, GRID_PADS, PAD_TO_LIGHT, KNOB_CCS, FADER_CCS, MIDI, DEVICE_SETTINGS, NAVIGATION_BUTTONS

class MixerModeHandler:
    def __init__(self, device_comm):
        self.device = device_comm
        self.track_offset = 0
        self.shift_active = False
        self.pad_states = {}
        self.pad_handlers = {}
        self.knob_handlers = {}
        self.fader_handlers = {}
        self.last_sent_names = {}
        self.last_sent_volumes = {}
        self.last_volume_send_time = {}
        self.volume_throttle_delay = 0.02
        
        self.eq_fader_pickup_state = {}
        self.last_selected_track = None
        
        
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup mixer mode handlers"""
        self._setup_pad_handlers()
        self._setup_knob_handlers()
        self._setup_eq_faders()
        self._setup_navigation()

    def _setup_pad_handlers(self):
        """Setup pad handlers for mute/solo controls"""

        pad_mapping = {
            0x28: (0, 'mute'),
            0x26: (1, 'mute'),
            0x2e: (2, 'mute'),
            0x2c: (3, 'mute'),
            0x31: (4, 'mute'),
            0x37: (5, 'mute'),
            0x33: (6, 'mute'),
            0x35: (7, 'mute'),

            0x25: (0, 'shift'),
            0x24: (1, 'solo'),
            0x2a: (2, 'solo'),
            0x36: (3, 'solo'),
            0x30: (4, 'solo'),
            0x2f: (5, 'solo'),
            0x2d: (6, 'solo'),
            0x2b: (7, 'solo')
        }

        for pad, (track, action) in pad_mapping.items():
            if action == 'shift':
                self.pad_handlers[(MIDI.NOTE_ON_CH2, pad)] = self._press_shift
                self.pad_handlers[(MIDI.NOTE_OFF_CH2, pad)] = self._release_shift
            else:
                self.pad_handlers[(MIDI.NOTE_ON_CH2, pad)] = lambda t=track, a=action: self._pad_action(t, a)

    def _setup_knob_handlers(self):
        """Setup knob handlers for volume/pan control"""
        for i, cc in enumerate(KNOB_CCS):
            self.knob_handlers[(MIDI.CC, cc, MIDI.LEFT_TURN)] = lambda idx=i: self._knob_left(idx)
            self.knob_handlers[(MIDI.CC, cc, MIDI.RIGHT_TURN)] = lambda idx=i: self._knob_right(idx)

    def _setup_eq_faders(self):
        """Setup EQ fader handlers for gain control"""
        pass

    def _setup_navigation(self):
        """Setup track navigation"""  
        self.knob_handlers[NAVIGATION_BUTTONS['DOWN']] = lambda: self._navigate_left()
        self.knob_handlers[NAVIGATION_BUTTONS['UP']] = lambda: self._navigate_right()

    def _get_effective_track_count(self):
        """Get effective track count excluding FL Studio's hidden last track"""
        return max(1, mixer.trackCount() - 1)

    def handle_event(self, event_data) -> bool:
        """Handle MIDI events for mixer mode"""
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

        if event_data.status == MIDI.CC and event_data.data1 in FADER_CCS:
            fader_cc = event_data.data1
            fader_value = event_data.data2
            fader_index = FADER_CCS.index(fader_cc)
            
            self._handle_eq_fader(fader_index, fader_value)
            event_data.handled = True
            return True

        return False

    def on_enter_mode(self):
        """Initialize mixer mode"""
        self.device.clear_mode_strings()
        self._update_all_lights()
        self.last_sent_volumes.clear()
        self.last_volume_send_time.clear()
        self._update_pad_strings()
        self._update_all_knob_displays()
        
        self.eq_fader_pickup_state.clear()
        self._update_all_eq_fader_displays()

    def on_exit_mode(self):
        """Clean up when leaving mixer mode"""
        self.shift_active = False
        for i in range(16, 32):
          self.device.turn_off_light(i)
        
        for i in range(4, 4 + DEVICE_SETTINGS['EQ_FADER_COUNT']):
            self.device.send_fader_name_string(i, "")
            self.device.send_fader_value_string(i, "")
        

    def update_lights(self):
        """Update mixer mode lights"""
        self._update_mute_solo_lights()
        self._check_track_change()
        

    def _pad_action(self, track_index: int, action: str):
        """Handle pad action (mute/solo)"""
        if track_index == 0:
            actual_track = 0
        else:
            if self.track_offset == 0:
                actual_track = track_index
            else:
                actual_track = self.track_offset + (track_index - 1)

        track_count = self._get_effective_track_count()
        if actual_track >= track_count:
            return

        if action == 'mute':
            current_state = mixer.isTrackMuted(actual_track)
            mixer.muteTrack(actual_track, not current_state)
        elif action == 'solo':
            current_state = mixer.isTrackSolo(actual_track)
            mixer.soloTrack(actual_track, not current_state)

        self._update_display()

    def _press_shift(self):
        """Activate shift mode for pan control"""
        self.shift_active = True
        shift_light = PAD_TO_LIGHT[0x25]
        self.device.set_light_solid(shift_light + 16, Colors.WHITE)
        self.last_sent_volumes.clear()
        self.last_volume_send_time.clear()
        self._update_all_knob_displays()

    def _release_shift(self):
        """Deactivate shift mode"""
        self.shift_active = False
        shift_light = PAD_TO_LIGHT[0x25]
        self.device.set_light_solid(shift_light + 16, Colors.MIXER_MUTE)
        self.last_sent_volumes.clear()
        self.last_volume_send_time.clear()
        self._update_all_knob_displays()

    def _knob_left(self, knob_index: int):
        """Handle knob turn left"""
        if knob_index == 0:
            track_index = 0
        else:
            if self.track_offset == 0:
                track_index = knob_index
            else:
                track_index = self.track_offset + (knob_index - 1)

        track_count = self._get_effective_track_count()
        if track_index >= track_count:
            return

        if self.shift_active:
            current_pan = mixer.getTrackPan(track_index)
            new_pan = max(current_pan - DEVICE_SETTINGS['PAN_STEP'], -1)
            mixer.setTrackPan(track_index, new_pan)
        else:
            current_volume = mixer.getTrackVolume(track_index)
            new_volume = max(current_volume - DEVICE_SETTINGS['VOLUME_STEP'], 0)
            mixer.setTrackVolume(track_index, new_volume)

        self._update_knob_display(knob_index)
        self._update_display()

    def _knob_right(self, knob_index: int):
        """Handle knob turn right"""
        if knob_index == 0:
            track_index = 0
        else:
            if self.track_offset == 0:
                track_index = knob_index
            else:
                track_index = self.track_offset + (knob_index - 1)

        track_count = self._get_effective_track_count()
        if track_index >= track_count:
            return

        if self.shift_active:
            current_pan = mixer.getTrackPan(track_index)
            new_pan = min(current_pan + DEVICE_SETTINGS['PAN_STEP'], 1)
            mixer.setTrackPan(track_index, new_pan)
        else:
            current_volume = mixer.getTrackVolume(track_index)
            new_volume = min(current_volume + DEVICE_SETTINGS['VOLUME_STEP'], 1)
            mixer.setTrackVolume(track_index, new_volume)

        self._update_knob_display(knob_index)
        self._update_display()

    def _navigate_left(self):
        """Navigate tracks left"""
        if self.track_offset > 0:
            self.track_offset = max(0, self.track_offset - 8)
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()
            self._update_all_lights()
            self._update_pad_strings()
            self._update_all_knob_displays()
            self._update_display()

    def _navigate_right(self):
        """Navigate tracks right"""
        track_count = self._get_effective_track_count()
        
        if self.track_offset == 0:
            tracks_on_current_page = min(8, track_count)
            next_offset = 8
        else:
            tracks_on_current_page = min(7, track_count - self.track_offset)
            next_offset = self.track_offset + 7
        
        if next_offset < track_count:
            self.track_offset = next_offset
            self.last_sent_volumes.clear()
            self.last_volume_send_time.clear()
            self._update_all_lights()
            self._update_pad_strings()
            self._update_all_knob_displays()
            self._update_display()


    def _update_all_lights(self):
        """Update all mixer mode lights"""
        track_count = self._get_effective_track_count()
        
        pad_colors = {
            0: Colors.MIXER_MASTER,
            1: Colors.MIXER_MUTE, 2: Colors.MIXER_MUTE, 3: Colors.MIXER_MUTE,
            4: Colors.MIXER_MUTE, 5: Colors.MIXER_MUTE, 6: Colors.MIXER_MUTE, 7: Colors.MIXER_MUTE,
            8: Colors.MIXER_MUTE,
            9: Colors.MIXER_SOLO, 10: Colors.MIXER_SOLO, 11: Colors.MIXER_SOLO,
            12: Colors.MIXER_SOLO, 13: Colors.MIXER_SOLO, 14: Colors.MIXER_SOLO, 15: Colors.MIXER_SOLO
        }

        for pad_index, color in pad_colors.items():
            if pad_index == 0:
                track_index = 0
            elif pad_index == 8:
                track_index = -1
            else:
                if pad_index <= 7:
                    track_rel = pad_index
                else:
                    track_rel = pad_index - 8
                
                if self.track_offset == 0:
                    track_index = track_rel
                else:
                    track_index = self.track_offset + (track_rel - 1)
            
            if track_index == -1 or track_index < track_count:
                self.device.set_light_solid(pad_index + 16, color)
            else:
                self.device.turn_off_light(pad_index + 16)

        self._update_mute_solo_lights()

    def _update_mute_solo_lights(self):
        """Update mute and solo lights based on current states"""
        track_count = self._get_effective_track_count()
        
        track_mapping = {
            0: (0, 'mute', Colors.MIXER_MASTER),
            1: (1, 'mute', Colors.MIXER_MUTE),
            2: (2, 'mute', Colors.MIXER_MUTE),
            3: (3, 'mute', Colors.MIXER_MUTE),
            4: (4, 'mute', Colors.MIXER_MUTE),
            5: (5, 'mute', Colors.MIXER_MUTE),
            6: (6, 'mute', Colors.MIXER_MUTE),
            7: (7, 'mute', Colors.MIXER_MUTE),

            9: (1, 'solo', Colors.MIXER_SOLO),
            10: (2, 'solo', Colors.MIXER_SOLO),
            11: (3, 'solo', Colors.MIXER_SOLO),
            12: (4, 'solo', Colors.MIXER_SOLO),
            13: (5, 'solo', Colors.MIXER_SOLO),
            14: (6, 'solo', Colors.MIXER_SOLO),
            15: (7, 'solo', Colors.MIXER_SOLO)
        }

        for pad_index, (track_rel, action, default_color) in track_mapping.items():
            if track_rel == 0:
                track_index = 0
            else:
                if self.track_offset == 0:
                    track_index = track_rel
                else:
                    track_index = self.track_offset + (track_rel - 1)

            if track_index >= track_count:
                if self.pad_states.get(pad_index) is not None:
                    self.device.turn_off_light(pad_index + 16)
                    self.pad_states[pad_index] = None
                continue

            if action == 'mute':
                is_active = mixer.isTrackMuted(track_index)
            else:
                is_active = mixer.isTrackSolo(track_index)

            color = Colors.WHITE if is_active else default_color

            if self.pad_states.get(pad_index) != color:
                self.device.set_light_solid(pad_index + 16, color)
                self.pad_states[pad_index] = color

    def _update_pad_strings(self):
        """Update pad strings with channel names for mixer mode"""
        for pad_index in range(8):
            if pad_index == 0:
                track_index = 0
                channel_name = mixer.getTrackName(track_index)
                self.device.send_pad_string(pad_index + 16, f"M-{channel_name}")
            else:
                if self.track_offset == 0:
                    track_index = pad_index
                else:
                    track_index = self.track_offset + (pad_index - 1)
                
                channel_name = mixer.getTrackName(track_index)
                self.device.send_pad_string(pad_index + 16, f"M-{channel_name}")
        
        for pad_index in range(8, 16):
            if pad_index == 8:
                self.device.send_pad_string(pad_index + 16, "Hold - Pan")
            else:
                track_rel = pad_index - 8
                if self.track_offset == 0:
                    track_index = track_rel
                else:
                    track_index = self.track_offset + (track_rel - 1)
                
                channel_name = mixer.getTrackName(track_index)
                self.device.send_pad_string(pad_index + 16, f"S-{channel_name}")


    def _update_knob_display(self, knob_index: int):
        """Update the display for a single knob."""
        if knob_index == 0:
            track_index = 0
        else:
            if self.track_offset == 0:
                track_index = knob_index
            else:
                track_index = self.track_offset + (knob_index - 1)
            
        track_count = self._get_effective_track_count()

        if track_index >= track_count or track_index > DEVICE_SETTINGS['MAX_TRACKS']:
            self.device.send_knob_name_string(knob_index + 8, "")
            self.device.send_knob_volume_string(knob_index + 8, "")
            self.last_sent_names[knob_index] = ""
            return

        if self.track_offset == 0:
            max_knobs_for_page = min(8, track_count)
        else:
            max_knobs_for_page = min(7, track_count - self.track_offset)

        if knob_index >= max_knobs_for_page:
            self.device.send_knob_name_string(knob_index + 8, "")
            self.device.send_knob_volume_string(knob_index + 8, "")
            self.last_sent_names[knob_index] = ""
            return

        track_name = mixer.getTrackName(track_index)
        if self.last_sent_names.get(knob_index) != track_name:
            self.device.send_knob_name_string(knob_index + 8, track_name)
            self.last_sent_names[knob_index] = track_name

        if self.shift_active:
            pan = mixer.getTrackPan(track_index)

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
            
            self.device.send_knob_volume_with_value(knob_index + 8, pan_byte, pan_str)
        else:
            volume_percent = mixer.getTrackVolume(track_index)
            volume_db = mixer.getTrackVolume(track_index, 1)
            
            volume_0_125 = round(volume_percent * 125)
            
            if volume_db <= -100:
                volume_db_str = "-INF db"
            else:
                volume_db_str = f"{volume_db:.1f}db"
            
            volume_key = f"{volume_0_125}:{volume_db_str}"
            current_time = time.time()
            
            should_send = False
            last_send_time = self.last_volume_send_time.get(knob_index, 0)
            
            if self.last_sent_volumes.get(knob_index) != volume_key:
                if current_time - last_send_time >= self.volume_throttle_delay:
                    should_send = True
            
            if should_send:
                self.device.send_knob_volume_with_value(knob_index + 8, volume_0_125, volume_db_str)
                self.last_sent_volumes[knob_index] = volume_key
                self.last_volume_send_time[knob_index] = current_time

    def _update_all_knob_displays(self):
        """Update all knob displays."""
        for i in range(DEVICE_SETTINGS['KNOB_COUNT']):
            self._update_knob_display(i)

    def _update_display(self):
        """Update FL Studio mixer display and log track info."""
        track_count = self._get_effective_track_count()
        
        start_track = self.track_offset
        
        if self.track_offset == 0:
            tracks_to_show = min(8, track_count)
            end_track = tracks_to_show - 1
        else:
            remaining_tracks = track_count - self.track_offset
            tracks_to_show = min(7, remaining_tracks)
            end_track = start_track + tracks_to_show - 1
        
        ui.miDisplayRect(start_track, end_track, 1000)


    def _handle_eq_fader(self, fader_index: int, fader_value: int):
        """Handle EQ fader control for gain adjustment with pickup functionality"""
        
        try:
            band_count = mixer.getEqBandCount()
            
            if band_count == 0 or fader_index >= band_count:
                return

            selected_track = mixer.trackNumber()
            
            try:
                current_fl_gain_normalized = mixer.getEqGain(selected_track, fader_index)
                current_fl_fader_value = int(current_fl_gain_normalized * 127)
            except:
                self.eq_fader_pickup_state[fader_index] = True
                current_fl_fader_value = fader_value

            pickup_threshold = 3
            
            if not self.eq_fader_pickup_state.get(fader_index, False):
                if abs(fader_value - current_fl_fader_value) <= pickup_threshold:
                    self.eq_fader_pickup_state[fader_index] = True
                else:
                    fader_eq_gain_db = ((fader_value - 64) / 63.0) * 18.0
                    self._update_eq_fader_display_with_pickup_indicator(fader_index, fader_eq_gain_db, False)
                    return

            eq_gain_normalized = fader_value / 127.0
            eq_gain_db = ((fader_value - 64) / 63.0) * 18.0
            
            try:
                mixer.setEqGain(selected_track, fader_index, eq_gain_normalized)
            except:
                try:
                    mixer.setEqGain(fader_index, eq_gain_normalized, selected_track)
                except:
                    return
            
            self._update_eq_fader_display(fader_index, eq_gain_db)
            
        except Exception as e:
            pass

    def _update_eq_fader_display(self, fader_index: int, eq_gain_db: float):
        """Update fader display with EQ information"""
        eq_bands = DEVICE_SETTINGS['EQ_BANDS']
        band_name = eq_bands[fader_index] if fader_index < len(eq_bands) else f"Band {fader_index + 1}"
        
        fader_name = band_name
        
        if eq_gain_db >= 0:
            gain_str = f"+{eq_gain_db:.1f}dB"
        else:
            gain_str = f"{eq_gain_db:.1f}dB"
        
        physical_fader_index = fader_index + 4
        self.device.send_fader_name_string(physical_fader_index, fader_name)
        self.device.send_fader_value_string(physical_fader_index, gain_str)

    def _update_eq_fader_display_with_pickup_indicator(self, fader_index: int, fader_eq_gain_db: float, is_picked_up: bool):
        """Update fader display with pickup status indicator"""
        eq_bands = DEVICE_SETTINGS['EQ_BANDS']
        band_name = eq_bands[fader_index] if fader_index < len(eq_bands) else f"Band {fader_index + 1}"
        
        if is_picked_up:
            fader_name = band_name
            if fader_eq_gain_db >= 0:
                gain_str = f"+{fader_eq_gain_db:.1f}dB"
            else:
                gain_str = f"{fader_eq_gain_db:.1f}dB"
        else:
            fader_name = band_name
            gain_str = "Pick up"
        
        physical_fader_index = fader_index + 4
        self.device.send_fader_name_string(physical_fader_index, fader_name)
        self.device.send_fader_value_string(physical_fader_index, gain_str)

    def _update_all_eq_fader_displays(self):
        """Initialize all EQ fader displays with current values"""
        try:
            band_count = mixer.getEqBandCount()
            
            for fader_index in range(DEVICE_SETTINGS['EQ_FADER_COUNT']):
                if band_count == 0 or fader_index >= band_count:
                    physical_fader_index = fader_index + 4
                    self.device.send_fader_name_string(physical_fader_index, "No EQ")
                    self.device.send_fader_value_string(physical_fader_index, "")
                else:
                    try:
                        selected_track = mixer.trackNumber()
                        current_gain_db = mixer.getEqGain(selected_track, fader_index, 1)
                        self._update_eq_fader_display(fader_index, current_gain_db)
                    except Exception as e:
                        eq_bands = DEVICE_SETTINGS['EQ_BANDS']
                        band_name = eq_bands[fader_index] if fader_index < len(eq_bands) else f"Band {fader_index + 1}"
                        physical_fader_index = fader_index + 4
                        self.device.send_fader_name_string(physical_fader_index, band_name)
                        self.device.send_fader_value_string(physical_fader_index, "0.0dB")
                        
        except Exception as e:
            for fader_index in range(DEVICE_SETTINGS['EQ_FADER_COUNT']):
                physical_fader_index = fader_index + 4
                self.device.send_fader_name_string(physical_fader_index, "")
                self.device.send_fader_value_string(physical_fader_index, "")

    def _check_track_change(self):
        """Check if the selected track has changed and reset pickup state if needed"""
        try:
            current_selected_track = mixer.trackNumber()
            if self.last_selected_track != current_selected_track:
                self.eq_fader_pickup_state.clear()
                self.last_selected_track = current_selected_track
                self._update_all_eq_fader_displays()
        except:
            pass