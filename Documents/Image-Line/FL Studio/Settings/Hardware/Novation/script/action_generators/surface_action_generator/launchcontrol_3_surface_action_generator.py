from script.action_generators.surface_action_generator.keyboard_controller_common import (
    KeyboardControllerCommonButtonActionGenerator,
    KeyboardControllerCommonDeviceLayoutActionGenerator,
    KeyboardControllerCommonEncoderActionGenerator,
)


class LaunchControl3SurfaceActionGenerator:
    def __init__(self, product_defs):
        self.product_defs = product_defs
        self.event_type_to_button = {
            self.product_defs.SurfaceEvent.ButtonTrackLeft.value: self.product_defs.Button.TrackLeft,
            self.product_defs.SurfaceEvent.ButtonTrackRight.value: self.product_defs.Button.TrackRight,
            self.product_defs.SurfaceEvent.ButtonEncoderPageUp.value: self.product_defs.Button.EncoderPageUp,
            self.product_defs.SurfaceEvent.ButtonEncoderPageDown.value: self.product_defs.Button.EncoderPageDown,
            self.product_defs.SurfaceEvent.ButtonFunction.value: self.product_defs.Button.Function,
            self.product_defs.SurfaceEvent.Button_1.value: self.product_defs.Button.Button_1,
            self.product_defs.SurfaceEvent.Button_2.value: self.product_defs.Button.Button_2,
            self.product_defs.SurfaceEvent.Button_3.value: self.product_defs.Button.Button_3,
            self.product_defs.SurfaceEvent.Button_4.value: self.product_defs.Button.Button_4,
            self.product_defs.SurfaceEvent.Button_5.value: self.product_defs.Button.Button_5,
            self.product_defs.SurfaceEvent.Button_6.value: self.product_defs.Button.Button_6,
            self.product_defs.SurfaceEvent.Button_7.value: self.product_defs.Button.Button_7,
            self.product_defs.SurfaceEvent.Button_8.value: self.product_defs.Button.Button_8,
        }

        self.modified_event_type_to_button = {
            self.product_defs.SurfaceEvent.ButtonTrackLeft.value: self.product_defs.Button.TrackLeftShift,
            self.product_defs.SurfaceEvent.ButtonTrackRight.value: self.product_defs.Button.TrackRightShift,
            self.product_defs.SurfaceEvent.Button_1.value: self.product_defs.Button.ShiftButton_1,
            self.product_defs.SurfaceEvent.Button_2.value: self.product_defs.Button.ShiftButton_2,
            self.product_defs.SurfaceEvent.Button_3.value: self.product_defs.Button.ShiftButton_3,
            self.product_defs.SurfaceEvent.Button_4.value: self.product_defs.Button.ShiftButton_4,
            self.product_defs.SurfaceEvent.Button_5.value: self.product_defs.Button.ShiftButton_5,
            self.product_defs.SurfaceEvent.Button_6.value: self.product_defs.Button.ShiftButton_6,
            self.product_defs.SurfaceEvent.Button_7.value: self.product_defs.Button.ShiftButton_7,
            self.product_defs.SurfaceEvent.Button_8.value: self.product_defs.Button.ShiftButton_8,
        }

        self.common_action_generators = [
            KeyboardControllerCommonButtonActionGenerator(
                self._get_button_for_event,
                is_modifier_event=lambda event: event == product_defs.SurfaceEvent.ButtonShift.value,
            ),
            KeyboardControllerCommonEncoderActionGenerator(product_defs),
            KeyboardControllerCommonDeviceLayoutActionGenerator(product_defs),
        ]

    def handle_midi_event(self, fl_event):
        for action_generator in self.common_action_generators:
            if actions := action_generator.handle_midi_event(fl_event):
                return actions
        return []

    def _get_button_for_event(self, event, modifier_button_is_held):
        if event == self.product_defs.SurfaceEvent.ButtonShift.value:
            return self.product_defs.Button.Shift
        if modifier_button_is_held:
            return self.modified_event_type_to_button.get(event)
        return self.event_type_to_button.get(event)
