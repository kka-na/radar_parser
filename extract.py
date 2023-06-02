'''
USAGE
python ectract.py cpr_idx th1 th2 last_scan

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


import zlib
import numpy as np
import struct
import os
import sys
import imageio

if len(sys.argv) < 5:
    print("USAGE$ python extract.py cpr_idx th1 th2 last_scan")
    sys.exit()
else:
    cpr_idx = int(sys.argv[1]) #0
    th1 = int(sys.argv[2]) #0
    th2 = int(sys.argv[3]) #0
    last_scan = int(sys.argv[4])

cpr_type = ['BUD_20151201-130001-098D0C90', 'BUD_20151201-140001-098D0C90','BUD_20151201-150001-098D0C90',
            'ICN_BS-20111219-135958-002FFDF8','ICN_BS-20111219-143958-002FFAD0','ICN_BS-20111219-151503-06CB0228']

folder = f'./{cpr_type[cpr_idx]}/{th1}_{th2}'
os.makedirs(f'{folder}/extracted', exist_ok=True)

for i in range(1, last_scan+1):
    with open(f"{folder}/radar_{i}.txt", "rb") as file:
        radar_data = file.read()

    header = radar_data[:26]
    bScope_header = radar_data[26:50]
    compressed_aScope_data = radar_data[50:]
    preamble, messageIdentifier, messageLength, checkSum, latitude, longitude = struct.unpack('<HHIHdd', header)
    print(preamble, messageIdentifier, messageLength, checkSum)
    print(latitude, longitude)

    scanIndex, rangeBin, nACP, startRange, endRange = struct.unpack('<IHHdd', bScope_header)
    print(scanIndex, rangeBin, nACP, startRange, endRange)

    header_txt = f"{preamble}\n{messageIdentifier}\n{messageLength}\n{checkSum}\n{latitude}\n{longitude}\n{scanIndex}\n{rangeBin}\n{nACP}\n{startRange}\n{endRange}"
    with open(f"{folder}/extracted/{i}_header.txt", 'w') as file:
        file.write(header_txt)

    with open(f"{folder}/extracted/{i}_bscope.zip", "wb") as file:
        file.write(compressed_aScope_data)

    try:
        decompressed_aScope_data = zlib.decompress(compressed_aScope_data)
    except zlib.error as e:
        print(str(e))

    bScope_mat = np.zeros((rangeBin, nACP))
    for i in range(0, len(decompressed_aScope_data), 2+rangeBin):
        aScope = decompressed_aScope_data[i:i+2+rangeBin]
        acp = int(struct.unpack('<H',aScope[:2])[0]/16)
        adc = struct.unpack('B'*rangeBin, aScope[2:])
        if acp < rangeBin:
            bScope_mat[acp] = adc         

    np.savetxt(f'{folder}/extracted/{scanIndex}_bscope_mat.txt', bScope_mat, fmt='%d')
    bScope_mat_int = bScope_mat.astype(np.uint8)
    imageio.imwrite(f'{folder}/extracted/{scanIndex}_bscope_img.jpg', bScope_mat_int)