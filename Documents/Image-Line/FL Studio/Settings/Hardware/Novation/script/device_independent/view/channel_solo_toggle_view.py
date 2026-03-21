from script.actions import ChannelSoloStateChangedAction
from script.colour_utils import clamp_brightness, scale_colour
from script.colours import Colours
from script.constants import ChannelNavigationMode, ChannelNavigationSteps, LedLightingType
from script.device_independent.util_view import View
from script.fl_constants import RefreshFlags


class ChannelSoloToggleView(View):
    button_functions = [
        "ToggleSoloChannel_1",
        "ToggleSoloChannel_2",
        "ToggleSoloChannel_3",
        "ToggleSoloChannel_4",
        "ToggleSoloChannel_5",
        "ToggleSoloChannel_6",
        "ToggleSoloChannel_7",
        "ToggleSoloChannel_8",
    ]

    channel_offset_for_button = [0, 1, 2, 3, 4, 5, 6, 7]

    def __init__(
        self,
        action_dispatcher,
        product_defs,
        fl,
        model,
        button_led_writer,
        *,
        next_button_mode_function,
        use_mute_state_for_leds=False,
    ):
        super().__init__(action_dispatcher)
        self.action_dispatcher = action_dispatcher
        self.product_defs = product_defs
        self.button_led_writer = button_led_writer
        self.fl = fl
        self.model = model
        self.next_button_mode_function = next_button_mode_function
        self.use_mute_state_for_leds = use_mute_state_for_leds
        self.bright_colour_min_brightness = 100
        self.dim_colour_scale_factor = 0.25

    def _on_show(self):
        self.update_leds()

    def _on_hide(self):
        self.turn_off_leds()

    @property
    def channel_offset_for_bank(self):
        navigation_mode = self.model.channel_rack.navigation_mode
        if navigation_mode == ChannelNavigationMode.Single.value:
            return self.fl.selected_channel()
        return self.model.channel_rack.active_bank * ChannelNavigationSteps.Bank.value

    @property
    def channels_in_bank(self):
        channel_offset_for_bank = self.channel_offset_for_bank
        return [
            channel_offset_for_bank + channel
            for channel in self.channel_offset_for_button
            if channel_offset_for_bank + channel < self.fl.channel_count()
        ]

    @property
    def button_to_channel_index(self):
        return {
            self.product_defs.FunctionToButton.get(function): channel
            for function, channel in zip(self.button_functions, self.channels_in_bank)
        }

    def handle_ButtonPressedAction(self, action):
        if action.button in self.button_to_channel_index:
            channel = self.button_to_channel_index[action.button]
            self._toggle_solo(channel)

    def handle_ChannelBankChangedAction(self, action):
        self.update_leds()

    def handle_OnRefreshAction(self, action):
        if action.flags & RefreshFlags.LedUpdate.value:
            self.update_leds()

    def get_colour_for_channel(self, channel):
        if self.use_mute_state_for_leds:
            if self.fl.is_channel_mute_enabled(group_channel=channel):
                return self.dim_channel_colour(self.fl.get_channel_colour(group_channel=channel))
            return self.bright_channel_colour(self.fl.get_channel_colour(group_channel=channel))

        if self.fl.is_channel_solo_enabled(group_channel=channel):
            return self.bright_channel_colour(self.fl.get_channel_colour(group_channel=channel))
        return self.dim_channel_colour(self.fl.get_channel_colour(group_channel=channel))

    def update_leds(self):
        self.turn_off_leds()
        solo_button = self.product_defs.FunctionToButton.get(self.next_button_mode_function)
        self.button_led_writer.set_button_colour(
            solo_button, Colours.mixer_track_mute.value, lighting_type=LedLightingType.RGB
        )
        for button, channel in self.button_to_channel_index.items():
            colour = self.get_colour_for_channel(channel)
            self.button_led_writer.set_button_colour(button, colour, lighting_type=LedLightingType.RGB)

    def turn_off_leds(self):
        solo_button = self.product_defs.FunctionToButton.get(self.next_button_mode_function)
        self.button_led_writer.set_button_colour(solo_button, Colours.off)
        for function in self.button_functions:
            button = self.product_defs.FunctionToButton.get(function)
            self.button_led_writer.set_button_colour(button, Colours.off)

    def dim_channel_colour(self, base_colour):
        return scale_colour(base_colour, self.dim_colour_scale_factor)

    def bright_channel_colour(self, base_colour):
        return clamp_brightness(base_colour, minimum=self.bright_colour_min_brightness)

    def _toggle_solo(self, channel):
        enabled = not self.fl.is_channel_solo_enabled(group_channel=channel)
        self.fl.toggle_channel_solo(group_channel=channel)
        self.action_dispatcher.dispatch(ChannelSoloStateChangedAction(channel=channel, enabled=enabled))
