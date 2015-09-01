from pybuilder.core import use_plugin, init

use_plugin("python.core")
#use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.pychecker")
use_plugin("python.frosted")
#use_plugin("python.pytddmon")
#use_plugin("python.coverage")
use_plugin("python.distutils")


name = "watchdog"
default_task = "publish"


@init
def initialize(project):
    pass
