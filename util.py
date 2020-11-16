# 命令に関するユーティリティ関数

def left(inst):
    return inst[0]

def right(inst, n=0):
    if n == 0:
        return inst[2:]
    elif n < len(inst):
        return inst[1+n]
    else:
        return []

def op(inst):
    return inst[1]

# コピー文かどうか
def is_copy(inst):
    return is_id(left(inst)) and op(inst) == '='

# 項に関するユーティリティ関数

def is_id(term):
    return term is not None and term[0] == 'id'

def is_num(term):
    return term is not None and term[0] == 'num'

def is_label(term):
    return term is not None and term[0] == 'label'

def is_type(term):
    return term is not None and term[0] == 'type'

def is_term(term):
    return is_id(term) or is_num(term) or is_label(term) or is_type(term)

# 項の値を返す。
def tval(term):
    return term[1]

def set_tval(term, val):
    term[1] = val
    
def label_name(term):
    return tval(term)

def id_name(term):
    return tval(term)

def num_value(term):
    return tval(term)

def type_name(term):
    return tval(term)

def id_type(func, term):
    return func.symtable.get_sym(id_name(term), 'type')

def num_type(func, term):
    # 数値の型は仕様からint固定とする。
    return 'int'

# 項の内部型を求める。
def term_type(func, term):
    if is_id(term):
        return id_type(func, term)
    elif is_num(term):
        return num_type(func, term)
    else:
        return None

# デバッグ関連
def dump_func(func):
    print('****** {} start *****'.format(func.name))
    for bb in func.bbtable.values():
        for inst in bb.insts:
            if op(inst) == 'deflabel':
                print(f'{inst}')
            else:
                print(f'    {inst}')
    print('****** {} end *****'.format(func.name))
    
def dump_program(p):
    print('------ program start -----')
    for func in p.func_list:
        dump_func(func)
    print('------ program end -----')

def dump_rawfunc(func):
    print('****** {} start (raw) *****'.format(func.name))
    for inst in func.insts:
        if op(inst) == 'deflabel':
            print(f'{inst}')
        else:
            print(f'    {inst}')
    print('****** {} end (raw) *****'.format(func.name))
