class LaunchControl3DeviceManager:
    def __init__(self, sender, product_defs):
        self.sender = sender
        self.product_defs = product_defs

    def enable_encoder_relative_mode(self):
        self.sender.send_message(0xB6, 0x45, 0x7F)
        self.sender.send_message(0xB6, 0x48, 0x7F)
