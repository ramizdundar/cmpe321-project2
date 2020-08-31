import os


# global variables

# page size
psize = 1024
sc = 'syscat'


# disk manager 
def dmr(fname, pnumber):
    f = open(fname, "rb")
    f.seek(pnumber * psize)
    page = f.read(psize)
    f.close()
    return page

def dmw(fname, pnumber, page):
    f = open(fname, "r+b")
    f.seek(pnumber * psize)
    f.write(page)
    f.close()

def create_file(fname):
    newpage = bytearray(b'\x00'*1024)
    newpage[0:4] = encode(0)
    newpage[4:8] = encode(0)
    newpage[8:12] = encode(-1)
    f = open(fname, 'wb')
    f.write(newpage)


# to encode/decode
def encode(var, size=4):
    if isinstance(var, int):
        return var.to_bytes(size, byteorder='big', signed=True)
    
    if isinstance(var, str):
        return var.encode() + b'\x00'*(size-len(var))

def decode(var, vtype):
    if vtype == int:
        return int.from_bytes(var, byteorder='big', signed=True)
    
    if vtype == str:
        s = var.decode()
        i = s.find('\x00')
        if i != -1:
            return s[:i]
        return s



def search_rec(fname, key):
    pnumber = 0
    f = dmr(fname, pnumber)
    mrec = find_mrec(fname)
    reclen = find_reclen(fname)
    isempty = 0

    while True:
        for i in range(mrec):
            if fname == 'syscat':
                tkey = decode(f[i*reclen+12:i*reclen+12+14], str)
                isempty = decode(f[i*reclen+12+14:i*reclen+12+14+1], int)
            else:
                tkey = decode(f[i*reclen+12:i*reclen+12+4], int)
                isempty = decode(f[i*reclen+12+4:i*reclen+12+4+1], int)
            
            if tkey == key and isempty == 0:
                return (pnumber, i*reclen+12)
        
        if f[8:12] != -1:
            pnumber += 1
            f = dmr(fname, pnumber)
            break
        else:
            return


# find maximum number of records in a page
def find_mrec(fname):
    return (psize-12) // find_reclen(fname)



def find_reclen(fname):
    syscat = 'syscat'
    if fname == syscat:
        return 100

    address = search_rec(syscat, fname)

    f = dmr(syscat, address[0])

    # fnumber = 0
    # offset = address[1] + 15
    # for i in range(9):
    #     if f[offset+i*9:offset+(i+1)*9] == b'\x00'*9:
    #         break
    #     fnumber += 1
    
    # return 5 + fnumber*4


    offset = address[1] + 15
    reclen = decode(f[offset:offset+4], int)
    
    return reclen



def flush_page(fname, pnumber):
    mrec = find_mrec(fname)
    f = bytearray(dmr(fname, pnumber))
    offset = 26 if fname == 'syscat' else 16
    reclen = find_reclen(fname)

    for i in range(mrec):
        f[offset+i*reclen:offset+i*reclen+1] = encode(1, 1)

    dmw(fname, pnumber, f)



# finds non-full page of a file and returns page number
def find_nonfull_page(fname):
    create_page = False
    pnumber = 0
    f = dmr(fname, pnumber)
    mrec = find_mrec(fname)

    while not create_page:
        nrec = decode(f[4:8], int)
        if nrec < mrec:
            return decode(f[0:4], int)
        else:
            npage = decode(f[8:12], int)
            if npage != -1:
                pnumber += 1
                f = dmr(fname, pnumber)
            else:
                pnumber += 1
                f = bytearray(f)
                f[8:12] = encode(pnumber)
                dmr(fname, pnumber-1)
                create_page = True
    
    if create_page:
        newpage = bytearray(b'\x00'*1024)
        flush_page(fname, pnumber)
        newpage[0:4] = encode(pnumber)
        newpage[4:8] = encode(0)
        newpage[8:12] = encode(-1)
        dmw(fname, pnumber, newpage)
    
    return pnumber



def insert_rec(fname, rec):
    pnumber = find_nonfull_page(fname)
    mrec = find_mrec(fname)
    reclen = find_reclen(fname)
    offset = 26 if fname == 'syscat' else 16

    f = bytearray(dmr(fname, pnumber))
    
    for i in range (mrec):
        if  f[offset+i*reclen:offset+i*reclen+1] == encode(1, 1):
            f[12+i*reclen:12+(i+1)*reclen] = rec
            dmw(fname, pnumber, f)
            break


# ddl
def create_type():
    rectype = b''

    isempty = 0
    print('type name: ')
    tname = input()

    rectype += encode(tname, 14)
    rectype += encode(isempty, 1)

    print('please enter field names') 
    print('maximum 9 fields') 
    print('to finish give empty string') 
    print('empty string will not create a field') 

    nfields = 0
    fields = []
    for i in range(1, 10):
        print(f'please enter field name {i}: ')
        field = input()
        if field == '': break
        fields.append(field)
        nfields += 1
    
    rectype += encode(nfields)
    for field in fields:
        rectype += encode(field, 9)

    rectype += b'\x00'*((9-len(fields))*9)

    insert_rec('syscat', rectype)

    create_file(tname)
    flush_page(tname, 0)


def delete_type(rectype):
    address = search_rec(sc, rectype)
    f = bytearray(dmr(sc, address[0]))
    f[address[1] + 14:address[1] + 15] = encode(1, 1)
    dmw(sc, address[0], f)
    os.remove(rectype)


def list_types():
    mrec = find_mrec(sc)
    pnumber = 0
    f = dmr(sc, pnumber)
    reclen = find_reclen(sc)
    hasnext = True

    types = []
    while hasnext:
        for i in range (mrec):
            if decode(f[26+i*reclen:26+i*reclen+1], int) == 0:
                types.append(decode(f[12+i*reclen:12+i*reclen+14], str))
        
        if decode(f[8:12], int) == -1:
            hasnext = False
        else:
            pnumber += 1
            f = dmr(sc, pnumber)

    for rectype in types:
        print(rectype)

    return rectype



































if not os.path.exists(sc):
    create_file('syscat')
    flush_page('syscat', 0)


exit = False
while not exit:
    print('ddl or dml?')
    ui = input()
    if(ui == 'ddl'):
        print('create a type: 0')
        print('delete a type: 1')
        print('list all types: 2')

        ui = int(input())

        if ui == 0: 
            create_type()
            continue
        if ui == 1:
            print('please enter name of the type you want to delete: ')
            delete_type(input())
            continue
        if ui == 2: 
            list_types()
            continue


    if(ui == 'dml'):
        print('create a record: 0')
        print('delete a record: 1')
        print('search for a record: 2')
        print('list all records: 3')
    else:
        exit = True


