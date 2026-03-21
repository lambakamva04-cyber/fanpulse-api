from script.constants import ChannelNavigationMode
from script.device_dependent.LaunchControl3.daw_control_button_layout_manager import DawControlButtonLayoutManager
from script.device_dependent.LaunchControl3.daw_control_encoder_layout_manager import DawControlEncoderLayoutManager
from script.device_independent.util_view.shift_toggle_view import ShiftToggleView
from script.device_independent.view import (
    ChannelBankNamesHighlightView,
    ChannelBankSelectedScreenView,
    ChannelBankView,
    ChannelRackVolumePreviewView,
    ChannelRackVolumeScreenView,
    ChannelRackVolumeView,
    ChannelSelectedScreenView,
    ChannelSelectView,
)


class DawControlDeviceLayoutManager:
    def __init__(
        self,
        action_dispatcher,
        command_dispatcher,
        fl,
        model,
        fl_window_manager,
        product_defs,
        led_writer,
        screen_writer,
        device_manager,
    ):
        self.action_dispatcher = action_dispatcher
        self.fl_window_manager = fl_window_manager
        self.command_dispatcher = command_dispatcher
        self.product_defs = product_defs
        self.device_manager = device_manager
        self.model = model
        model.channel_rack.navigation_mode = ChannelNavigationMode.Bank

        self.channel_bank_names_highlight_view = ChannelBankNamesHighlightView(
            action_dispatcher,
            fl,
            model,
            num_channels=product_defs.Constants.ChannelsPerBank.value,
        )

        self.channel_select_or_bank_view = ShiftToggleView(
            action_dispatcher,
            product_defs,
            default_view=ChannelBankView(
                action_dispatcher,
                led_writer,
                fl,
                product_defs,
                model,
                decrement_button="SelectPreviousChannelBank",
                increment_button="SelectNextChannelBank",
            ),
            shift_view=ChannelSelectView(action_dispatcher, led_writer, fl, product_defs),
        )

        self.channel_bank_selected_screen_view = ChannelBankSelectedScreenView(
            action_dispatcher, screen_writer, fl, model
        )
        self.channel_selected_screen_view = ChannelSelectedScreenView(action_dispatcher, screen_writer, fl)
        self.channel_rack_volume_view = ChannelRackVolumeView(
            action_dispatcher,
            fl,
            model,
            product_defs=product_defs,
            led_writer=led_writer,
            control_to_index=product_defs.EncoderRow2ToIndex,
        )
        self.channel_rack_volume_screen_view = ChannelRackVolumeScreenView(action_dispatcher, screen_writer, fl)
        self.channel_rack_volume_preview_view = ChannelRackVolumePreviewView(
            action_dispatcher, product_defs, model, control_to_index=product_defs.EncoderRow2ToIndex
        )

        self.encoder_page_layout_manager = DawControlEncoderLayoutManager(
            action_dispatcher,
            fl,
            model,
            product_defs,
            screen_writer,
            led_writer,
        )

        self.button_mode_layout_manager = DawControlButtonLayoutManager(
            action_dispatcher,
            fl,
            model,
            product_defs,
            screen_writer,
            led_writer,
        )

    @property
    def views(self):
        return [
            self.channel_bank_names_highlight_view,
            self.channel_select_or_bank_view,
            self.channel_selected_screen_view,
            self.channel_bank_selected_screen_view,
            self.channel_rack_volume_view,
            self.channel_rack_volume_screen_view,
            self.channel_rack_volume_preview_view,
            self.encoder_page_layout_manager,
            self.button_mode_layout_manager,
        ]

    def show(self):
        self.device_manager.enable_encoder_relative_mode()
        self.action_dispatcher.subscribe(self)
        for view in self.views:
            view.show()

    def hide(self):
        self.action_dispatcher.unsubscribe(self)
        for view in self.views:
            view.hide()

    def focus_windows(self):
        self.fl_window_manager.hide_last_focused_plugin_window()
        self.fl_window_manager.focus_channel_window()

    def handle_ButtonPressedAction(self, action):
        if action.button == self.product_defs.FunctionToButton.get("ShiftModifier"):
            self.focus_windows()
