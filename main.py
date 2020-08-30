# global variables

# page size
psize = 1024


# disk manager 
def dmr(fname, pnumber):
    f = open(fname, "rb")
    f.seek(pnumber * psize)
    return f.read(psize)

def dmw(fname, pnumber, page):
    f = open(fname, "r+")
    f.seek(pnumber * psize)
    f.write(page)


# to encode/decode
def encode(var, size=0):
    if isinstance(var):
        return var.to_bytes(4, byteorder='big', signed=True)
    if isinstance(var, str):
        if size = 0:
            return -1
        
        return var.encode() + b'\x00'*size

def decode(var, vtype):
    if vtype == int:
        return int.from_bytes(var, byteorder='big', signed=True)
    if vtype == str:
        s = var.decode()
        i = s.find('\x00')
        if i != -1:
            return s[:i]
        return s






