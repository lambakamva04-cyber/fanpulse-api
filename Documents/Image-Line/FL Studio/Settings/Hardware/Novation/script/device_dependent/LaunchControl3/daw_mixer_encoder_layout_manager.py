from script.device_independent.layout_manager.paged_layout_manager import PagedLayoutManager
from script.device_independent.view import (
    MixerPanPreviewView,
    MixerPanScreenView,
    MixerPanView,
    MixerTrackEqPreviewView,
    MixerTrackEqScreenView,
    MixerTrackEqView,
)


class DawMixerEncoderLayoutManager(PagedLayoutManager):
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

        super().__init__(
            action_dispatcher,
            product_defs,
            screen_writer,
            led_writer,
            page_up_function="SelectPreviousEncoderMode",
            page_down_function="SelectNextEncoderMode",
            layouts=[
                PagedLayoutManager.Layout(
                    layout_id=product_defs.DawMixerEncoderMode.Pan,
                    notification_primary="Mixer",
                    notification_secondary="Pan",
                    views=[
                        MixerPanView(
                            action_dispatcher,
                            fl,
                            model,
                            product_defs,
                            led_writer,
                            control_to_index=product_defs.EncoderRow1ToIndex,
                        ),
                        MixerPanScreenView(action_dispatcher, screen_writer, fl),
                        MixerPanPreviewView(
                            action_dispatcher, fl, product_defs, model, control_to_index=product_defs.EncoderRow1ToIndex
                        ),
                    ],
                ),
                PagedLayoutManager.Layout(
                    layout_id=product_defs.DawMixerEncoderMode.EQ,
                    notification_primary="Mixer",
                    notification_secondary="Equalizer",
                    views=[
                        MixerTrackEqView(
                            action_dispatcher,
                            fl,
                            product_defs,
                            led_writer,
                            control_to_index=product_defs.EncoderRow1ToIndex,
                        ),
                        MixerTrackEqScreenView(action_dispatcher, screen_writer, fl),
                        MixerTrackEqPreviewView(action_dispatcher),
                    ],
                ),
            ],
        )

    def show(self):
        if self.model.daw_mixer_encoder_mode is not None:
            self.set_layout(self.model.daw_mixer_encoder_mode)
        super().show()

    def on_layout_selected(self, layout_id):
        self.model.daw_mixer_encoder_mode = layout_id
