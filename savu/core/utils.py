# Copyright 2015 Diamond Light Source Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. module:: utils
   :platform: Unix
   :synopsis: Simple core utility methods.
.. moduleauthor:: Mark Basham <scientificsoftware@diamond.ac.uk>

"""

import logging
import logging.handlers as handlers
import itertools
from mpi4py import MPI


def logfunction(func):
    """ Decorator to add logging information around calls for use with . """
    def _wrapper(*args, **kwds):
        logging.info("Start::%s:%s",
                     func.__module__,
                     func.__name__)
        returnval = func(*args, **kwds)
        logging.info("Finish::%s:%s",
                     func.__module__,
                     func.__name__)
        return returnval
    return _wrapper


def logmethod(func):
    """ Decorator to add logging information around calls for use with . """
    def _wrapper(self, *args, **kwds):
        logging.info("Start::%s.%s:%s",
                     func.__module__,
                     self.__class__.__name__,
                     func.__name__)
        returnval = func(self, *args, **kwds)
        logging.info("Finish::%s.%s:%s",
                     func.__module__,
                     self.__class__.__name__,
                     func.__name__)
        return returnval
    return _wrapper


def docstring_parameter(*sub):
    """ Decorator to add strings to a doc string."""
    def dec(obj):
        obj.__doc__ = obj.__doc__.format(*sub)
        return obj
    return dec


def import_class(class_name):
    """ Import a class.

    :params: class name
    :returns: class instance
    :rtype: instance of class_name
    """
    name = class_name
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    temp = name.split('.')[-1]
    module2class = ''.join(x.capitalize() for x in temp.split('_'))
    return getattr(mod, module2class.split('.')[-1])


def add_base(this, base):
    """ Add a base class to a class.

    :params class this: a class instance
    :params class base: a class to add as a base class
    """
    cls = this.__class__
    namespace = this.__class__.__dict__.copy()
    this.__class__ = cls.__class__(cls.__name__, (cls, base), namespace)
    base().__init__()


def add_base_classes(this, bases):
    """ Add multiple base classes to a class.

    :params class this: a class instance.
    :params list(class) bases: a list of base classes
    """
    bases = bases if isinstance(bases, list) else [bases]
    for base in bases:
        add_base(this, base)


def get_available_gpus():
    try:
        import pynvml as pv
    except:
        logging.debug("pyNVML module not found")
        raise Exception("pyNVML module not found")
    pv.nvmlInit()
    count = int(pv.nvmlDeviceGetCount())
    return pv, count


USER_LOG_LEVEL = 100
USER_LOG_HANDLER = None


def user_message(message):
    logging.log(USER_LOG_LEVEL, message)
    if USER_LOG_HANDLER is not None:
        USER_LOG_HANDLER.flush()


def user_messages_from_all(header, message_list):
    comm = MPI.COMM_WORLD
    messages = comm.gather(message_list, root=0)
    if messages is None:
        return
    # flatten the list
    messages = list(itertools.chain(*messages))
    if comm.rank == 0:
        for message in set(messages):
            user_message("%s : %i processes report : %s" %
                         (header, messages.count(message), message))


def _output_summary(mpi_flag, plugin):
    if mpi_flag:
        user_messages_from_all(plugin.name, plugin.executive_summary())
    else:
        for message in plugin.executive_summary():
            user_message("%s - %s" % (plugin.name, message))


def add_user_log_level():
    logging.addLevelName(USER_LOG_LEVEL, "USER")


def add_user_log_handler(logger, user_log_path):
    fh = logging.FileHandler(user_log_path, mode='w')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    fh.setLevel(USER_LOG_LEVEL)
    logger.addHandler(fh)
    USER_LOG_HANDLER = fh
    user_message("User Log Started")
    user_message("User Log location is '%s'" % (user_log_path))


def add_syslog_log_handler(logger, syslog_address, syslog_port):
    syslog = handlers.SysLogHandler(address=(syslog_address, syslog_port))
    syslog.setFormatter(logging.Formatter('SAVU:%(message)s'))
    syslog.setLevel(logging.WARN)  # only log user log messages
    logger.addHandler(syslog)


def _get_log_level(options):
    """ Gets the right log level for the flags -v or -q
    """
    if ('verbose' in options) and options['verbose']:
        return logging.DEBUG
    if ('quiet' in options) and options['quiet']:
        return logging.WARN
    return logging.INFO


def _send_email(address):
    import smtplib
    from email.mime.text import MIMEText

    me = 'nicola.wadeson@diamond.ac.uk'
    you = address
    # Open a plain text file for reading.  For this example, assume that
    # the text file contains only ASCII characters.
#    fp = open(textfile, 'rb')
#    # Create a text/plain message
#    msg = MIMEText(fp.read())
#    fp.close()

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = 'Your Savu job has completed'
    msg['From'] = me
    msg['To'] = you
    
    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP('localhost')
    s.sendmail(me, [you], msg.as_string('write something here'))
    s.quit()


def _savu_encoder(data):
    return '#savu_encoded#' + str(data)


def _savu_decoder(data):
    if isinstance(data, str) and len(data.split('#savu_encoded#')) > 1:
        exec('data = ' + data.split('#savu_encoded#')[-1])
        return data
    return data
