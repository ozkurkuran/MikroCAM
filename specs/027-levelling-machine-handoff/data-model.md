# Presentation state

Controller selection: existing strings MACH3, MACH4, LinuxCNC, GRBL. GRBL shows the handoff
card and hides/disables the legacy serial frame; offline values hide card and restore existing
probe-code/import buttons. Serial connection remains absent in Levelling.
Machine dock: existing app-owned object, reused without creation of another controller.
No new persisted entity. Callback guard rejects GRBL before UI/worker/device side effects.
