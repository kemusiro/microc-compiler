# microc-compiler

実験用のミニ言語MicroCコンパイラです。MicroC言語のソースコードから、LLVMが対応している任意のターゲットCPUの実行ファイルを作成します。
以下の特徴を持ちます。

- LLVM IRのアセンブリコードを生成することにより、LLVMのバックエンドが持つ機能を活用できます。
- 字句解析処理と構文解析処理をPython Lex-Yacc(PLY)を使って自動生成しています。
- LLVM IRが前提とする静的単一代入(SSA)化を行うための計算処理を実装しており、コンパイラフロントエンドで行われている処理の基本を学習することができます。
- 全編Pythonで実装することにより、コンパイラ内部状態のインタラクティブな把握が可能です。

# 前提条件

- Python Lex-Yacc 3.11
- Python 3
- Clang/LLVM 11.0

# インストール

Ubuntu 20.04.1 LTS上でのインストール方法は以下の通りです。

## 1. Clang/LLVM

~~~shell
$ sudo apt update
$ sudo bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"
~~~



## 2. Python Lex-Yacc

~~~shell
# PLYの前提パッケージをインストールする。
$ sudo apt install python3-distutils

# PLYをダウンロードしてセットアップスクリプトを実行する。
$ mkdir work; cd work
$ wget http://www.dabeaz.com/ply/ply-3.11.tar.gz
$ tar zxvf ply-3.11.tar.gz
$ cd ply-3.11/
$ sudo python3 setup.py install
~~~

## 3. MicroCコンパイラ

適当なフォルダにgit cloneしてください。

~~~shell
$ git clone https://github.com/kemusiro/microc-compiler.git
~~~



# 使い方

MicroC言語のソースコードを作ります。たとえばフィボナッチ数を求めるプログラムは以下のようになります。プログラムのエントリポイントは`app_main`という名前にしてください。

~~~c
int fib(int n) {
    if (n == 0) {
        return 0;
    }
    else if (n == 1) {
        return 1;
    }
    else {
        return fib(n-1) + fib(n-2);
    }
}

int app_main(int n) {
    return fib(n);
}
~~~

ソースコードを以下によりコンパイルします。

```shell
$ python microc.py fib.mc
```

結果としてLLVM IRのファイル(`fib.ll`)とランタイムコードのファイル(`main-fib.c`)ができるので、これらをClangでコンパイルして実行ファイを作成します。

~~~shell
$ clang-11 fib.ll main-fib.c -o fib
$ ./fib 10
55
~~~

生成されたLLVM IRは以下となります。

```assembly
define i32 @fib(i32 %n.1) {
__entry:
    %0 = icmp eq i32 %n.1, 0
    br i1 %0, label %label3, label %label4
label3:
    br label %__end
label4:
    %1 = icmp eq i32 %n.1, 1
    br i1 %1, label %label0, label %label1
label0:
    br label %__end
label1:
    %2 = sub i32 %n.1, 1
    %3 = call i32 @fib (i32 %2)
    %4 = sub i32 %n.1, 2
    %5 = call i32 @fib (i32 %4)
    %6 = add i32 %3, %5
    br label %__end
__end:
    %.retval.5 = phi i32 [0, %label3], [1, %label0], [%6, %label1]
    ret i32 %.retval.5
}
define i32 @app_main(i32 %n.1) {
__entry:
    %0 = call i32 @fib (i32 %n.1)
    br label %__end
__end:
    ret i32 %0
}
```

また生成したLLVM IRの関数を実行するためのランタイムコードとして以下のコードが自動生成されます。コマンドライン引数の数は、`app_main`関数の引数の数と同じものになります。

```C
#include <stdio.h>
#include <stdlib.h>

extern int app_main(int arg1);

int main(int argc, char *argv[])
{
    int result;
    if (argc <= 1) {
        printf("%s arg1\n", argv[0]);
        return -1;
    }
    result = app_main(atoi(argv[1]));
    printf("%d\n", result);
    return 0;
}
```



# MicroC言語仕様概要

MicroC言語はC言語のサブセットである。以下の機能を持つ。

- 扱える型は32ビット符号付き整数型のみ
- 演算子は+, -, *, /, <, <=, >, >=, ==, !=, 単項マイナス。演算子の優先順位はC言語と同じ
- 文はif文、while文、return文、代入文、複文のみ。
- 関数の定義が可能
- 局所変数のスコープは関数全体(どこに書いても先頭に書いたときと同じ)
- コメントは//のみ。
- プログラムのエントリポイントはapp_main関数とする。
- 初期化付きの変数宣言は行えない。

# MicroC言語内部表現

## 記号表(SymbolTable)

記号表は`SymbolTable`クラスで管理する。`SymbolTable`は以下の要素を持つ。

- `scope` --  記号表の属するスコープ。現在関数とグローバルの2種類がある。関数スコープは関数名をスコープ名とし、グローバルスコープは`.global`をスコープ名とする。　
- `table` -- 記号名をキー、記号の属性を値としてもつ辞書である。属性も辞書構造であり、記号の種類ごとに任意の属性をもつことができる。

記号表のエントリの例を以下に示す。

`{'x': {'kind': 'localvar', 'type': 'int'}}`

対応している属性を以下に示す。

| 属性         | 意味                                           | とりうる属性値                                               |
| ------------ | ---------------------------------------------- | ------------------------------------------------------------ |
| `'kind'`     | 記号の種別。すべての記号がもつ必須属性とする。 | `'localvar'`(局所変数)、`'temp'`(コンパイラ内で生成した一時変数)、`'ssavar'`(SSA化した変数)、`'func'`(関数名)、`'param'`(関数の仮引数)、`'label'`(ラベル名) |
| `'type'`     | 変数の型、または関数の返却値型を表す。         | `'int'`、`'boolean'`                                         |
| `'bb'`       | 変数が属する基本ブロック                       | ラベル名                                                     |
| `'origin'`   | SSA化された変数の元になった変数名              | 変数名                                                       |
| `'llvmname'` | LLVM IR仕様に従った記号名                      | 変数名、関数名、ラベル名                                     |

記号表のエントリの一覧は`sym_enumerator()`ジェネレータにより任意の属性ごとに生成できる。複数の属性のいずれかを指定する場合はタプルを指定する。

```Python
# 'int'型の変数の一覧を印字する。
table = 処理中の関数スコープに属する記号表
for id in table.sym_enumerator(type='int'):
    print(id)

# すべての変数の一覧をリストで取得する。
variables = [id for id in table.sym_enumerator(kind=('localvar', 'param', 'temp'))]

# すべての記号をダンプする。
for sym in table.sym_enumerator():
    print(sym)
```



## 内部コード

### 表現

内部コードはいわゆる3アドレスコードの命令の列で表現する。つまり1つの演算子による計算結果を左辺の変数に代入するということを表現する。命令は以下の形式のリストである。

`[ID, op, arg1, arg2, ...]`

このリストの意味は"ID = op(arg1, arg2, ...)"である。

### 項(term)

項は以下のいずれかである。

#### 識別子 (ID)

`['id', 識別子名]`

#### 数値 (NUM)

`['num', 数値]`

#### ラベル (LABEL)

`['label', ラベル名]`

#### 型 (TYPE)

`['type', 型名]`

### 命令(instruction)

命令の一覧を以下に示す。

#### 記法

- a | b
aかbのいずれか
- (a)*
aの0回以上の繰り返し
- (a)+
aの1回以上の繰り返し
- 項名n
他の項と区別するために項の名前に添字をつけたもの。(例) ID1, NUM2など。

#### コピー文

`[ID2, '=', ID1|NUM1]`

ID2にID1またはNUM1の値を代入する。

#### 2項演算

`[ID3, 演算子, ID1|NUM1, ID2|NUM2]`

ID1またはNUM1とID2またはNUM2の演算結果をID3に代入する。

#### 単項演算

`[ID2, 演算子, ID1|NUM1]`

ID1またはNUM1の演算結果をID2に代入する。

#### 関数呼び出し

`[ID2, ’call', ID1 (ID|NUM)*]`

関数名ID1の関数を呼び出し返値をID2に代入する。関数の引数はIDまたはNUMを関数定義にしたがって並べる。

#### goto文

`[None, 'goto', LABEL]`

LABELに分岐する。

#### if文

`[None, 'if', ID|NUM, LABEL1, LABEL2]`

IDまたはNUMの値が1ならLABEL1に分岐し、0ならLABEL2に分岐する。

#### φ関数呼び出し

`[ID4, 'phi', ID1|NUM1, ID2|NUM2 (ID3|NUM3)*]`

2個以上のIDまたはNUMを合流させ、ID4で代表する。

#### ラベル文

`[None, 'deflabel', LABEL]`

現在の位置にラベルを定義する。

#### 局所変数宣言

`[ID, 'deflocal', TYPE]`

型TYPEの局所変数IDを定義する。

#### 関数パラメータ定義

`[ID, 'defparam', TYPE]`

関数のパラメータの定義が発生していることを明示する。

#### 関数定義

`[None, 'deffunc', ID1, TYPE, (ID)*]`

返値型がTYPEの関数名ID1の関数を定義する。仮引数のIDと0個以上指定する。


