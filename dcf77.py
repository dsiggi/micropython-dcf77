'''
2023-11-17  -   First release
'''

import utime
from machine import Pin, Timer

class dcf77:
    # Constants for the irq handler
    IRQ_MINUTE = 0
    IRQ_HOUR = 1
    IRQ_DAY = 2
    IRQ_MONTH = 3
    IRQ_YEAR = 4
    IRQ_DST = 5

    def __init__ (self, tco_pin: Pin,
                  false_time: list[int] = [50, 130],
                  true_time: list[int] = [150, 230],
                  pause_time: list[int] = [1700, 2500],
                  debug = False):
        '''
        - ``tco_pin``: Pin object of the TCO pin
        - ``false_time``: Minimum/Maximum impulse width for a FALSE signal
        - ``true_time``: Minimum/Maximum impulse width for a TRUE signal
        - ``pause_time``: Minimum/Maximum pause to recognize tick 59
        - ``debug``: Print debug messages
        '''
        self.FALSE_TIME = false_time
        self.TRUE_TIME = true_time
        self.TICK59_TIME = pause_time
        self.TCO = tco_pin
        self.DEBUG = debug
        self.TIMEOUT_TIME = self.TICK59_TIME[1] + 1000

        self.irq_start = 0  #Starttime of the interrupt
        self.irq_last = 0   #Time of last interrupt
        self.last_pulse = 0 #Length of last pulse
        self.timer_timeout = Timer(-1) #Timer for timeout handling

        self.found59 = False    #Tick59 was found
        self.tick = 0           #Actual tick
        self.signal = []        #Actual received signal
        self.signal_last = []   #Last received signal
        self.valid = False      #Signal is valid
        self.datetime = [0, 0, 0, 0, 0, 0, 0, 0]
        self.datetime_last = [0, 0, 0, 0, 0, 0, 0, 0]
        self.dst_changed = False

        # Init TCO pin
        self.TCO.init(mode=Pin.IN, pull=Pin.PULL_UP)

    # Function to print debug messages
    def __print(self, *val):
        if self.DEBUG:
            text = ''
            for v in range(len(val)):
                text += str(val[v])

            print("DCF77: ", text)

    # Interrupt handler for the DCF IRQ
    def __handler_interrupt(self, pin):
        self.__run()

    # Interrupt hanlder for the timeout timer
    def __timeout_callback(self, timer):
        self.found59 = False
        self.valid = False
        self.tick = 0
        self.signal.clear()
        self.__print("Signal timeout - Start new scanning for tick 59")

    # Main function. Called from the interrupt handler
    def __run(self):
        # Starting the timeout timer
        self.timer_timeout.init(mode=Timer.ONE_SHOT, period=self.TIMEOUT_TIME, callback=self.__timeout_callback)

        # If the last edge was detected between min/max TICK59_TIME
        # we have found the beginning of the telegram
        if utime.ticks_diff(utime.ticks_ms(), self.irq_last) > self.TICK59_TIME[0] \
            and utime.ticks_diff(utime.ticks_ms(), self.irq_last) < self.TICK59_TIME[1]:
            if not self.found59:
                self.__print("Found Tick 59")
                self.tick = 0
                self.found59 = True

        # Saving the actual time for comparsion
        self.irq_last = utime.ticks_ms()
        # If the signal from the DCF module is low
        # we save the time
        if not self.TCO.value():
            self.irq_start = utime.ticks_ms()
        else:
            # The signal from the DCF module is high
            # Calculate the pulse length
            diff = utime.ticks_diff(utime.ticks_ms(), self.irq_start)
            self.last_pulse = diff
            val = 2

            # Is the pulse a 0 or 1?
            if diff >= self.FALSE_TIME[0] and diff <= self.FALSE_TIME[1]:
                val = 0
            elif diff >= self.TRUE_TIME[0] and diff <= self.TRUE_TIME[1]:
                val = 1
            else:
                self.__print("Wrong pulse width - Start new scanning for tick 59")
                self.found59 = False
                self.signal.clear()

            # If the beginning of the telegram was found let count the ticks and save the values
            if self.found59:
                # self.__print("Tick: ", self.tick, " - ", val)
                self.signal.append(val)
                self.irq_start = 0
                self.tick += 1

                # If we have tick 59 the telegram is completed
                # Copy the data to another list and clear the source list
                if self.tick > 58:
                    self.signal_last = self.signal.copy()
                    self.signal.clear()
                    self.tick = 0

                # If tick is 1 end the saved signal list is not empty
                # we have a valid telegram
                if self.tick == 1:
                    if len(self.signal_last) > 0:
                        self.valid = True
                        self.__decode()
                        self.__custom_irq()
                        self.__print("Last Transmission: ", self.signal_last)

    # Function to decoding the time informations
    def __decode_time(self, time, check_parity):
        vals = [1, 2, 4, 8, 10, 20, 40, 80] # Values for the bit positions
        sum = 0 # Counter variable
        parity_check = 0 # Counter variable for the parity check

        # If check_parity is True the last value in the list is the parity
        # so we should not count this value
        end = len(time)
        if check_parity:
            end -= 1

        # Counting the time or date    
        for t in range(end):
            if time[t]:
                sum += vals[t]
                parity_check += 1

        # Checking parity
        # If a even number of bits was TRUE the parity
        # has to be FALSE
        if check_parity:
            if ( parity_check % 2 ) == 0:
                if time[-1]:
                    self.valid = False
                    self.__print("Parity is not correct")
                    return 999
        
        return sum
    
    # Function to decoding the date informations
    def __decode_date(self, date, check_parity=True):
        vals = [1, 2, 4, 8, 10, 20, 40, 80] # Values for the bit positions
        parity_check = 0 # Counter variable for the parity check

        # Checking parity
        # If a even number of bits was TRUE the parity
        # has to be FALSE
        if check_parity:
            for t in range(len(date) - 1):
                if date[t]:
                    parity_check += 1

            if ( parity_check % 2 ) == 0:
                if date[-1]:
                    self.valid = False
                    self.__print("Parity is not correct")
                    return [999, 999, 999, 999]
            
        # Decoding Day of month
        DayOfMonth = 0
        for v, b in enumerate(date[0:6]):
            if b:
                DayOfMonth += vals[v]

        # Decoding the weekday
        Weekday = 0
        for v, b in enumerate(date[6:9]):
            if b:
                Weekday += vals[v]

        # Decoding the month
        Month = 0
        for v, b in enumerate(date[9:14]):
            if b:
                Month += vals[v]

        # Decoding the year
        Year = 0
        for v, b in enumerate(date[14:22]):
            if b:
                Year += vals[v]
       
        return [DayOfMonth, Weekday, Month, Year]
    
    # Decoding the telegram
    def __decode(self, with_seconds=False):
        '''
        Decoding the DCF77 signal.
        If ``None`` is returned the signal is not valid
        If some value return ``999`` the decoding failed

        Bit 00      = 0 Minutenmarke, immer 0-Bit
        Bit 01..14  = Wetterdaten
        Bit 15      = Rufbit, ist es 1, liegt ggf. Störung vor
        Bit 16      = Ankündigung Zeitumstellung
        Bit 17..18  = Offset in stunden zur UTC.
        Bit 19      = Ankündigung Schaltsekunde
        Bit 20      = Start des Zeitprotokolls, immer 1-Bit
        Bit 21..28  = Minuten mit Parität
        Bit 29..35  = Stunden mit Parität
        Bit 36..41  = Kalendertag
        Bit 42..44  = Wochentag, 1=Montag
        Bit 45..49  = Monat
        Bit 50..58  = Jahr mit Parität
        Bit 59      = Kein Impuls
        '''

        # Signal to short or to long
        if len(self.signal_last) != 59:
            self.__print("Signal not valid -- Shorter or longer as 59 ticks")
            self.valid = False
            return
        
        # Checking some bits that must be everytime 0 or 1
        if self.signal_last[0]:
            self.__print("Bit 0 is not FALSE")
            self.valid = False
            return
        if not self.signal_last[20]:
            self.__print("Bit 20 is not TRUE")
            self.valid = False
            return
        
        # Decoding
        minutes = self.__decode_time(self.signal_last[21:29], True)
        hours = self.__decode_time(self.signal_last[29:36], True)
        day, weekday, month, year = self.__decode_date(self.signal_last[36:59], True)
        
        seconds = 0
        if with_seconds:
            seconds = self.tick

        self.datetime_last = self.datetime.copy()
        self.datetime = [ year, month, day, weekday - 1, hours, minutes, seconds , 0]

    # Function to run the custom irq handler
    def __custom_irq(self):
        if self.irq_handler != None:
            run_handler = False

            # Minute has changed
            if self.IRQ_MINUTE in self.irq_mode:
                if self.datetime_last[5] != self.datetime[5]:
                    run_handler = True
            # Hour has changed
            if self.IRQ_HOUR in self.irq_mode:
                if self.datetime_last[4] != self.datetime[4]:
                    run_handler = True
            # Day has changed
            if self.IRQ_DAY in self.irq_mode:
                if self.datetime_last[2] != self.datetime[2]:
                    run_handler = True
            # Month has changed
            if self.IRQ_MONTH in self.irq_mode:
                if self.datetime_last[1] != self.datetime[1]:
                    run_handler = True
            # Year has changed
            if self.IRQ_YEAR in self.irq_mode:
                if self.datetime_last[0] != self.datetime[0]:
                    run_handler = True
            # DST changed to TRUE
            if self.IRQ_DST in self.irq_mode:
                if self.signal_last[16]:
                    if not self.dst_changed:
                        run_handler = True
                        self.dst_changed = True
                else:
                    self.dst_changed = False

            if run_handler:
                self.irq_handler()

    # Function to start fetching the DCF77 signal
    def start(self):
        '''
        Start fetching time informations
        '''
        # Configure IRQ
        self.TCO.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, 
                     handler=self.__handler_interrupt)
        
        self.__print("Start decoding")

    # Function to stop fetching the DCF77 signal
    def stop(self):
        '''
        Stop fetching time informations
        '''
        # Disable IRQ
        self.TCO.irq(handler=None)
        self.timer_timeout.deinit()
        self.valid = False
        self.__print("Stop decoding")

    # Function that returns the last fetched signal
    def get_LastSignal(self):
        '''
        Return the last fetched signal as list
        '''
        return self.signal_last
    
    # Function that returns the actual time and date informations
    def get_DateTime(self, with_seconds = False):
        '''
        Returns the actual time and date informations as an 8-tuple 
        which contains: year, month, day, weekday, hours, minutes, seconds, subseconds
        This tuple can be directly used with the machine.RTC module

        - ``year`` contains only the last 2 digest
        - ``seconds`` is everytime 0, when ``with_seconds`` is TRUE the value will be set to the actual tick
        - ``subseconds`` is everytime 0

        - If ``None`` is returned the signal is not valid
        - If some value return ``999`` the decoding failed
        '''
        return self.datetime
    
    # Function that returns some status informations
    def get_Infos(self):
        '''
        Returns some status informations as dict
        '''
        info = {    "Found59": self.found59,
                    "Valid": self.valid,
                    "Last pulse length": self.last_pulse,
                    "Tick": self.tick}
        
        if self.valid:
            info.update({"Call bit": self.signal_last[15],
                        "Summer time announcement": self.signal_last[16],
                        "CEST": self.signal_last[17],
                        "CET": self.signal_last[18],
                        "Leap second": self.signal_last[19] })

        return info
    
    # Enable an custom irq handler
    def irq(self, mode: list[int] = [0], handler=None):
        '''
        Enables an custom irq handler for various events.
        ```Mode``` has to be a list of the following modes:
        - ```IRQ_MINUTE``` = irq is fired when the minute changed
        - ```IRQ_HOUR``` = irq is fired when the hour changed
        - ```IRQ_DAY``` = irq is fired when the day changed
        - ```IRQ_MONTH``` = irq is fired when the month changed
        - ```IRQ_YEAR``` = irq is fired when the year changed
        - ```IRQ_DST``` = irq is fired when the DST flag changes to TRUE
        '''
        self.irq_mode = mode
        self.irq_handler = handler