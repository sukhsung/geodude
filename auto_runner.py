import os, datetime
import json
import device
from crontab import CronTab


class path_manager():
    user = 'raspberry'
    prefix = '/media'
    def __init__(self, dev=False):
        if dev:
            self.prefix='./media'

        print( " ")
        print( datetime.datetime.now() )

        if self.load_config() == False:
            return

        self.prepare_path()

    def prepare_path( self ):
        print( "Prepping Folder Structure") 
        os.makedirs( f'{self.path}/results', exist_ok=True )


    def list_drives(self):
        try:
            dir_media = os.listdir(f'{self.prefix}/{self.user}')
            return dir_media
        except:
            return []
        
    def load_config(self):
        print( "Loading Configuration File")
        dir_media = self.list_drives()
    
        if len(dir_media) == 0:
            return False
        else:
            for dir in dir_media:
                if os.path.isfile( f'{self.prefix}/{self.user}/{dir}/config.json'):
                    self.path = f'{self.prefix}/{self.user}/{dir}'

                    file_config = open(f'{self.path}/config.json','r')
                    self.config = json.load( file_config )
                    return self.check_config()
            return False

    def print_config( self ):
        try:
            print(f"Sampling: {self.config['sampling']}")
            print(f"Found {len(self.config['ADC'])} ADC Settings")
            for adc in self.config['ADC']:
                print( f"Gain: {adc['gain']}, Polarity: {adc['polarity']}, Buffer: {adc['buffer']}")
            print(f"Acquisition Time (s): {self.config['time_acquire']}")
            print(f"Cron schedule: {self.config['schedule']}")
        except:
            print("!!!!! Something wrong with config")
        
        
    def check_config( self ):
        print("Checking Configuration File")
        try:
            _ = self.config['sampling']
        except:
            print("Invalid Sampling Configuration")
            return False
        
        try:
            _ = len(self.config['ADC'])
            for adc in self.config['ADC']:
                _ = adc['gain']
                _ = adc['polarity']
                _ = adc['buffer']
        except:
            print("Invalid ADC Configuration")
            return False
        
        try:
            _ = self.config['time_acquire']
        except:
            print("Invalid Acquisition Time")
            return False
        
        try:
            _ = self.config['schedule']
        except:
            print("Invalid cron schedule")
            return False
        
        return True
        


class governor():
    def __init__(self, dev=False):
        self.pm = path_manager(dev=dev)
        self.config = self.pm.config

        print( "Managing Crontab")
        self.cron = CronTab(user=True)
        self.set_crontab()

        print("All Set!")

    def set_crontab(self):
        self.cron.remove_all(comment='Geophone')
        self.cron.write()

        job = self.cron.new(command=f'/home/{self.pm.user}/env_geo/bin/python /home/{self.pm.user}/geodude/run_geodude.py>> {self.pm.path}/log.txt', comment='Geophone')
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
        folder = f'{now.year}-{now.month:02d}-{now.day:02d}'
        fname = f'{now.hour:02d}-{now.minute:02d}-{now.second:02d}.csv'
        self.savepath = f'{self.pm.path}/results/{folder}'

        os.makedirs( self.savepath, exist_ok=True )
        self.device.prepare_acquire( f'{self.savepath}/{fname}', self.config['time_acquire'])
        print( f"Start acquiring for {self.config['time_acquire']} s")
        print( f"Saving to {self.device.acquire_file.name}")
        self.device.start_acquire()

    def close(self):
        self.device.close()