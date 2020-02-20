from ipykernel.kernelbase import Kernel
import logging, sys, time, os, re
import serial, socket, serial.tools.list_ports, select
from upydevice import SERIAL_DEVICE, WS_DEVICE
from ipykernel.ipkernel import IPythonKernel
# from upydevice import uparser_dec
import argparse
import shlex
import glob
from binascii import hexlify
import json
from IPython.utils.tokenutil import token_at_cursor, line_at_cursor
try:
    from upydev import __path__ as DEVSPATH
except Exception as e:
    DEVSPATH = '.'

logger = logging.getLogger('micropython-upydevice')
logger.setLevel(logging.INFO)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('parso.python.diff').setLevel(logging.WARNING)
logging.getLogger('parso.cache').setLevel(logging.WARNING)

serialtimeout = 0.5
serialtimeoutcount = 10

# use of argparse for handling the %commands in the cells

ap_serialconnect = argparse.ArgumentParser(prog="%serialconnect", add_help=False)
ap_serialconnect.add_argument('portname', type=str, default=0, nargs="?")
ap_serialconnect.add_argument('baudrate', type=int, default=115200, nargs="?")
ap_serialconnect.add_argument("-kbi", default=False, help='KeyboardInterrupt on start', action='store_true')

# ap_socketconnect = argparse.ArgumentParser(prog="%socketconnect", add_help=False)
# ap_socketconnect.add_argument('--raw', help='Just open connection', action='store_true')
# ap_socketconnect.add_argument('ipnumber', type=str)
# ap_socketconnect.add_argument('portnumber', type=int)

ap_websocketconnect = argparse.ArgumentParser(prog="%websocketconnect", add_help=False)
ap_websocketconnect.add_argument('websocketurl', type=str, default="192.168.4.1", nargs="?")
ap_websocketconnect.add_argument("--password", type=str)
ap_websocketconnect.add_argument("-kbi", default=False, help='KeyboardInterrupt on start', action='store_true')
ap_websocketconnect.add_argument("-ssl", default=False, help='use WebSecureREPL if enabled', action='store_true')

ap_logdata = argparse.ArgumentParser(prog="%logdata", add_help=False)
ap_logdata.add_argument('v', type=str, nargs="+", help='Name of variables')
ap_logdata.add_argument("-fs", type=int, help='Sampling frequency in Hz')
ap_logdata.add_argument("-tm", type=int, help='Sampling timeout in ms')
ap_logdata.add_argument("-u", type=str, nargs="+", help='Unit of variables')
ap_logdata.add_argument("-s", default=False, help='Silent mode', action='store_true')

# ap_writebytes = argparse.ArgumentParser(prog="%writebytes", add_help=False)
# ap_writebytes.add_argument('-b', help='binary', action='store_true')
# ap_writebytes.add_argument('stringtosend', type=str)

# ap_sendtofile = argparse.ArgumentParser(prog="%sendtofile", description="send a file to the microcontroller's file system", add_help=False)
# ap_sendtofile.add_argument('-a', help='append', action='store_true')
# ap_sendtofile.add_argument('-b', help='binary', action='store_true')
# ap_sendtofile.add_argument('destinationfilename', type=str)
# ap_sendtofile.add_argument('--source', help="source file", type=str, default="<<cellcontents>>", nargs="?")


def parseap(ap, percentstringargs1):
    try:
        return ap.parse_known_args(percentstringargs1)[0]
    except SystemExit:  # argparse throws these because it assumes you only want to do the command line
        return None  # should be a default one


class MicroPythonKernel(IPythonKernel):
    implementation = 'micropython_kernel_upydevice'
    implementation_version = "v3"

    banner = "MicroPython upydevice Jupyter Kernel v0.0.3"

    language_info = {'name': 'python',
                     'codemirror_mode': 'python',
                     'mimetype': 'text/x-python',
                     'file_extension': '.py',
                     'pygments_lexer': 'python'}

    def __init__(self, **kwargs):
        # Kernel.__init__(self, **kwargs)
        super(MicroPythonKernel, self).__init__(**kwargs)
        self.silent = False
        self.dev = None
        self.dev_connected = False
        self.frozen_modules = {}
        self.global_execution_count = 0
        self.magic_kw = ['%disconnect', '%serialconnect', '%websocketconnect',
                         '%rebootdevice', '%is_reachable', '%lsmagic',
                         '%meminfo', '%whoami', '%gccollect', '%local',
                         '%sync', '%logdata', '%devplot']
        self.block_kw = ['if ', 'else:', 'def ', 'while ', 'for ', 'elif ', ':',
                         'try:', 'except ']

        self.datalog_args = None

        try:
            self.shell.user_global_ns['remote'] = self.remote
        except AttributeError:
            logger.exception("Could not set 'remote' in local environment")

    class LocalCell(Exception):
        """
        Raised when a %local cell is hit to tell kernel to forward to ipython
        """

    class syncLocalCell(Exception):
        """
        Raised when a %sync cell is hit to tell kernel to forward device output to ipython
        """

    class logdataLocalCell(Exception):
        """
        Raised when a %logdata cell is hit to tell kernel to forward device output data stream to ipython and store it in 'devlog'
        """

    class devplotLocalCell(Exception):
        """
        Raised when a %devplot cell is hit to tell kernel to plot devlog in ipython
        """

    def interpretpercentline(self, percentline, cellcontents):
        percentstringargs = shlex.split(percentline)
        percentcommand = percentstringargs[0]

        if percentcommand == ap_serialconnect.prog:
            apargs = parseap(ap_serialconnect, percentstringargs[1:])
            try:
                if apargs.kbi:
                    self.dev = SERIAL_DEVICE(apargs.portname, baudrate=apargs.baudrate)
                    self.dev._kbi_cmd()
                self.dev = SERIAL_DEVICE(apargs.portname, baudrate=apargs.baudrate, autodetect=True)
                if self.dev.is_reachable():
                    self.sres("\n ** Serial connected **\n\n", 32)
                    self.sres(str(self.dev.serial_port))
                    self.sres("\n")
                    self.dev.banner(pipe=self.sres)
                    # self.sres(self.dev.response)
                    self.dev.wr_cmd("help('modules')", silent=True, long_string=True)
                    self.frozen_modules['FM'] = self.dev.output.split()[:-6]
                    self.dev.wr_cmd("import os;import gc", silent=True)
                    # self.sres(str(self.frozen_modules['FM']))
                    self.dev_connected = True
                    logger.info("Device {} connected in {}".format(self.dev.dev_platform, self.dev.serial_port))
                else:
                    self.sres('Device is not reachable.', 31)
            except Exception as e:
                self.sres('Serial Port {} not availalbe'.format(apargs.portname), 31)
            return None

        # if percentcommand == ap_socketconnect.prog:
        #     apargs = parseap(ap_socketconnect, percentstringargs[1:])
        #     self.dc.socketconnect(apargs.ipnumber, apargs.portnumber)
        #     if self.dc.workingsocket:
        #         self.sres("\n ** Socket connected **\n\n", 32)
        #         self.sres(str(self.dc.workingsocket))
        #         self.sres("\n")
        #         #if not apargs.raw:
        #         #    self.dc.enterpastemode()
        #     return None

        if percentcommand == ap_websocketconnect.prog:
            apargs = parseap(ap_websocketconnect, percentstringargs[1:])

            # Catch entry point @
            if 'UPY_G.config' in os.listdir(DEVSPATH[0]) and "@" in apargs.websocketurl:
                with open(DEVSPATH[0]+'/UPY_G.config', 'r') as cfg_file:
                    ws_devs = json.loads(cfg_file.read())
                dev_cfg = ws_devs[apargs.websocketurl.replace("@", '')]
                apargs.websocketurl, apargs.password = dev_cfg

            self.dev = WS_DEVICE(apargs.websocketurl, apargs.password)
            if self.dev.is_reachable():
                self.dev.open_wconn(ssl=apargs.ssl, auth=True, capath=DEVSPATH[0])
                self.sres("\n ** WebREPL connected **\n", 32)
                if apargs.kbi:
                    self.dev.kbi(silent=True)
                    time.sleep(0.5)
                    self.dev.flush_conn()
                self.dev.banner(pipe=self.sres)
                # self.sres(self.dev.response)
                self.dev.wr_cmd("import sys; sys.platform", silent=True)
                self.dev.dev_platform = self.dev.output
                self.dev.name = '{}_{}'.format(self.dev.dev_platform, self.dev.ip.split('.')[-1])
                self.dev.wr_cmd("help('modules')", silent=True, long_string=True)
                self.frozen_modules['FM'] = self.dev.output.split()[:-6]
                self.dev.wr_cmd("import os;import gc", silent=True)
                # self.sres(str(self.frozen_modules['FM']))
                self.dev_connected = True
                logger.info("Device {} connected in {}:{}".format(self.dev.dev_platform, self.dev.ip, self.dev.port))
            else:
                self.sres('Device is not reachable.', 31)
            return None

        if percentcommand == "%lsmagic":
            self.sres("%disconnect\n    disconnects device\n\n")
            self.sres("%lsmagic\n    list magic commands\n\n")
            # self.sres("%readbytes\n    does serial.read_all()\n\n")
            self.sres("%rebootdevice\n    reboots device\n\n")
            self.sres("%is_reachable\n    Test if device is reachable (must be connected first)\n\n")
            # self.sres(re.sub("usage: ", "", ap_sendtofile.format_usage()))
            # self.sres("    send cell contents or file from disk to device file\n\n")
            self.sres(re.sub("usage: ", "", ap_serialconnect.format_usage()))
            self.sres("    connects to a device over USB, default baudrate is 115200\n\n")
            # self.sres(re.sub("usage: ", "", ap_socketconnect.format_usage()))
            # self.sres("    connects to a socket of a device over wifi\n\n")
            # self.sres("%suppressendcode\n    doesn't send x04 or wait to read after sending the cell\n")
            # self.sres("  (assists for debugging using %writebytes and %readbytes)\n\n")
            self.sres(re.sub("usage: ", "", ap_websocketconnect.format_usage()))
            self.sres("    connects to the WebREPL over wifi (WebREPL daemon must be running)\n")
            self.sres("    websocketurl defaults to 192.168.4.1 (uri -> ws://192.168.4.1:8266)\n\n")
            # self.sres(re.sub("usage: ", "", ap_writebytes.format_usage()))
            # self.sres("    does serial.write() of the python quoted string given\n\n")
            self.sres("%meminfo\n    Shows RAM size/used/free/use% info\n\n")
            self.sres("%whoami\n    Shows Device name, port, id, and system info\n\n")
            self.sres("%gccollect\n    To use the garbage collector and free some RAM if possible\n\n")
            self.sres("%local\n    To run the cell contents in local iPython\n\n")
            self.sres("%sync\n    To sync a variable/output data structure of the device into iPython \n    if no var name provided it stores the output into _\n\n")
            self.sres(re.sub("usage: ", "", ap_logdata.format_usage()))
            self.sres("    To log output data of the device into iPython, \n    data is stored in 'devlog'\n\n")
            self.sres("   {}\n   {}\n".format(ap_logdata.format_help().split('\n\n')[1].replace('\n', '\n    '),
                                         ap_logdata.format_help().split('\n\n')[2].replace('\n', '\n    ')))
            self.sres("%devplot\n    To plot devlog data\n\n")
            return None

        if percentcommand == "%disconnect":
            self.dev.close_wconn()
            self.sres('Device {} disconnected.'.format(self.dev.dev_platform), 31)
            self.dev_connected = False
            logger.info('Device {} disconnected.'.format(self.dev.dev_platform))
            return None

        if percentcommand == "%rebootdevice":
            # self.dev.close_wconn()
            self.sres("Rebooting device {}...\n".format(self.dev.dev_platform))
            self.dev.reset(silent=True)
            self.dev.wr_cmd("import os;import gc", silent=True)
            self.sres("Done!\n")
            return None

        if percentcommand == "%local":
            # self.dev.close_wconn()
            raise self.LocalCell

        if percentcommand == "%sync":
            # self.dev.close_wconn()
            raise self.syncLocalCell

        if percentcommand == ap_logdata.prog:
            # self.dev.close_wconn()
            apargs = parseap(ap_logdata, percentstringargs[1:])
            self.sres('vars:{}, fs:{} Hz, tm:{} ms, u: {}, silent: {}\n'.format(apargs.v, apargs.fs, apargs.tm, apargs.u, apargs.s))
            self.sres("{}\n".format('-'*30))
            self.datalog_args = {'vars': apargs.v, 'fs': apargs.fs,
                                 'tm': apargs.tm, 'u': apargs.u,
                                 'silent':apargs.s}
            raise self.logdataLocalCell
            # return None

        if percentcommand == "%devplot":
            # self.dev.close_wconn()
            raise self.devplotLocalCell

        if percentcommand == "%is_reachable":
            # self.dev.close_wconn()
            resp = self.dev.is_reachable()
            if resp:
                self.sres("Device is reachable!\n", 32)
            else:
                self.sres("Device is NOT reachable!\n", 31)
            return None

        if percentcommand == '%meminfo':
            RAM = self.send_custom_sh_cmd(
                'from micropython import mem_info;mem_info()', long_string=True)
            # self.sres(RAM)
            mem_info = RAM.splitlines()[1]
            mem = {elem.strip().split(':')[0]: int(elem.strip().split(':')[
                              1]) for elem in mem_info[4:].split(',')}
            self.sres("{0:12}{1:^12}{2:^12}{3:^12}{4:^12}\n".format(*['Memmory',
                                                                'Size', 'Used',
                                                                'Avail',
                                                                'Use%']))
            total_mem = mem['total']/1024
            used_mem = mem['used']/1024
            free_mem = mem['free']/1024
            total_mem_s = "{:.3f} KB".format(total_mem)
            used_mem_s = "{:.3f} KB".format(used_mem)
            free_mem_s = "{:.3f} KB".format(free_mem)

            self.sres('{0:12}{1:^12}{2:^12}{3:^12}{4:>8}\n'.format('RAM', total_mem_s,
                                                              used_mem_s, free_mem_s,
                                                              "{:.1f} %".format((used_mem/total_mem)*100)))
            return None
        if percentcommand == '%whoami':
            uid = self.send_custom_sh_cmd("from machine import unique_id; unique_id()")
            try:
                unique_id = hexlify(uid).decode()
            except Exception as e:
                unique_id = uid
            if self.dev.dev_class == 'SERIAL':
                self.sres('DEVICE: {}, SERIAL PORT: {} , BAUDRATE: {},  ID: {}\n'.format(self.dev.name, self.dev.serial_port, self.dev.baudrate, unique_id))
            else:
                self.sres('DEVICE: {}, IP: {} , PORT: {},  ID: {}\n'.format(self.dev.name, self.dev.ip, self.dev.port, unique_id))
            sysinfo = self.send_custom_sh_cmd('import os;os.uname()')
            dev_info = sysinfo.split("'")
            self.sres('SYSTEM NAME: {}\n'.format(dev_info[1]))
            self.sres('NODE NAME: {}\n'.format(dev_info[3]))
            self.sres('RELEASE: {}\n'.format(dev_info[5]))
            self.sres('VERSION: {}\n'.format(dev_info[7]))
            self.sres('MACHINE: {}\n'.format(dev_info[9]))
            return None

        if percentcommand == '%gccollect':
            self.dev.wr_cmd("import gc;gc.collect()")

            return None
        self.sres("Unrecognized percentline {}\n".format([percentline]), 31)
        return cellcontents

    def send_custom_sh_cmd(self, cmd, long_string=False):
        self.dev.wr_cmd(cmd, silent=True, long_string=long_string)
        if self.dev.output is None or self.dev.output == '':
            return self.dev.response
        else:
            return self.dev.output

    def remote(self, command):
        self.dev.wr_cmd(command, silent=True)
        output = "[{}]:{}\n".format(self.dev.dev_platform, self.dev.output)
        self.sres(output)

    def runnormalcell(self, cellcontents, bsuppressendcode):
        block = False
        indexline = 0
        if any([kw in cellcontents for kw in self.block_kw]):
            if self.dev.dev_class == 'SERIAL':

                self.dev.paste_buff(cellcontents)
                cmdlines = True
            else:

                self.dev.paste_buff(cellcontents)
                cmdlines = True

            block = True
        else:
            cmdlines = cellcontents.splitlines(True)

        if not block:
            if len(cmdlines) == 1:
                for line in cmdlines:
                    if line:
                        indexline += 1
                        if line[-2:] == '\r\n':
                            line = line[:-2]
                        elif line[-1] == '\n':
                            line = line[:-1]
                        self.dev.wr_cmd(line, follow=True, pipe=self.sres)
            elif len(cmdlines) > 1:
                cmd_chain = '\n'.join(cmdlines)
                self.dev.paste_buff(cmd_chain)
                self.dev.wr_cmd('\x04', follow=True, pipe=self.sres, multiline=True)
        else:
            if cmdlines:

                self.dev.wr_cmd('\x04', follow=True, pipe=self.sres, multiline=True)

    def sendcommand(self, cellcontents):
        bsuppressendcode = False  # can't yet see how to get this signal through

        # extract any %-commands we have here at the start (or ending?)
        mpercentline = re.match("\s*(%.*)", cellcontents)
        if mpercentline:
            cellcontents = self.interpretpercentline(mpercentline.group(1), cellcontents)
            if cellcontents is None:
                return

        if not self.dev_connected:
            self.sres("No device connected\n", 31)
            self.sres("  %serialconnect or websocketconnect to connect\n")
            self.sres("  %lsmagic to list commands")
            return

        # run the cell contents as normal
        else:
            if cellcontents:
                try:
                    self.runnormalcell(cellcontents, bsuppressendcode)
                except Exception as e:
                    raise e

    # 1=bold, 31=red, 32=green, 34=blue; from http://ascii-table.com/ansi-escape-sequences.php
    def sres(self, output, asciigraphicscode=None, std="stdout", execute_prompt=False):
        if not self.silent:
            if asciigraphicscode:
                output = "\x1b[{}m{}\x1b[0m".format(asciigraphicscode, output)
            if not execute_prompt:
                stream_content = {'name': std, 'text': output}
                self.send_response(self.iopub_socket, 'stream', stream_content)
            else:
                output_content = {'execution_count':self.global_execution_count, 'data': {"text/plain": output}, 'metadata' : {}}
                self.send_response(self.iopub_socket, 'execute_result', output_content)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        self.silent = silent
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.shell.execution_count, 'payload': [], 'user_expressions': {}}

        interrupted = False
        self.global_execution_count += 1
        try:
            if not interrupted:
                self.sendcommand(code)
                self.shell.execution_count += 1
                # res = self.shell.run_cell("['dev']", store_history=False, silent=silent)
                # logger.info(res)
        except KeyboardInterrupt:
            interrupted = True
        except self.LocalCell:
            # Run local cell in regular ipython kernel
            code = code.replace('%local', '')
            return super(MicroPythonKernel, self).do_execute(code=code, silent=silent,
                                                             store_history=store_history,
                                                             user_expressions=user_expressions,
                                                             allow_stdin=allow_stdin)
        except self.syncLocalCell:
            code = code.replace('%sync\n', '')
            code = code.replace('%sync ', '')
            self.dev.wr_cmd(code, silent=True)
            if '=' not in code:
                var = '_'
                self.sres(self.dev.response, execute_prompt=True)
            else:
                var = code.split('=')[0]
                self.dev.wr_cmd(var, silent=True)
            if isinstance(self.dev.output, str):
                code = '{} = "{}"'.format(var, self.dev.output)
            else:
                code = '{} = {}'.format(var, self.dev.output)
            return super(MicroPythonKernel, self).do_execute(code=code, silent=silent,
                                                             store_history=store_history,
                                                             user_expressions=user_expressions,
                                                             allow_stdin=allow_stdin)

        except self.logdataLocalCell:
            code = '\n'.join(code.split('\n')[1:])
            # self.dev.wr_cmd(code, silent=True)
            self.dev.paste_buff(code)
            if not self.datalog_args['silent']:
                self.dev.wr_cmd('\x04', follow=True, pipe=self.sres, multiline=True, dlog=True)
                # self.dev.wr_cmd('\x04', silent=True, follow=True, pipe=None, multiline=True, dlog=True)
            else:
                # self.sres("{}\n".format(self.datalog_args['silent']))
                self.dev.wr_cmd('\x04', silent=True, follow=True, pipe=None, multiline=True, dlog=True)
            self.dev.get_datalog(dvars=self.datalog_args['vars'], fs=self.datalog_args['fs'],
                                 time_out=self.datalog_args['tm'], units=self.datalog_args['u'])

            code = '{} = {}'.format('devlog', self.dev.datalog)
            return super(MicroPythonKernel, self).do_execute(code=code, silent=silent,
                                                             store_history=store_history,
                                                             user_expressions=user_expressions,
                                                             allow_stdin=allow_stdin)

        except self.devplotLocalCell:
            if self.dev.datalog is not None and self.dev.datalog != []:
                importmatplotlib = "import matplotlib.pyplot as plt"
                code = """
                fig, ax1 = plt.subplots(figsize=(10, 4), dpi=128)
                plt.grid(which='minor', linestyle='dotted')
                ax1.grid(linestyle='dotted')
                ax1.set_xlabel('Time(s)')
                ax1.set_ylabel(devlog['u'])
                for key in devlog['vars']:
                    plt.plot(devlog['ts'], devlog[key],linewidth=1, label=key)
                    plt.legend(loc=1)
                plt.show()"""
                show_plot = super(MicroPythonKernel, self).do_execute(code=importmatplotlib, silent=silent,
                                                                 store_history=store_history,
                                                                 user_expressions=user_expressions,
                                                                 allow_stdin=allow_stdin)
                return super(MicroPythonKernel, self).do_execute(code=code, silent=silent,
                                                                 store_history=store_history,
                                                                 user_expressions=user_expressions,
                                                                 allow_stdin=allow_stdin)
        except Exception as e:
            self.sres("\n\n*** OSError *** \n")
            self.sres("\n\n {} \n".format(str(e)))
            self.sres("\n\n*** Connection broken ***\n", 31)
            self.sres("You may need to reconnect")

        if interrupted:
            self.sres("\n\n*** Sending Ctrl-C\n\n")
            if self.dev_connected:
                self.dev.close_wconn()
                self.dev.kbi()
                self.dev.open_wconn()
                interrupted = True
                # self.dc.receivestream(bseekokay=False, b5secondtimeout=True)
            return {'status': 'abort', 'execution_count': self.global_execution_count}

        # everything already gone out with send_response(), but could detect errors (text between the two \x04s
        outp =  [{"data": {"text/plain": ["[1, 2, 3]"]},"execution_count": 6, "metadata": {},"output_type": "execute_result"}]
        return {'status': 'ok', 'execution_count': self.global_execution_count, 'payload': [], 'user_expressions': {}}

    def do_complete(self, code, cursor_pos):
        """Override in subclasses to find completions.
        """
        glb = False
        import_cmd = False
        buff_text_frst_cmd = code.split(' ')[0]
        if buff_text_frst_cmd.startswith('%') and '%sync' not in buff_text_frst_cmd:  # magic keyword
            if cursor_pos is None:
                cursor_pos = len(code)
            # line, offset = line_at_cursor(code, cursor_pos)
            # line_cursor = cursor_pos - offset
            result = [
                val for val in self.magic_kw if val.startswith(buff_text_frst_cmd)]
            if buff_text_frst_cmd == '%serialconnect':
                ls_cmd_str = "/dev/tty.*"
                alt_port = "/dev/ttyUSB"
                result = glob.glob(ls_cmd_str)
                result += glob.glob(alt_port)
                buff_text_frst_cmd = code.split(' ')[1]

            if buff_text_frst_cmd == '%websocketconnect':
                result = []
                if 'UPY_G.config' in os.listdir(DEVSPATH[0]):
                    with open(DEVSPATH[0]+'/UPY_G.config', 'r') as cfg_file:
                        ws_devs = json.loads(cfg_file.read())
                    result = ["@{}".format(key) for key in ws_devs.keys()]
                    buff_text_frst_cmd = code.split(' ')[1]

            if buff_text_frst_cmd.startswith('%local'):
                # code = code.replace('%local\n', '')
                # cursor_pos = len(code)
                # return {'matches' : [code, cursor_pos],
                #         'cursor_end' : cursor_pos,
                #         'cursor_start' : cursor_pos - len(buff_text_frst_cmd),
                #         'metadata' : {},
                #         'status' : 'ok'}
                return super(MicroPythonKernel, self).do_complete(code=code,
                                                                  cursor_pos=cursor_pos)

            else:

                return {'matches' : result,
                        'cursor_end' : cursor_pos,
                        'cursor_start' : cursor_pos - len(buff_text_frst_cmd),
                        'metadata' : {},
                        'status' : 'ok'}

        else:
            try:
                # catch last line before cursor_pos
                code = code[:cursor_pos].splitlines()[-1]
                buff_text_frst_cmd = code.split(' ')[0]
                if buff_text_frst_cmd == 'import' or buff_text_frst_cmd == 'from':
                    import_cmd = True
                if ').' not in code:
                    buff_text = code.replace('=', ' ').replace('(', ' ').split(' ')[-1]
                else:
                    buff_text = code.replace('=', ' ').split(' ')[-1]
                if isinstance(buff_text, str):
                    if '.' in buff_text:

                        root_text = '.'.join(buff_text.split('.')[:-1])
                        rest = buff_text.split('.')[-1]
                        if rest != '':
                            self.dev.wr_cmd("[val for val in dir({}) if val.startswith('{}')]".format(root_text, rest), silent=True)
                            self.dev.flush_conn()

                        else:
                            try:
                                self.dev.wr_cmd('dir({});gc.collect()'.format(root_text),
                                                silent=True)
                                self.dev.flush_conn()
                            except KeyboardInterrupt:
                                time.sleep(0.2)
                                self.dev.kbi(silent=True)

                            self.dev.flush_conn()

                    else:
                        rest = ''
                        glb = True
                        cmd_ls_glb = 'dir()'
                        if buff_text != '':
                            cmd_ls_glb = "[val for val in dir() if val.startswith('{}')]".format(buff_text)
                        if import_cmd:
                            fbuff_text = code.split()
                            if 'import' in fbuff_text and 'from' in fbuff_text and len(fbuff_text) >= 3:
                                if fbuff_text[1] not in self.frozen_modules['FM']:
                                    if len(fbuff_text) == 3:
                                        cmd_ls_glb = "import {0};dir({0})".format(fbuff_text[1])
                                    if len(fbuff_text) == 4:
                                        cmd_ls_glb = "import {0};[val for val in dir({0}) if val.startswith('{1}')]".format(fbuff_text[1], fbuff_text[3])
                                else:
                                    if len(fbuff_text) == 3:
                                        cmd_ls_glb = "import {0};dir({0})".format(fbuff_text[1])
                                    if len(fbuff_text) == 4:
                                        cmd_ls_glb = "import {0};[val for val in dir({0}) if val.startswith('{1}')]".format(fbuff_text[1], fbuff_text[3])
                            else:
                                cmd_ls_glb = "[scp.split('.')[0] for scp in os.listdir()+os.listdir('./lib') if '.py' in scp]"
                                self.frozen_modules['SUB'] = self.frozen_modules['FM']
                                if buff_text != '':
                                    cmd_ls_glb = "[scp.split('.')[0] for scp in os.listdir()+os.listdir('./lib') if '.py' in scp and scp.startswith('{}')]".format(buff_text)
                                    self.frozen_modules['SUB'] = [mod for mod in self.frozen_modules['FM'] if mod.startswith(buff_text)]

                        try:
                            self.dev.wr_cmd(cmd_ls_glb+';gc.collect()',
                                            silent=True)
                            self.dev.flush_conn()
                        except KeyboardInterrupt:
                            time.sleep(0.2)
                            self.dev.kbi(silent=True)
                        self.dev.flush_conn()

                else:
                    root_text = buff_text.split('.')[0]
                    rest = buff_text.split('.')[1]
                    try:
                        self.dev.wr_cmd('dir({});gc.collect()'.format(root_text), silent=True)
                        self.dev.flush_conn()
                    except KeyboardInterrupt:
                        time.sleep(0.2)
                        self.dev.kbi(silent=True)
                    self.dev.flush_conn()
            except Exception as e:
                pass
            if glb:
                kw_line_buff = code.split()
                if len(kw_line_buff) > 0 and len(kw_line_buff) <= 2:
                    if 'import' == kw_line_buff[0] or 'from' == kw_line_buff[0]:
                        self.dev.output = self.dev.output + self.frozen_modules['SUB']
            txt = []
            if rest != '':  # print attributes
                result = [
                    val for val in self.dev.output if val.startswith(rest)]
                if len(result) > 1:
                    comm_part = os.path.commonprefix(result)
                    if comm_part == rest:
                        # txt = comm_part[len(rest):]
                        pass
                    else:
                        txt = comm_part[len(rest):]
                else:
                    try:
                        txt = result[0][len(rest):]
                    except Exception as e:
                        pass
            if glb:
                rest = buff_text

            if cursor_pos is None:
                cursor_pos = len(code)
            # line, offset = line_at_cursor(code, cursor_pos)
            # line_cursor = cursor_pos - offset
            try:
                if self.dev._traceback.decode() in self.dev.output:
                    self.dev.output = []
            except TypeError:
                self.dev.output = []

            offset = cursor_pos - len(rest)

            return {'matches' : self.dev.output,
                    'cursor_end' : cursor_pos,
                    'cursor_start' : offset,
                    'metadata' : {},
                    'status' : 'ok'}
