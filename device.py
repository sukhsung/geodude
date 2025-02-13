import time,sys,struct
from datetime import datetime
import numpy as np
from math import floor

if '-verbose' in sys.argv:
    verbose = True
else:
    verbose = False

if '-dev' in sys.argv:
    print( 'DEV MODE: Dummy Devices' )
    from dummy_device import list_ports
    from dummy_device import Serial
else:
    from serial.tools.list_ports import comports as list_ports
    from serial import Serial
import socket
    
def get_port_list():
    port_list = [p.device for p in list_ports() if p.vid]
    return port_list

def auto_connect():
    dev = ADC8()
    port_list = get_port_list()

    for port in port_list:
        dev.connect_device( port )
        if dev.connected:
            return dev
        
    return False


class ADC8( ):
    def __init__(self):
        self.address = None
        self.connected = False
        self.device_type = None

        self.time_interval = 0.1
        self.lineending = '\r\n'

        self.encoding = 'utf-8'
        self.lineending = '\n'
        self.time_interval = 0.1
        self.board_type = 'ADC-8x'
        self.NUM_CHANNELS = 0     

    def __repr__(self):
        return self.get_board_status()
    
    def set_sampling(self, sampling):
        msg = self.query(f"s {sampling}" )
        self.parse_answer(msg)

    def set_ADC_settings(self, ch, gain, polarity, buffer):
        msg = self.query(f"g {ch} {gain} {polarity} {buffer}")
        self.parse_answer(msg)

    def set_impedance( self,ch,impedance):
        if self.i_function:
            msg = self.query( f"i {ch}{impedance}")
            self.parse_answer(msg)

    def connect_device( self, addr, baudrate=9600 ):
        self.device = Serial( addr, baudrate=baudrate, exclusive=True )
        self.device.timeout = 0.1
        self.default_timeout = self.device.timeout
        
        if not self.dev_check():
            print( 'Invalid Device, closing')
            self.device.close()
        else:
            self.addr = addr
            self.initialize()
            self.set_connected( True )

    def disconnect_device( self ):
        self.reset()
        self.device.close()
        self.set_connected(False)
        self.address = None
        self.device_type = None
        self.status = 'NOT-READY'
        self.device = None


    def set_connected( self, val ):
        self.connected = val

    def write( self, val ):
        if verbose:
            print("SENDING: "+ val)
        val = val+self.lineending
        self.device.write( val.encode( self.encoding) )

    def read( self ):
        val = self.device.read_all().decode(self.encoding)
        if verbose:
            print(val)
        return val
    
    def query( self,val, repeat=False, announce=False ):

        self.write(val)
        time.sleep( self.time_interval)
        msg = self.read()
        return msg

    def close( self ):
        self.device.close()

    def dev_check(self):
        try:
            msg = self.get_board_id()
            if msg.startswith("ADC-8"):
                return True
        except:
            return False
        
    def get_board_id(self):
        """Return the board's identification string and store its serial_number."""
        self.device.write(b'\n')
        self.device.reset_input_buffer()
        self.device.read(1000)		# Wait for timeout

        self.device.write(b'*\n')
        id = self.device.read_until(size=80)
        n = id.rfind(b"   ")
        if n < 0:
            self.serial_number = ""
        else:
            # Remove the final '\n' and convert to an ASCII string
            self.serial_number = id[n + 3:-1].decode()
            
        return id[:n].decode()
    
    def while_listening(self):
        pass

    def reset(self):
        pass

    def initialize(self):
        self.NUM_CHANNELS = self.get_available_NUM_CHANNELS()
        self.set_board_type()

        self.adcs = []
        for i in range(self.NUM_CHANNELS):
            self.adcs.append( {'label': f"Ch {i+1}",
                               'gain':None,
                               'polarity':None,
                               'buffer':None,
                               'impedance':None})

        self.sampling = 0
        
        self.device.write(b'\n')

        self.get_board_status()

    def parse_answer(self, msg):
        if msg.startswith("Sampling rate set to "):
            parts = msg.split(' ')
            self.sampling = float(parts[4])

        elif msg.startswith("ADC "):
            ch = int(msg[4])
            i = ch -1
            if msg.endswith("disabled\n"):
                self.adcs[i]['gain'] = 0
            else:
                parts = msg.split(',')
                parts_gain = parts[0]
                parts_polarity = parts[1]
                parts_buffer = parts[2]

                parts_gain = parts_gain.split(' ')
                # ch = int(parts_gain[1])
                gain = int(parts_gain[5])


                self.adcs[i]['gain'] = gain

                parts_polarity = parts_polarity.split(' ')[-1]
                if parts_polarity=="(unipolar)":
                    self.adcs[i]['polarity'] = 1
                elif parts_polarity=="(bipolar)":
                    self.adcs[i]['polarity'] = 2

                parts_buffer = parts_buffer.split(' ')[-1]
                if parts_buffer.startswith( "buffered" ):
                    self.adcs[i]['buffer'] = 'b'
                elif parts_buffer.startswith( "unbuffered"):
                    self.adcs[i]['buffer'] = 'u'
                
        elif msg.startswith("All ADCs "):
            if msg.endswith("disabled\n"):
                for i in range(self.NUM_CHANNELS):
                    self.adcs[i]['gain'] = 0
            else:


                parts = msg.split(',')
                parts_gain = parts[0]
                parts_polarity = parts[1]
                parts_buffer = parts[2]

                parts_gain = parts_gain.split(' ')

                gain = int(parts_gain[5])
                parts_polarity = parts_polarity.split(' ')[-1]

                parts_buffer = parts_buffer.split(' ')[-1]

                for i in range(self.NUM_CHANNELS):
                    self.adcs[i]['gain'] = gain

                    if parts_polarity=="(unipolar)":
                        self.adcs[i]['polarity'] = 1
                    elif parts_polarity=="(bipolar)":
                        self.adcs[i]['polarity'] = 2

                    if parts_buffer.startswith( "buffered" ):
                        self.adcs[i]['buffer'] = 'b'
                    elif parts_buffer.startswith( "unbuffered"):
                        self.adcs[i]['buffer'] = 'u'
            

        elif msg.startswith("Impedance settings"):
            settings = msg.strip().split()[3:]

            for i in range(self.NUM_CHANNELS):
                self.adcs[i]['impedance'] = settings[i][1]

            
        elif msg.startswith("\nCurrent settings"):
            lines = msg.split('\n')
            for line in lines:
                if line.startswith('Current settings:'):
                    self.sampling = float(line.split(' ')[-1])
                elif line.startswith('ADC '):
                    parts = line.split(': ')
                    ch = int(parts[0][-1])

                    if parts[1].startswith('disabled'):
                        self.adcs[ch-1]['gain'] = 0
                    else:
                        parts = parts[1].split(', ')

                        gain = int(parts[0].split(' ')[1])
                        polarity = parts[1]
                        if polarity == 'bipolar':
                            polarity = 2
                        else:
                            polarity = 1

                        buffer = parts[2]
                        if buffer == 'unbuffered':
                            buffer = 'u'
                        else:
                            buffer = 'b'

                        if len(parts)==4:
                            impedance = parts[3][-1]
                        else:
                            impedance = ''
                        
                        self.adcs[ch-1]['gain'] = gain
                        self.adcs[ch-1]['polarity'] = polarity
                        self.adcs[ch-1]['buffer'] = buffer
                        self.adcs[ch-1]['impedance'] = impedance

        else:
            print("CAN'T PARSE")
            print(msg)


    def get_board_status(self):
        msg = self.query("c", repeat=True,announce=True)
        self.parse_answer(msg)
        return msg

    def set_board_type( self):
        if self.board_type == "ADC-8x":
            self.HDR_LEN = 10 + self.NUM_CHANNELS * 2
            self.BIPOLAR = 2
            self.SCALE_24 = 1.0 / (1 << 24)
            self.VREF = 2.5 * 1.02		# Include 2% correction factor
            self.check_i_function()
        elif self.board_type == "ADC-8":
            self.HDR_LEN = 16
            self.BIPOLAR = 2
            self.SCALE_24 = 1.0 / (1 << 24)
            self.VREF = 2.5 * 1.02		# Include 2% correction factor
        elif self.board_type is None:
            self.NUM_CHANNELS = 0
            self.HDR_LEN = 0
            self.BIPOLAR = 2
            self.SCALE_24 = 0
            self.VREF = 0

    def check_m_function( self ):
        # Check whether m function exist
        self.device.read(1000)
        self.device.write(b'm\n')
        msg = self.device.read(10).decode(self.encoding).strip()
        if msg.startswith('Measuring'):
            self.m_function = True
            print( 'M exists')
            for i in range(10):
                time.sleep(1)
                print(i)
        else:
            self.m_function = False
            print( 'M does not exist')
        print( self.device.read(1000))

    def check_i_function( self ):
        # Check whether m function exist
        self.device.read(1000)
        self.device.write(b'i\n')
        msg = self.device.read(1000).decode()
        if msg.startswith('Impedance'):
            self.i_function = True
            # print( 'I function exists')
        else:
            self.i_function = False
            # print( 'I function does not exist')
        _ = self.device.read(1000)


    def get_available_NUM_CHANNELS( self ): 
        # Get number of channels
        self.device.write(b'c\n')
        msg = self.device.read(1000).decode()
        msg = msg.split('\n')
        msg = [x for x in msg if x.startswith('ADC ')]
        return len( msg )
    
    def prepare_acquire( self, fpath, acquire_time ):
        self.acquire_file = open( fpath, 'w' )
        self.acquire_time = acquire_time

    def start_acquire(self):
        self.device.write(f"b{self.acquire_time}\n".encode())
        self.device.timeout = 6
        self.device.read_until(b"+")		# Skip initial text
        sig = b""
        h = self.device.read(self.HDR_LEN)
        
        if len(h) == self.HDR_LEN:
            if self.board_type == 'ADC-8':
                fmt = f"<4sHBB {2 * self.NUM_CHANNELS}B"
            elif self.board_type == 'ADC-8x':
                fmt = f"<8sH {2 * self.NUM_CHANNELS}B"
            hdr = struct.unpack(fmt, h)
            sig = hdr[0]		# The signature
         
        if sig == b"ADC8":
            chans = hdr[4:]			# The ADC channel entries
        elif sig == b"ADC8x-1.":
            chans = hdr[2:]			# The ADC channel entries
        else:
            print("Invalid header received, transfer aborted")
            self.device.write(b"\n")
            self.set_request( "LISTEN" )
            return -1
        
        num = 0
        gains = [chans[2 * i] for i in range(self.NUM_CHANNELS)]
        bipolar = [chans[2 * i + 1] & self.BIPOLAR for i in range(self.NUM_CHANNELS)]
        for g in gains:
            if g > 0:
                num += 1
        if num == 0:
            print("Header shows no active ADCs, transfer aborted")
            self.device.write(b"\n")
            return -1
        

        blocksize = num * 3

        total_blocks = 0
        warned = False

        output_data = []
        # Receive and store the data


        time_start = time.time()
        time_counter = 0
        cont = True
        if self.board_type == 'ADC-8x' and self.NUM_CHANNELS==4:
            self.device.read(8)

        print("[",end="")
        while cont:
            time_cur = time.time()
            time_elapsed = floor(time_cur - time_start)
            if time_elapsed == time_counter:
                # print(f"Time Elapsed: {time_elapsed}")
                print(".",end="")
                time_counter += 1
            n = self.device.read(1)		# Read the buffer's length byte
            
            if len(n) == 0:
                print("\nTimeout")
                break
            n = n[0]
            if n == 0:
                print("\nEnd of data")
                break

            d = self.device.read(n)		# Read the buffer contents
            if len(d) < n:
                print("\nShort data buffer received")
                break
            
            if n % blocksize != 0:
                if not warned:
                    print("\nWarning: Invalid buffer length", n)
                    warned = True
                n -= n % blocksize

            for i in range(0, n, blocksize):
                # Convert the block data to floats and write them out
                volts = self.convert_values(d[i:i + blocksize], gains, bipolar, num)
                output_data.append ( volts )
                
                write_str = ""
                for volt in volts:
                    write_str += str(volt) + ","
                self.acquire_file.write( write_str[:-1]+"\n" )

            total_blocks += n // blocksize

        print("]")
        self.device.write(b"\n")

        self.device.timeout = self.default_timeout#0.01
        self.device.read(1000)		# Flush any extra output

        self.acquire_file.close()
        return output_data


    def convert_values(self, block, gains, bipolar, num):
        """Convert the 24-bit values in block to floating-point numbers
        and store them in the global variable volts."""

        j = v = 0
        volts = [0.] * num
        for i, g in enumerate(gains):
            if g == 0:
                continue
            x = (block[j] + (block[j+1] << 8) + (block[j+2] << 16)) * self.SCALE_24
            if bipolar[i]:
                x = 2. * x - 1.
            volts[v] = round(x * self.VREF / g, 9)
            j += 3
            v += 1
        return volts

class Timer():
    def __init__(self):
        self.t0 = False
        self.started = False
    
    def start(self):
        self.t0 = datetime.now()
        self.started = True

    def elapsed(self):
        return (datetime.now() - self.t0).total_seconds()
    
    def elapsed_n_now(self):
        now = datetime.now() 
        return (now - self.t0).total_seconds(), now
    
    def stop(self):
        self.t0 = False
        self.started = False

    def restart(self):
        self.t0 = datetime.now()
    
