Emulator request from clean (#193): fwtest's flash chip never ignores an
erase, so no test can make the store's erase read-back fail. Let the flash
file set block-protection bits on fwtest's chip, so a protected erase or
program is ignored as HW-121 says, with a case that shows the store's
read-back catching it. Also publish the fwtest 0.11.0 image if it isn't yet,
since clean's start3 moves its pin to it.
End with "done, ready to clear", Questions, merge order.
