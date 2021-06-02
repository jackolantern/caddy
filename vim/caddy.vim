"if exists("b:current_syntax")
"    finish
"endif

let b:current_syntax = "caddy"

syn match caddy_number '\<[+-]\=\d\+'
syn match caddy_number '\<\zs[+-]\=\d\+\.\d*'

syn match caddy_define '\(^\s*\|{\s*\|,\_s*\)\zs[a-zA-Z_][a-zA-Z_0-9]*\s*\ze:'
syn match caddy_special '\[\|\]\|{\|}\|,\|:\|(\|)\|;'
syn match caddy_operator '+\|-\|/\|\*\|='
syn region caddy_string start='"' end='"'
syn region caddy_comment start="/\*" end="\*/"
syn keyword caddy_kw let in import function namespace true false this
syn keyword caddy_cond if then else


hi def link caddy_special        Special
hi def link caddy_operator       Operator
hi def link caddy_number         Number
hi def link caddy_string         String
hi def link caddy_comment        Comment
hi def link caddy_kw             Keyword
hi def link caddy_cond           Conditional
hi def link caddy_name           Tag


