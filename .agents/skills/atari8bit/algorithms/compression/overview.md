# Overview

## Quick-lookup

| Need | See § |
|---|---|
| RLE format (flag byte, literal/repeat runs) | §12.1 |
| RLE depacker (getb/putb, count = flag>>1 + 1) | §12.1 |
| LZ4 token/offset rules, no separate window | §12.2 |
| Exomizer bit stream, offset tables, backwards decrunch | §12.3 |
| DEFLATE/zlib — inflate 499 B code + 764 B data + 10 B ZP | §12.4 |
| Format trade-off table (code/size/speed/ratio) | §12.5 |
| Choosing a low-RAM compression model | §12.5 |
| Upkr ratio-first unpacking; ZX0/ZX2 faster alternatives | §12.6 |
