from util.plain_data import PlainData


class ModeCyclingLayoutManager:
    @PlainData
    class Layout:
        layout_id: int
        notification_primary: str
        notification_secondary: str
        views: list

    def __init__(
        self,
        screen_writer,
        *,
        layouts,
    ):
        self.screen_writer = screen_writer
        self.layouts = layouts
        self.active_layout_index = None

    def show(self):
        if self.active_layout_index is None:
            self.active_layout_index = 0
            self.on_layout_selected(self._active_layout.layout_id)

        self._show_layout_views()

    def hide(self):
        self._hide_layout_views()
        self.active_layout_index = None

    def on_layout_selected(self, layout_id):
        pass

    @property
    def active_layout(self):
        return self._active_layout.layout_id

    def set_layout(self, layout_id):
        index = next(index for index, layout in enumerate(self.layouts) if layout.layout_id == layout_id)
        self.active_layout_index = index

    def activate_next_layout(self):
        next_index = (self.active_layout_index + 1) % len(self.layouts)
        self._set_active_layout_index(next_index)
        self.on_layout_selected(self._active_layout.layout_id)

    def _show_layout_views(self):
        for view in self._active_layout.views:
            view.show()

    def _hide_layout_views(self):
        if self.active_layout_index is None:
            return

        for view in self._active_layout.views:
            view.hide()

    @property
    def _active_layout(self):
        return self.layouts[self.active_layout_index]

    def _set_active_layout_index(self, index):
        self._hide_layout_views()

        self.active_layout_index = index

        self._show_layout_views()
        self.screen_writer.display_notification(
            self._active_layout.notification_primary, self._active_layout.notification_secondary
        )
