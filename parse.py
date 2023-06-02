'''
USAGE
python parse.py cpr_idx th1 th2 last_scan

message ARPA_ReportRadarProcessedData

struct T_ENET_HEADER
{
    USHORT usPreamble;				// Preamble : "$\" = 0x245C
    USHORT usMsgId;					// Message Identifier : 0x02
    UINT32 unMsgLen;				// Message Length : payload size
    USHORT usChecksum;				// Check Sum
};

struct T_ASCOPE
{
    USHORT usACP;					// 0 ~ 65535
    UCHAR ucADC[MAX_RANGE_BIN];		// 0 ~ 255
};

struct T_REPORT_RADAR_IMAGE
{
    DOUBLE dLat;					// 레이더 위도 (deg)
    DOUBLE dLon;					// 레이더 경도 (deg)
    UINT32 unScanIndex;				// Scan Index
    USHORT usRangeBin;				// No. of RangeBIN
    USHORT usACP;					// No. of ACP
    DOUBLE dStartRange;				// meter
    DOUBLE dEndRange;				// meter
    T_ASCOPE tAScopes[MAX_ACP_NUM];	// 영상정보
};

'''

import socket
import struct
import os
import sys

if len(sys.argv) < 5:
    print("USAGE$ python parse.py cpr_idx th1 th2 last_scan")
    sys.exit()
else:
    cpr_idx = int(sys.argv[1]) #0
    th1 = int(sys.argv[2]) #0
    th2 = int(sys.argv[3]) #0
    last_scan = int(sys.argv[4]) #50

cpr_type = ['BUD_20151201-130001-098D0C90', 'BUD_20151201-140001-098D0C90','BUD_20151201-150001-098D0C90',
            'ICN_BS-20111219-135958-002FFDF8','ICN_BS-20111219-143958-002FFAD0','ICN_BS-20111219-151503-06CB0228']

os.makedirs(f'./{cpr_type[cpr_idx]}', exist_ok=True)
os.makedirs(f'./{cpr_type[cpr_idx]}/{th1}_{th2}/', exist_ok=True)
folder = f'./{cpr_type[cpr_idx]}/{th1}_{th2}'

ip = '127.0.0.1'
port = 9011

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((ip, port))

buffer = b''
preamble_hex = b'\x5c\x24\x02\x00'
cnt = 0
while True:
    data = socket.recv(1024)
    buffer += data
    preamble_idx = buffer.find(preamble_hex)
    if preamble_idx != -1 :
        cnt = 0
        header = buffer[preamble_idx:preamble_idx+50]
        if len(header) < 50:
            data = socket.recv(50)
            buffer += data
            header = buffer[preamble_idx:preamble_idx+50]
        
        messageLength = struct.unpack('<I', header[4:8])[0]
        scanIndex = struct.unpack('<I', header[26:30])[0]
        if scanIndex > last_scan:
            print("Parsing Over")
            break
        data = socket.recv(messageLength+50)
        buffer += data
        radar_data = buffer[preamble_idx:preamble_idx+10+messageLength]
        buffer = b''
        with open(f"{folder}/radar_{scanIndex}.txt", "wb") as file:
            file.write(radar_data)
       
    else:
        cnt += 1
        if cnt >= 100000:
            break

socket.close()

