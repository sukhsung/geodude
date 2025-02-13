#!/home/raspberry/env_geo/bin/python
import auto_runner
g = auto_runner.geodude()
g.start_acquire()
g.close()