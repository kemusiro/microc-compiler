import ply.yacc as yacc
from lexer import tokens
from classes import Function, Program, SymbolTable
from util import *

# プログラム全体
_program = None

#  仮の識別子表
_global_symtable = None
_func_symtable = None

# 関数の入り口のラベル名
function_entry = '__entry'

# 新しい変数名を生成し、識別子表に登録する。
def newvar():
    newvar.counter += 1
    var = '.temp{}'.format(newvar.counter)
    _func_symtable.add_sym(var, 'temp')
    return ['id', var]

newvar.counter = -1

# 新しいラベル名を生成し、識別子表に登録する。
def newlabel():
    newlabel.counter += 1
    label = 'label{}'.format(newlabel.counter)
    _func_symtable.add_sym(label, 'label')
    return ['label', label]

newlabel.counter = -1

# 命令列のリストをマージしたリストと、マージ元のリストの
# 最後の変数のリストを返す。
def merge_insts_list(*insts_list):
    if len(insts_list) == 1 and is_term(insts_list[0]):
        # 項だけが渡された場合はマージ後の命令列はなしで
        # 最後の変数として項を返す。
        return None, insts_list[0]
    else:
        result = []
        last_vars = []
        for i in insts_list:
            result.extend(i)
            if is_id(left(result[-1])):
                last_vars.append(left(result[-1]))
        return result, last_vars

# 命令リストからコピー文をひとつ取り出す。
def pop_copy_inst(insts):
    candidate = -1
    for i in range(len(insts)):
        if is_copy(insts[i]):
            candidate = i
            break;
    if candidate >= 0:
        if len(insts) > 1:
            return insts.pop(i)
        else:
            # 命令リストが1個のコピー文しか含んでいなかった場合は、
            # 右辺の項(識別子または数値)を返す。
            # このとき代入先の一時変数を辞書から削除する。
            inst = insts.pop(i)
            if is_id(left(inst)):
                _func_symtable.delete_sym(id_name(left(inst)))
            return right(inst, 1)
    else:
        return None

# 命令リストのコピー文を削除し、式に対する命令列をシュリンクさせる。
# 結果は、すべてのコピー文が削除された命令列か、識別子一つのいずれかとなる。
def shrink(insts):
    while True:
        # コピー文を一つ取り出す。
        copy_inst = pop_copy_inst(insts)
        if copy_inst is None:
            return insts
        elif is_term(copy_inst):
            return copy_inst
        else:
            # コピー文の左辺変数の参照先をコピー文の右辺変数で置き換える。
            copy_right = right(copy_inst, 1)
            copy_left = left(copy_inst)
            for inst in insts:
                for pos in range(2, len(inst)):
                    if is_id(inst[pos]) and id_name(inst[pos]) == id_name(copy_left):
                        inst[pos] = copy_right
                        
            # 置換元変数は不要になったので識別子表から削除する。
            _func_symtable.delete_sym(id_name(copy_left))
    return insts

# 文法の開始記号
start = 'func_def_list'

# プログラムは関数定義のリストで構成する。
def p_func_def_list(p):
    '''func_def_list : func_def
                     | func_def_list func_def'''
    global _program
    global _func_symtable

    if len(p) == 2:
        func = p[1]
    elif len(p) == 3:
        func = p[2]

    if _program is None:
        _program = Program()
    func.program = _program
    _program.func_list.append(func)
    _global_symtable.add_sym(func.name, 'func', {'type': func.ftype})
    _func_symtable.scope = func.name

    # 状態をリセットし、次のパースに備える。
    _func_symtable = SymbolTable('.temp')
    newvar.counter = -1
    newlabel.counter = -1
    p[0] = _program
    
# 関数定義の文法
def p_func_def(p):
    '''func_def : type_spec ID LPAREN RPAREN compound_stat
                | type_spec ID LPAREN param_list RPAREN compound_stat'''
    p[0] = None
    if len(p) == 6:
        p[0] = Function(p[2], p[1][1], [], function_entry, _func_symtable, p[5])
    elif len(p) == 7:
        p[0] = Function(p[2], p[1][1], p[4], function_entry, _func_symtable, p[6])
    _func_symtable.add_sym(function_entry, 'label')
    p[0].entry = function_entry
    
def p_param_list(p):
    '''param_list : param
                  | param_list COMMA param'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = p[1] + p[3]

def p_param(p):
    'param : type_spec ID'
    p[0] = [[p[1], ['id', p[2]]]]
    _func_symtable.add_sym(p[2], 'param', {'type': p[1][1]})

def p_type_spec(p):
    'type_spec : INT'
    p[0] = ['type', p[1]]

# 複文
def p_compound_stat(p):
    '''compound_stat : LBRACE RBRACE
                     | LBRACE stat_list RBRACE
                     | LBRACE decl_list stat_list RBRACE'''
    if len(p) == 3:
        p[0] = []
    elif len(p) == 4:
        p[0] = p[2]
    elif len(p) == 5:
        p[0] = p[2] + p[3]

# 変数宣言のリスト
def p_decl_list(p):
    '''decl_list : decl
                 | decl_list decl'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[1] + p[2]

# 変数宣言
def p_decl(p):
    'decl : type_spec ID SEMI'
    p[0] = [[['id', p[2]], 'deflocal', p[1]]]
    _func_symtable.add_sym(p[2], 'localvar', {'type': p[1][1]})

def p_stat_list(p):
    '''stat_list : stat
                 | stat_list stat
    '''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        p[0] = p[1] + p[2]

def p_stat(p):
    '''stat : assignment_stat
            | while_stat
            | if_stat
            | return_stat
            | compound_stat'''
    p[0] = p[1]

def p_assignment_stat(p):
    'assignment_stat : ID EQUAL expr SEMI'
    p[0], lastvar = merge_insts_list(p[3])
    if p[0] == None:
        p[0] = [[['id', p[1]], '=', lastvar]]
    else:
        # 最後の文の左辺を代入文の左辺に置き換える。
        # 置き換える元の変数名は識別子表から削除する。
        last_inst = p[0][-1]
        _func_symtable.delete_sym(id_name(left(last_inst)))
        set_tval(left(last_inst), p[1])

def p_while_stat(p):
    'while_stat : WHILE LPAREN expr RPAREN stat'
    label_entry = newlabel();
    label_body = newlabel();
    label_end = newlabel();
    p[0] = [[None, 'deflabel', label_entry]]
    expr, lastvar = merge_insts_list(p[3])
    if expr is None:
        p[0].append([None, 'if', lastvar, label_body, label_end])
    else:
        p[0].extend(expr)
        p[0].append([None, 'if', lastvar[0], label_body, label_end])
    p[0].append([None, 'deflabel', label_body])
    p[0].extend(p[5])
    if op(p[5][-1]) not in ('goto', 'if', 'return'):
        p[0].append([None, 'goto', label_entry])
    p[0].append([None, 'deflabel', label_end])

def p_if_stat(p):
    '''if_stat : IF LPAREN expr RPAREN stat
               | IF LPAREN expr RPAREN stat ELSE stat'''
    if len(p) == 6:
        label_then = newlabel();
        label_end = newlabel();
        p[0], lastvar = merge_insts_list(p[3])
        if p[0] is None:
            p[0] = [[None, 'if', lastvar, label_then, label_end]]
        else:
            p[0].append([None, 'if', lastvar[0], label_then, label_end])
        p[0].append([None, 'deflabel', label_then])
        p[0].extend(p[5])
        if op(p[5][-1]) not in ('goto', 'if', 'return'):
            p[0].append([None, 'goto', label_end])
        p[0].append([None, 'deflabel', label_end])
    elif len(p) == 8:
        label_then = newlabel();
        label_else = newlabel();
        label_end = newlabel();
        p[0], lastvar = merge_insts_list(p[3])
        if p[0] is None:
            p[0] = [[None, 'if', lastvar, label_then, label_else]]
        else:
            p[0].append([None, 'if', lastvar[0], label_then, label_else])
        p[0].append([None, 'deflabel', label_then])
        p[0].extend(p[5])
        if op(p[5][-1]) != 'return':
            p[0].append([None, 'goto', label_end])
        p[0].append([None, 'deflabel', label_else])
        p[0].extend(p[7])
        if op(p[7][-1]) not in ('goto', 'if', 'return'):
            p[0].append([None, 'goto', label_end])
        p[0].append([None, 'deflabel', label_end])

# return文
def p_return_stat(p):
    'return_stat : RETURN expr SEMI'
    p[0], lastvar = merge_insts_list(p[2])
    if p[0] is None:
        p[0] = [[None, 'return', lastvar]]
    else:
        p[0].append([None, 'return', lastvar[0]])

# 式
def p_expr(p):
    'expr : equality_expr'
    # 式からコピー文を削除したものを返す。
    p[0] = shrink(p[1])

# 等号比較式
def p_equality_epxr(p):
    '''equality_expr : relational_expr
                     | equality_expr EQUALEQUAL relational_expr
                     | equality_expr EXCLAIMEQUAL relational_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0], last_vars = merge_insts_list(p[1], p[3])
        p[0].append([newvar(), p[2], last_vars[0], last_vars[1]])

def p_relational_expr(p):
    '''relational_expr : additive_expr
                       | relational_expr LESS additive_expr
                       | relational_expr LESSEQUAL additive_expr
                       | relational_expr MORE additive_expr
                       | relational_expr MOREEQUAL additive_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0], last_vars = merge_insts_list(p[1], p[3])
        p[0].append([newvar(), p[2], last_vars[0], last_vars[1]])

def p_additive_expr(p):
    '''additive_expr : multicative_expr
                     | additive_expr PLUS multicative_expr
                     | additive_expr MINUS multicative_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0], last_vars = merge_insts_list(p[1], p[3])
        p[0].append([newvar(), p[2], last_vars[0], last_vars[1]])

def p_multicative_expr(p):
    '''multicative_expr : unary_expr
                        | multicative_expr STAR unary_expr
                        | multicative_expr SLASH unary_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0], last_vars = merge_insts_list(p[1], p[3])
        p[0].append([newvar(), p[2], last_vars[0], last_vars[1]])

def p_unary_expr(p):
    '''unary_expr : postfix_expr
                  | MINUS unary_expr'''
    if len(p) == 2:
        p[0] = p[1]
    elif p[1] == '-':
        p[0], last_vars = merge_insts_list(p[2])
        p[0].append([newvar(), 'unary_minus', last_vars[0]])

def p_postfix_expr(p):
    '''postfix_expr : primary_expr
                    | ID LPAREN RPAREN
                    | ID LPAREN argument_expr_list RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = [[newvar(), 'call', ['id', p[1]], []]]
    elif len(p) == 5:
        p[0], last_vars = merge_insts_list(*p[3])
        p[0].append([newvar(), 'call', ['id', p[1]], *last_vars])

def p_argument_expr_list(p):
    '''argument_expr_list : equality_expr
                          | argument_expr_list COMMA equality_expr'''
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 4:
        p[0] = p[1] + [p[3]]
    
def p_primary_expr_id(p):
    'primary_expr : ID'
    p[0] = [[newvar(), '=', ['id', p[1]]]]

def p_primary_expr_number(p):
    'primary_expr : NUMBER'
    p[0] = [[newvar(), '=', ['num', p[1]]]]

def p_primary_expr_paren(p):
    'primary_expr : RPAREN expr LPAREN'
    p[0] = p[1]

def p_error(p):
    if p:
        print("Syntax error at token '{}' at line {}, pos {}"
              .format(p.value, p.lineno, p.lexpos))
    else:
        print('Syntax error at EOF')
        
# 入力された文字列を構文解析する。
# 解析した結果のプログラムデータを返す。
def parse(data, debug=False):
    global _func_symtable
    global _global_symtable
    global _program
    
    _global_symtable = SymbolTable('.global')

    # 関数スコープの識別子表名はfunc_defを還元しときに確定するので、
    # ここでは仮に.tempとしておく
    _func_symtable = SymbolTable('.temp')

    parser = yacc.yacc()
    _program = parser.parse(data, debug)
    if _program is not None:
        _program.symtable = _global_symtable
    
    # 使われなかった一時識別子表をゴミ集めの対象にする。
    _func_symtable = None
    
    return _program
