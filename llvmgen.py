from util import *

# 項に対するLLM表現を返す。
def llvm_id(func, value):
    if func.symtable.get_sym(value) is not None:
        return func.symtable.get_sym(value, 'llvm_name')
    elif func.program.symtable.get_sym(value) is not None:
        return func.program.symtable.get_sym(value, 'llvm_name')
    else:
        return None

def llvm_num(func, value):
    return value

def llvm_type(func, value):
    llvm_type_map = {'int': 'i32', 'boolean': 'i1'}
    return llvm_type_map[value]

def llvm_label(func, value):
    return value

def llvm_term(func, term):
    if is_id(term):
        return llvm_id(func, id_name(term))
    elif is_num(term):
        return llvm_num(func, num_value(term))
    elif is_label(term):
        return llvm_label(func, label_name(term))
    elif is_type(term):
        return llvm_type(func, type_name(term))
    else:
        return tval(term)

# φ関数引数のLLVM表現を構築する。
def create_phi_arg(func, terms):
    result = []
    for pos, t in enumerate(terms):
        if is_id(t):
            bb = func.symtable.get_sym(id_name(t), 'bb')
            result.append([llvm_term(func, t),
                           '%{}'.format(llvm_label(func, bb))])
        elif is_num(t):
            # 数値の場合は、ファイ関数の引数の位置に相当する先行ブロックから
            # 到達するものと考える。
            curbb = func.context['current_bb']
            pred_bb = func.bbtable[curbb].pred[pos]
            result.append([llvm_term(func, t),
                           '%{}'.format(llvm_label(func, func.bbtable[pred_bb].name))])
        else:
            print('WARNING: invalid phi arg {}'.format(t))
            result.append([])
    return result

# ひとつの命令をLLVM IRに変換し出力する。
def gen_inst(func, inst, result):
    llvm_binop = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'sdiv'}
    llvm_relop = {'<': 'slt', '<=': 'sle', '>': 'sgt', '>=': 'sge', '==': 'eq', '!=': 'ne'}

    if op(inst) == 'deflabel':
        result.append('{}:'.format(llvm_term(func, right(inst, 1))))
    elif op(inst) == 'defparam':
        pass
    elif op(inst) == 'goto':
        result.append('    br label %{}'.format(llvm_term(func, right(inst, 1))))
    elif op(inst) == 'if':
        result.append('    br {} {}, label %{}, label %{}'
                      .format(llvm_type(func, term_type(func, right(inst, 1))),
                              llvm_term(func, right(inst, 1)),
                              llvm_term(func, right(inst, 2)),
                              llvm_term(func, right(inst, 3))))
    elif op(inst) == 'phi':
        phiarg = create_phi_arg(func, right(inst))
        argstr = []
        for a in phiarg:
            argstr.append('[{}, {}]'.format(*a))
        result.append('    {} = phi {} {}'
                      .format(llvm_term(func, left(inst)),
                              llvm_type(func, term_type(func, left(inst))),
                              ', '.join(argstr)))

    elif op(inst) == 'return':
        result.append('    ret {} {}'
                      .format(llvm_type(func, term_type(func, right(inst, 1))),
                              llvm_term(func, right(inst, 1))))
    elif op(inst) == 'call':
        argstr = []
        for a in right(inst)[1:]:
            argstr.append('{} {}'.format(llvm_type(func, term_type(func, a)),
                                         llvm_term(func, a)))
        result.append('    {} = call i32 {} ({})'
                      .format(llvm_term(func, left(inst)),
                              llvm_term(func, right(inst, 1)),
                              ', '.join(argstr)))
    elif op(inst) in llvm_binop:
        result.append('    {} = {} {} {}, {}'
                      .format(llvm_term(func, left(inst)),
                              llvm_binop[op(inst)],
                              llvm_type(func, term_type(func, right(inst, 1))),
                              llvm_term(func, right(inst, 1)),
                              llvm_term(func, right(inst, 2))))
    elif op(inst) in llvm_relop:
        result.append('    {} = icmp {} {} {}, {}'
                      .format(llvm_term(func, left(inst)),
                              llvm_relop[op(inst)],
                              llvm_type(func, term_type(func, right(inst, 1))),
                              llvm_term(func, right(inst, 1)),
                              llvm_term(func, right(inst, 2))))
    elif op(inst) == '=':
        # コピー文をLLVM IRでは表現できない(?)ようなので、
        # ゼロとの加算命令に置き換える。
        result.append('    {} = {} {} {}, {}'
                      .format(llvm_term(func, left(inst)),
                              llvm_binop['+'],
                              llvm_type(func, term_type(func, right(inst, 1))),
                              llvm_term(func, right(inst, 1)),
                              llvm_num(func, '0')))

# LLVM IRを生成する。
def llvmgen(p):
    # LLVM IRの命名規則にしたがった識別子名を登録する。
    for item in p.symtable.sym_enumerator(kind='func'):
        p.symtable.set_sym(item, {'llvm_name': '@{}'.format(item)})
    for func in p.func_list:
        counter = 0
        symtable = func.symtable
        for item in func.symtable.sym_enumerator(kind='ssavar'):
            origin = func.symtable.get_sym(item, 'origin')
            if func.symtable.get_sym(origin, 'kind') == 'temp':
                func.symtable.set_sym(item, {'llvm_name': '%{}'.format(counter)})
                counter += 1
            elif func.symtable.get_sym(origin, 'kind') in ('localvar', 'param'):
                func.symtable.set_sym(item, {'llvm_name': '%{}'.format(item)})

    result = []
    # 各関数のLLVM IRを出力する。
    for func in p.func_list:
        argstr = []
        for param in func.params:
            argstr.append('{} {}'.format(llvm_term(func, param[0]),
                                         llvm_term(func, param[1])))
        result.append('define {} {}({}) {{'.format(llvm_type(func, func.ftype),
                                                   llvm_id(func, func.name),
                                                   ', '.join(argstr)))
        for k in func.bbtable.keys():
            func.context['current_bb'] = k
            for inst in func.bbtable[k].insts:
                gen_inst(func, inst, result)
        result.append('}')
        del func.context['current_bb']

    return result
