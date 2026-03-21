from script.constants import Encoders
from util.control_to_index import make_control_to_index
from util.custom_enum import CustomEnum


class DeviceLayout(CustomEnum):
    Mixer = 1
    Control = 2


class DawMixerEncoderMode(CustomEnum):
    Pan = 0
    EQ = 1


class DawMixerButtonMode(CustomEnum):
    Mute = 0
    Select = 1
    Arm = 2


class DawControlEncoderMode(CustomEnum):
    Plugin = 0
    Pan = 1


class DawControlButtonMode(CustomEnum):
    Mute = 0
    Select = 1


class Constants(CustomEnum):
    DisplayedDeviceName = "Launch Control 3"

    NovationProductId = 0x16

    LightingTargetCC = 0x50
    LightingTypeStatic = 0x00
    LightingTypeRGB = 0x03

    ChannelsPerBank = 8

    NumEncoders = 16
    EncoderCcOffset = 0x0D
    EncoderRow1FirstIndex = Encoders.FirstControlIndex.value
    EncoderRow2FirstIndex = Encoders.FirstControlIndex.value + 8

    VolumeControlFirstIndex = EncoderRow2FirstIndex
    PanControlFirstIndex = EncoderRow1FirstIndex
    EqControlFirstIndex = EncoderRow1FirstIndex
    PluginParameterFirstIndex = EncoderRow1FirstIndex


class Button(CustomEnum):
    EncoderPageUp = 1
    EncoderPageDown = 2
    TrackLeft = 3
    TrackRight = 4
    TrackLeftShift = 5
    TrackRightShift = 6
    Shift = 7
    Function = 8
    Button_1 = 9
    Button_2 = 10
    Button_3 = 11
    Button_4 = 12
    Button_5 = 13
    Button_6 = 14
    Button_7 = 15
    Button_8 = 16
    ShiftButton_1 = 17
    ShiftButton_2 = 18
    ShiftButton_3 = 19
    ShiftButton_4 = 20
    ShiftButton_5 = 21
    ShiftButton_6 = 22
    ShiftButton_7 = 23
    ShiftButton_8 = 24


class SurfaceEvent(CustomEnum):
    EnterDawMode = 0x9F, 0x0C, 0x7F
    ExitDawMode = 0x9F, 0x0C, 0x00
    ButtonEncoderPageUp = 0xB0, 0x6A
    ButtonEncoderPageDown = 0xB0, 0x6B
    ButtonTrackLeft = 0xB0, 0x67
    ButtonTrackRight = 0xB0, 0x66
    ButtonShift = 0xB6, 0x3F
    DeviceLayout = 0xB6, 0x1E
    ButtonFunction = 0xB0, 0x42
    EncoderFirst = 0xBF, 0x4D
    EncoderLast = 0xBF, 0x5C
    Button_1 = 0xB0, 0x25
    Button_2 = 0xB0, 0x26
    Button_3 = 0xB0, 0x27
    Button_4 = 0xB0, 0x28
    Button_5 = 0xB0, 0x29
    Button_6 = 0xB0, 0x2A
    Button_7 = 0xB0, 0x2B
    Button_8 = 0xB0, 0x2C


class DisplayAddress(CustomEnum):
    Permanent = 0x35
    Overlay = 0x36
    FirstEncoder = 0x0D
    LastEncoder = 0x1C


FunctionToButton = {
    "SelectPreviousEncoderMode": Button.EncoderPageUp,
    "SelectNextEncoderMode": Button.EncoderPageDown,
    "SelectPreviousChannelBank": Button.TrackLeft,
    "SelectNextChannelBank": Button.TrackRight,
    "MixerBankLeft": Button.TrackLeft,
    "MixerBankRight": Button.TrackRight,
    "SelectPreviousChannel": Button.TrackLeftShift,
    "SelectNextChannel": Button.TrackRightShift,
    "SelectPreviousMixerTrack": Button.TrackLeftShift,
    "SelectNextMixerTrack": Button.TrackRightShift,
    "ShiftModifier": Button.Shift,
    "ShowHighlights": Button.Shift,
    "SwitchToNextButtonMode": Button.Function,
    "MixerTrackMute_1": Button.Button_1,
    "MixerTrackMute_2": Button.Button_2,
    "MixerTrackMute_3": Button.Button_3,
    "MixerTrackMute_4": Button.Button_4,
    "MixerTrackMute_5": Button.Button_5,
    "MixerTrackMute_6": Button.Button_6,
    "MixerTrackMute_7": Button.Button_7,
    "MixerTrackMute_8": Button.Button_8,
    "ToggleSoloTrack_1": Button.ShiftButton_1,
    "ToggleSoloTrack_2": Button.ShiftButton_2,
    "ToggleSoloTrack_3": Button.ShiftButton_3,
    "ToggleSoloTrack_4": Button.ShiftButton_4,
    "ToggleSoloTrack_5": Button.ShiftButton_5,
    "ToggleSoloTrack_6": Button.ShiftButton_6,
    "ToggleSoloTrack_7": Button.ShiftButton_7,
    "ToggleSoloTrack_8": Button.ShiftButton_8,
    "SelectTrack_1": Button.Button_1,
    "SelectTrack_2": Button.Button_2,
    "SelectTrack_3": Button.Button_3,
    "SelectTrack_4": Button.Button_4,
    "SelectTrack_5": Button.Button_5,
    "SelectTrack_6": Button.Button_6,
    "SelectTrack_7": Button.Button_7,
    "SelectTrack_8": Button.Button_8,
    "ToggleRecordArm_1": Button.Button_1,
    "ToggleRecordArm_2": Button.Button_2,
    "ToggleRecordArm_3": Button.Button_3,
    "ToggleRecordArm_4": Button.Button_4,
    "ToggleRecordArm_5": Button.Button_5,
    "ToggleRecordArm_6": Button.Button_6,
    "ToggleRecordArm_7": Button.Button_7,
    "ToggleRecordArm_8": Button.Button_8,
    "ToggleMuteChannel_1": Button.Button_1,
    "ToggleMuteChannel_2": Button.Button_2,
    "ToggleMuteChannel_3": Button.Button_3,
    "ToggleMuteChannel_4": Button.Button_4,
    "ToggleMuteChannel_5": Button.Button_5,
    "ToggleMuteChannel_6": Button.Button_6,
    "ToggleMuteChannel_7": Button.Button_7,
    "ToggleMuteChannel_8": Button.Button_8,
    "SelectChannel_1": Button.Button_1,
    "SelectChannel_2": Button.Button_2,
    "SelectChannel_3": Button.Button_3,
    "SelectChannel_4": Button.Button_4,
    "SelectChannel_5": Button.Button_5,
    "SelectChannel_6": Button.Button_6,
    "SelectChannel_7": Button.Button_7,
    "SelectChannel_8": Button.Button_8,
    "ToggleSoloChannel_1": Button.ShiftButton_1,
    "ToggleSoloChannel_2": Button.ShiftButton_2,
    "ToggleSoloChannel_3": Button.ShiftButton_3,
    "ToggleSoloChannel_4": Button.ShiftButton_4,
    "ToggleSoloChannel_5": Button.ShiftButton_5,
    "ToggleSoloChannel_6": Button.ShiftButton_6,
    "ToggleSoloChannel_7": Button.ShiftButton_7,
    "ToggleSoloChannel_8": Button.ShiftButton_8,
}


ButtonToLedIndex = {
    Button.EncoderPageUp: 0x6A,
    Button.EncoderPageDown: 0x6B,
    Button.TrackLeft: 0x67,
    Button.TrackRight: 0x66,
    Button.TrackLeftShift: 0x67,
    Button.TrackRightShift: 0x66,
    Button.Function: 0x42,
    Button.Button_1: 0x25,
    Button.Button_2: 0x26,
    Button.Button_3: 0x27,
    Button.Button_4: 0x28,
    Button.Button_5: 0x29,
    Button.Button_6: 0x2A,
    Button.Button_7: 0x2B,
    Button.Button_8: 0x2C,
    Button.ShiftButton_1: 0x25,
    Button.ShiftButton_2: 0x26,
    Button.ShiftButton_3: 0x27,
    Button.ShiftButton_4: 0x28,
    Button.ShiftButton_5: 0x29,
    Button.ShiftButton_6: 0x2A,
    Button.ShiftButton_7: 0x2B,
    Button.ShiftButton_8: 0x2C,
}


EncoderIndexToControlIndex = {
    index: Encoders.FirstControlIndex.value + control
    for index, control in enumerate(range(Constants.NumEncoders.value))
}


class LaunchControl3ProductDefs:
    def __init__(self):
        self.Constants = Constants
        self.Button = Button
        self.DeviceLayout = DeviceLayout
        self.DawMixerEncoderMode = DawMixerEncoderMode
        self.DawMixerButtonMode = DawMixerButtonMode
        self.DawControlEncoderMode = DawControlEncoderMode
        self.DawControlButtonMode = DawControlButtonMode
        self.SurfaceEvent = SurfaceEvent
        self.DisplayAddress = DisplayAddress
        self.FunctionToButton = FunctionToButton
        self.ButtonToLedIndex = ButtonToLedIndex
        self.EncoderIndexToControlIndex = EncoderIndexToControlIndex
        self.ControlIndexToEncoderIndex = {v: k for k, v in self.EncoderIndexToControlIndex.items()}
        self.EncoderRow1ToIndex = make_control_to_index(Constants.EncoderRow1FirstIndex.value, Encoders.Num.value)
        self.EncoderRow2ToIndex = make_control_to_index(Constants.EncoderRow2FirstIndex.value, Encoders.Num.value)

    def IsShiftButton(self, button):
        return button in [
            Button.TrackRightShift,
            Button.TrackLeftShift,
            Button.ShiftButton_1,
            Button.ShiftButton_2,
            Button.ShiftButton_3,
            Button.ShiftButton_4,
            Button.ShiftButton_5,
            Button.ShiftButton_6,
            Button.ShiftButton_7,
            Button.ShiftButton_8,
        ]

    def ForwardButtonLedGivenShift(self, button, shift_pressed):
        return self.IsShiftButton(button) == shift_pressed
