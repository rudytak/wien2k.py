from wien2_helper import *

# GUI controls
import win32gui
from pywinauto.application import Application
from pywinauto.controls.hwndwrapper import HwndWrapper

# image processing
from pytesseract import pytesseract

# SCP
from paramiko import SSHClient
from scp import SCPClient

import time, os, re, string, random, json, asyncio, PIL.ImageOps
from queue import PriorityQueue

class CMD_input:
    def __init__(self, cmd_inst, action_type, wait_time=0.1, kwargs={}):
        self.cmd_inst = cmd_inst
        self.action_type = action_type
        self.wait_time = wait_time
        self.kwargs = kwargs

        self.on_finish_future = asyncio.get_event_loop().create_future()
        self.nbf = 0

    def __lt__(self, other):
        return self.nbf < other.nbf

    def assign_nbf(self, new_not_before):
        self.nbf = new_not_before

    handler_checking_timeout = 0.1
    handler_min_command_timeout = 0.1
    CMD_records = {}
    PriorityQ = PriorityQueue()

    @staticmethod
    def try_create_CMD_record(cmd):
        if cmd.uid not in CMD_input.CMD_records:
            CMD_input.CMD_records[cmd.uid] = {"last_command_finish_time": time.time()}

    @staticmethod
    def enqueue(input_obj):
        CMD_input.try_create_CMD_record(input_obj.cmd_inst)

        # get the soonest time when the command can run
        not_before = max(
            time.time(),
            CMD_input.CMD_records[input_obj.cmd_inst.uid]["last_command_finish_time"],
        )
        CMD_input.CMD_records[input_obj.cmd_inst.uid][
            "last_command_finish_time"
        ] = not_before + input_obj.wait_time
        
        # print("Q+", not_before)

        # add the record to the priority queue
        input_obj.assign_nbf(not_before)
        CMD_input.PriorityQ.put((not_before, input_obj))

        return input_obj.on_finish_future

    @staticmethod
    def dequeue():
        if CMD_input.PriorityQ.qsize() > 0:
            el = CMD_input.PriorityQ.get()
            # print("Q-", CMD_input.PriorityQ.qsize())
            return el[1]
        else:
            return None

    @staticmethod
    async def handler_loop():
        while True:
            entry = CMD_input.dequeue()
            if entry == None:
                await asyncio.sleep(CMD_input.handler_checking_timeout)
                continue

            time_to_wait = max(entry.nbf - time.time(), CMD_input.handler_min_command_timeout)
            await asyncio.sleep(time_to_wait)

            # execute the action
            await CMD_input.handle_input_action(entry)

    @staticmethod
    async def handle_input_action(input_obj):
        results = None
        if input_obj.action_type == "type":
            results = input_obj.cmd_inst._type(**input_obj.kwargs)
        elif input_obj.action_type == "read":
            results = input_obj.cmd_inst._read_output(**input_obj.kwargs)
        elif input_obj.action_type == "cd":
            results = input_obj.cmd_inst._cd(**input_obj.kwargs)

        await asyncio.sleep(input_obj.wait_time)
        
        asyncio.get_event_loop().call_soon_threadsafe(
            input_obj.on_finish_future.set_result,
            results
        )

# run the input handler loop
# asyncio.get_event_loop().run_in_executor(
#     None, lambda: asyncio.run(CMD_input.handler_loop())
# )

class CMD_Window:
    def __init__(self):
        # Create the app window instance
        self.app = Application().start(
            r"c:\WINDOWS\System32\cmd.exe /k",
            # r'wt new-tab --profile "wien2k_readable" /k',
            create_new_console=True,
            wait_for_idle=False,
        )

        # get the CMD top window and wait for it to load
        self.app.top_window().wait(wait_for="ready")

        # get the topmost window - this is later used to send kyestrokes!!
        self.uid = win32gui.GetForegroundWindow()
        self.handle = HwndWrapper(self.uid)

        # force the thing to maximize
        time.sleep(0.6)
        self.handle.maximize()
        time.sleep(0.2)
        self.handle.maximize()
        time.sleep(0.2)
        
        # self._type("powershell")
        # self._type("wt new-tab --profile \"wien2k_readable\"\n")
        
        # keeps tract of the current directory
        self.curr_dir = "./"
        self.associated_host = ""

    # ---------------- INPUT ----------------

    def type(
        self, text, wait_after=1.5, speed_multiplier=10, do_ENTER=True
    ) -> asyncio.Future:
        return CMD_input.enqueue(
            CMD_input(
                self,
                "type",
                wait_after,
                {
                    "text": text,
                    "wait_after": 0,
                    "speed_multiplier": speed_multiplier,
                    "do_ENTER": do_ENTER,
                },
            )
        )

    def _type(self, text, wait_after=0.1, speed_multiplier=10, do_ENTER=True):
        self.bring_forward()
        time.sleep(0.05)
        
        # type the text
        self.handle.type_keys(text, with_spaces=True, pause=0.05 / speed_multiplier)
        if do_ENTER:
            self.handle.type_keys("{ENTER}", with_spaces=True)

        # TODO: remove or re-implement this
        # # add additional timeout for bad connections if the wait_after is not exactly 0
        # if self.associated_host in SCP_Connection.pings and wait_after != 0:
        #     wait_after += SCP_Connection.pings[self.associated_host]
        
        time.sleep(wait_after)

        return text

    # ---------------- OUTPUT ----------------

    def read_output(self, line_count, order=-1) -> asyncio.Future:
        return CMD_input.enqueue(
            CMD_input(self, "read", 1, {"line_count": line_count, "order": order})
        )

    def _read_output(self, line_count, order=-1):
        self.bring_forward()
        time.sleep(0.05)

        # save the temporary screenshot
        img = self.handle.capture_as_image()
        w, h = img.size
        img = img.crop((10, 70, w - 10, h - 10))
        #invert img to help tesseract
        img = PIL.ImageOps.invert(img)

        # analyze
        pytesseract.tesseract_cmd = TESSERACT_PATH
        text = pytesseract.image_to_string(img)

        time.sleep(0.05)

        return lfilt(text.split("\n"), lambda l: l != "")[-line_count:][::order]

    # ---------------- NAVIGATION ----------------

    def bring_forward(self):
        self.app["PseudoConsoleWindow"].set_focus()

    def cd(self, path=None) -> asyncio.Future:
        return CMD_input.enqueue(
            CMD_input(
                self,
                "cd",
                0.1,
                {
                    "path": path
                }
            )
        )

    def _cd(self, path=None):
        # update the scp location and move in the console
        if path == None:
            self.curr_dir = "./"
            self._type(f"cd")
        else:
            self.curr_dir = os.path.normpath(os.path.join(self.curr_dir, path)).replace(
                "\\", "/"
            )
            self._type(f"cd {path}")

    def home(self) -> asyncio.Future:
        return self.cd()

    def kill(self) -> asyncio.Future:
        # Doesn't clean up after itself
        return self.type("%{F4}", do_ENTER=False)


class SCP_Connection:
    def __init__(self, cmd: CMD_Window, credentials_json_path: string):
        self.cmd = cmd

        # handle connection credentails
        self.credentials_path = credentials_json_path
        with open(self.credentials_path) as json_reader:
            self.credentials = json.load(json_reader)

    ports = {}
    pings = {}  # baseline s
    ping_growth = {}  # s per byte
    windows = {}

    @staticmethod
    def get_host_twohop_port(cred, ping_count=4):
        """Gets the port number designated to a specific host"""

        # if there is no port assigned to this host, we have to create a new server proxy
        if not cred["host1"] in SCP_Connection.ports:
            # choose a random port from a range that has not been chosen yet
            # TODO: fix "unknown host problem on ports other than 2222"
            port = 2222
            while port in SCP_Connection.ports.values():
                port = random.randint(2222, 9999)

            # save the port so that it's know that this proxy is already running
            SCP_Connection.ports[cred["host1"]] = port

            # create a new cmd window and run the proxy using it
            # connects to ssh and at the same time creates a proxy server on localhost that poinst to this, so that the SCP command can be used on two-hop ssh connections
            cmd_win = CMD_Window()

            # assess ssh speed
            # small payloads
            cmd_win._type(f"ping {cred['host1']} -l 32 -n {ping_count}")
            time.sleep(ping_count)
            times1 = lmap(
                lfilt(
                    lmap(
                        cmd_win._read_output(6 + ping_count),
                        lambda l: re.findall(r"time=(\d+)ms", l),
                    ),
                    lambda a: len(a) != 0,
                ),
                lambda val: float(val[0]) / 1000,
            )
            SCP_Connection.pings[cred["host1"]] = max(times1)

            # large payloads
            cmd_win._type(f"ping {cred['host1']} -l 1024 -n {ping_count}")
            time.sleep(ping_count)
            times2 = lmap(
                lfilt(
                    lmap(
                        cmd_win._read_output(6 + ping_count),
                        lambda l: re.findall(r"time=(\d+)ms", l),
                    ),
                    lambda a: len(a) != 0,
                ),
                lambda val: float(val[0]) / 1000,
            )
            SCP_Connection.ping_growth[cred["host1"]] = abs(
                sum(times2) / len(times2) - sum(times1) / len(times1)
            ) / (1024 - 32)

            # create the proxy
            cmd_win._type(
                f"ssh {cred['username1']}@{cred['host1']} -L {port}:{cred['host2']}:22",
                1,
            )
            cmd_win._type(
                f"{cred['password1']}",
                0.5,
            )

            cmd_win.handle.minimize()
            SCP_Connection.windows[cred["host1"]] = cmd_win

        # return the port of the running proxy
        return SCP_Connection.ports[cred["host1"]]

    def connect_twohop(self):
        # get the ssh credentials
        cred = self.credentials["ssh"]

        # make sure that there is a proxy tow-hop server running
        port = SCP_Connection.get_host_twohop_port(cred)

        # create ssh connection
        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        # connect it
        self.ssh_client.connect(
            "localhost",
            username=cred["username2"],
            port=str(port),
            password=cred["password2"],
            look_for_keys=False,
        )

        # create a scp client
        self.scp_client = SCPClient(self.ssh_client.get_transport())

    def disconnect(self):
        # close the secondary ssh connection
        self.ssh_client.close()

    # ---------------- INPUT ----------------

    def upload_file(self, src_filepath, destination_filename):
        """Copies a local file saves the copy in the current server directory.
        If the uploaded file already exists, it's contents will be overwritten."""

        # first create a temporary copy of this file with LF endings and send that
        with open(src_filepath, "rb") as open_file:
            content = open_file.read()

        # replace line endings
        # Windows ➡ Unix
        content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)

        tmp_path = f"LF_tmp_{rng_string(32)}"
        with open(tmp_path, "wb") as open_file:
            open_file.write(content)

        # send the LF compatible copy
        self.scp_client.put(
            tmp_path,
            os.path.join(self.cmd.curr_dir, destination_filename).replace("\\", "/"),
        )
        time.sleep(0.2)

        # remove the temp file
        os.remove(tmp_path)

    # ---------------- OUTPUT ----------------

    def download_file(self, src_filename, receive_filepath):
        """Copies a file that is in the current server directory and saves it locally.
        If the local file already exists, it's contents will be overwritten."""

        tmp_path = f"LF_tmp_{rng_string(32)}"

        # first copy the file from the server with LF endings
        self.scp_client.get(
            os.path.join(self.cmd.curr_dir, src_filename).replace("\\", "/"),
            tmp_path,
        )

        # open the temporary file
        with open(tmp_path, "rb") as open_file:
            content = open_file.read()

        # replace line endings
        # Windows ➡ Unix
        content = content.replace(UNIX_LINE_ENDING, WINDOWS_LINE_ENDING)

        # save the CRLF content
        with open(receive_filepath, "wb") as open_file:
            open_file.write(content)

        # remove the temp file
        os.remove(tmp_path)


class dSSH_Connection:
    def __init__(self, cmd: CMD_Window, credentials_json_path: string):
        self.cmd = cmd

        # handle connection credentails
        self.credentials_path = credentials_json_path
        with open(self.credentials_path) as json_reader:
            self.credentials = json.load(json_reader)

    def connect(self) -> asyncio.Future:
        cred = self.credentials["ssh"]

        # connects to the first server via ssh
        self.cmd.type(
            f"ssh {cred['username1']}@{cred['host1']}",
            1,
        )
        self.cmd.type(f"{cred['password1']}", 1)

        # second ssh connection
        self.cmd.associated_host = cred["host1"]
        self.cmd.type(f"ssh {cred['username2']}@{cred['host2']}", 1)
        return self.cmd.type(f"{cred['password2']}", 1)

    def disconnect(self) -> asyncio.Future:
        self.cmd.type("exit", 1)
        return self.cmd.type("exit", 1)
