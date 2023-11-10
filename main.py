import machine
import dcf77

dcf = dcf77.dcf77(machine.Pin(0))

# Starting receiving and decoding
dcf.start()

rtc = machine.RTC()

# Cutstom irq handler
def handler():
    print("It's a new day or year.")

dcf.irq([dcf.IRQ_DAY, dcf.IRQ_YEAR], handler)

print("RTC initalized")
datetime = rtc.datetime()
print("Actual time: {:02d}:{:02d} {:02d}.{:02d}.{}".format(datetime[4], datetime[5], datetime[2], datetime[1], datetime[0]))

print("Wait for a valid dcf77 signal")
while not dcf.get_Infos()['Valid']:
    pass

print("Found Valid signal")
datetime = dcf.get_DateTime()
print("DCF77 time: {:02d}:{:02d} {:02d}.{:02d}.{}".format(datetime[4], datetime[5], datetime[2], datetime[1], datetime[0]))

print("Setting RTC")
rtc.datetime(datetime)