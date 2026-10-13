# Overview

## Macros

Macros make it easier for us to perform repetitive tasks by automating them. They exist only in the assembler's memory and are assembled only at the time of invocation. With their help, **MADS** can push and pull parameters for procedures declared with the `.PROC` directive onto/from the software stack, and switch extended memory banks in *BANK SENSITIVE* mode (`OPT B+`).

> _Macros are read only in the first assembly pass, so a macro defined in a file that is included with `ICL` from inside a macro body is not recognized (a top-level `ICL` of a macro file works)_:

```
 .macro test
   icl 'additional_macros.mac'
 .endm
```
