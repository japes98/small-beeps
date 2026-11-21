#220 is merging (it carries your #221, leds1). Spec's prompt for steps K
and J is ready: drop/prompts/clean-br17-audio5.md. The owner has allowed
both. Build them on top of leds1, as one file.

One owner change to J: one key press runs the whole sweep automatically
(CON1 bits 0–15, then CON3 bits 0–7, each tried alone, put back, read
back, ~100 ms, logged), stopping by itself and leaving the bit set if
the link moves; a second press aborts and restores. Run it in whatever
CLK_CON2 state the keys left (so the owner runs it once with bit 9 set
and once clear). Everything else per the prompt. K may likewise run all
its measurements from one press.
