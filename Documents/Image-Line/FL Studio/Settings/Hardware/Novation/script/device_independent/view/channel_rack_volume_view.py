from script.actions import ChannelVolumeChangedAction
from script.colours import Colours
from script.constants import ChannelNavigationMode, ChannelNavigationSteps, ControlChangeType, Pots
from script.device_independent.util_view.view import View
from script.device_independent.view.control_change_rate_limiter import ControlChangeRateLimiter
from script.fl_constants import RefreshFlags
from util.math_helpers import clamp


class ChannelRackVolumeView(View):
    channels_per_bank = Pots.Num.value

    def __init__(self, action_dispatcher, fl, model, *, control_to_index, product_defs=None, led_writer=None):
        super().__init__(action_dispatcher)
        self.fl = fl
        self.model = model
        self.control_to_index = control_to_index
        self.reset_pickup_on_first_movement = False
        self.control_change_rate_limiter = ControlChangeRateLimiter(action_dispatcher)
        self.product_defs = product_defs
        self.led_writer = led_writer

    def _on_show(self):
        self._update_leds()
        self.reset_pickup_on_first_movement = True
        self.control_change_rate_limiter.start()

    def _on_hide(self):
        self.control_change_rate_limiter.stop()

    def handle_ChannelBankChangedAction(self, action):
        self._update_leds()
        self.control_change_rate_limiter.reset()
        self.reset_pickup_on_first_movement = True

    def handle_OnRefreshAction(self, action):
        if action.flags & RefreshFlags.LedUpdate.value:
            self._update_leds()

    def handle_ChannelSelectAction(self, action):
        self.control_change_rate_limiter.reset()
        if self.model.channel_rack.navigation_mode == ChannelNavigationMode.Single.value:
            self._reset_pickup_for_current_channel_bank()

    def handle_ControlChangedAction(self, action):
        index = self.control_to_index.get(action.control)
        if index is None:
            return

        navigation_mode = self.model.channel_rack.navigation_mode
        if navigation_mode is None:
            return

        if navigation_mode == ChannelNavigationMode.Bank.value:
            channel_offset = self.model.channel_rack.active_bank * ChannelNavigationSteps.Bank.value
        elif navigation_mode == ChannelNavigationMode.Single.value:
            channel_offset = self.fl.selected_channel()

        channel = channel_offset + index
        if channel >= self.fl.channel_count():
            return

        is_absolute_control = action.control_change_type == ControlChangeType.Absolute.value
        if is_absolute_control:
            volume = action.value
            if self.reset_pickup_on_first_movement:
                self.reset_pickup_on_first_movement = False
                self._reset_pickup_for_current_channel_bank()
        else:
            volume = clamp(self.fl.get_channel_volume(channel) + action.value, 0, 1)

        if self.control_change_rate_limiter.forward_control_change_event(channel, volume):
            self.fl.set_channel_volume(channel, volume)
            self.action_dispatcher.dispatch(ChannelVolumeChangedAction(channel=channel, control=action.control))

    def _reset_pickup_for_current_channel_bank(self):
        start_channel = self.model.channel_rack.active_bank * self.channels_per_bank
        for channel in range(start_channel, start_channel + self.channels_per_bank):
            if channel >= self.fl.channel_count():
                break
            self.fl.reset_channel_volume_pickup(channel)

    def _update_leds(self):
        if self.led_writer is None or self.product_defs is None:
            return

        encoder_first_index = self.product_defs.Constants.VolumeControlFirstIndex.value
        encoder_cc_offset = encoder_first_index + self.product_defs.Constants.EncoderCcOffset.value
        channel_offset = self.model.channel_rack.active_bank * ChannelNavigationSteps.Bank.value
        channel_count = self.fl.channel_count()
        for index in range(self.channels_per_bank):
            channel = channel_offset + index
            encoder = self.control_to_index.get(index + encoder_first_index) + encoder_cc_offset
            colour = Colours.channel_rack_volume if channel < channel_count else Colours.off
            self.led_writer.set_encoder_led_colour(
                encoder, colour, target=self.product_defs.Constants.LightingTargetCC.value
            )
