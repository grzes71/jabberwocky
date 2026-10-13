# Overview

## Directives


 [.A8, .A16, .AI8, .AI16](#a8)<br>
 [.I8, .I16, .IA8, .IA16](#i8)<br>

 [.ASIZE](#asize)<br>
 [.ISIZE](#isize)<br>

 [.ALIGN N[,fill]](segments.md#align)

 [.ARRAY label [elements0][elements1][...] .type [= init_value]](../arrays.md#arrays)<br>
 [.ENDA, [.AEND]](../arrays.md#arrays)<br>

 [.DEF label [= expression]](symbols-vars.md#def)

 [.DEFINE macro_name expression](symbols-vars.md#define)<br>
 [.UNDEF macro_name](symbols-vars.md#undef)<br>

 [.ENUM label](../data-types.md#enumerations)<br>
 [.ENDE, [.EEND]](../data-types.md#enumerations)<br>

 [.ERROR [ERT] 'string'["string"] or .ERROR [ERT] expression](file-output.md#error)

 [.EXTRN label [,label2,...] type](../relocatable-code/external-symbols.md#external-symbols)

 [.IF [IFT] expression](conditionals-repeat.md#if_else)<br>
 [.ELSE [ELS]](conditionals-repeat.md#if_else)<br>
 [.ELSEIF [ELI] expression](conditionals-repeat.md#if_else)<br>
 [.ENDIF [EIF]](conditionals-repeat.md#if_else)<br>

 [.IFDEF label](conditionals-repeat.md#ifdef)<br>
 [.IFNDEF label](conditionals-repeat.md#ifndef)<br>

 [.LOCAL label](../local-areas.md#local-area)<br>
 [.ENDL, [.LEND]](../local-areas.md#local-area)<br>

 [.LONGA ON|OFF](../relocatable-code/65816-width-directives.md#directives-longa-and-longi)<br>
 [.LONGI ON|OFF](../relocatable-code/65816-width-directives.md#directives-longa-and-longi)<br>

 [.LINK 'filename'](../relocatable-code/linking.md#linking-link)

 [.MACRO label](../macros/overview.md#macros)<br>
 [.ENDM, [.MEND]](../macros/overview.md#macros)<br>
 [:[%%]parameter](../macros/overview.md#macros)<br>
 [.EXITM [.EXIT]](../macros/overview.md#macros)<br>

 [.NOWARN](#nowarn)

 [.PRINT [.ECHO] 'string1','string2'...,value1,value2,...](file-output.md#print)

 [.PAGES [expression]](segments.md#pages)<br>
 [.ENDPG, [.PGEND]](segments.md#pages)<br>

 [.PUBLIC, [.GLOBAL], [.GLOBL] label [,label2,...]](../relocatable-code/public-symbols.md#public-symbols)

 [.PROC label](../procedures/declaration.md#procedure-declaration)<br>
 [.ENDP, [.PEND]](../procedures/declaration.md#procedure-declaration)<br>
 [.REG, .VAR](../procedures/declaration.md#procedure-declaration)<br>

 [.REPT expression [,parameter1, parameter2, ...]](conditionals-repeat.md#rept)<br>
 [.ENDR, [.REND]](conditionals-repeat.md#rept)<br>
 [.R](conditionals-repeat.md#rept)<br>

 [.RELOC [.BYTE|.WORD]](../relocatable-code/reloc-block.md#relocatable-block-reloc)

 [.STRUCT label](../data-types.md#structures)<br>
 [.ENDS, [.SEND]](../data-types.md#structures)<br>

 [.SYMBOL label](#symbol)

 [.SEGDEF label address length [attrib] [bank]](segments.md#seg)<br>
 [.SEGMENT label](segments.md#seg)<br>
 [.ENDSEG](segments.md#seg)<br>

 [.USING, [.USE] proc_name, local_name](symbols-vars.md#using)

 [.VAR var1[=value],var2[=value]... (.BYTE|.WORD|.LONG|.DWORD)](symbols-vars.md#var)<br>
 [.ZPVAR var1, var2... (.BYTE|.WORD|.LONG|.DWORD)](symbols-vars.md#zpvar)<br>

 [.END](#end)

 [.EN](#en)

 [.BYTE](#byte)<br>
 [.WORD](#byte)<br>
 [.LONG](#byte)<br>
 [.DWORD](#byte)<br>

 [.OR](file-output.md#or_and)<br>
 [.AND](file-output.md#or_and)<br>
 [.XOR](file-output.md#or_and)<br>
 [.NOT](file-output.md#or_and)<br>

 [.LO (expression)](expression-helpers.md#lohi)<br>
 [.HI (expression)](expression-helpers.md#lohi)<br>

 [.DBYTE words](data-storage.md#dbyte)<br>
 [.DS expression](data-storage.md#_ds)<br>

 [.BY [+byte] bytes and/or ASCII](data-storage.md#_by)<br>
 [.WO words](data-storage.md#_wo)<br>
 [.HE hex bytes](data-storage.md#_he)<br>
 [.SB [+byte] bytes and/or ASCII](data-storage.md#_sb)<br>
 [.CB [+byte] bytes and/or ASCII](data-storage.md#_cb)<br>
 [.FL floating point numbers](data-storage.md#_fl)<br>

 [.ADR label](data-storage.md#adr)

 [.LEN label ['filename']](file-output.md#sizeof)<br>
 [.SIZEOF label](file-output.md#sizeof)<br>
 [.FILESIZE 'filename'](file-output.md#sizeof)<br>

 [.FILEEXISTS 'filename'](file-output.md#fileexists)<br>

 [.GET [index] 'filename'["filename"][*][+-value][,+-ofset[,length]]](file-output.md#get)<br>
 [.WGET [index]](file-output.md#get)<br>
 [.LGET [index]](file-output.md#get)<br>
 [.DGET [index]](file-output.md#get)<br>
 [.PUT [index] = value](file-output.md#put)<br>
 [.SAV [index] ['filename',] length](file-output.md#sav)<br>


<a name="symbol"></a>


## Legacy Index Anchors

<a name="a8"></a>
<a name="i8"></a>
<a name="asize"></a>
<a name="isize"></a>
<a name="nowarn"></a>
<a name="symbol"></a>
<a name="end"></a>
<a name="en"></a>
<a name="byte"></a>
