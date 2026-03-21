class ShiftToggleView:
    def __init__(self, action_dispatcher, product_defs, *, default_view, shift_view, shift_button="ShiftModifier"):
        self.action_dispatcher = action_dispatcher
        self.product_defs = product_defs
        self.default_view = default_view
        self.shift_view = shift_view
        self.shift_button = shift_button
        self._active_view = self.default_view

    def show(self):
        self.action_dispatcher.subscribe(self)
        self._active_view.show()

    def hide(self):
        self.action_dispatcher.unsubscribe(self)
        self._active_view.hide()

    def _is_shift_button(self, button):
        return button == self.product_defs.FunctionToButton.get(self.shift_button)

    def handle_ButtonPressedAction(self, action):
        if self._is_shift_button(action.button):
            self._set_active_view(self.shift_view)

    def handle_ButtonReleasedAction(self, action):
        if self._is_shift_button(action.button):
            self._set_active_view(self.default_view)

    def _set_active_view(self, view):
        if self._active_view != view:
            self._active_view.hide()
            self._active_view = view
            self._active_view.show()
