from script.device_independent.layout_manager.paged_layout_manager import PagedLayoutManager
from script.device_independent.view import (
    ChannelRackPanPreviewView,
    ChannelRackPanScreenView,
    ChannelRackPanView,
    PluginParameterLedView,
    PluginParameterPreviewView,
    PluginParameterScreenView,
    PluginParameterView,
)
from script.plugin import plugin_parameter_mappings


class DawControlEncoderLayoutManager(PagedLayoutManager):
    def __init__(
        self,
        action_dispatcher,
        fl,
        model,
        product_defs,
        screen_writer,
        led_writer,
    ):
        self.model = model
        encoder_row1_to_index = product_defs.EncoderRow1ToIndex

        super().__init__(
            action_dispatcher,
            product_defs,
            screen_writer,
            led_writer,
            page_up_function="SelectPreviousEncoderMode",
            page_down_function="SelectNextEncoderMode",
            layouts=[
                PagedLayoutManager.Layout(
                    layout_id=product_defs.DawControlEncoderMode.Plugin,
                    notification_primary="Channel Rack",
                    notification_secondary="Plugin",
                    views=[
                        PluginParameterView(
                            action_dispatcher, fl, plugin_parameter_mappings, control_to_index=encoder_row1_to_index
                        ),
                        PluginParameterScreenView(
                            action_dispatcher,
                            fl,
                            screen_writer,
                            plugin_parameter_mappings,
                            control_to_index=encoder_row1_to_index,
                        ),
                        PluginParameterPreviewView(
                            action_dispatcher,
                            fl,
                            product_defs,
                            plugin_parameter_mappings,
                            control_to_index=encoder_row1_to_index,
                        ),
                        PluginParameterLedView(
                            action_dispatcher,
                            led_writer,
                            fl,
                            product_defs,
                            plugin_parameter_mappings,
                            control_to_index=encoder_row1_to_index,
                        ),
                    ],
                ),
                PagedLayoutManager.Layout(
                    layout_id=product_defs.DawControlEncoderMode.Pan,
                    notification_primary="Channel Rack",
                    notification_secondary="Pan",
                    views=[
                        ChannelRackPanView(
                            action_dispatcher,
                            fl,
                            model,
                            product_defs,
                            led_writer,
                            control_to_index=encoder_row1_to_index,
                        ),
                        ChannelRackPanScreenView(action_dispatcher, screen_writer, fl),
                        ChannelRackPanPreviewView(
                            action_dispatcher, fl, product_defs, model, control_to_index=encoder_row1_to_index
                        ),
                    ],
                ),
            ],
        )

    def show(self):
        if self.model.daw_control_encoder_mode is not None:
            self.set_layout(self.model.daw_control_encoder_mode)
        super().show()

    def on_layout_selected(self, layout_id):
        self.model.daw_control_encoder_mode = layout_id
