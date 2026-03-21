# name=SMK-37 Elite
# supportedDevices=SMK-37Elite_BLE-Bt,MIDIIN2 (SMK-37 Elite Midi)

"""
Refactored version with clean architecture
"""
from main_controller import SMK37ProController

# Global controller instance
controller = SMK37ProController()

def OnInit():
    """Initialize the device"""
    controller.initialize()

def OnDeInit():
    """Cleanup on shutdown"""
    controller.shutdown()

def OnMidiIn(event):
    """Handle incoming MIDI events"""
    controller.process_midi_event(event)

def OnIdle():
    """Update function called during idle time"""
    controller.update_idle()

def OnRefresh(flags):
    """Handle refresh events"""
    if not controller.initialized:
        controller.initialize()
