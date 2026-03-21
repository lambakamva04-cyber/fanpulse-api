from script.device_dependent.LaunchControl3.daw_mixer_button_layout_manager import DawMixerButtonLayoutManager
from script.device_dependent.LaunchControl3.daw_mixer_encoder_layout_manager import DawMixerEncoderLayoutManager
from script.device_independent.view import (
    MixerBankButtonView,
    MixerBankHighlightView,
    MixerBankScreenView,
    MixerTrackSelectedScreenView,
    MixerTrackSelectView,
    MixerVolumePreviewView,
    MixerVolumeScreenView,
    MixerVolumeView,
)


class DawMixerDeviceLayoutManager:
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
        self.fl = fl
        self.model = model
        self.fl_window_manager = fl_window_manager
        self.product_defs = product_defs
        self.led_writer = led_writer
        self.device_manager = device_manager

        self.mixer_track_select_view = MixerTrackSelectView(action_dispatcher, product_defs, model, led_writer, fl)
        self.mixer_bank_view = MixerBankButtonView(action_dispatcher, led_writer, fl, product_defs, model)
        self.mixer_bank_highlight_view = MixerBankHighlightView(action_dispatcher, fl, model)
        self.mixer_bank_screen_view = MixerBankScreenView(action_dispatcher, screen_writer, model)
        self.mixer_track_selected_screen_view = MixerTrackSelectedScreenView(
            action_dispatcher, screen_writer, fl, show_index_in_primary_text=True
        )

        self.mixer_volume_view = MixerVolumeView(
            action_dispatcher,
            fl,
            model,
            product_defs=product_defs,
            led_writer=led_writer,
            control_to_index=product_defs.EncoderRow2ToIndex,
        )
        self.mixer_volume_screen_view = MixerVolumeScreenView(action_dispatcher, screen_writer, fl)
        self.mixer_volume_preview_view = MixerVolumePreviewView(
            action_dispatcher, product_defs, model, control_offset=8
        )

        self.encoder_page_layout_manager = DawMixerEncoderLayoutManager(
            action_dispatcher,
            fl,
            model,
            product_defs,
            screen_writer,
            led_writer,
        )

        self.button_mode_layout_manager = DawMixerButtonLayoutManager(
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
            self.mixer_track_select_view,
            self.mixer_bank_view,
            self.mixer_bank_highlight_view,
            self.mixer_bank_screen_view,
            self.mixer_track_selected_screen_view,
            self.mixer_volume_view,
            self.mixer_volume_screen_view,
            self.mixer_volume_preview_view,
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
        self.fl_window_manager.focus_mixer_window()

    def handle_ButtonPressedAction(self, action):
        if action.button == self.product_defs.FunctionToButton.get("ShiftModifier"):
            self.focus_windows()
