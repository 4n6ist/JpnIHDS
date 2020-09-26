#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import csv
from datetime import datetime, timedelta, timezone
from ctypes import *

class FHeader(LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ('modified_time', c_uint64),
        ('file_size', c_uint32),
        ('unknown1', c_uint32), # 1 or 2
        ('history_num', c_uint32),
        ('header_size', c_uint32),
        ('learn_num', c_uint32), 
        ('history_size', c_uint32)
    )

class RHeader(LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ('conv_time', c_uint64),
        ('record_size', c_uint16),
        ('header_size', c_uint16),
        ('unknown2', c_byte), # always 1
        ('conv_num', c_byte),
        ('unknown3', c_uint16) # history == 0, learn > 0
    )

class RBody(LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ('body_size', c_uint16),
        ('input_length', c_ubyte),
        ('conv_length', c_ubyte),
        ('unknown4', c_uint32)
    )

def print_fhdr_info(fhdr):
    timestamp_us = fhdr.modified_time/10.
    print("--File Header Information--")
    print("Timestamp(UTC): ", datetime(1601,1,1) + timedelta(microseconds=timestamp_us))
    print("FileSize: ", fhdr.file_size)
    print("Unknown1: ", fhdr.unknown1) 
    print("HistoryRecords: ", fhdr.record_num)
    print("HeaderSize: ", fhdr.header_size)
    print("LearnRecords: ", fhdr.learn_num)
    print("HistorySize: ", fhdr.history_size)
    print()

def print_rhdr_info(rhdr):
    print("--Record Header Information--")
    print("RecordSize: ", rhdr.record_size)
    print("HeaderSize: ", rhdr.header_size)
    print("Unknown2: ", rhdr.unknown2)
    print("ConvNum: ", rhdr.conv_num)
    print("Unknown3: ", rhdr.unknown3)
    print()

def print_rbody_info(rbody):
    print("--Record Body Information--")
    print("BodySize: ", rbody.body_size)
    print("InputLength: ", rbody.input_length)
    print("ConvLength: ", rbody.conv_length)
    print("Unknown4: ", rbody.unknown4)
    print()

def parse_record_body(input_file, rbody, inputlist, convlist, mergelist, unknown4list):
    unknown4list.append(str(rbody.unknown4))
    input_chars = input_file.read(rbody.input_length*2).decode('UTF-16LE')
    inputlist.append(input_chars)
    if rbody.conv_length > 0:
        conv_chars = input_file.read(rbody.conv_length*2).decode('UTF-16LE')
        convlist.append(conv_chars)
        mergelist.append(conv_chars)
    else:
        mergelist.append(input_chars)

def utc_to_jst(timestamp_utc):
#    timestamp_jst = timestamp_utc.astimezone(timezone(timedelta(hours=+9)))
    timestamp_jst = timestamp_utc + timedelta(hours=+9)
    converted_jst = datetime.strftime(timestamp_jst, '%Y-%m-%d %H:%M:%S.%f')
    return converted_jst

def parse_jpnihds(input_file, output, debug):       
    record_field = []
    num=0
    
    fhdr = FHeader()
    input_file.readinto(fhdr)
    if debug:
        print_fhdr_info(fhdr)

    cur_pos = fhdr.header_size
    while input_file.tell() < fhdr.file_size:
        input_file.seek(cur_pos)
        rhdr = RHeader()
        input_file.readinto(rhdr)

        timestamp_us = rhdr.conv_time/10.
        timestamp_utc = datetime(1601,1,1) + timedelta(microseconds=timestamp_us)
        tsstr_utc = datetime.strftime(timestamp_utc, '%Y-%m-%d %H:%M:%S.%f')
        tsstr_jst = utc_to_jst(timestamp_utc)
        
        if debug:
            print_rhdr_info(rhdr)

        inputlist, convlist, mergelist, unknown4list = [],[],[],[]

        input_file.seek(cur_pos+rhdr.header_size)
        rbody = RBody()
        
        input_file.readinto(rbody)
        if debug:
            print_rbody_info(rbody)            
        parse_record_body(input_file, rbody, inputlist, convlist, mergelist, unknown4list)

        for i in range(rhdr.conv_num-1):
            input_file.readinto(rbody)
            if debug:
                print_rbody_info(rbody)
            parse_record_body(input_file, rbody, inputlist, convlist, mergelist, unknown4list)

        input_str=" ".join(inputlist)
        conv_str=" ".join(convlist)
        merge_str="".join(mergelist)
        unknown4_str=" ".join(unknown4list)

        record_field.extend([cur_pos, num, tsstr_utc, tsstr_jst, input_str, conv_str, merge_str, rhdr.unknown2, rhdr.unknown3, unknown4_str])        
        csv.writer(output, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_ALL).writerow(record_field)
        record_field = []
        num += 1
        cur_pos += rhdr.record_size

def main():
    parser = argparse.ArgumentParser(description="JpnIHDS.dat parser")
    parser.add_argument("input", help="Input File - JpnIHDS.dat")
    parser.add_argument("-o", "--output", help="Output File (Default: stdout)")
    parser.add_argument("--debug", action="store_true", default=False, help="Debug Mode")
    args = parser.parse_args()
    if os.path.exists(os.path.abspath(args.input)):
        input_file = open(args.input, "rb")
    else:
        sys.exit("{0} does not exist.".format(args.input))        
    if args.output:
        tsv = open(args.output, "w", encoding='UTF-16')
    else:
        tsv = sys.stdout
    row = ["offset", "no.", "timestamp(utc)", "timestamp(jst)", "input", "converted", "merged", "unknown2", "unknown3", "unknown4"]
    csv.writer(tsv, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_ALL).writerow(row)
    parse_jpnihds(input_file, tsv, args.debug)

if __name__ == '__main__':
    main()
