from script.device_independent.layout_manager.mode_cycling_layout_manager import ModeCyclingLayoutManager
from script.device_independent.util_view.shift_toggle_view import ShiftToggleView
from script.device_independent.view import (
    MixerTrackMuteToggleView,
    MixerTrackRecordArmToggleView,
    MixerTrackSelectInBankView,
    MixerTrackSoloToggleView,
)


class DawMixerButtonLayoutManager(ModeCyclingLayoutManager):
    def __init__(
        self,
        action_dispatcher,
        fl,
        model,
        product_defs,
        screen_writer,
        button_led_writer,
    ):
        self.model = model
        self.action_dispatcher = action_dispatcher
        self.product_defs = product_defs

        self.next_button_mode_function = "SwitchToNextButtonMode"

        super().__init__(
            screen_writer,
            layouts=[
                ModeCyclingLayoutManager.Layout(
                    layout_id=product_defs.DawMixerButtonMode.Mute,
                    notification_primary="Mixer",
                    notification_secondary="Mute / solo",
                    views=[
                        ShiftToggleView(
                            action_dispatcher,
                            product_defs,
                            default_view=MixerTrackMuteToggleView(
                                action_dispatcher,
                                product_defs,
                                fl,
                                model,
                                button_led_writer,
                                next_button_mode_function=self.next_button_mode_function,
                            ),
                            shift_view=MixerTrackSoloToggleView(
                                action_dispatcher,
                                product_defs,
                                fl,
                                model,
                                button_led_writer,
                                next_button_mode_function=self.next_button_mode_function,
                                use_mute_state_for_leds=True,
                            ),
                        )
                    ],
                ),
                ModeCyclingLayoutManager.Layout(
                    layout_id=product_defs.DawMixerButtonMode.Select,
                    notification_primary="Mixer",
                    notification_secondary="Select",
                    views=[
                        MixerTrackSelectInBankView(
                            action_dispatcher,
                            product_defs,
                            fl,
                            model,
                            button_led_writer,
                            next_button_mode_function=self.next_button_mode_function,
                        )
                    ],
                ),
                ModeCyclingLayoutManager.Layout(
                    layout_id=product_defs.DawMixerButtonMode.Arm,
                    notification_primary="Mixer",
                    notification_secondary="Arm",
                    views=[
                        MixerTrackRecordArmToggleView(
                            action_dispatcher,
                            product_defs,
                            fl,
                            model,
                            button_led_writer,
                            next_button_mode_function=self.next_button_mode_function,
                        )
                    ],
                ),
            ],
        )

    def show(self):
        self.action_dispatcher.subscribe(self)
        if self.model.daw_mixer_button_mode is not None:
            self.set_layout(self.model.daw_mixer_button_mode)
        super().show()

    def hide(self):
        self.action_dispatcher.unsubscribe(self)
        super().hide()

    def on_layout_selected(self, layout_id):
        self.model.daw_mixer_button_mode = layout_id

    def handle_ButtonPressedAction(self, action):
        if action.button == self.product_defs.FunctionToButton.get(self.next_button_mode_function):
            self.activate_next_layout()
