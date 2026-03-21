import transport
import general
import midi
import ui
from config import Colors


class TransportController:
    def __init__(self, device_comm):
        self.device = device_comm
        self.play_state = False
        self.record_state = False
        self.metronome_state = False

        self.window_states = {
            'playlist': False,
            'channel_rack': False,
            'mixer': False
        }

        self.hold_states = {
            'rewind': False,
            'fast_forward': False
        }

    def play(self):
        """Toggle play/stop"""
        if transport.isPlaying():
            transport.stop()
        else:
            transport.start()
        return True

    def record(self):
        """Start recording"""
        transport.globalTransport(12, 1, midi.PME_System, midi.GT_Global)
        return True

    def view_channel_rack(self):
        """Toggle Channel Rack window (pad 8)"""
        is_visible = ui.getVisible(1)

        if is_visible:
            ui.hideWindow(1)
            self.window_states['channel_rack'] = False
            self.device.set_light_solid(8, Colors.GLOBE_TRANSPORT)
            ui.setHintMsg('Channel Rack Closed')
        else:
            ui.showWindow(1)
            self.window_states['channel_rack'] = True
            self.device.set_light_solid(8, Colors.WHITE)
            ui.setHintMsg('Channel Rack Opened')

        return True

    def view_playlist(self):
        """Toggle Playlist window (pad 9)"""
        is_visible = ui.getVisible(0)
        if is_visible:
            ui.hideWindow(0)
            self.window_states['playlist'] = False
            self.device.set_light_solid(9, Colors.GLOBE_TRANSPORT)
            ui.setHintMsg('Playlist Closed')
        else:
            ui.showWindow(0)
            self.window_states['playlist'] = True
            self.device.set_light_solid(9, Colors.WHITE)
            ui.setHintMsg('Playlist Opened')

        return True

    def view_mixer(self):
        """Toggle Mixer window (pad 10)"""
        is_visible = ui.getVisible(2)

        if is_visible:
            ui.hideWindow(2)
            self.window_states['mixer'] = False
            self.device.set_light_solid(10, Colors.GLOBE_TRANSPORT)
            ui.setHintMsg('Mixer Closed')
        else:
            ui.showWindow(2)
            self.window_states['mixer'] = True
            self.device.set_light_solid(10, Colors.WHITE)
            ui.setHintMsg('Mixer Opened')

        return True

    def rewind_press(self):
        """Start rewind (pad 11) - hold to continue"""
        if not self.hold_states['rewind']:
            self.hold_states['rewind'] = True
            transport.globalTransport(13, 2, midi.PME_System, midi.GT_All)
            self.device.set_light_solid(11, Colors.WHITE)
            ui.setHintMsg('Rewinding...')
        return True

    def rewind_release(self):
        """Stop rewind when pad is released"""
        if self.hold_states['rewind']:
            self.hold_states['rewind'] = False
            transport.globalTransport(13, 0, midi.PME_System, midi.GT_All)
            self.device.set_light_solid(11, Colors.GLOBE_TRANSPORT)
        return True

    def fast_forward_press(self):
        """Start fast forward (pad 12) - hold to continue"""
        if not self.hold_states['fast_forward']:
            self.hold_states['fast_forward'] = True
            transport.globalTransport(14, 2, midi.PME_System, midi.GT_All)
            self.device.set_light_solid(12, Colors.WHITE)
            ui.setHintMsg('Fast Forwarding...')
        return True

    def fast_forward_release(self):
        """Stop fast forward when pad is released"""
        if self.hold_states['fast_forward']:
            self.hold_states['fast_forward'] = False
            transport.globalTransport(14, 0, midi.PME_System, midi.GT_All)
            self.device.set_light_solid(12, Colors.GLOBE_TRANSPORT)
        return True

    def metronome(self):
        """Toggle metronome (pad 13)"""
        transport.globalTransport(110, 1, midi.PME_System, midi.GT_Global)
        return True

    def metronome_release(self):
        """Handle metronome pad release (pad 13)"""
        is_metronome = ui.isMetronomeEnabled()
        color = Colors.WHITE if is_metronome else Colors.GLOBE_TRANSPORT
        self.device.set_light_solid(13, color)
        return True

    def loop(self):
        """Toggle loop mode (pad 14)"""
        transport.globalTransport(15, 1, midi.PME_System, midi.GT_Global)
        self.device.set_light_solid(14, Colors.WHITE)
        return True

    def loop_release(self):
        """Handle loop pad release (pad 14)"""
        self.device.set_light_solid(14, Colors.GLOBE_TRANSPORT)
        return True

    def undo(self):
        """Undo last action (pad 15)"""
        general.undo()
        self.device.set_light_solid(15, Colors.WHITE)
        ui.setHintMsg('Undo')
        return True

    def undo_release(self):
        """Handle undo pad release (pad 15)"""
        self.device.set_light_solid(15, Colors.GLOBE_TRANSPORT)
        return True

    def update_lights(self):
        """Update transport button lights based on current state"""
        is_playing = transport.isPlaying()
        if is_playing != self.play_state:
            if is_playing:
                self.device.set_light_flashing(32, 0x01, Colors.OFF)
            else:
                self.device.set_light_solid(32, 0x02)
            self.play_state = is_playing

        is_recording = transport.isRecording()
        if is_recording != self.record_state:
            if is_recording:
                self.device.set_light_solid(33, 0x01)
            else:
                self.device.set_light_solid(33, Colors.OFF)
            self.record_state = is_recording

        is_metronome = ui.isMetronomeEnabled()
        if is_metronome != self.metronome_state:
            color = Colors.WHITE if is_metronome else Colors.GLOBE_TRANSPORT
            self.device.set_light_solid(13, color)
            self.metronome_state = is_metronome

        self._update_window_lights()

    def _update_window_lights(self):
        """Update window button lights based on actual window visibility"""
        channel_rack_visible = ui.getVisible(1)
        if channel_rack_visible != self.window_states['channel_rack']:
            color = Colors.WHITE if channel_rack_visible else Colors.GLOBE_TRANSPORT
            self.device.set_light_solid(8, color)
            self.window_states['channel_rack'] = channel_rack_visible

        playlist_visible = ui.getVisible(0)
        if playlist_visible != self.window_states['playlist']:
            color = Colors.WHITE if playlist_visible else Colors.GLOBE_TRANSPORT
            self.device.set_light_solid(9, color)
            self.window_states['playlist'] = playlist_visible

        mixer_visible = ui.getVisible(2)
        if mixer_visible != self.window_states['mixer']:
            color = Colors.WHITE if mixer_visible else Colors.GLOBE_TRANSPORT
            self.device.set_light_solid(10, color)
            self.window_states['mixer'] = mixer_visible