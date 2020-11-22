from parser import parse
from classes import Function, BasicBlock
from util import *

_verbose = False

# 基本ブロックへの分割
def divide_into_blocks(f):
    # 最初の命令が[None, 'deflabel', LABEL]であることを前提とする。

    prev_bb = f.entry
    prev_inst = f.insts[0]
    f.bbtable[f.entry] = BasicBlock(f.entry)
    f.bbtable[f.entry].insts.append(f.insts[0])
    cur_label = f.entry

    # 基本ブロックに分割し、ブロックへの命令の登録と後続ブロックの設定を行う。
    for cur_inst in f.insts[1:] + [[None, 'deflabel', ['label', f.end]]]:
        if op(cur_inst) == 'deflabel':
            prev_bb = cur_label
            cur_label = label_name(right(cur_inst, 1))
            f.bbtable[cur_label] = BasicBlock(cur_label)
            if op(prev_inst) == 'goto':  # [None, 'goto', LABEL]
                f.bbtable[prev_bb].succ.append(label_name(right(prev_inst, 1)))
            elif op(prev_inst) == 'if':  # [None, 'if', ID, LABEL, LABEL]
                f.bbtable[prev_bb].succ.append(label_name(right(prev_inst, 2)))
                f.bbtable[prev_bb].succ.append(label_name(right(prev_inst, 3)))
            elif op(prev_inst) == 'return':
                f.bbtable[prev_bb].succ.append(f.end)
            else:
                f.bbtable[prev_bb].succ.append(cur_label)
        f.bbtable[cur_label].insts.append(cur_inst)
        # 代入文の左辺の変数が属する基本ブロックを登録する。
        if is_id(left(cur_inst)):
            f.symtable.set_sym(id_name(left(cur_inst)), {'bb': cur_label})
        prev_inst = cur_inst

    # 基本ブロック末尾の命令を調整する。
    for label in f.bbtable.keys():
        if label == f.end:
            continue
        last_inst = f.bbtable[label].insts[-1]
        if op(last_inst) == 'return':
            # return文の置き換えを行う。
            # [None, 'return', ID]
            # -> ['retval', '=', ID] [None, 'goto', '__end']
            f.bbtable[label].insts[-1:] = [[['id', '.retval'], '=', right(last_inst, 1)],
                                           [None, 'goto', ['label', '__end']]]
        elif op(last_inst) not in ('goto', 'if', 'return'):
            # 末尾が分岐系命令でなければ後続ブロックへのgoto命令を挿入する。
            f.bbtable[label].insts.append(
                [None, 'goto', ['label', f.bbtable[label].succ[0]]])

    # 関数は必ず出口ブロックで終了するものとする。
    # したがって関数中のすべてのreturn文は出口ブロックに一度分岐する。
    # 返却値は特別な変数'.retval'に代入しておくものとする。
    f.symtable.add_sym(f.end, 'label')
    f.symtable.add_sym('.retval', 'localvar', {'type': f.ftype, 'bb': f.end })
    f.bbtable[f.entry].insts.insert(
        1, [['id', '.retval'], 'deflocal', ['type', f.ftype]])
    f.bbtable['__end'] = BasicBlock(f.end)
    f.bbtable[f.end].insts.extend(
        [[None, 'deflabel', ['label', f.end]],
         [None, 'return', ['id', '.retval']]])

    # 関数入口からたどることのできる基本ブロックを列挙する。
    def find_connected_block(bb, result):
        if bb in result:
            return
        result.add(bb)
        for succ in f.bbtable[bb].succ:
            find_connected_block(succ, result)

    # 不要になった基本ブロックは削除する。
    all_bbs = set([bb for bb in f.bbtable.keys()])
    result = set()
    find_connected_block(f.entry, result)
    f.bbtable = {k:v for k, v in f.bbtable.items() if k in result}
    for bb in all_bbs - result:
        f.symtable.delete_sym(bb)
    
    # 先行ブロックの接続
    for bbname in f.bbtable.keys():
        for s in f.bbtable[bbname].succ:
            f.bbtable[s].pred.append(bbname)

    if _verbose:
        print('*** Basic Blocks start ***')
        for bb in f.bbtable.values():
            print('{} (pred={}) (succ={})'.format(bb.name, bb.pred, bb.succ))
            for i in bb.insts:
                print('  {}'.format(i))
        print('*** Basic Blocks end ***')
    
# 基本ブロックの支配集合DOMを計算する。
# DOM(B): Bが支配するブロックの集合
def calc_dom(f):
    # 初期としてすべてのブロックをDOM集合に入れる。
    # ただしエントリブロックはエントリブロックのみ支配するものとする。
    for bbname in f.bbtable.keys():
        f.dom[bbname] = set(f.bbtable.keys())
    f.dom[f.entry] = set([f.entry])

    # DOM集合の状態が変わらなくなるまで繰り返す。
    while True:
        changed = False
        for this_bb in f.bbtable.keys():
            prev_len = len(f.dom[this_bb])
            for pred in f.bbtable[this_bb].pred:
                f.dom[this_bb] &= f.dom[pred]
            f.dom[this_bb] |= set([this_bb])
            if len(f.dom[this_bb]) != prev_len:
                changed = True
        if not changed:
            break

    if _verbose:
        print('*** DOM start  ***')
        for k, v in f.dom.items():
            print(k, v)
        print('*** DOM end  ***')

# 直接支配IDOMの関係と支配木treeを計算する。
def calc_idom(f):
    candidate = {}
    for x in f.dom:
        candidate[x] = f.dom[x] - set([x])

    processed = [f.entry]
    while True:
        ascendant = None
        for k, v in candidate.items():
            if k not in processed and len(v) == 1:
                processed.append(k)
                ascendant = v
                break
        if ascendant is not None:
            for k, v in candidate.items():
                if len(v) > 1:
                    v -= ascendant
        else:
            break
    f.idom = {}
    for k, v in candidate.items():
        if len(v) == 1:
            f.idom[k] = v.pop()
        else:
            f.idom[k] = None

    # 直接支配の関係から支配木を作成する。
    f.tree = {bbname:[] for bbname in f.idom.values()}
    for k, v in f.idom.items():
        f.tree[v].append(k)

    if _verbose:
        print('*** IDOM start  ***')
        for k, v in f.idom.items():
            print(k, v)
        print('*** IDOM end  ***')
        print('*** TREE start  ***')
        for k, v in f.tree.items():
            print(k, v)
        print('*** TREE end  ***')

# 支配辺境を計算する。
def calc_df(f):
    # 深さ優先で訪れるリーフノードのリストを作成する。
    def get_traverse_order(tree, current, order):
        if current not in tree:
            order.append(current)
            return
        else:
            for child in tree[current]:
                get_traverse_order(tree, child, order)
            order.append(current)
            return

    f.df = {}
    order = []
    get_traverse_order(f.tree, f.entry, order)

    for x in order:
        f.df[x] = []
        for y in f.bbtable[x].succ:
            if f.idom[y] != x:
                f.df[x].append(y)
        child = []
        for t in f.bbtable.keys():
            if f.idom[t] == x:
                child.append(t)
        for z in child:
            for y in f.df[z]:
                if f.idom[y] != x:
                    f.df[x].append(y)

    if _verbose:
        print('*** DF start  ***')
        for k, v in f.df.items():
            print(k, v)
            print('*** DF end  ***')

# 変数の定義が指定した基本ブロックにあるか確かめる。
def exists_def(f, bb, var):
    for i in f.bbtable[bb].insts:
        if is_id(left(i)) and id_name(left(i)) == var:
            return True
    return False

# φ関数を挿入する。
def insert_phi_functions(f):
    # 局所変数の定義命令を、0への定数コピー文に置換する。
    insts = f.bbtable[f.entry].insts
    for i in range(len(insts)):
        if (op(insts[i]) == 'deflocal'
            and not exists_def(f, f.entry, tval(right(insts[i], 1)))):
            insts[i] = [['id', tval(left(insts[i]))], '=', ['num', '0']]

    # 局所変数('localvar')と関数引数('param')が定義される基本ブロックを列挙する。
    # 現在の仕様ではlocalvarとparamはエントリブロックにしかないはず。
    defbb = {}
    for var in f.symtable.sym_enumerator(kind=('localvar', 'param')):
        defbb[var] = [b for b, battr in f.bbtable.items() for i in battr.insts
                      if is_id(left(i)) and tval(left(i)) == var]
    inserted = {x:None for x in f.bbtable.keys()}
    work = {x:None for x in f.bbtable.keys()}
    w = []
    for v in defbb.keys():
        for b in defbb[v]:
            w.append(b)
            work[b] = v
        while w != []:
            x = w.pop()  # 任意の基本ブロックを一つ取り出す。
            for y in f.df[x]:
                if inserted[y] != v:
                    # 変数xに対するファイ関数がまだ基本ブロックyに挿入されて
                    # いなければ先頭に挿入する。
                    ids = []
                    for k in range(len(f.bbtable[y].pred)):
                        ids.append(['id', v])
                    f.bbtable[y].insts.insert(1, [['id', v], 'phi', *ids])
                    inserted[y] = v
                    if work[y] == v:
                        w.append(y)
                        work[y] = v

    if _verbose:
        print('*** insert Phi start ***')
        for bb in f.bbtable.values():
            print('{} (pred={}) (succ={})'.format(bb.name, bb.pred, bb.succ))
            for i in bb.insts:
                print('  {}'.format(i))
        print('*** insert Phi end ***')

# 置き換えられる変数名を探して実際に置き換える。
def search(f, stack, counter, bbname):
    # 基本ブロック内の文を先頭から変数の置き換えを実施する。
    for i in f.bbtable[bbname].insts:
        # 右辺がファイ関数呼び出しでない場合、右辺の各変数VをViに置き換える。
        if op(i) != 'phi':
            for pos in range(len(right(i))):
                term = right(i, 1+pos)
                if is_id(term) and tval(term) in stack:
                    set_tval(term, '{}.{}'
                             .format(tval(term), stack[tval(term)][-1]))
        # 左辺には変数名が2個以上となることはないことを前提として、
        # 左辺の変数を新しい番号の変数に置き換える。
        # if stmt[0] in stack:
        if is_id(left(i)):
            lterm = left(i)
            old_name = lterm[1]
            new_name = '{}.{}'.format(lterm[1], counter[old_name])
            f.symtable.add_sym(new_name, 'ssavar',
                             {'type': f.symtable.get_sym(old_name, 'type'),
                              'bb': bbname,
                              'origin': old_name})
            stack[old_name].append(counter[old_name])
            counter[old_name] += 1
            lterm[1] = new_name

    # 後続ブロックに対して変数名の置き換えを実施する。
    for succ in f.bbtable[bbname].succ:
        # 後続ブロックからみて現在のブロックが何番目かを調べ、
        # φ関数中の同じ位置の引数の変数名を置き換える。
        pos = f.bbtable[succ].pred.index(bbname)
        for i in f.bbtable[succ].insts:
            if op(i) == 'phi':
                term = right(i, pos+1)
                set_tval(term, '{}.{}'
                         .format(tval(right(i, pos+1)),
                                 stack[tval(right(i, pos+1))][-1]))

    # 支配木上での子ブロックに対して再帰的に変数名の置き換えを実施する。
    if bbname in f.tree:
        for child in f.tree[bbname]:
            search(f, stack, counter, child)

    # 元の左辺の変数に対するスタックを1つ戻す。
    ssavars = [k for k in f.symtable.sym_enumerator(kind='ssavar')]
    for i in f.bbtable[bbname].insts:
        if is_id(left(i)) and id_name(left(i)) in ssavars:
            stack[f.symtable.get_sym(id_name(left(i)), 'origin')].pop()

# SSA形式の命令列に対して変数名の置き換え、SSA形式として完成させる。
def rename_variables(f):
    stack = {var: [0] for var in f.symtable.sym_enumerator(
        kind=('localvar', 'param', 'temp'))}
    counter = {var: 1 for var in f.symtable.sym_enumerator(
        kind=('localvar', 'param', 'temp'))}
    search(f, stack, counter, f.entry)

    if _verbose:
        print('*** rename var start ***')
        for bb in f.bbtable.values():
            print('{} (pred={}) (succ={})'.format(bb.name, bb.pred, bb.succ))
            for i in bb.insts:
                print('  {}'.format(i))
        print('*** rename var end ***')

# 項の型を求める。
def get_term_type(f, term):
    if is_id(term):
        if f.symtable.get_sym(id_name(term)):
            return f.symtable.get_sym(id_name(term), 'type')
        else:
            return f.program.symtable.get_sym(id_name(term), 'type')
    elif is_num(term):
        # 数値はすべてintとする。
        return 'int'
    else:
        return None

# 基本ブロックをたどって型が未決の識別子に型を設定する。
# 支配木情報を利用するため、支配木の確定後に実行すること。
def set_type(f, block):
    if block in f.tree:
        for child in f.tree[block]:
            set_type(f, child)
            
    # 自ブロックの各文に対して型を設定する。
    for i in f.bbtable[block].insts:
        # 左辺が識別子の場合は右辺の型が左辺の型になる。
        if is_id(left(i)) and get_term_type(f, left(i)) is None:
            if op(i) in ('+', '-', '*', '/'):
                # 右辺が加減乗除の場合は右辺の計算結果が左辺の型になる。
                t1 = get_term_type(f, right(i, 1))
                t2 = get_term_type(f, right(i, 2))
                if t1 != t2:
                    print('WARNING: type mismatch: {}(), {}()'
                          .format(right(i, 1), t1, right(i, 2), t2))
                f.symtable.set_sym(id_name(left(i)), {'type': t1})
            elif op(i) in ('<', '<=', '>', '>=', '==', '!='):
                # 右辺が比較式の場合は式の結果はboolean型とする。
                t1 = get_term_type(f, right(i, 1))
                t2 = get_term_type(f, right(i, 2))
                if t1 != t2:
                    print('WARNING: type mismatch: {}(), {}()'
                          .format(right(i, 1), t1, right(i, 2), t2))
                f.symtable.set_sym(id_name(left(i)), {'type': 'boolean'})
            elif op(i) in ('unary_minus', '='):
                # 単項演算子またはコピー文の場合
                t1 = get_term_type(f, right(i, 1))
                f.symtable.set_sym(id_name(left(i)), {'type': t1})
            elif op(i) == 'call':
                # 関数呼び出しの場合
                t1 = get_term_type(f, right(i, 1))
                f.symtable.set_sym(id_name(left(i)), {'type': t1})

# 型解析を実施する。
# 支配木情報を利用するため、支配木の計算が終わった後に実行する必要がある。
def type_analysis(f):
    # 構文解析時に型が決まっていなかった識別子に型を設定する。
    set_type(f, f.entry)

# コピー伝播最適化を行う。
def copy_propagation(f):
    copy_inst = {}
    # コピー文を探す。
    for bbattr in f.bbtable.values():
        pos = []
        for i in range(len(bbattr.insts)):
            inst = bbattr.insts[i]
            if is_copy(inst):
                # コピー文の左辺の変数名をキーとし、右辺の項(変数または数値)を
                # 値とする辞書要素を追加する。
                copy_inst[id_name(left(inst))] = right(inst, 1)
                pos.append(i)
                
        # コピー文を削除する。
        bbattr.insts = [bbattr.insts[i]
                        for i in range(len(bbattr.insts)) if i not in pos]

    # コピー先の変数の使用箇所をコピー元の変数または数値で置き換える。
    for bbattr in f.bbtable.values():
        for inst in bbattr.insts:
            for pos in range(2, len(inst)):
                if id_name(inst[pos]) in copy_inst:
                    inst[pos] = copy_inst[id_name(inst[pos])]

# 構文解析した結果の命令列をSSA形式の内部表現に変換する。
def irgen(source):
    program = parse(source, debug=False)
    if program is not None:
        for func in program.func_list:
            divide_into_blocks(func)
            calc_dom(func)
            calc_idom(func)
            calc_df(func)
            type_analysis(func)
            insert_phi_functions(func)
            rename_variables(func)
            copy_propagation(func)
    return program
