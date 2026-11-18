Answers to the four open items from BR-17 (#181 is merged):
1. Trying the candidates: yes, I'll try both on the unit when I'm next at the installer and send you its exact words. Nothing to do on them until then.
2. Header bytes 10-15: carry the values JieLi's tools write (4 and 0x200). They're fixed, so R-REPRO holds. Mark them as taken from the tools, with their meaning still open (Q-25).
3. Key: 0xFFFF first, then 0x980F.
4. The du was acceptable: sizes only, no file opened. Next time measure only clean's own folders.
Also: flash.bin alone is right; isd_config.ini lives below 0x4000, and an app-area-only package leaves that region alone.
