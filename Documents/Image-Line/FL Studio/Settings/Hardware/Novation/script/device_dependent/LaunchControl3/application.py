from script.device_dependent.LaunchControl3.daw_control_device_layout_manager import DawControlDeviceLayoutManager
from script.device_dependent.LaunchControl3.daw_mixer_device_layout_manager import DawMixerDeviceLayoutManager
from script.device_independent.fl_gui.fl_window_manager import FLWindowManager
from script.device_independent.view import FLStudioTextView, ShowHighlightsView
from script.model import Model
from util.command_dispatcher import CommandDispatcher


class Application:
    def __init__(self, _, button_led_writer, fl, action_dispatcher, screen_writer, device_manager, product_defs):
        self.active_device_layout_manager = None
        self.button_led_writer = button_led_writer
        self.fl = fl
        self.action_dispatcher = action_dispatcher
        self.command_dispatcher = CommandDispatcher()
        self.screen_writer = screen_writer
        self.product_defs = product_defs
        self.device_manager = device_manager
        self.model = None

        self.global_views = set()
        self.fl_window_manager = FLWindowManager(action_dispatcher, fl)

    def init(self):
        self.active_device_layout_manager = None
        self.model = Model()

        self.action_dispatcher.subscribe(self)

        self.global_views = {
            FLStudioTextView(self.screen_writer, self.action_dispatcher),
            ShowHighlightsView(self.action_dispatcher, self.product_defs, self.model),
        }

        for view in self.global_views:
            view.show()

    def deinit(self):
        if self.active_device_layout_manager:
            self.active_device_layout_manager.hide()

        for view in self.global_views:
            view.hide()

        self.action_dispatcher.unsubscribe(self)

    def handle_ButtonPressedAction(self, action):
        if action.button == self.product_defs.FunctionToButton.get("ShiftModifier"):
            self.button_led_writer.shift_modifier_pressed()

    def handle_ButtonReleasedAction(self, action):
        if action.button == self.product_defs.FunctionToButton.get("ShiftModifier"):
            self.button_led_writer.shift_modifier_released()

    def handle_DeviceLayoutChangedAction(self, action):
        if self.active_device_layout_manager:
            self.active_device_layout_manager.hide()

        self.active_device_layout_manager = self._create_device_layout_manager(action.layout)
        if self.active_device_layout_manager:
            self.active_device_layout_manager.show()
            self.active_device_layout_manager.focus_windows()

    def _create_device_layout_manager(self, layout):
        if layout == self.product_defs.DeviceLayout.Mixer:
            return DawMixerDeviceLayoutManager(
                self.action_dispatcher,
                self.command_dispatcher,
                self.fl,
                self.model,
                self.fl_window_manager,
                self.product_defs,
                self.button_led_writer,
                self.screen_writer,
                self.device_manager,
            )
        if layout == self.product_defs.DeviceLayout.Control:
            return DawControlDeviceLayoutManager(
                self.action_dispatcher,
                self.command_dispatcher,
                self.fl,
                self.model,
                self.fl_window_manager,
                self.product_defs,
                self.button_led_writer,
                self.screen_writer,
                self.device_manager,
            )
        return None
