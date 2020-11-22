# プログラムの全体構造を管理するクラス
class Program:
    def __init__(self):
        self.func_list = []
        self.symtable = None

# 関数の構造を管理するクラス
class Function:
    def __init__(self, name, ftype, params, entry, symtable, insts):
        self.program = None
        self.name = name
        self.ftype = ftype
        self.params = params
        self.symtable = symtable
        self.insts = insts
        self.entry = '__entry'
        self.end = '__end'
        self.bbtable = {}
        self.dom = {}
        self.idom = {}
        self.tree = {}
        self.df = {}
        # 何らかの処理を実行中のコンテキストを保存する。
        self.context = {}
        
        self.insts.insert(0, [None, 'deflabel', ['label', self.entry]])
        self.insts[1:1] = [[p[1], 'defparam', p[0]] for p in params]

class SymbolTable:
    def __init__(self, scope):
        self.scope = scope
        self.table = {}

    # 識別子表に新しい識別子を追加する。
    def add_sym(self, name, kind, attrs={}):
        self.table[name] = {'kind': kind}
        self.table[name].update(attrs)

    # 識別子表から識別子を削除する。
    def delete_sym(self, name):
        del self.table[name]
        
    # 識別子の持つ属性を取得する。
    def get_sym(self, name, attr=None):
        if self.table.get(name) is not None:
            if attr is not None:
                return self.table.get(name).get(attr)
            else:
                return self.table.get(name)
        return None
    
    # 識別子に属性を追加する。
    # 識別子が識別子表にない場合は何もしない。
    def set_sym(self, name, attrs):
        if self.table.get(name) is None:
            pass
        else:
            self.table[name].update(attrs)

    # 特定の属性値を持つ識別子を生成するジェネレータ
    def sym_enumerator(self, **kwargs):
        for name in self.table:
            entry = self.get_sym(name)
            match = True
            for attr, value in kwargs.items():
                # attr = 'kind', value = ('temp', 'ssavar'), entry = ID
                if type(value) is tuple:
                    if entry.get(attr) not in value:
                        match = False
                        break
                elif entry.get(attr) != value:
                    match = False
                    break
            if match:
                yield name
    
# 基本ブロックを表すクラス
class BasicBlock:
    def __init__(self, name):
        # 基本ブロック名
        self.name = name
        # 後続基本ブロック名のリスト
        self.succ = []
        # 先行基本ブロック名のリスト
        self.pred = []
        # 基本ブロックに含まれる命令のリスト
        self.insts = []

