export class Expr {
    constructor(public children: Expr[], public type: string) {}

    toString() {
        return `${this.type}(${this.children.map((c) => c.toString()).join(', ')})`;
    }
}
export class Atom<T> extends Expr {
    constructor(public data: T, public token: moo.Token, type: string) {
        super([], type);
    }

    toString() {
        return `${this.token}`;
    }
}

export class Integer extends Atom<number> {
    constructor(tok: moo.Token) {
        super(parseInt(tok.text), tok, 'int');
    }
}

export class Name extends Atom<string> {
    name: string;
    constructor(public token: moo.Token) {
        super(token.text, token, 'name');
    }
}

export class Apply extends Expr {
    static unop([op, a]: [moo.Token, Expr]) {
        return new Apply(op.text, a);
    }
    static binop([a, op, b]: [Expr, moo.Token, Expr]) {
        return new Apply(op.text, a, b);
    }
    constructor(fun: string, ...args: Expr[]) {
        super(args, fun);
    }

    toString(): string {
        console.log('apply', this.type, this.children)
        if (this.type === '(')
            return `${this.children[0].toString()}(${this.children
                .slice(1)
                .map((c) => c.toString())
                .join(', ')})`;
        else if (this.type === '[')
            return `${this.children[0].toString()}[${this.children
                .slice(1)
                .map((c) => c.toString())
                .join(', ')}]`;
        else return super.toString();
    }
}
