def int_to_bcd(val: int) -> int:
    if val < 0:
        raise ValueError("Cannot be a negative integer")

    val_as_str = str(val)
    out_int = 0

    for digit in val_as_str:
        out_int += int(digit)
        out_int <<= 4

    out_int >>= 4
    return out_int


def int_to_bcd_bytes(val: int) -> bytes:
    if val < 0:
        raise ValueError("Cannot be a negative integer")

    val_as_str = str(val)
    if len(val_as_str) % 2 > 0:
        val_as_str = '0' + val_as_str

    out_bytes = bytes()
    for i in range(len(val_as_str) // 2):
        duet = val_as_str[ i*2 : (i+1)*2 ]
        out_int = int(duet[0])
        out_int <<= 4
        out_int += int(duet[1])
        out_bytes += bytes([out_int])

    return out_bytes


def bcd_to_int(val: int) -> int:
    if val < 0:
        raise ValueError("Cannot be a negative integer")

    val_as_str = "{0:0b}".format(val)  # 1333 = '101 0011 0101'
    while len(val_as_str) % 4 > 0:
        val_as_str = '0' + val_as_str  # '0101 0011 0101'

    out_as_str = ''
    for i in range(len(val_as_str) // 4):
        tetrad = val_as_str[ i*4 : (i+1)*4 ]
        out_as_str += str(int(tetrad, 2))

    out_int = int(out_as_str)
    return out_int
