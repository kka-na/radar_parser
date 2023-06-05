'''
USAGE
python combined.py cpr_idx th1 th2 last_scan

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
HEADER
[0:2] Preamble
[2:4] Message Identifier
[4:8] Message Length
[8:10] Checksum
---
BODY
[10:18] Latitude
[18:26] Longitude
[26:30] Scan Index
[30:32] nRange Bin
[32:34] nACP
[34:42] StartRange
[42:50] EndRage	
[50:] AScopes

'''

import zlib
import numpy as np
import socket
import struct
import os
import sys
import imageio


dth1 = 72
dth2 = 52

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
os.makedirs(f'./{cpr_type[cpr_idx]}/{th1}_{th2}_{dth1-th1}_{dth2-th2}/', exist_ok=True)
folder = f'./{cpr_type[cpr_idx]}/{th1}_{th2}_{dth1-th1}_{dth2-th2}'
os.makedirs(f'{folder}/extracted', exist_ok=True)

ip = '127.0.0.1'
port = 9011

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.connect((ip, port))

buffer = b''
preamble_hex = b'\x5c\x24\x02\x00'

find = False
get_sucess = False
while True:
    data = socket.recv(1024)
    buffer += data
    if not find:
        preamble_idx = buffer.find(preamble_hex)
        if preamble_idx != -1 :
            cnt = 0
            find = True
    else:
        header = buffer[preamble_idx:preamble_idx+50]
        messageLength = struct.unpack('<I', header[4:8])[0]
        scanIndex = struct.unpack('<I', header[26:30])[0]

        if scanIndex > last_scan:
            print("Process Over")
            break

        if not get_sucess:
            radar_data = buffer[preamble_idx:preamble_idx+10+messageLength]
            if len(radar_data) < messageLength+10:
                continue
            else:
                get_sucess = True
        else:
            print(len(radar_data), messageLength)

            with open(f"{folder}/radar_{scanIndex}.txt", "wb") as file:
                file.write(radar_data)
            
            header = radar_data[:26]
            bScope_header = radar_data[26:50]
            compressed_aScope_data = radar_data[50:]
            preamble, messageIdentifier, messageLength, checkSum, latitude, longitude = struct.unpack('<HHIHdd', header)
            scanIndex, rangeBin, nACP, startRange, endRange = struct.unpack('<IHHdd', bScope_header)

            header_txt = f"{preamble}\n{messageIdentifier}\n{messageLength}\n{checkSum}\n{latitude}\n{longitude}\n{scanIndex}\n{rangeBin}\n{nACP}\n{startRange}\n{endRange}"
            with open(f"{folder}/extracted/{scanIndex}_header.txt", 'w') as file:
                file.write(header_txt)

            try:
                decompressed_aScope_data = zlib.decompress(compressed_aScope_data)
                bScope_mat = np.zeros((rangeBin, nACP))
                for i in range(0, len(decompressed_aScope_data), 2+rangeBin):
                    aScope = decompressed_aScope_data[i:i+2+rangeBin]
                    acp = int(struct.unpack('<H',aScope[:2])[0]/16)
                    adc = struct.unpack('B'*rangeBin, aScope[2:])
                    if acp < rangeBin:
                        bScope_mat[acp] = adc         

                np.savetxt(f'{folder}/extracted/{scanIndex}_bscope_mat.txt', bScope_mat, fmt='%d')
            except zlib.error as e:
                print(scanIndex, str(e))

            buffer = b''
            find = False
            get_sucess = False

socket.close()

