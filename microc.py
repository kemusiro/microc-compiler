import sys
import os
from analysis import irgen
from llvmgen import llvmgen

rt_template = r'''
#include <stdio.h>
#include <stdlib.h>

extern int app_main({1});

int main(int argc, char *argv[])
{{
    int result;
    if (argc <= {0}) {{
        printf("%s {2}\n", argv[0]);
        return -1;
    }}
    result = app_main({3});
    printf("%d\n", result);
    return 0;
}}
'''

# ランタイム用のmain関数を作成する。
def create_main(program):
    app_main = [f for f in program.func_list if f.name == 'app_main']
    if app_main == []:
        print("function app_main not found")
        return

    narg = len(app_main[0].params)
    extern_spec = ['int arg{}'.format(1+n) for n in range(narg)]
    usage_spec = ['arg{}'.format(1+n) for n in range(narg)]
    arg_spec = ['atoi(argv[{}])'.format(1+n) for n in range(narg)]

    return rt_template.format(narg,', '.join(extern_spec),
                              ' '.join(usage_spec), ', '.join(arg_spec))

if __name__ == '__main__':
    args = sys.argv
    if len(args) < 2:
        print('microc.py <source>')
    else:
        with open(args[1]) as f:
            source = f.read()
            
        program = irgen(source)
        if program is not None:
            result = llvmgen(program)

            dirname, filename = os.path.split(sys.argv[1])
            basename = os.path.splitext(filename)[0]
            with open('{}{}{}.ll'
                      .format(dirname, os.path.sep, basename), mode='w') as f:
                f.writelines('\n'.join(result))

            runtime_c = create_main(program)
            with open('{}{}main-{}.c'
                      .format(dirname, os.path.sep, basename), mode='w') as f:
                f.writelines(runtime_c)
