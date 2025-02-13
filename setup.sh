#!/home/raspberry/env_geo/bin/python
import auto_runner
g = auto_runner.governor()
g.start_acquire()
g.close()