@preprocessor esmodule
#@preprocessor typescript
@{%
import moo from "moo";
import { Apply, Integer, Name } from "./ast";

const lexer = moo.compile({
  WS:     /[ \t]+/u,
  int: /[0-9]+/u,
  word: /[\p{L}\p{N}_]+/u,
  punct: /[()\[\]:;,{}]/u,
  op: /[.*+-/%|&<>=!]+/u
});
let oldNext = lexer.next;
lexer.next = () => { 
    let t;// : moo.Token;
    for(t = oldNext.call(lexer); t?.type === 'WS'; t = oldNext.call(lexer))
        ;
    return t;
}
%}
@lexer lexer

main -> statement:? more_statement:* {% ([a,bs]) => [a, ...bs] %}
statement
    -> "rows" query:+ {% ([op,args]) => new Apply(op, ...args) %}
    |  "columns" query:+ {% ([op,args]) => new Apply(op, ...args) %}


query
    -> ("from"|"where") expr_list {% ([op,args]) => new Apply(op, ...args) %}

from_clause -> "from" expr_list {% id %}
more_statement -> ";" statement:? {% ([a,b]) => b %}
name -> %word {% ([a]) => new Name(a) %}

literal -> %int {% ([a]) => new Integer(a) %}

expr_list
    -> expr:?
    |  expr "," expr_list {% ([a,_,bs]) => [a, ...bs] %}

expr -> lambda_expr {% id %}

lambda_expr -> cond_expr {% id %}

cond_expr -> assign_expr {% id %}

assign_expr -> logic_expr {% id %}

logic_expr -> bit_expr {% id %}

bit_expr -> eq_expr {% id %}

eq_expr -> cmp_expr {% id %}

cmp_expr -> shift_expr {% id %}

shift_expr -> add_expr {% id %}

add_expr 
    -> mul_expr {% id %} 
    |  add_expr ("+"|"-") mul_expr {% Apply.binop %}

mul_expr 
    -> exp_expr {% id %} 
    |  mul_expr ("*"|"/"|"%"|"//") exp_expr {% Apply.binop %}

exp_expr
    -> unop_expr {% id %}
    |  unop_expr "**" exp_expr {% Apply.binop %}

unop_expr
    -> apply_expr {% id %}
    |  ("-"|"+"|"!") unop_expr {% Apply.unop %}

apply_expr 
    -> atom
    |  apply_expr "." name {% Apply.binop %}
    |  apply_expr "(" expr_list ")" {% ([fun,op,args,_3]) => new Apply(op.text, fun, ...args) %}
    |  apply_expr "[" expr_list "]" {% ([fun,op,args,_3]) => new Apply(op.text, fun, ...args) %}

atom
    -> literal {% id %}
    |  name {% id %}
    |  "(" expr ")" {% id %}
