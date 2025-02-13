import os, datetime
import json
import device
from crontab import CronTab


class path_manager():
    def __init__(self, dev=False):
        if dev:
            self.user='raspberry'
            self.prefix='./media'
        else:
            self.user = os.environ.get('USER')
            self.prefix='/media'

        print( "Loading Configuration File")
        self.load_config()
        self.check_config()

        print( "Prepping Folder Structure") 
        self.prepare_path()

    def prepare_path( self ):
        if not os.path.isdir( f'{self.path}/results'):
            os.mkdir( f'{self.path}/results' )

        now = datetime.datetime.now()
        folder = f'{now.year}-{now.month}-{now.day}'
        self.savepath = f'{self.path}/results/{folder}'
        if not os.path.isdir( self.savepath ):
            os.mkdir( self.savepath )

    def list_drives(self):
        try:
            dir_media = os.listdir(f'{self.prefix}/{self.user}')
            return dir_media
        except:
            return []
        
    def load_config(self):
        dir_media = self.list_drives()

        if len(dir_media) == 0:
            return False
        else:
            for dir in dir_media:
                if os.path.isfile( f'{self.prefix}/{self.user}/{dir}/config.json'):
                    self.path = f'{self.prefix}/{self.user}/{dir}'

                    file_config = open(f'{self.path}/config.json','r')
                    self.config = json.load( file_config )

                    return True
            return False
        
    def check_config( self ):
        try:
            print(f"Sampling: {self.config['sampling']}")
        except:
            print("Invalid Sampling Configuration")
            return False
        
        try:
            print(f"Found {len(self.config['ADC'])} ADC Settings")

            for adc in self.config['ADC']:
                print( f"Gain: {adc['gain']}, Polarity: {adc['polarity']}, Buffer: {adc['buffer']}")

        except:
            print("Invalid ADC Configuration")
            return False
        
        try:
            print(f"Acquisition Time (s): {self.config['time_acquire']}")
        except:
            print("Invalid Acquisition Time")
            return False
        
        try:
            print(f"Cron schedule: {self.config['schedule']}")
        except:
            print("Invalid cron schedule")
            return False
        
        


class governor():
    def __init__(self, dev=False):
        self.pm = path_manager(dev=dev)
        self.config = self.pm.config

        print( "Managing Crontab")
        self.cron = CronTab(user=True)
        self.set_crontab()

        print(" All Set!")

    def set_crontab(self):
        self.cron.remove_all(comment='Geophone')
        self.cron.write()

        job = self.cron.new(command=f'{self.pm.path}/run_geodude', comment='Geophone')
        job.setall( self.config['schedule'])
        job.enable()
        self.cron.write()




class geodude():
    def __init__(self, dev=False):
        self.pm = path_manager(dev=dev)
        self.config = self.pm.config

        print( "Connecting to Serial Device")
        self.device = device.auto_connect()
        try:
            self.device.set_sampling( self.config['sampling'])
            ch = 1
            for adc in self.config['ADC']:
                self.device.set_ADC_settings( ch, adc['gain'], adc['polarity'], adc['buffer'])
                ch += 1

            print( self.device )
        except:
            self.device.close()
            return -1

    def start_acquire(self):
        now = datetime.datetime.now()
        fname = f'{now.hour}:{now.minute}:{now.second}.csv'
        self.device.prepare_acquire( f'{self.pm.savepath}/{fname}', self.config['time_acquire'])
        print( f"Start acquiring for {self.config['time_acquire']} s")
        print( f"Saving to {self.device.acquire_file.name}")
        self.device.start_acquire()

    def close(self):
        self.device.close()