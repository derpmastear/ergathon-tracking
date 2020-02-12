import os
from time import sleep

import requests
from ctypes import *

SERVER = "https://ergathontracker.sites.tjhsst.edu/"
DLL_NAME = "erg.dll"
DLL = None


def load_dll(interface_path=""):
    global DLL
    if len(interface_path) == 0:
        interface_path = os.path.dirname(os.path.abspath(__file__))
    DLL = WinDLL(interface_path + "\\" + DLL_NAME)  # Load DLL from same folder
    print("Loaded interface DLL from {}".format(interface_path + "\\" + DLL_NAME))
    start_error = DLL.Init()  # Init the interface and count ergs
    if start_error != 0:
        print("Error on DLL startup:", start_error)
    print("Initialized DLL.")


class Erg:

    def __init__(self, serial, port):
        self.serial = serial
        self.port = port
        self.distance = 0

    def update(self):
        self.distance = DLL.GetDistance(self.port)
        return self.distance


class Tracker:

    def __init__(self, node_id, node_name=None):

        self.node_id = node_id
        if node_name is None or len(node_name) == 0:
            self.node_name = str(node_id)  # If no node name is given, default to the ID
        else:
            self.node_name = node_name

        erg_count = DLL.GetNumDevices2()

        self.ergs = list()
        DLL.GetSerialNumber.restype = c_char_p  # Declare a string return type
        serials = set()
        for port in range(erg_count):
            serial = DLL.GetSerialNumber(port).decode("utf-8")
            if serial in serials:
                print("ERROR: Repeated serial!")
            serials.add(serial)
            self.ergs.append(Erg(serial, port))
            print("Discovered erg {}".format(serial))
        print("Discovered {} erg(s)".format(erg_count))

    def update_ergs(self):
        for erg in self.ergs:
            x = erg.update()
            print(x)
        self.send_distances()

    def send_info(self):
        response = requests.post(SERVER + "nodes/", json={
            "name": self.node_name,
            "id": self.node_id
        })
        if response.status_code == 200:
            print("Updated server's node registry.")
        else:
            print("ERROR:", response.status_code, response.reason, "in sending node data.")

    def send_distances(self):
        data = list()
        for index, erg in enumerate(self.ergs):
            data.append({
                "distance": erg.distance,
                "serial": erg.serial,
                "node": self.node_id,
                "subnode": erg.port,
            })
        response = requests.put(SERVER + "ergs/", json=data)
        if response.status_code != 200:
            print("Error in sending:", response)


def get_node_name(node_id):
    response = requests.get(SERVER + "nodes/" + str(node_id))
    if response.status_code == 200 and len(response.text)>0:
        return response.text
    else:
        return None


def main():
    load_dll(input("Enter interface directory (blank for this one): "))
    tracker_id = int(input("Enter tracker ID: "))
    old_name = get_node_name(tracker_id)
    if old_name is None:
        old_name = str(tracker_id)
        name = input("Enter tracker name (blank to use id): ".format(old_name))
    else:
        print("Name found on server:", old_name)
        name = input("Enter tracker name (blank to continue using \"{}\"): ".format(old_name))
    if len(name) == 0:
        name = old_name
    tracker = Tracker(tracker_id, name)
    tracker.send_info()
    input("Ready! (Enter to begin)")
    while True:
        sleep(1)
        tracker.update_ergs()


if __name__ == "__main__":
    main()
