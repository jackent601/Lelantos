![Alt text](lelantos_base/static/lelantos_base/imgs/lelantos-about.png?raw=true "Title")

## Requirements

- python3 (most features compatible with lower versions but start-up script requires python3)

## Installation

- clone this repo and move into it

see _setup --help for all options.

### Kali

Kali OS supports wifiphisher and aircrack-ng meaning both plug-ins are installed during installation, as well as lelantos

```
source _setup --kali [--ec2, --start]
```

### Ubuntu

Ubuntu can be manually configured for wifiphisher however the wifiphisher project does not offer primary support for this distro. The start script will only install aircrack-ng during installation, as well as lelantos.

```
source _setup --ubuntu [--ec2, --start]
```
## Usage

```
./helpers/_createMockData
```
will create test data to play with in the UI

```
./helpers/_createGuestUser 
```
will create a fresh user to play with in the UI

```
./run
```
will start up the command and control server running on port 8000
Visit http://<IP>:8000/home/ and get hacking!
