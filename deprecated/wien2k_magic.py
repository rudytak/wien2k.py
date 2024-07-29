import os
from typing import Optional, Literal
import json
import atexit

USE_PROFILE: Literal["CMD", "Default"] = "CMD" # "Default" | "CMD"
class LocalState:
    settings_path: str
    backup_path: str
    def __init__(self, path: str):
        self.path = path
        self.settings_path = os.path.join(path, "settings.json")
        self.backup_path = os.path.join(path, "settings_backup.json")
        global CURRENT_STATE 
        CURRENT_STATE = self
    def has_backup(self) -> bool:
        return os.path.exists(self.backup_path)
    
    def has_settings(self) -> bool:
        return os.path.exists(self.settings_path)
    
    def backup(self) -> bool:
        if not self.has_settings():
            return False
        if self.has_backup():
            return False
        # Copy content of the settings file to the backup file
        with open(self.settings_path, "r") as settings_file:
            with open(self.backup_path, "w") as backup_file:
                backup_file.write(settings_file.read())
        return True
    def restore(self) -> bool:
        if not self.has_backup():
            return False
        # Copy content of the backup file to the settings file
        with open(self.backup_path, "r") as backup_file:
            with open(self.settings_path, "w") as settings_file:
                settings_file.write(backup_file.read())
        # Delete the backup file
        os.remove(self.backup_path)
        return True
    
    def get_settings_json(self) -> Optional[dict]:
        if not self.has_settings():
            return None
        with open(self.settings_path, "r") as file:
            return json.load(file)

    def save_json(self, data: dict) -> bool:
        with open(self.settings_path, "w") as file:
            json.dump(data, file, indent=4)
        return True

CURRENT_STATE: Optional[LocalState] = None

def fuck_with_profile(profile, font_size: int) -> None:
    if "font" in profile:
        profile["font"]["size"] = font_size
        profile["font"]["face"] = "Source Code Pro"
    else: 
        profile["font"] = {
            "size": font_size,
            "face": "Source Code Pro"
        }
    profile["colorScheme"] = "One Half Light"

def find_path() -> Optional[LocalState]:
    root = os.path.expandvars("%USERPROFILE%\\AppData\\Local\\Packages\\")
    terminals = list(filter(lambda dirname: "windowsterminal" in dirname.lower() ,os.listdir(root)))
    if len(terminals) == 0:
        print("ProFucker: Windows Terminal not found, cannot fuck with it.")
        return None
    if len(terminals) > 1:
        print("ProFucker: There is a non-1 number of Windows Terminal installations. I cannot determin with witch one I should fuck.")
        return None
    terminal_folder = os.path.join(root, terminals[0])
    local_state = os.path.join(terminal_folder, "LocalState")
    return LocalState(local_state)

def fuck_with_settings(state: LocalState, font_size: float = 25) -> bool:
    if not state.backup():
        print("ProFucker: The program encountred an error while trying to fuck with windows terminal. To prevent fucking it too hard, it will abort.")
        if state.has_backup() and state.has_settings():
            print("ProFucker: I found an active backup. I will load this backup and abort. Run this a second time to perform the fuckery.")
            state.restore()
            return False
        if state.has_backup():
            print("ProFucker: I found an active backup, but no settings. This is a very sus situation. I will load from this backup and abort, but if this happens often, consider inspecting, if you aren't fucking the Windows Terminal too hard.")
            state.restore()
            return False
    settings_json = state.get_settings_json()
    default_profile_id = get_id(settings_json)
    profiles = settings_json["profiles"]["list"]
    profiles_filtered = list(filter(lambda profile: profile["guid"] == default_profile_id, profiles))

    if len(profiles_filtered) == 0:
        print("ProFucker: I did not find the profile I was looking for. Loading backup and aborting. Your settings are fucked.")
        if state.restore():
            print("ProFucker: Backup successfuly loaded.")
        else: 
            print("ProFucker: Failed to load backup")
        
        return False
    if len(profiles_filtered) > 1:
        print("ProFucker: What the actual fuck. I guess you have multiple profiles with the same ID. I'm surprised the Windows Terminal app doesn't crash on you. Loading backup and aborting.") 
        if state.restore():
            print("ProFucker: Backup successfuly loaded.")
        else: 
            print("ProFucker: Failed to load backup")
        return False
    profile_index = find_index(profiles, profiles_filtered[0])
    profile = profiles[profile_index]

    fuck_with_profile(profile, font_size)

    settings_json["profiles"]["list"][profile_index] = profile
    if state.save_json(settings_json):
        print("ProFucker: Fuckery successful") 
        return True
    else:
        print("ProFucker: I cannot fuck. Aborting and loading backup.")
        if state.restore():
            print("ProFucker: Backup successfuly loaded.")
        else: 
            print("ProFucker: Failed to load backup")
        return False
def find_index(list_to_find: list, value) -> int:
    for [i, thing] in enumerate(list_to_find):
        if thing == value:
            return i
    return -1

def exit_handler():
    if CURRENT_STATE == None:
        print("ProFucker: Settings weren't fucked with. Leaving.")
    else:
        if CURRENT_STATE.has_backup():
            print("ProFucker: Settings were fucked with, loading backup...")
            if CURRENT_STATE.restore():
                print("ProFucker: Backup loaded.")
            else:
                print("ProFucker: Failed to load backup.")
        else:
            print("ProFucker: No backup found to load. Exiting.")


atexit.register(exit_handler)

def get_id(settings_json) -> str:
    if USE_PROFILE == "Default":
       return settings_json["defaultProfile"]
    if USE_PROFILE == "CMD":
        profiles = settings_json["profiles"]["list"]
        cmd_profiles = list(filter(lambda profile: "commandline" in profile and profile["commandline"] == "%SystemRoot%\\System32\\cmd.exe", profiles))
        return cmd_profiles[0]["guid"]
    
def main():
    path = find_path()
    print(f"ProFucker: Operating at: {path.path}")
    fuck_with_settings(path)