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

import time, os, re, string, random, json

class CMD_Window:
    def __init__(self):
        # Create the app window instance
        self.app = Application().start(
            r"c:\WINDOWS\System32\cmd.exe /k",
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

        # keeps tract of the current directory
        self.curr_dir = "./"
        self.associated_host = ""

    # ---------------- INPUT ----------------

    def type(self, text, wait_after=0.1, speed_multiplier=10, do_ENTER=True):
        self.bring_forward()
        # type the text
        self.handle.type_keys(text, with_spaces=True, pause=0.05 / speed_multiplier)
        if do_ENTER:
            self.handle.type_keys("{ENTER}", with_spaces=True)

        # add additional timeout for bad connections if the wait_after is not exactly 0
        if self.associated_host in SCP_Connection.pings and wait_after != 0:
            wait_after += SCP_Connection.pings[self.associated_host]
        time.sleep(wait_after)

    # ---------------- OUTPUT ----------------

    def read_output(self, line_count, order=-1):
        self.bring_forward()

        # save the temporary screenshot
        img = self.handle.capture_as_image()
        w, h = img.size
        img = img.crop((10, 70, w - 10, h - 10))

        # analyze
        pytesseract.tesseract_cmd = TESSERACT_PATH
        text = pytesseract.image_to_string(img)

        return lfilt(text.split("\n"), lambda l: l != "")[-line_count:][::order]

    # ---------------- NAVIGATION ----------------

    def bring_forward(self):
        self.app["PseudoConsoleWindow"].set_focus()

    def cd(self, path=None):
        # update the scp location and move in the console
        if path == None:
            self.curr_dir = "./"
            self.type(f"cd")
        else:
            self.curr_dir = os.path.normpath(os.path.join(self.curr_dir, path)).replace(
                "\\", "/"
            )
            self.type(f"cd {path}")

    def home(self):
        self.cd()

    def kill(self):
        # Doesn't clean up after itself
        self.type("%{F4}", do_ENTER=False)

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
            cmd_win.type(f"ping {cred['host1']} -l 32 -n {ping_count}")
            time.sleep(ping_count)
            times1 = lmap(
                lfilt(
                    lmap(
                        cmd_win.read_output(6 + ping_count),
                        lambda l: re.findall(r"time=(\d+)ms", l),
                    ),
                    lambda a: len(a) != 0,
                ),
                lambda val: float(val[0]) / 1000,
            )
            SCP_Connection.pings[cred["host1"]] = max(times1)

            # large payloads
            cmd_win.type(f"ping {cred['host1']} -l 1024 -n {ping_count}")
            time.sleep(ping_count)
            times2 = lmap(
                lfilt(
                    lmap(
                        cmd_win.read_output(6 + ping_count),
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
            cmd_win.type(
                f"ssh {cred['username1']}@{cred['host1']} -L {port}:{cred['host2']}:22",
                1,
            )
            cmd_win.type(cred['password1'])
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

    def connect(self):
        cred = self.credentials["ssh"]

        # connects to the first server via ssh
        self.cmd.type(
            f"ssh {cred['username1']}@{cred['host1']}",
            1,
        )
        self.cmd.type(f"{cred['password1']}", 1)

        # second ssh connection
        self.cmd.type(f"ssh {cred['username2']}@{cred['host2']}", 1)
        self.cmd.type(f"{cred['password2']}", 1)

        self.cmd.associated_host = cred["host1"]

    def disconnect(self):
        self.cmd.type("exit", 1)
        self.cmd.type("exit", 1)
