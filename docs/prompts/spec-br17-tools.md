Owner ruling for BR-17: spec may read two MIT-licensed tools and record what
they show as hardware facts in HARDWARE-SPEC, with provenance:
- github.com/jvitkauskas/m-flasher at 8fbece7348d7 (MIT): src/formats.rs
  (Package::parse, the app table and its checks), src/ops.rs (plan_firmware),
  docs/usage.md, docs/safety.md.
- github.com/jvitkauskas/m-bootloader at 3ac7651a019f (MIT): docs/SPEC.md,
  the flash formats and the checked start.
Still out of bounds: every GPL firmware (m-vave/fm1_open, Felucca and its
forks, and the rest) and every stock package. Record only the package format
and what installers and loaders check; no stock-firmware details (016's
configuration values and the like). Log what you read, with those commits,
in EXPOSURE.

Use them to settle Q-25, Qpackage's image is placed,
what size and identity an installer accepts, and how the chip key is checked.
Then update the clean promate can pass every check
in one go, and tell me which file to try.

Phase B round 1, from the unit: both candidates (key-ffff 3fbee115...,
key-980f b236d043...) werewas written, with
"unexpected flash image sichanged.
