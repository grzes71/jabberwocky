# MADS Directives

Router for MADS dot directives.

Load only the focused file that matches the task.

- [overview.md](directives/overview.md) - original overview and command index
- [symbols-vars.md](directives/symbols-vars.md) - .SYMBOL label, .VAR var1[=value1],var2[=value2]... (.BYTE|.WORD|.LONG|.DWORD) [=address], .ZPVAR var1, var2... (.BYTE|.WORD|.LONG|.DWORD) [=address], .DEF label [= expression], .DEFINE macro_name expression, .UNDEF macro_name, .USING, [.USE]
- [data-storage.md](directives/data-storage.md) - .END, .BYTE, .WORD, .LONG, .DWORD, .DBYTE, .DS expression, .ADR label, .BY/.WO/.HE/.SB/.CB/.FL, .EN
- [conditionals-repeat.md](directives/conditionals-repeat.md) - .REPT expression [,parameter1, parameter2, ...], .ENDR [.REND], .R, .IFDEF label, .IFNDEF label, .IF/.ELSE/.ELSEIF/.ENDIF
- [file-output.md](directives/file-output.md) - .PRINT [.ECHO], .ERROR [ERT] 'string'["string"] | .ERROR [ERT] expression, .LEN label ['filename'], .SIZEOF label, .FILESIZE 'filename', .FILEEXISTS 'filename', .GET [index] 'filename', .WGET [index], .LGET [index], .DGET [index], .PUT [index] = value, .SAV [index] ['filename',] length
- [segments.md](directives/segments.md) - .ALIGN N [,fill], .PAGES [expression], .SEGDEF label address length [attrib] [bank], .SEGMENT label, .ENDSEG
- [expression-helpers.md](directives/expression-helpers.md) - .OR, .AND, .XOR, .NOT, .LO (expression), .HI (expression)
- [misc.md](directives/misc.md) - .NOWARN
