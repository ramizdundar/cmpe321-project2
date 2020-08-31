import os

# to add test cases drag out zip contents into db folder
# note that db is global variable

# global variables

# page size
psize = 112
sc = 'syscat'
db = 'db112'


# disk manager 
def dmr(fname, pnumber):
    f = open(db+'/'+fname, "rb")
    f.seek(pnumber * psize)
    page = f.read(psize)
    f.close()
    return page

def dmw(fname, pnumber, page):
    f = open(db+'/'+fname, "r+b")
    f.seek(pnumber * psize)
    f.write(page)
    f.close()

def create_file(fname):
    newpage = bytearray(b'\x00'*psize)
    newpage[0:4] = encode(0)
    newpage[4:8] = encode(0)
    newpage[8:12] = encode(-1)
    f = open(db+'/'+fname, 'wb')
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
        else:
            return


# find maximum number of records in a page
def find_mrec(fname):
    return (psize-12) // find_reclen(fname)

def find_nfields(fname):
    if fname == sc:
        return 9

    address = search_rec(sc, fname)

    f = dmr(sc, address[0])

    offset = address[1] + 15
    nfields = decode(f[offset:offset+4], int)

    return nfields



def find_reclen(fname):
    syscat = 'syscat'
    if fname == syscat:
        return 100

    nfields = find_nfields(fname)

    return 5 + nfields*4 

    # fnumber = 0
    # offset = address[1] + 15
    # for i in range(9):
    #     if f[offset+i*9:offset+(i+1)*9] == b'\x00'*9:
    #         break
    #     fnumber += 1
    
    # return 5 + fnumber*4


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
                dmw(fname, pnumber-1, f)
                create_page = True
    
    if create_page:
        newpage = bytearray(b'\x00'*psize)
        newpage[0:4] = encode(pnumber)
        newpage[4:8] = encode(0)
        newpage[8:12] = encode(-1)
        dmw(fname, pnumber, newpage)
        flush_page(fname, pnumber)
    
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
            f[4:8] = encode(decode(f[4:8], int)+1)
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


def delete_type():
    print('please enter name of the type you want to delete: ')
    rectype = input()
    address = search_rec(sc, rectype)
    f = bytearray(dmr(sc, address[0]))
    f[address[1] + 14:address[1] + 15] = encode(1, 1)
    f[4:8] = encode(decode(f[4:8], int)-1)
    dmw(sc, address[0], f)
    os.remove(db+'/'+rectype)


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


# dml
def create_record():
    print('please enter the type of record you want to enter: ')
    rectype = input()
    nfields = find_nfields(rectype)

    print('please enter the id of record(must be integer) you want to enter: ')
    rec = encode(int(input()))
    rec += encode(0, 1)

    print(f'please enter {nfields} fields(must be integers): ')

    address_sc = search_rec(sc, rectype)
    scf = dmr(sc, address_sc[0])
    offset = address_sc[1] + 19
    for i in range(1, nfields+1):
        fname = decode(scf[offset+9*(i-1):offset+9*i], str)
        print(f'please enter {fname}: ')
        rec += encode(int(input()))

    insert_rec(rectype, rec)


def delete_record():
    print('please enter name of the type you want to delete: ')
    rectype = input()
    print('please enter id of the type you want to delete: ')
    recid = int(input())
    address = search_rec(rectype, recid)
    f = bytearray(dmr(rectype, address[0]))
    f[address[1] + 4:address[1] + 5] = encode(1, 1)
    f[4:8] = encode(decode(f[4:8], int)-1)
    dmw(rectype, address[0], f)


def search_record():
    print('please enter name of the type you want to search: ')
    rectype = input()
    print('please enter id of the type you want to search: ')
    recid = int(input())

    address = search_rec(rectype, recid)

    if address is None:
        print('not found')
        return

    f = dmr(rectype, address[0])
    rec = f[address[1]:address[1] + find_reclen(rectype)]
    
    rid = decode(rec[0:4], int)
    isempty = decode(rec[4:5], int)
    if isempty == 1: return
    print(f'id: {rid}', end=' || ')

    address_sc = search_rec(sc, rectype)
    scf = dmr(sc, address_sc[0])
    offset = address_sc[1] + 19
    for i in range(find_nfields(rectype)):
        field = decode(rec[5+4*i:5+4*(i+1)], int)
        fname = decode(scf[offset+9*i:offset+9*(i+1)], str)
        print(f'{fname}: {field}', end=' || ')

    print()



def list_records():
    print('please enter name of the type you want to list: ')
    rectype = input()
    mrec = find_mrec(rectype)
    pnumber = 0
    f = dmr(rectype, pnumber)
    reclen = find_reclen(rectype)
    hasnext = True

    recs = []
    while hasnext:
        for i in range (mrec):
            if decode(f[16+i*reclen:16+i*reclen+1], int) == 0:
                recs.append(decode(f[12+i*reclen:12+i*reclen+4], int))
        
        if decode(f[8:12], int) == -1:
            hasnext = False
        else:
            pnumber += 1
            f = dmr(rectype, pnumber)

    print(f'total {len(recs)} records')

    for rec in recs:
        print(rec)

    return rectype
    

if not os.path.exists(db+'/'+sc):
    print('syscat not found')
    print('new syscat created')
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
            delete_type()
            continue
        if ui == 2: 
            list_types()
            continue


    if(ui == 'dml'):
        print('create a record: 0')
        print('delete a record: 1')
        print('search for a record: 2')
        print('list all records: 3')

        ui = int(input())

        if ui == 0: 
            create_record()
            continue
        if ui == 1:
            delete_record()
            continue
        if ui == 2: 
            search_record()
            continue
        if ui == 3: 
            list_records()
            continue
    else:
        exit = True


