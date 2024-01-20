# micropython-dcf77

Micropython modul to decode the dcf77 signal delivered by a receiver module.

To use this module you need an dcf77 receiver module connectet to a gpoi pin of your board.

## Class
```
tco_pin = The pin object for the pin where the receiver is connected
false_time = Min/Max time in ms for detecing a 0 pulse
true_time = Min/Max time in ms for detecting a 1 pulse
pause_time = Min/Max time in ms for detecting the beginning of the telegramm
```
```python
>>> dcf = dcf77.dcf77(machine.Pin(0))
```
## Methods

### start
Starting the receiving and decoding of the telegramm.
```python
>>> dcf.start()
```

### stop
Stopping the receiving and decoding of the telegramm.
```python
>>> dcf.stop()
```
### get_LastSignal
Returns the last telegram as list
```python
>>> dcf.get_LastSignal()
[0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0]
>>>
```
### get_DateTime
Returns the actual time and date informations as an 8-tuple 
which contains: year, month, day, weekday, hours, minutes, seconds, subseconds
This tuple can be directly used with the machine.RTC module

-   ``year`` contains only the last 2 digest
-   ``seconds`` is everytime 0, when ``with_seconds`` is TRUE the value will be set to the actual tick
-   ``subseconds`` is everytime 0

- If ``None`` is returned the signal is not valid
- If some value return ``999`` the decoding failed

```python
>>> dcf.get_DateTime(with_seconds=False)
[23, 11, 10, 4, 16, 33, 0, 0]
>>>
```
### get_Infos
Returns some infos
```python
>>> dcf.get_Infos()
{'Call bit': 0, 'Summer time announcement': 0, 'Found59': True, 'Valid': True, 'Leap second': 0, 'Tick': 49, 'Last pulse length': 102, 'CEST': 0, 'CET': 1}
>>>

```
### get_irq
Enables an custom irq handler for various events. \
```Mode``` has to be a list of the following modes:
-   ```IRQ_MINUTE``` = irq is fired when the minute changed
-   ```IRQ_HOUR``` = irq is fired when the hour changed
-   ```IRQ_DAY``` = irq is fired when the day changed
-   ```IRQ_MONTH``` = irq is fired when the month changed
-   ```IRQ_YEAR``` = irq is fired when the year changed
-   ```IRQ_DST``` = irq is fired when the DST flag changes to TRUE
```python
>>> dcf.irq(mode=[dcf.IRQ_DAY, dcf.IRQ_DST], handler=myhandler)
```

### debug
Enable and disable debug messages on the console.
```python
>>> dcf.debug(True)
```

## Sample Code
```python
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
```




