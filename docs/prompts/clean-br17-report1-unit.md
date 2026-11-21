Unit observation for the report log (source UNIT, from a full flash
read-back on 2026-11-21): the store's record at 0xFC000 reads back as
plain bytes, so records you write through the flash path are readable as
written. Sectors outside your image and the store are not blank on this
unit (old data from before small-beeps), so the log must erase its sector
before first use and never assume blank flash.
