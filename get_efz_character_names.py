from ctypes import *
from ctypes.wintypes import *
from subprocess import check_output

OpenProcess = windll.kernel32.OpenProcess
ReadProcessMemory = windll.kernel32.ReadProcessMemory
CloseHandle = windll.kernel32.CloseHandle

PROCESS_VM_READ = 0x0010
process_name = "EFZ.exe"

characters = [
        "RUMI",
        "AYU",
        "MAI",
        "MAKOTO",
        "AKANE",
        "MAYU",
        "CELLO",
        "MISAKI",
        "SHIORI",
        "SAYURI",
        "NEYU",
        "MIO",
        "DOPPEL",
        "KAORI",
        "IKUMI",
        "MISHIO",
        "AKIKO",
        "NAYU",
        "UNKNOWN",
        "KANNA",
        "KANO",
        "MINAGI",
        "NAYUKIa",
        "MISUZU",
        "MIZUKA",
        ]

def get_character_name(character_id):
    if character_id == 0xFF:
        return "RANDOM"
    else:
        try:
            return characters[character_id]
        except IndexError:
            return "INVALID ID"

def get_pid():
    
    l = check_output('tasklist /fi "Imagename eq EFZ.exe"').split()
    try:
        return int(l[14])
    except IndexError:
        print("Failed to find EFZ PID")
        return -1

pid = get_pid()
p1_character = 0x00
p2_character = 0x00

buffer = c_long()
buffer2 = create_string_buffer(2)

if (pid>0):
    processHandle = OpenProcess(PROCESS_VM_READ, False, pid)
    if ReadProcessMemory(processHandle, 0x790114, byref(buffer), 4, None):
        if ReadProcessMemory(processHandle, buffer.value + 0x53C, buffer2, 2, None):
            p1_character = ord(buffer2[0])
            p2_character = ord(buffer2[1])
        else:
            print("Failed to Read Process Memory")
        
    else:
        print("Failed to Read Process Memory")

    CloseHandle(processHandle)
    
    print(get_character_name(p1_character) + " VS " + get_character_name(p2_character))
