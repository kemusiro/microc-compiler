import ply.lex as lex

# 予約語のリスト
reserved = {
    'if' :'IF',
    'else' : 'ELSE',
    'while' : 'WHILE',
    'return' : 'RETURN',
    'int' : 'INT'
}

# トークン名のリスト
tokens = [
    'PLUS', 'MINUS', 'STAR', 'SLASH',
    'MORE', 'MOREEQUAL', 'LESS', 'LESSEQUAL', 'EQUALEQUAL', 'EXCLAIMEQUAL',
    'EQUAL', 'COMMA', 'SEMI',
    'LPAREN', 'RPAREN','LBRACE', 'RBRACE',
    'NUMBER', 'ID',
]

# 予約語とトークン名をマージする。
tokens = tokens + list(reserved.values())

# トークンの正規表現ルール
t_PLUS = r'\+'
t_MINUS = r'-'
t_STAR = r'\*'
t_SLASH = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'{'
t_RBRACE = r'}'
t_SEMI = r';'
t_EQUAL = r'='
t_COMMA = r','
t_EQUALEQUAL = r'=='
t_LESS = r'<'
t_LESSEQUAL = r'<='
t_MORE = r'>'
t_MOREEQUAL = r'>='
t_EXCLAIMEQUAL = r'!='
t_NUMBER = r'\d+'

# アクションを含む正規表現規則

# 識別子
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

# コメント
# 何も返さないトークン定義は読み飛ばすことを意味する。
def t_COMMENT(t):
    r'//.*'
    pass

# 改行を処理するルール
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# 読み飛ばす文字の定義    
t_ignore = ' \t'

# エラー発生時の処理の定義
def t_error(t):
    print("Illegal character {}"
          .format(t.value[0]))
    t.lexer.skip(1)

# 字句解析器の構築
lexer = lex.lex(debug=False)

# 字句解析器のテスト用コード
if __name__ == '__main__':
    data = '''
    int foo(int x, int y) {return x + y;}
    '''
    lexer.input(data)
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)
