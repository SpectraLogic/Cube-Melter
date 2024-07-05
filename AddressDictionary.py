from enum import Enum


class AddressDictionary(Enum):
    # PMM
    PMM = 0x78

    # DBA 1
    DBA1_DPM0 = 0x00
    DBA1_DPM1 = 0x01
    DBA1_DPM2 = 0x02
    DBA1_DPM3 = 0x03
    DBA1_DPM4 = 0x04
    DBA1_DPM5 = 0x05
    DBA1_DPM6 = 0x06
    DBA1_DPM7 = 0x07

    DBA1_DTL0 = 0x80
    DBA1_DTL1 = 0x81
    DBA1_DTL2 = 0x82
    DBA1_DTL3 = 0x83
    DBA1_DTL4 = 0x84
    DBA1_DTL5 = 0x85
    DBA1_DTL6 = 0x86
    DBA1_DTL7 = 0x87

    # DBA 2
    DBA2_DPM0 = 0x10
    DBA2_DPM1 = 0x11
    DBA2_DPM2 = 0x12
    DBA2_DPM3 = 0x13
    DBA2_DPM4 = 0x14
    DBA2_DPM5 = 0x15
    DBA2_DPM6 = 0x16
    DBA2_DPM7 = 0x17

    DBA2_DTL0 = 0x90
    DBA2_DTL1 = 0x91
    DBA2_DTL2 = 0x92
    DBA2_DTL3 = 0x93
    DBA2_DTL4 = 0x94
    DBA2_DTL5 = 0x95
    DBA2_DTL6 = 0x96
    DBA2_DTL7 = 0x97

    # DBA 3
    DBA3_DPM0 = 0x20
    DBA3_DPM1 = 0x21
    DBA3_DPM2 = 0x22
    DBA3_DPM3 = 0x23
    DBA3_DPM4 = 0x24
    DBA3_DPM5 = 0x25
    DBA3_DPM6 = 0x26
    DBA3_DPM7 = 0x27

    DBA3_DTL0 = 0xA0
    DBA3_DTL1 = 0xA1
    DBA3_DTL2 = 0xA2
    DBA3_DTL3 = 0xA3
    DBA3_DTL4 = 0xA4
    DBA3_DTL5 = 0xA5
    DBA3_DTL6 = 0xA6
    DBA3_DTL7 = 0xA7

    # DBA 4
    DBA4_DPM0 = 0x30
    DBA4_DPM1 = 0x31
    DBA4_DPM2 = 0x32
    DBA4_DPM3 = 0x33
    DBA4_DPM4 = 0x34
    DBA4_DPM5 = 0x35
    DBA4_DPM6 = 0x36
    DBA4_DPM7 = 0x37

    DBA4_DTL0 = 0xB0
    DBA4_DTL1 = 0xB1
    DBA4_DTL2 = 0xB2
    DBA4_DTL3 = 0xB3
    DBA4_DTL4 = 0xB4
    DBA4_DTL5 = 0xB5
    DBA4_DTL6 = 0xB6
    DBA4_DTL7 = 0xB7

    @classmethod
    def valid_dpm_address(cls, address):
        return cls._verify_address('DPM', address)

    @classmethod
    def valid_dtl_address(cls, address):
        return cls._verify_address('DTL', address)

    @classmethod
    def _verify_address(cls, matcher, address):
        matched_enums = (enum for enum in cls if matcher in enum.name)
        for enum in matched_enums:
            if enum.value == address:
                return True
        return False


class PMM_LUNS(Enum):
    # Supply's and their LUNs for the GetEnviornment
    PMM = 0x00
    Supply1 = 0x01
    Supply2 = 0x02
    Supply3 = 0x03


class DPM_LUNS(Enum):
    DBA1_DPM0 = 0x00
    DBA1_DPM1 = 0x01
    DBA1_DPM2 = 0x02
    DBA1_DPM3 = 0x03
    DBA1_DPM4 = 0x04
    DBA1_DPM5 = 0x05
    DBA1_DPM6 = 0x06
    DBA1_DPM7 = 0x07

    DBA2_DPM0 = 0x08
    DBA2_DPM1 = 0x09
    DBA2_DPM2 = 0x0A
    DBA2_DPM3 = 0x0B
    DBA2_DPM4 = 0x0C
    DBA2_DPM5 = 0x0D
    DBA2_DPM6 = 0x0E
    DBA2_DPM7 = 0x0F

    DBA3_DPM0 = 0x10
    DBA3_DPM1 = 0x11
    DBA3_DPM2 = 0x12
    DBA3_DPM3 = 0x13
    DBA3_DPM4 = 0x14
    DBA3_DPM5 = 0x15
    DBA3_DPM6 = 0x16
    DBA3_DPM7 = 0x17

    DBA4_DPM0 = 0x18
    DBA4_DPM1 = 0x19
    DBA4_DPM2 = 0x1A
    DBA4_DPM3 = 0x1B
    DBA4_DPM4 = 0x1C
    DBA4_DPM5 = 0x1D
    DBA4_DPM6 = 0x1E
    DBA4_DPM7 = 0x1F

