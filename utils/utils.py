import subprocess

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
# UTILS - Wifi Devices (using airmon-ng)
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
def get_wifi_interfaces()->[str]:
    """
    uses airmon-ng to find wifi interfaces (name only)
    """
    devices=get_wifi_devices()
    return [d["Interface"] for d in devices]

def get_wifi_devices()->[dict]:
    """
    uses airmon-ng to find available devices (each device is a dict of info) for scan
    """
    # Run airmon
    p = subprocess.run(["sudo", "airmon-ng"], capture_output=True, text=True)    
    # Parse output
    return parse_airmon_ng_console_output(p.stdout)

def parse_airmon_ng_console_output(consoleOutput: str, skip=3, up_to_minus=2, separator="\t")->[dict]:
    """
    At time of writing (14/11/2023) airmon-ng output took the following schema:
    
    ''
    HEADERS
    ''
    [<Entries>]
    ''
    ''
    each <Entries> was PHY, Interface, '', Driver, Chipset, TAB separated when in normal mode
    the '' entry isnt present in monitor mode. This is handled
    
    This can be used to parse the console output
    """
    result=[]
    entries = consoleOutput.split("\n")[skip:-up_to_minus]
    for e in entries:
        vals=e.split(separator)
        if len(vals) == 4:
            result.append(
                {
                    "Phy":vals[0],
                    "Interface":vals[1],
                    "Driver":vals[2],
                    "Chipset":vals[3]
                }
            )
        elif len(vals) == 5 and vals[2] == '':
            result.append(
                {
                    "Phy":vals[0],
                    "Interface":vals[1],
                    "Driver":vals[3],
                    "Chipset":vals[4]
                }
            )
        else:
            raise "unexpected format in airmon-ng console output, check validation schema"
    return result